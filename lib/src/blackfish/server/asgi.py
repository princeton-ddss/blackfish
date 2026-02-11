from __future__ import annotations

import configparser
import os
from os import urandom
import json
import aiohttp
from aiohttp.typedefs import StrOrURL
import requests
from datetime import datetime
from dataclasses import dataclass
from collections.abc import AsyncGenerator
from typing import Optional, Tuple, Any, Type, Annotated
import asyncio
from pathlib import Path
import bcrypt
from importlib import import_module
from uuid import UUID
from PIL import Image, UnidentifiedImageError
from io import BytesIO

from fabric.connection import Connection
from paramiko.sftp_client import SFTPClient
from pydantic import BaseModel, AfterValidator, ConfigDict

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError, NoResultFound, StatementError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Result

from litestar import Litestar, Request, get, post, put, delete
from litestar.utils.module_loader import module_to_os_path
from litestar.datastructures import State, UploadFile
from advanced_alchemy.extensions.litestar import (
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
    AlembicAsyncConfig,
)
from advanced_alchemy.base import UUIDAuditBase
from advanced_alchemy.extensions.litestar.plugins.init.config.engine import EngineConfig
from litestar.exceptions import (
    ClientException,
    NotFoundException,
    NotAuthorizedException,
    InternalServerException,
    HTTPException,
    ValidationException,
)
from litestar.status_codes import HTTP_409_CONFLICT, HTTP_404_NOT_FOUND
from litestar.config.cors import CORSConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.static_files import create_static_files_router
from litestar.template.config import TemplateConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template, Redirect, Stream, Response
from litestar.connection import ASGIConnection
from litestar.handlers.base import BaseRouteHandler
from litestar.response.redirect import ASGIRedirectResponse
from litestar.types import ASGIApp, Scope, Receive, Send
from litestar.datastructures.secret_values import SecretString
from litestar.middleware.base import MiddlewareProtocol
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.response import File
from litestar.enums import RequestEncodingType
from litestar.params import Body

from blackfish.server.logger import logger
from blackfish.server import services
from blackfish.server.files import (
    FileUploadResponse,
    try_write_file,
    try_delete_file,
    try_read_file,
    validate_file_exists,
    validate_file_extension,
    validate_file_size,
)
from blackfish.server import sftp
from blackfish.server.services.base import Service, ServiceLaunchError, ServiceStatus
from blackfish.server.services.speech_recognition import SpeechRecognitionConfig
from blackfish.server.services.text_generation import TextGenerationConfig
from blackfish.server.jobs.base import (
    BatchJob,
    BatchJobStatus,
    create_tigerflow_client,
    create_tigerflow_client_for_profile,
)
from blackfish.server.config import config as blackfish_config
from blackfish.server.utils import find_port
from blackfish.server.models.profile import (
    deserialize_profiles,
    deserialize_profile,
    SlurmProfile,
    LocalProfile,
    BlackfishProfile as Profile,
)
from blackfish.server.jobs.client import (
    TigerFlowClient,
    TigerFlowError,
    SSHRunner,
    LocalRunner,
)
from blackfish.server.setup import ProfileManager, ProfileSetupError
from blackfish.server.models.model import Model
from blackfish.server.job import JobConfig, JobScheduler, SlurmJobConfig
from blackfish.server.cluster import ClusterQueryError, SlurmClusterInfo
from blackfish.server.browser import RemoteFileBrowserSession

import importlib.metadata

logger.info(f"Starting Blackfish version: {importlib.metadata.version('blackfish-ai')}")


def load_service_classes() -> dict[str, Type[Service]]:
    service_classes: dict[str, Type[Service]] = {}
    directory = Path(services.__path__[0])
    for file in directory.glob("*.py"):
        if not file.stem.startswith("_") and not file.stem == "base":
            module = import_module(f"blackfish.server.{directory.stem}.{file.stem}")
            for k, v in module.__dict__.items():
                if isinstance(v, type) and v.__bases__[0] == Service:
                    service_classes[file.stem] = v
                    logger.debug(f"Added class {k} to service class dictionary.")

    return service_classes


service_classes = load_service_classes()


ContainerConfig = TextGenerationConfig | SpeechRecognitionConfig



# --- Auth ---
AUTH_TOKEN: Optional[bytes] = None
if blackfish_config.AUTH_TOKEN is not None:
    AUTH_TOKEN = bcrypt.hashpw(blackfish_config.AUTH_TOKEN.encode(), bcrypt.gensalt())
else:
    logger.warning("AUTH_TOKEN is not set. Blackfish API endpoints are unprotected.")


class AuthMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__()
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if Request(scope).session is None:
            logger.debug(
                "(AuthMiddleware) No session found. Redirecting to dashboard login."
            )
            response = ASGIRedirectResponse(path=f"{blackfish_config.BASE_PATH}/login")
            await response(scope, receive, send)
        elif Request(scope).session.get("token") is None:
            logger.debug(
                "(AuthMiddleware) No token found. Redirecting to dashboard login."
            )
            response = ASGIRedirectResponse(path=f"{blackfish_config.BASE_PATH}/login")
            await response(scope, receive, send)
        else:
            logger.debug(
                "(AuthMiddleware) Found session token!"
            )  # Request(scope).session
            await self.app(scope, receive, send)


def auth_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:  # type: ignore
    if AUTH_TOKEN is None:
        logger.error("AUTH_TOKEN is not set. Cannot authenticate user.")
        raise InternalServerException(detail="Authentication token is not set.")
    token = connection.session.get("token")
    if token is None:
        logger.debug("Session token is None. Raising NotAuthorizedException.")
        raise NotAuthorizedException
    if not bcrypt.checkpw(token.encode(), AUTH_TOKEN):
        logger.debug("Invalid token provided. Raising NotAuthorizedException.")
        raise NotAuthorizedException


PAGE_MIDDLEWARE = [] if blackfish_config.DEBUG else [AuthMiddleware]
ENDPOINT_GUARDS = [] if blackfish_config.DEBUG else [auth_guard]
if not blackfish_config.DEBUG:
    logger.info(
        f"Blackfish API is protected with AUTH_TOKEN = {blackfish_config.AUTH_TOKEN}"
    )
else:
    logger.warning(
        """Blackfish is running in debug mode. API endpoints are unprotected. In a production
          environment, set BLACKFISH_DEBUG=0 to require user authentication."""
    )


# --- Utils ---
async def get_batch_job(job_id: str, session: AsyncSession) -> BatchJob | None:
    """Query a single batch job ID from the application database and return `None`
    if the service is missing or the query fails.
    """
    try:
        query = sa.select(BatchJob).where(BatchJob.id == job_id)
        res = await session.execute(query)
    except StatementError:
        logger.error(f"{job_id} is not a valid UUID.")
        return None
    try:
        return res.scalar_one()
    except NoResultFound:
        logger.error(f"Batch job {job_id} not found.")
        return None


ModelInfoResult = dict[str, str]


def _get_validated_slurm_profile(profile_name: str) -> SlurmProfile:
    """Get and validate a profile for remote SFTP operations.

    Args:
        profile_name: Name of the profile to lookup

    Returns:
        Validated SlurmProfile

    Raises:
        NotFoundException: If profile doesn't exist
        ValidationException: If profile is not a remote SlurmProfile
    """
    try:
        profile = deserialize_profile(blackfish_config.HOME_DIR, profile_name)
    except FileNotFoundError:
        raise NotFoundException(f"Profile configuration not found: {profile_name}")

    if profile is None:
        raise NotFoundException(f"Profile '{profile_name}' not found")

    if not isinstance(profile, SlurmProfile) or profile.is_local():
        raise ValidationException(f"Profile '{profile_name}' is not a remote profile")

    return profile


def model_info(profile: Profile) -> Tuple[ModelInfoResult, ModelInfoResult]:
    if not profile.is_local():
        logger.error("Profile should be local.")
        raise Exception("Profile should be local.")

    cache_dir = Path(*[profile.cache_dir, "models", "info.json"])
    try:
        with open(cache_dir, "r") as f:
            cache_info = json.load(f)
    except OSError as e:
        logger.error(f"Failed to open cache info.json: {e}.")
        cache_info = dict()
    home_dir = Path(*[profile.home_dir, "models", "info.json"])
    try:
        with open(home_dir, "r") as f:
            home_info = json.load(f)
    except OSError as e:
        logger.error(f"Failed to open home info.json: {e}.")
        home_info = dict()
    return cache_info, home_info


def remote_model_info(
    profile: Profile, sftp: SFTPClient
) -> Tuple[ModelInfoResult, ModelInfoResult]:
    if not isinstance(profile, SlurmProfile):
        raise Exception("Profile should be a SlurmProfile.")

    cache_dir = os.path.join(profile.cache_dir, "models", "info.json")
    try:
        with sftp.open(cache_dir, "r") as f:
            cache_info = json.load(f)
    except Exception as e:
        logger.error(f"Failed to open remote cache info.json: {e}")
        cache_info = dict()
    home_dir = os.path.join(profile.home_dir, "models", "info.json")
    try:
        with sftp.open(home_dir, "r") as f:
            home_info = json.load(f)
    except Exception as e:
        logger.error(f"Failed to open remote home info.json: {e}")
        home_info = dict()
    return cache_info, home_info


async def find_models(profile: Profile) -> list[Model]:
    """Find all model revisions associated with a given profile.

    The model files associated with a given profile are determined by the contents
    found in `profile.home_dir` and `profile.cache_dir`. We assume that model files
    are stored using the same schema as Hugging Face.
    """
    models = []
    revisions = []
    if isinstance(profile, SlurmProfile) and not profile.is_local():
        logger.debug(f"Connecting to sftp::{profile.user}@{profile.host}")
        with (
            Connection(host=profile.host, user=profile.user) as conn,
            conn.sftp() as sftp,
        ):
            cache_info, home_info = remote_model_info(profile, sftp=sftp)
            cache_dir = os.path.join(profile.cache_dir, "models")
            logger.debug(f"Searching cache directory {cache_dir}")
            try:
                model_dirs = sftp.listdir(cache_dir)
                for model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                    _, namespace, model = model_dir.split("--")
                    repo = f"{namespace}/{model}"
                    logger.debug(f"Found model {repo}")
                    image = cache_info.get(repo)
                    if image is None:
                        logger.warning(
                            f"No image info found for model {repo} in {cache_dir}!"
                        )
                        image = "missing"
                    for revision in sftp.listdir(
                        os.path.join(cache_dir, model_dir, "snapshots")
                    ):
                        if revision not in revisions:
                            logger.debug(f"Found revision {revision}")
                            models.append(
                                Model(
                                    repo=repo,
                                    profile=profile.name,
                                    revision=revision,
                                    image=image,
                                    model_dir=os.path.join(cache_dir, model_dir),
                                )
                            )
                            revisions.append(revision)
            except FileNotFoundError as e:
                logger.error(f"Failed to list directory: {e}")

            home_dir = os.path.join(profile.home_dir, "models")
            logger.debug(f"Searching home directory: {home_dir}")
            try:
                model_dirs = sftp.listdir(home_dir)
                for model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                    _, namespace, model = model_dir.split("--")
                    repo = f"{namespace}/{model}"
                    logger.debug("Found model {repo}")
                    image = home_info.get(repo)
                    if image is None:
                        logger.warning(
                            f"No image info found for model {repo} in {home_dir}!"
                        )
                        image = "missing"
                    for revision in sftp.listdir(
                        os.path.join(home_dir, model_dir, "snapshots")
                    ):
                        if revision not in revisions:
                            logger.debug(f"Found revision {revision}")
                            models.append(
                                Model(
                                    repo=repo,
                                    profile=profile.name,
                                    revision=revision,
                                    image=image,
                                    model_dir=os.path.join(home_dir, model_dir),
                                )
                            )
                            revisions.append(revision)
            except FileNotFoundError as e:
                logger.error(f"Failed to list directory: {e}")
            return models
    else:
        cache_info, home_info = model_info(profile)
        cache_dir = os.path.join(profile.cache_dir, "models")
        logger.debug(f"Searching cache directory {cache_dir}")
        try:
            model_dirs = os.listdir(cache_dir)
            for model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                _, namespace, model = model_dir.split("--")
                repo = f"{namespace}/{model}"
                logger.debug(f"Found model {repo}")
                image = cache_info.get(repo)
                if image is None:
                    logger.warning(
                        f"No image info found for model {repo} in {cache_dir}!"
                    )
                    image = "missing"
                for revision in os.listdir(
                    os.path.join(cache_dir, model_dir, "snapshots")
                ):
                    if revision not in revisions:
                        logger.debug(f"Found revision {revision}")
                        models.append(
                            Model(
                                repo=repo,
                                profile=profile.name,
                                revision=revision,
                                image=image,
                                model_dir=os.path.join(cache_dir, model_dir),
                            )
                        )
                        revisions.append(revision)
        except FileNotFoundError as e:
            logger.error(f"Failed to list directory: {e}")

        home_dir = os.path.join(profile.home_dir, "models")
        logger.debug(f"Searching home directory: {home_dir}")
        try:
            model_dirs = os.listdir(home_dir)
            for model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                _, namespace, model = model_dir.split("--")
                repo = f"{namespace}/{model}"
                logger.debug(f"Found model {repo}")
                image = home_info.get(repo)
                if image is None:
                    logger.warning(
                        f"No image info found for model {repo} in {home_dir}!"
                    )
                    image = "missing"
                for revision in os.listdir(
                    os.path.join(home_dir, model_dir, "snapshots")
                ):
                    if revision not in revisions:
                        logger.debug(f"Found revision {revision}")
                        models.append(
                            Model(
                                repo=repo,
                                profile=profile.name,
                                revision=revision,
                                image=image,
                                model_dir=os.path.join(home_dir, model_dir),
                            )
                        )
                        revisions.append(revision)
        except FileNotFoundError as e:
            logger.error(f"Failed to list directory: {e}")
        return list(models)


# --- Pages ---
@get("/", middleware=PAGE_MIDDLEWARE)
async def index() -> Redirect:
    return Redirect(f"{blackfish_config.BASE_PATH}/dashboard")


@get(path="/dashboard", middleware=PAGE_MIDDLEWARE)
async def dashboard() -> Template:
    return Template(template_name="index.html")


@get(path="/login")
async def dashboard_login(request: Request) -> Template | Redirect:  # type: ignore
    if AUTH_TOKEN is None:
        logger.error("AUTH_TOKEN is not set. Redirecting to dashboard.")
        return Redirect(f"{blackfish_config.BASE_PATH}/dashboard")
    token = request.session.get("token")
    if token is not None:
        if bcrypt.checkpw(token.encode(), AUTH_TOKEN):
            logger.debug("User authenticated. Redirecting to dashboard.")
            return Redirect(f"{blackfish_config.BASE_PATH}/dashboard")

    logger.debug("User not authenticated. Returning login page.")
    return Template(template_name="index.html")


@get(path="/text-generation", middleware=PAGE_MIDDLEWARE)
async def text_generation() -> Template:
    return Template(template_name="index.html")


@get(path="/speech-recognition", middleware=PAGE_MIDDLEWARE)
async def speech_recognition() -> Template:
    return Template(template_name="index.html")


@get(path="/file-manager", middleware=PAGE_MIDDLEWARE)
async def file_manager() -> Template:
    return Template(template_name="file-manager.html")


# --- Endpoints ---
@get("/api/info", guards=ENDPOINT_GUARDS)
async def info(state: State) -> dict[str, Any]:
    return {
        "HOST": state.HOST,
        "PORT": state.PORT,
        "STATIC_DIR": state.STATIC_DIR,
        "HOME_DIR": state.HOME_DIR,
        "DEBUG": state.DEBUG,
        "CONTAINER_PROVIDER": state.CONTAINER_PROVIDER,
    }


@post("/api/login")
async def login(token: SecretString | None, request: Request) -> Optional[Redirect]:  # type: ignore
    if AUTH_TOKEN is None:
        logger.error("AUTH_TOKEN is not set. Cannot authenticate user.")
        raise InternalServerException(detail="Authentication token is not set.")
    session_token = request.session.get("token")
    if session_token is not None:
        if bcrypt.checkpw(session_token.encode(), AUTH_TOKEN):
            logger.debug("User logged in with session token. Redirecting to dashboard.")
            return Redirect(f"{blackfish_config.BASE_PATH}/dashboard")
    if token is not None:
        if bcrypt.checkpw(token.get_secret().encode(), AUTH_TOKEN):
            logger.debug(
                "Authentication token verified. Adding token to session and redirecting to dashboard."
            )
            request.set_session({"token": token.get_secret()})
            return Redirect(f"{blackfish_config.BASE_PATH}/dashboard")
        else:
            logger.debug("Invalid token provided. Redirecting to login.")
            return Redirect(f"{blackfish_config.BASE_PATH}/login?success=false")
    else:
        logger.debug("No token provided. Redirecting to login.")
        return Redirect(f"{blackfish_config.BASE_PATH}/login?success=false")


@post("/api/logout", guards=ENDPOINT_GUARDS)
async def logout(request: Request) -> Redirect:  # type: ignore
    token = request.session.get("token")
    if token is not None:
        request.set_session({"token": None})
        logger.debug("from logout: reset session.")
    return Redirect(f"{blackfish_config.BASE_PATH}/login")


@dataclass
class FileStats:
    name: str
    path: str
    is_dir: bool
    size: int  # bytes
    created_at: datetime
    modified_at: datetime


def listdir(path: str, hidden: bool = False) -> list[FileStats]:
    scan_iter = os.scandir(path)
    if not hidden:
        items = list(filter(lambda x: not x.name.startswith("."), scan_iter))
    else:
        items = list(scan_iter)
    return [
        FileStats(
            name=item.name,
            path=item.path,
            is_dir=item.is_dir(),
            size=item.stat().st_size,
            created_at=datetime.fromtimestamp(item.stat().st_ctime),
            modified_at=datetime.fromtimestamp(item.stat().st_mtime),
        )
        for item in items
    ]


@get("/api/files", guards=ENDPOINT_GUARDS)
async def get_files(
    path: str = "~",
    hidden: bool = False,
) -> dict[str, Any] | HTTPException:
    resolved_path = os.path.expanduser(path)
    if os.path.isdir(resolved_path):
        try:
            return {
                "path": resolved_path,
                "files": listdir(resolved_path, hidden=hidden),
            }
        except PermissionError:
            logger.debug("Permission error raised")
            raise NotAuthorizedException(
                f"User not authorized to access {resolved_path}"
            )
    else:
        logger.debug("Not found error")
        raise NotFoundException(detail=f"Path {resolved_path} does not exist.")


IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"]
TEXT_EXTENSIONS = [".txt", ".md", ".json", ".csv", ".xml", ".yaml", ".yml", ".log"]
AUDIO_EXTENSIONS = [".wav", ".mp3"]

# Mapping of task/image types to compatible pipeline tags
# e.g., text-generation services can also run image-text-to-text models (VLMs)
# See: https://docs.vllm.ai/en/latest/models/supported_models.html
COMPATIBLE_PIPELINES: dict[str, list[str]] = {
    "text-generation": [
        "text-generation",
        "image-text-to-text",
        "audio-text-to-text",
        "video-text-to-text",
        "image-to-text",
    ],
}


def has_image_extension(path: str) -> str:
    validate_file_extension(Path(path), IMAGE_EXTENSIONS)
    return path


def has_text_extension(path: str) -> str:
    validate_file_extension(Path(path), TEXT_EXTENSIONS)
    return path


def has_audio_extension(path: str) -> str:
    validate_file_extension(Path(path), AUDIO_EXTENSIONS)
    return path


class ImageUploadRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Annotated[str, AfterValidator(has_image_extension)]
    file: UploadFile


@post("/api/image", guards=ENDPOINT_GUARDS)
async def upload_image(
    data: Annotated[
        ImageUploadRequest, Body(media_type=RequestEncodingType.MULTI_PART)
    ],
    state: State,
    profile: Optional[str] = None,
) -> FileUploadResponse:
    """Upload an image file to a specified location."""

    content = await data.file.read()

    validate_file_size(content, state.MAX_FILE_SIZE)

    try:
        img = Image.open(BytesIO(content))
        img.verify()
    except UnidentifiedImageError as e:
        raise ValidationException(f"Pillow detected invalid image data: {e}")

    if profile is not None:
        remote_profile = _get_validated_slurm_profile(profile)
        logger.debug(f"Uploading image to remote profile {profile}: {data.path}")
        response = sftp.write_file(remote_profile, data.path, content, update=False)
        return FileUploadResponse(
            filename=response.filename,
            size=response.size,
            created_at=response.created_at,
        )

    path = Path(data.path)
    logger.debug(f"Attempting to upload image {data.file.filename} to {path}")

    if path.exists():
        raise ValidationException(f"The requested path ({path}) already exists")

    return try_write_file(path, content)


@get("/api/image", guards=ENDPOINT_GUARDS)
async def get_image(path: str, profile: Optional[str] = None) -> File | Stream:
    """Retrieve an image file from the specified path."""

    if profile is not None:
        validate_file_extension(Path(path), IMAGE_EXTENSIONS)
        remote_profile = _get_validated_slurm_profile(profile)
        logger.debug(f"Streaming image from remote profile {profile}: {path}")

        # Get file size and streaming generator
        file_size, chunk_generator = sftp.stream_file(remote_profile, path)

        try:
            # Determine content type from extension
            ext = os.path.splitext(path)[1].lower()
            content_type = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".bmp": "image/bmp",
                ".tiff": "image/tiff",
                ".webp": "image/webp",
            }.get(ext, "application/octet-stream")

            return Stream(
                chunk_generator,
                media_type=content_type,
                headers={
                    "Content-Length": str(file_size),
                    "Content-Disposition": f'attachment; filename="{os.path.basename(path)}"',
                },
            )
        except Exception:
            chunk_generator.close()
            raise

    file_path = Path(path)

    logger.debug(f"Attempting to retrieve image from {file_path}")

    validate_file_exists(file_path)
    validate_file_extension(file_path, IMAGE_EXTENSIONS)

    try:
        img = Image.open(file_path)
        img.verify()
    except Exception as e:
        raise ValidationException(f"Invalid image file: {e}")

    return try_read_file(file_path)


@put("/api/image", guards=ENDPOINT_GUARDS)
async def update_image(
    data: Annotated[
        ImageUploadRequest, Body(media_type=RequestEncodingType.MULTI_PART)
    ],
    state: State,
    profile: Optional[str] = None,
) -> FileUploadResponse:
    """Update/replace an existing image file at the specified path."""

    content = await data.file.read()

    validate_file_extension(Path(data.path), IMAGE_EXTENSIONS)
    validate_file_size(content, state.MAX_FILE_SIZE)

    try:
        img = Image.open(BytesIO(content))
        img.verify()
    except Exception as e:
        raise ValidationException(f"Pillow detected invalid image data: {e}")

    if profile is not None:
        remote_profile = _get_validated_slurm_profile(profile)
        logger.debug(f"Updating image on remote profile {profile}: {data.path}")
        response = sftp.write_file(remote_profile, data.path, content, update=True)
        return FileUploadResponse(
            filename=response.filename,
            size=response.size,
            created_at=response.created_at,
        )

    path = Path(data.path)
    logger.debug(f"Attempting to update image {data.file.filename} at {path}")

    validate_file_exists(path)

    return try_write_file(path, content, update=True)


@delete("/api/image", guards=ENDPOINT_GUARDS, status_code=200)
async def delete_image(path: str, profile: Optional[str] = None) -> Path | str:
    """Delete an image file at the specified path."""

    # Remote delete
    if profile is not None:
        validate_file_extension(Path(path), IMAGE_EXTENSIONS)
        remote_profile = _get_validated_slurm_profile(profile)
        logger.debug(f"Deleting image on remote profile {profile}: {path}")
        return sftp.delete_file(remote_profile, path)

    # Local delete
    file_path = Path(path)

    logger.debug(f"Attempting to delete image at {file_path}")

    validate_file_exists(file_path)
    validate_file_extension(file_path, IMAGE_EXTENSIONS)

    return try_delete_file(file_path)


class TextUploadRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Annotated[str, AfterValidator(has_text_extension)]
    file: UploadFile


@post("/api/text", guards=ENDPOINT_GUARDS)
async def upload_text(
    data: Annotated[TextUploadRequest, Body(media_type=RequestEncodingType.MULTI_PART)],
    state: State,
    profile: Optional[str] = None,
) -> FileUploadResponse:
    """Upload a text file to a specified location."""

    content = await data.file.read()

    validate_file_size(content, state.MAX_FILE_SIZE)

    # Text-specific validation
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValidationException(f"File contains invalid UTF-8 text data: {e}")

    if profile is not None:
        remote_profile = _get_validated_slurm_profile(profile)
        logger.debug(f"Uploading text file to remote profile {profile}: {data.path}")
        response = sftp.write_file(remote_profile, data.path, content, update=False)
        return FileUploadResponse(
            filename=response.filename,
            size=response.size,
            created_at=response.created_at,
        )

    path = Path(data.path)
    logger.debug(f"Attempting to upload text file {data.file.filename} to {path}")

    if path.exists():
        raise ValidationException(f"The requested path ({path}) already exists")

    return try_write_file(path, content)


@get("/api/text", guards=ENDPOINT_GUARDS)
async def get_text(path: str, profile: Optional[str] = None) -> File | Response[bytes]:
    """Retrieve a text file from the specified path."""

    if profile is not None:
        validate_file_extension(Path(path), TEXT_EXTENSIONS)
        remote_profile = _get_validated_slurm_profile(profile)
        logger.debug(f"Downloading text file from remote profile {profile}: {path}")
        content = sftp.read_file(remote_profile, path)

        try:
            content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValidationException(f"Invalid text file: {e}")

        # Determine content type from extension
        ext = os.path.splitext(path)[1].lower()
        content_type = {
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".json": "application/json",
            ".csv": "text/csv",
            ".xml": "application/xml",
            ".yaml": "application/yaml",
            ".yml": "application/yaml",
            ".log": "text/plain",
        }.get(ext, "text/plain")

        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'
            },
        )

    file_path = Path(path)

    logger.debug(f"Attempting to retrieve text file from {file_path}")

    validate_file_exists(file_path)
    validate_file_extension(file_path, TEXT_EXTENSIONS)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.read()
    except UnicodeDecodeError as e:
        raise ValidationException(f"Invalid text file: {e}")

    return try_read_file(file_path)


@put("/api/text", guards=ENDPOINT_GUARDS)
async def update_text(
    data: Annotated[TextUploadRequest, Body(media_type=RequestEncodingType.MULTI_PART)],
    state: State,
    profile: Optional[str] = None,
) -> FileUploadResponse:
    """Update/replace an existing text file at the specified path."""

    content = await data.file.read()

    validate_file_extension(Path(data.path), TEXT_EXTENSIONS)
    validate_file_size(content, state.MAX_FILE_SIZE)

    try:
        content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValidationException(f"File contains invalid UTF-8 text data: {e}")

    if profile is not None:
        remote_profile = _get_validated_slurm_profile(profile)
        logger.debug(f"Updating text file on remote profile {profile}: {data.path}")
        response = sftp.write_file(remote_profile, data.path, content, update=True)
        return FileUploadResponse(
            filename=response.filename,
            size=response.size,
            created_at=response.created_at,
        )

    path = Path(data.path)
    logger.debug(f"Attempting to update text file {data.file.filename} at {path}")

    validate_file_exists(path)

    return try_write_file(path, content, update=True)


@delete("/api/text", guards=ENDPOINT_GUARDS, status_code=200)
async def delete_text(path: str, profile: Optional[str] = None) -> Path | str:
    """Delete a text file at the specified path."""

    if profile is not None:
        validate_file_extension(Path(path), TEXT_EXTENSIONS)
        remote_profile = _get_validated_slurm_profile(profile)
        logger.debug(f"Deleting text file on remote profile {profile}: {path}")
        return sftp.delete_file(remote_profile, path)

    file_path = Path(path)

    logger.debug(f"Attempting to delete text file at {file_path}")

    validate_file_exists(file_path)
    validate_file_extension(file_path, TEXT_EXTENSIONS)

    return try_delete_file(file_path)


class AudioUploadRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Annotated[str, AfterValidator(has_audio_extension)]
    file: UploadFile


@post("/api/audio", guards=ENDPOINT_GUARDS)
async def upload_audio(
    data: Annotated[
        AudioUploadRequest, Body(media_type=RequestEncodingType.MULTI_PART)
    ],
    state: State,
    profile: Optional[str] = None,
) -> FileUploadResponse:
    """Upload an audio file to a specified location."""

    content = await data.file.read()

    validate_file_size(content, state.MAX_FILE_SIZE)

    if profile is not None:
        remote_profile = _get_validated_slurm_profile(profile)
        logger.debug(f"Uploading audio file to remote profile {profile}: {data.path}")
        response = sftp.write_file(remote_profile, data.path, content, update=False)
        return FileUploadResponse(
            filename=response.filename,
            size=response.size,
            created_at=response.created_at,
        )

    path = Path(data.path)
    logger.debug(f"Attempting to upload audio file {data.file.filename} to {path}")

    if path.exists():
        raise ValidationException(f"The requested path ({path}) already exists")

    return try_write_file(path, content)


@get("/api/audio", guards=ENDPOINT_GUARDS)
async def get_audio(path: str, profile: Optional[str] = None) -> File | Response[bytes]:
    """Retrieve an audio file from the specified path."""

    if profile is not None:
        validate_file_extension(Path(path), AUDIO_EXTENSIONS)
        remote_profile = _get_validated_slurm_profile(profile)
        logger.debug(f"Downloading audio file from remote profile {profile}: {path}")
        content = sftp.read_file(remote_profile, path)

        # Determine content type from extension
        ext = os.path.splitext(path)[1].lower()
        content_type = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
        }.get(ext, "application/octet-stream")

        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'
            },
        )

    file_path = Path(path)

    logger.debug(f"Attempting to retrieve audio file from {file_path}")

    validate_file_exists(file_path)
    validate_file_extension(file_path, AUDIO_EXTENSIONS)

    return try_read_file(file_path)


@put("/api/audio", guards=ENDPOINT_GUARDS)
async def update_audio(
    data: Annotated[
        AudioUploadRequest, Body(media_type=RequestEncodingType.MULTI_PART)
    ],
    state: State,
    profile: Optional[str] = None,
) -> FileUploadResponse:
    """Update/replace an existing audio file at the specified path."""

    content = await data.file.read()
    validate_file_extension(Path(data.path), AUDIO_EXTENSIONS)
    validate_file_size(content, state.MAX_FILE_SIZE)

    if profile is not None:
        remote_profile = _get_validated_slurm_profile(profile)
        logger.debug(f"Updating audio file on remote profile {profile}: {data.path}")
        response = sftp.write_file(remote_profile, data.path, content, update=True)
        return FileUploadResponse(
            filename=response.filename,
            size=response.size,
            created_at=response.created_at,
        )

    path = Path(data.path)
    logger.debug(f"Attempting to update audio file {data.file.filename} at {path}")

    validate_file_exists(path)

    return try_write_file(path, content, update=True)


@delete("/api/audio", guards=ENDPOINT_GUARDS, status_code=200)
async def delete_audio(path: str, profile: Optional[str] = None) -> Path | str:
    """Delete an audio file at the specified path."""

    if profile is not None:
        validate_file_extension(Path(path), AUDIO_EXTENSIONS)
        remote_profile = _get_validated_slurm_profile(profile)
        logger.debug(f"Deleting audio file on remote profile {profile}: {path}")
        return sftp.delete_file(remote_profile, path)

    file_path = Path(path)

    logger.debug(f"Attempting to delete audio file at {file_path}")

    validate_file_exists(file_path)
    validate_file_extension(file_path, AUDIO_EXTENSIONS)

    return try_delete_file(file_path)


@get("/api/ports", guards=ENDPOINT_GUARDS)
async def get_ports(request: Request) -> int:  # type: ignore
    """Find an available port on the server. This endpoint allows a UI to run local services."""
    return find_port()


class ServiceRequest(BaseModel):
    name: str
    image: str
    repo_id: str
    profile: Profile
    container_config: ContainerConfig
    job_config: JobConfig
    mount: Optional[str] = None
    grace_period: int = 180  # seconds


@dataclass
class StopServiceRequest:
    timeout: bool = False
    failed: bool = False


def build_service(data: ServiceRequest) -> Service:
    """Convert a service request into a service object based on the requested image."""

    ServiceClass = service_classes.get(data.image)

    if ServiceClass is None:
        raise ValidationException(
            detail=f"Unrecognized service image {data.image}",
            extra=[
                {"message": "Invalid service request", "key": "image", "source": "data"}
            ],
        )

    flattened = {
        "name": data.name,
        "model": data.repo_id,
        "profile": data.profile.name,
        "home_dir": data.profile.home_dir,
        "cache_dir": data.profile.cache_dir,
        "mount": data.mount,
        "grace_period": data.grace_period,
    }

    if isinstance(data.profile, LocalProfile):
        if blackfish_config.CONTAINER_PROVIDER is None:
            raise ValidationException(
                detail="Container provider is None",
                extra=[
                    {
                        "message": "Invalid config",
                        "key": "CONTAINER_PROVIDER",
                        "source": "config",
                    }
                ],
            )
        flattened["host"] = "localhost"
        flattened["provider"] = blackfish_config.CONTAINER_PROVIDER
    if isinstance(data.profile, SlurmProfile) and isinstance(
        data.job_config, SlurmJobConfig
    ):
        flattened["host"] = data.profile.host
        flattened["user"] = data.profile.user
        flattened["time"] = data.job_config.time
        flattened["ntasks_per_node"] = data.job_config.ntasks_per_node
        flattened["mem"] = data.job_config.mem
        flattened["gres"] = data.job_config.gres
        flattened["partition"] = data.job_config.partition
        flattened["constraint"] = data.job_config.constraint
        flattened["scheduler"] = JobScheduler.Slurm

    return ServiceClass(**flattened)


@post("/api/services", guards=ENDPOINT_GUARDS)
async def run_service(
    data: ServiceRequest,
    session: AsyncSession,
    state: State,
) -> Service:
    service = build_service(data)

    try:
        await service.start(
            session,
            state,
            container_options=data.container_config,
            job_options=data.job_config,
        )
    except ServiceLaunchError as e:
        logger.warning(f"Service launch failed: {e.error_type}")
        raise InternalServerException(detail=e.user_message())
    except Exception as e:
        logger.error(f"Unexpected error starting service: {e}")
        raise InternalServerException(detail="Failed to launch service.")

    return service


@put("/api/services/{service_id:str}/stop", guards=ENDPOINT_GUARDS)
async def stop_service(
    service_id: UUID, data: StopServiceRequest, session: AsyncSession, state: State
) -> Service:
    service = await session.get(Service, service_id)
    if service is None:
        raise NotFoundException(detail="Service not found")

    await service.stop(session, timeout=data.timeout, failed=data.failed)
    return service


@get("/api/services/{service_id:str}", guards=ENDPOINT_GUARDS)
async def fetch_service(
    service_id: UUID,
    session: AsyncSession,
    state: State,
    refresh: Optional[bool] = False,
) -> Service:
    service = await session.get(Service, service_id)
    if service is None:
        raise NotFoundException(detail=f"Service {service_id} not found")

    if refresh:
        logger.info("Refreshing service status")
        await service.refresh(session, state)

    return service


@get("/api/services", guards=ENDPOINT_GUARDS)
async def fetch_services(
    session: AsyncSession,
    state: State,
    id: Optional[UUID] = None,
    image: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    port: Optional[int] = None,
    name: Optional[str] = None,
    profile: Optional[str] = None,
    refresh: Optional[bool] = False,
) -> list[Service]:
    query_params = {
        k: v
        for k, v in {
            "id": id,
            "image": image,
            "model": model,
            "status": status,
            "port": port,
            "name": name,
            "profile": profile,
        }.items()
        if v is not None
    }

    query = sa.select(Service).filter_by(**query_params)
    res = await session.execute(query)
    services = res.scalars().all()

    if refresh:
        logger.info("Refreshing service statuses")
        await asyncio.gather(*[s.refresh(session, state) for s in services])

    return list(services)


@delete("/api/services", guards=ENDPOINT_GUARDS, status_code=200)
async def delete_service(
    session: AsyncSession,
    state: State,
    id: Optional[UUID] = None,
    image: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    port: Optional[int] = None,
    name: Optional[str] = None,
    profile: Optional[str] = None,
) -> list[dict[str, str]]:
    # Build query parameters
    query_params = {
        k: v
        for k, v in {
            "id": id,
            "image": image,
            "model": model,
            "status": status,
            "port": port,
            "name": name,
            "profile": profile,
        }.items()
        if v is not None
    }

    # Query database
    query = sa.select(Service).filter_by(**query_params)
    query_res = await session.execute(query)
    services = query_res.scalars().all()
    if len(services) == 0:
        logger.warning(
            f"The query parameters {query_params} did not match any services."
        )
        return []

    # Refresh services (async)
    await asyncio.gather(*[s.refresh(session, state) for s in services])

    # Delete running services
    res = []
    for service in services:
        if service.status in [
            ServiceStatus.STOPPED,
            ServiceStatus.TIMEOUT,
            ServiceStatus.FAILED,
            None,
        ]:
            # Try to delete the service; skip job clean up if this fails
            logger.debug(f"Attempting to delete service {service.id}")
            deletion = sa.delete(Service).where(Service.id == service.id)
            try:
                await session.execute(deletion)
            except Exception as e:
                logger.error(f"Failed to delete service {service.id}: {e}")
                res.append(
                    {
                        "id": str(service.id),
                        "status": "error",
                        "message": f"Failed to delete service: {e}",
                    }
                )
                continue

            # Attempt job clean up; don't fail whole operation if this doesn't work!
            try:
                job = service.get_job()
                if job is not None:
                    job.remove()
            except Exception as e:
                logger.warning(f"Unable to remove job for service {service.id}: {e}")

            res.append(
                {
                    "id": str(service.id),
                    "status": "ok",
                }
            )
        else:
            logger.warning(
                f"Service {service.id} is still running (status={service.status}). Skipping."
            )
            res.append(
                {
                    "id": str(service.id),
                    "status": "error",
                    "message": "Service is still running",
                }
            )

    return res


@delete("/api/services/prune", guards=ENDPOINT_GUARDS, status_code=200)
async def prune_services(session: AsyncSession, state: State) -> int:
    # Query database
    query = sa.select(Service).where(
        Service.status.in_(
            [
                ServiceStatus.STOPPED,
                ServiceStatus.TIMEOUT,
                ServiceStatus.FAILED,
            ]
        )
    )
    res = await session.execute(query)
    services = res.scalars().all()

    # Any running services found?
    if len(services) == 0:
        return 0

    # Refresh services
    await asyncio.gather(*[s.refresh(session, state) for s in services])

    # Delete services
    count = 0
    for service in services:
        # Try to delete the service; skip job clean upu if this fails
        logger.debug(f"Attempting to delete service {service.id}")
        deletion = sa.delete(Service).where(Service.id == service.id)
        try:
            await session.execute(deletion)
        except Exception as e:
            logger.error(f"Failed to delete service {service.id}: {e}")
            continue

        # Attempt job clean up; don't fail whole operation if this doesn't work!
        try:
            job = service.get_job()
            if job is not None:
                job.remove()
        except Exception as e:
            logger.warning(f"Unable to remove job for service {service.id.hex}: {e}")

        count += 1

    return count


class BatchJobRequest(BaseModel):
    """Request model for creating a batch job."""

    name: str
    task: str  # e.g., "transcribe", "summarize"
    repo_id: str  # Model ID (e.g., "openai/whisper-large-v3")
    revision: Optional[str] = None  # Model revision
    profile: Profile
    input_dir: str  # Input directory on cluster
    output_dir: str  # Output directory on cluster
    params: Optional[dict[str, Any]] = None  # Task-specific parameters
    resources: Optional[dict[str, Any]] = None  # Resource requirements


def build_batch_job(data: BatchJobRequest) -> BatchJob:
    """Convert a batch job request into a BatchJob object."""
    # Build batch job
    job_data: dict[str, Any] = {
        "name": data.name,
        "task": data.task,
        "repo_id": data.repo_id,
        "revision": data.revision,
        "profile": data.profile.name,
        "home_dir": data.profile.home_dir,
        "input_dir": data.input_dir,
        "output_dir": data.output_dir,
        "params": data.params,
        "resources": data.resources,
    }

    if isinstance(data.profile, LocalProfile):
        job_data["host"] = "localhost"
    elif isinstance(data.profile, SlurmProfile):
        job_data["user"] = data.profile.user
        job_data["host"] = data.profile.host

    batch_job = BatchJob(**job_data)
    logger.debug(f"Batch job created: {batch_job}")
    return batch_job


@get("/api/jobs/tasks", guards=ENDPOINT_GUARDS)
async def list_tasks(
    state: State,
    profile: str,
) -> list[dict[str, Any]]:
    """List available batch job tasks from tigerflow-ml.

    Args:
        profile: Name of the profile to query tasks from
    """
    try:
        client = create_tigerflow_client_for_profile(profile, state)
        return await client.list_tasks()
    except FileNotFoundError:
        raise NotFoundException(detail=f"Profile '{profile}' not found")
    except TigerFlowError as e:
        raise InternalServerException(detail=e.user_message())


@get("/api/jobs/tasks/{task:str}", guards=ENDPOINT_GUARDS)
async def get_task(
    task: str,
    state: State,
    profile: str,
) -> dict[str, Any]:
    """Get details for a specific task from tigerflow-ml.

    Args:
        task: Name of the task to get details for
        profile: Name of the profile to query from
    """
    try:
        client = create_tigerflow_client_for_profile(profile, state)
        return await client.get_task_info(task)
    except FileNotFoundError:
        raise NotFoundException(detail=f"Profile '{profile}' not found")
    except TigerFlowError as e:
        # Check if this is a "task not found" type error
        if "not found" in e.details.lower() or "unknown task" in e.details.lower():
            raise NotFoundException(detail=f"Task '{task}' not found")
        raise InternalServerException(detail=e.user_message())


@post("/api/jobs", guards=ENDPOINT_GUARDS)
async def run_job(
    data: BatchJobRequest,
    session: AsyncSession,
    state: State,
) -> BatchJob:
    """Create and start a batch job."""
    logger.debug(f"Received job request: {data}")

    logger.debug("Building batch job...")
    batch_job = build_batch_job(data)

    # Add to database first to get ID
    session.add(batch_job)
    await session.flush()

    logger.debug("Attempting to start batch job...")
    try:
        client = create_tigerflow_client(batch_job, state)
        await batch_job.start(client)
    except TigerFlowError as e:
        batch_job.status = BatchJobStatus.STOPPED
        detail = f"Unable to start batch job: {e.user_message()}"
        logger.error(detail)
        raise InternalServerException(detail=detail)
    except Exception as e:
        batch_job.status = BatchJobStatus.STOPPED
        detail = f"Unable to start batch job. Error: {e}"
        logger.error(detail)
        raise InternalServerException(detail=detail)

    # Persist final state
    session.add(batch_job)
    await session.flush()

    return batch_job


@get("/api/jobs", guards=ENDPOINT_GUARDS)
async def fetch_jobs(
    session: AsyncSession,
    state: State,
    id: Optional[str] = None,
    task: Optional[str] = None,
    repo_id: Optional[str] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
    profile: Optional[str] = None,
) -> list[BatchJob]:
    """List batch jobs with optional filtering."""
    query_params = {
        "id": id,
        "task": task,
        "repo_id": repo_id,
        "status": status,
        "name": name,
        "profile": profile,
    }

    query_params = {k: v for k, v in query_params.items() if v is not None}
    query = sa.select(BatchJob).filter_by(**query_params)
    logger.debug(f"Executing query {query}...")
    try:
        res = await session.execute(query)
    except StatementError as e:
        raise ValidationException(detail=f"Invalid query statement: {e}")

    jobs = list(res.scalars().all())
    logger.debug(f"Found {len(jobs)} matching batch jobs.")

    # Update status for each job
    for job in jobs:
        try:
            client = create_tigerflow_client(job, state)
            await job.update(client)
            session.add(job)
        except Exception as e:
            logger.warning(f"Failed to update job {job.id}: {e}")

    await session.flush()

    return jobs


@get("/api/jobs/{id:str}", guards=ENDPOINT_GUARDS)
async def get_job(
    id: str,
    session: AsyncSession,
    state: State,
) -> BatchJob | None:
    """Fetch a job by its ID."""
    query = sa.select(BatchJob).where(BatchJob.id == id)
    try:
        res = await session.execute(query)
    except StatementError:
        raise NotFoundException(detail=f"Job {id} not found. Invalid job ID {id}")
    except Exception as e:
        logger.error(f"Failed to execute query: {e}")
        raise InternalServerException(
            detail="An error occurred while fetching the job."
        )
    try:
        return res.scalar_one()
    except NoResultFound:
        raise NotFoundException(detail=f"Job {id} not found")


@put("/api/jobs/{job_id:str}/stop", guards=ENDPOINT_GUARDS)
async def stop_job(
    job_id: str,
    session: AsyncSession,
    state: State,
) -> BatchJob | None:
    """Stop a job by its ID."""
    job = await get_batch_job(job_id, session)
    if job is None:
        raise NotFoundException(detail=f"Job {job_id} not found")

    try:
        client = create_tigerflow_client(job, state)
        await job.stop(client)
        await job.update(client)
        session.add(job)
        await session.flush()
        return job
    except Exception as e:
        logger.error(f"Failed to stop job {job_id}: {e}")
        raise InternalServerException(
            detail="An error occurred while stopping the job."
        )


@dataclass
class DeleteBatchJobResponse:
    job_id: str
    status: str
    message: Optional[str] = None


@delete("/api/jobs", guards=ENDPOINT_GUARDS, status_code=200)
async def delete_job(
    session: AsyncSession,
    state: State,
    id: Optional[str] = None,
    task: Optional[str] = None,
    repo_id: Optional[str] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
    profile: Optional[str] = None,
) -> list[DeleteBatchJobResponse] | None:
    """Delete batch jobs matching the provided query parameters."""

    query_params = {
        "id": id,
        "task": task,
        "repo_id": repo_id,
        "status": status,
        "name": name,
        "profile": profile,
    }

    query_params = {k: v for k, v in query_params.items() if v is not None}
    query = sa.select(BatchJob).filter_by(**query_params)

    logger.debug(f"Executing query {query}...")
    try:
        query_res = await session.execute(query)
    except StatementError as e:
        raise ValidationException(detail=f"Invalid query statement: {e}")

    jobs = query_res.scalars().all()
    logger.debug(f"Found {len(jobs)} matching batch jobs.")

    if len(jobs) == 0:
        logger.warning(
            f"The query parameters {query_params} did not match any batch jobs."
        )
        return []

    # Update job statuses before deletion check
    for job in jobs:
        try:
            client = create_tigerflow_client(job, state)
            await job.update(client)
        except Exception as e:
            logger.warning(f"Failed to update job {job.id} status: {e}")

    res = []
    for batch_job in jobs:
        if batch_job.status in [BatchJobStatus.STOPPED, None]:
            logger.debug(f"Queueing batch job {batch_job.id} for deletion")
            deletion = sa.delete(BatchJob).where(BatchJob.id == batch_job.id)
            try:
                await session.execute(deletion)
            except Exception as e:
                logger.error(
                    f"An error occurred while attempting to delete batch job {batch_job.id.hex}: {e}"
                )
                res.append(
                    DeleteBatchJobResponse(
                        job_id=batch_job.id.hex,
                        status="error",
                        message=f"Delete query error: {e}",
                    )
                )
                continue
            res.append(DeleteBatchJobResponse(job_id=batch_job.id.hex, status="ok"))
        else:
            logger.warning(
                f"Batch job {batch_job.id.hex} is still running (status={batch_job.status}). Aborting delete."
            )
            res.append(
                DeleteBatchJobResponse(
                    job_id=batch_job.id.hex,
                    status="error",
                    message="Batch job is still running",
                )
            )

    return res


async def asyncpost(url: StrOrURL, data: Any, headers: Any) -> Any:
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, headers=headers) as response:
            return await response.json()


@post(
    [
        "/proxy/{port:int}/{cmd:str}",
        "/proxy/{port:int}/{ver:str}/{cmd:path}",
    ],
    guards=ENDPOINT_GUARDS,
)
async def proxy_service(
    data: dict[Any, Any],
    port: int,
    ver: Optional[str],
    cmd: str,
    streaming: Optional[bool],
    session: AsyncSession,
    state: State,
) -> Any | Stream:
    """Call a service via proxy and return the response.

    Setting query parameter `streaming` to `True` streams the response.
    """

    if ver is not None:
        url = f"http://localhost:{port}/{ver}{cmd}"
    else:
        url = f"http://localhost:{port}/{cmd}"

    if streaming:

        async def generator() -> AsyncGenerator:  # type: ignore
            headers = {"Content-Type": "application/json"}
            with requests.post(url, json=data, headers=headers, stream=True) as res:
                for x in res.iter_content(chunk_size=None):
                    if x:
                        yield x

        return Stream(generator)
    else:
        res = await asyncpost(
            url,
            json.dumps(data),
            {"Content-Type": "application/json"},
        )
        return res


@get("/api/models", guards=ENDPOINT_GUARDS)
async def get_models(
    session: AsyncSession,
    state: State,
    profile: Optional[str] = None,
    image: Optional[str] = None,
    refresh: Optional[bool] = False,
) -> list[Model]:
    profiles = deserialize_profiles(state.HOME_DIR)

    res: list[list[Model]] | Result[Tuple[Model]]
    if refresh:
        if profile is not None:
            matched = next((p for p in profiles if p.name == profile), None)
            if matched is None:
                logger.warning(
                    f"Profile '{profile}' not found. Returning an empty list."
                )
                return list()
            models = await find_models(matched)
            logger.debug(
                f"Deleting existing models WHERE model.profile == '{profile}'..."
            )
            try:
                delete_query = sa.delete(Model).where(Model.profile == profile)
                await session.execute(delete_query)
            except Exception as e:
                logger.error(f"Failed to execute query: {e}")
        else:
            gathered = await asyncio.gather(
                *[find_models(profile) for profile in profiles], return_exceptions=True
            )
            models = []
            for p, result in zip(profiles, gathered):
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to find models for profile '{p.name}': {result}"
                    )
                elif isinstance(result, list):
                    models.extend(result)
            logger.debug("Deleting all existing models...")
            try:
                delete_all_query = sa.delete(Model)
                await session.execute(delete_all_query)
            except Exception as e:
                logger.error(f"Failed to execute query: {e}")
        logger.debug("Inserting refreshed models...")
        session.add_all(models)
        try:
            await session.flush()
        except Exception as e:
            logger.error(f"Failed to execute transaction: {e}")
        if image is not None:
            # Use compatible pipelines if defined, otherwise exact match
            compatible = COMPATIBLE_PIPELINES.get(image, [image])
            return sorted(
                list(filter(lambda x: x.image in compatible, models)),
                key=lambda x: x.repo.lower(),
            )
        else:
            return sorted(models, key=lambda x: x.repo.lower())
    else:
        logger.info("Querying model table...")

        # Build query with optional filters
        query = sa.select(Model)
        if profile is not None:
            query = query.where(Model.profile == profile)
        if image is not None:
            # Use compatible pipelines if defined, otherwise exact match
            compatible = COMPATIBLE_PIPELINES.get(image, [image])
            query = query.where(Model.image.in_(compatible))

        select_query = query.order_by(sa.func.lower(Model.repo))
        try:
            res = await session.execute(select_query)
            return list(res.scalars().all())
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return []


@get("/api/models/{model_id:str}", guards=ENDPOINT_GUARDS)
async def get_model(model_id: str, session: AsyncSession) -> Model:
    query = sa.select(Model).where(Model.id == model_id)
    try:
        res = await session.execute(query)
    except StatementError:
        logger.error(f"{model_id} is not a valid UUID.")
        raise ValidationException(detail=f"{model_id} is not a valid UUID.")
    try:
        return res.scalar_one()
    except NoResultFound as e:
        raise NotFoundException(detail=f"Model {model_id} not found") from e


@post("/api/models", guards=ENDPOINT_GUARDS)
async def create_model(data: Model, session: AsyncSession) -> Model:
    session.add(data)
    return data


@delete("/api/models/{model_id:str}", guards=ENDPOINT_GUARDS)
async def delete_model(model_id: str, session: AsyncSession) -> None:
    """Delete a specific model by its database ID (UUID).

    This endpoint removes a single model from the database using its unique identifier.
    Use this when you have the exact model UUID and want to delete that specific record.

    Args:
        model_id: The UUID of the model to delete (e.g., "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        session: Database session (injected)

    Returns:
        None (204 No Content on success)

    Raises:
        ValidationException: If model_id is not a valid UUID
        NotFoundException: If no model exists with the given ID

    Example:
        DELETE /api/models/a1b2c3d4-e5f6-7890-abcd-ef1234567890
    """
    try:
        query = sa.delete(Model).where(Model.id == model_id)
        res = await session.execute(query)
    except StatementError:
        logger.error(f"{model_id} is not a valid UUID.")
        raise ValidationException(detail="{model_id} is not a valid UUID.")

    if res.rowcount == 0:  # type: ignore[attr-defined]
        raise NotFoundException(detail=f"No model deleted: {model_id} not found.")


@dataclass
class DeleteModelResponse:
    model_id: str
    status: str
    message: Optional[str] = None


@delete("/api/models", guards=ENDPOINT_GUARDS, status_code=200)
async def delete_models(
    session: AsyncSession,
    repo_id: Optional[str] = None,
    profile: Optional[str] = None,
    revision: Optional[str] = None,
) -> list[DeleteModelResponse]:
    """Bulk delete models matching query parameters.

    This endpoint deletes multiple models based on their attributes (repo_id, profile,
    revision) rather than database IDs. Useful for operations like "delete all models
    for a profile" or "delete all revisions of a specific model".

    At least one query parameter must be provided to prevent accidental deletion of all
    models. The operation attempts to delete each matching model individually and reports
    success or failure for each. Partial success is possible - some models may be deleted
    successfully while others fail, allowing you to identify and address specific issues.

    Args:
        session: Database session (injected)
        repo_id: Filter by repository ID (e.g., "openai/whisper-large-v3")
        profile: Filter by profile name (e.g., "default", "production")
        revision: Filter by model revision/commit hash

    Returns:
        List of DeleteModelResponse objects with status ("ok" or "error") for each model.
        Empty list if no models match the query parameters.

    Raises:
        ValidationException: If no query parameters provided or query is invalid

    Examples:
        DELETE /api/models?profile=test
            → Deletes all models associated with the "test" profile

        DELETE /api/models?repo_id=openai/whisper-large-v3&profile=default
            → Deletes all revisions of whisper-large-v3 in the default profile

        DELETE /api/models?repo_id=meta/llama-2&profile=prod&revision=abc123
            → Deletes a specific model revision in the prod profile

    Response Format:
        [
            {"model_id": "uuid", "status": "ok"},
            {"model_id": "uuid", "status": "error", "message": "error details"}
        ]

    Note:
        If you have the exact model UUID, use DELETE /api/models/{model_id} instead.
        This bulk endpoint is designed for CLI usage and filtering by model attributes.
    """

    # Build query parameters
    query_params = {
        k: v
        for k, v in {
            "repo": repo_id,
            "profile": profile,
            "revision": revision,
        }.items()
        if v is not None
    }

    if not query_params:
        logger.warning("No query parameters provided for model deletion.")
        raise ValidationException(
            detail="At least one query parameter (repo_id, profile, or revision) must be provided."
        )

    # Query database
    query = sa.select(Model).filter_by(**query_params)
    try:
        query_res = await session.execute(query)
    except StatementError as e:
        raise ValidationException(detail=f"Invalid query statement: {e}")

    models = query_res.scalars().all()

    if len(models) == 0:
        logger.warning(f"The query parameters {query_params} did not match any models.")
        return []

    # Delete models
    res = []
    for model in models:
        logger.debug(f"Attempting to delete model {model.id}")
        deletion = sa.delete(Model).where(Model.id == model.id)
        try:
            await session.execute(deletion)
            res.append(
                DeleteModelResponse(
                    model_id=str(model.id),
                    status="ok",
                )
            )
        except Exception as e:
            logger.error(f"Failed to delete model {model.id}: {e}")
            res.append(
                DeleteModelResponse(
                    model_id=str(model.id),
                    status="error",
                    message=f"Failed to delete model: {e}",
                )
            )

    return res


@get("/api/profiles", guards=ENDPOINT_GUARDS)
async def read_profiles() -> list[Profile]:
    try:
        logger.debug("Fetching profiles")
        return deserialize_profiles(blackfish_config.HOME_DIR)
    except FileNotFoundError:
        logger.error("Profiles config not found.")
        raise NotFoundException(detail="Profiles config not found.")


@get("/api/profiles/{name: str}", guards=ENDPOINT_GUARDS)
async def read_profile(name: str) -> Profile | None:
    try:
        profile = deserialize_profile(blackfish_config.HOME_DIR, name)
    except FileNotFoundError:
        logger.debug("Profiles config not found.")
        raise NotFoundException(detail="Profile config not found.")
    except Exception as e:
        raise InternalServerException(detail=f"Failed to deserialize profile: {e}.")

    if profile is not None:
        return profile
    else:
        logger.error("Profile not found.")
        raise NotFoundException(detail="Profile not found.")


class ProfileRequest(BaseModel):
    """Request model for creating or updating a profile."""

    name: str
    schema_type: str  # "slurm" or "local"
    host: Optional[str] = None  # Required for slurm
    user: Optional[str] = None  # Required for slurm
    home_dir: str
    cache_dir: str
    python_path: Optional[str] = None  # For remote TigerFlow setup


def _profiles_config_path() -> str:
    """Return path to profiles.cfg."""
    return os.path.join(blackfish_config.HOME_DIR, "profiles.cfg")


def _get_profiles_config() -> configparser.ConfigParser:
    """Load the profiles configuration file."""
    return ProfileManager.get_profiles_config(_profiles_config_path())


def _save_profiles_config(config: configparser.ConfigParser) -> None:
    """Save the profiles configuration file."""
    ProfileManager.save_profiles_config(config, _profiles_config_path())


@post("/api/profiles", guards=ENDPOINT_GUARDS)
async def create_profile(data: ProfileRequest) -> Profile:
    """Create a new profile.

    For Slurm profiles, this sets up directories and TigerFlow.
    For Local profiles, this sets up local directories.
    """
    config = _get_profiles_config()

    if data.name in config:
        raise ClientException(
            status_code=HTTP_409_CONFLICT,
            detail=f"Profile '{data.name}' already exists.",
        )

    if data.schema_type == "slurm":
        if not data.host or not data.user:
            raise ValidationException(
                detail="'host' and 'user' are required for Slurm profiles."
            )

        # Choose runner based on host
        runner: SSHRunner | LocalRunner
        if data.host == "localhost":
            runner = LocalRunner()
        else:
            runner = SSHRunner(user=data.user, host=data.host)

        # Set up directories and TigerFlow
        try:
            profile_mgr = ProfileManager(
                runner=runner,
                home_dir=data.home_dir,
                cache_dir=data.cache_dir,
            )
            await profile_mgr.create_directories()
            await profile_mgr.check_cache()

            tigerflow = TigerFlowClient(
                runner=runner,
                home_dir=data.home_dir,
                python_path=data.python_path or "python3",
            )
            await tigerflow.setup()
        except ProfileSetupError as e:
            raise InternalServerException(detail=e.user_message())
        except TigerFlowError as e:
            raise InternalServerException(detail=e.user_message())

        config[data.name] = {
            "schema": "slurm",
            "host": data.host,
            "user": data.user,
            "home_dir": data.home_dir,
            "cache_dir": data.cache_dir,
        }
        if data.python_path:
            config[data.name]["python_path"] = data.python_path

        _save_profiles_config(config)

        return SlurmProfile(
            name=data.name,
            host=data.host,
            user=data.user,
            home_dir=data.home_dir,
            cache_dir=data.cache_dir,
        )

    elif data.schema_type == "local":
        # Set up local directories
        try:
            runner = LocalRunner()
            profile_mgr = ProfileManager(
                runner=runner,
                home_dir=data.home_dir,
                cache_dir=data.cache_dir,
            )
            await profile_mgr.create_directories()
            await profile_mgr.check_cache()
        except ProfileSetupError as e:
            raise InternalServerException(detail=e.user_message())

        config[data.name] = {
            "schema": "local",
            "home_dir": data.home_dir,
            "cache_dir": data.cache_dir,
        }
        _save_profiles_config(config)

        return LocalProfile(
            name=data.name,
            home_dir=data.home_dir,
            cache_dir=data.cache_dir,
        )

    else:
        raise ValidationException(
            detail=f"Invalid schema_type '{data.schema_type}'. Must be 'slurm' or 'local'."
        )


@put("/api/profiles/{name:str}", guards=ENDPOINT_GUARDS)
async def update_profile(name: str, data: ProfileRequest) -> Profile:
    """Update an existing profile."""
    config = _get_profiles_config()

    if name not in config:
        raise NotFoundException(detail=f"Profile '{name}' not found.")

    # Update the profile (name change not supported)
    if data.name != name:
        raise ValidationException(
            detail="Profile name cannot be changed. Delete and recreate instead."
        )

    if data.schema_type == "slurm":
        if not data.host or not data.user:
            raise ValidationException(
                detail="'host' and 'user' are required for Slurm profiles."
            )

        config[name] = {
            "schema": "slurm",
            "host": data.host,
            "user": data.user,
            "home_dir": data.home_dir,
            "cache_dir": data.cache_dir,
        }
        if data.python_path:
            config[name]["python_path"] = data.python_path

        _save_profiles_config(config)

        return SlurmProfile(
            name=name,
            host=data.host,
            user=data.user,
            home_dir=data.home_dir,
            cache_dir=data.cache_dir,
        )

    elif data.schema_type == "local":
        config[name] = {
            "schema": "local",
            "home_dir": data.home_dir,
            "cache_dir": data.cache_dir,
        }
        _save_profiles_config(config)

        return LocalProfile(
            name=name,
            home_dir=data.home_dir,
            cache_dir=data.cache_dir,
        )

    else:
        raise ValidationException(
            detail=f"Invalid schema_type '{data.schema_type}'. Must be 'slurm' or 'local'."
        )


@delete("/api/profiles/{name:str}", guards=ENDPOINT_GUARDS, status_code=200)
async def delete_profile(name: str) -> dict[str, str]:
    """Delete a profile.

    This does not clean up remote resources (venv, files) as they may be shared.
    """
    config = _get_profiles_config()

    if name not in config:
        raise NotFoundException(detail=f"Profile '{name}' not found.")

    del config[name]
    _save_profiles_config(config)

    return {"status": "ok", "message": f"Profile '{name}' deleted."}


@put("/api/profiles/{name:str}/repair", guards=ENDPOINT_GUARDS)
async def repair_profile(name: str) -> dict[str, str]:
    """Repair TigerFlow installation on a Slurm profile.

    Removes and reinstalls TigerFlow. Useful when the installation is broken.
    """
    config = _get_profiles_config()

    if name not in config:
        raise NotFoundException(detail=f"Profile '{name}' not found.")

    profile_data = dict(config[name])
    schema = profile_data.get("schema") or profile_data.get("type")

    if schema != "slurm":
        raise ValidationException(detail="Repair is only available for Slurm profiles.")

    host = profile_data.get("host")
    user = profile_data.get("user")
    home_dir = profile_data.get("home_dir")
    python_path = profile_data.get("python_path", "python3")

    if not host or not user or not home_dir:
        raise ValidationException(
            detail="Profile is missing required fields (host, user, home_dir)."
        )

    # Choose runner based on host
    runner: SSHRunner | LocalRunner
    if host == "localhost":
        runner = LocalRunner()
    else:
        runner = SSHRunner(user=user, host=host)

    try:
        client = TigerFlowClient(
            runner=runner,
            home_dir=home_dir,
            python_path=python_path,
        )
        await client.cleanup()
    except TigerFlowError as e:
        raise InternalServerException(detail=e.user_message())

    return {"status": "ok", "message": f"TigerFlow reinstalled on {host}."}


# --- Cluster Status ---
@dataclass
class GpuAvailabilityResponse:
    gpu_type: str
    total: int
    used: int
    idle: int


@dataclass
class PartitionResourcesResponse:
    name: str
    state: str
    nodes_total: int
    nodes_idle: int
    nodes_allocated: int
    nodes_down: int
    cpus_total: int
    cpus_idle: int
    cpus_allocated: int
    memory_total_mb: int
    memory_allocated_mb: int
    gpus: list[GpuAvailabilityResponse]
    max_time_minutes: int | None
    features: list[str]  # Convert set to list for JSON serialization


@dataclass
class QueueStatsResponse:
    running: int
    pending: int
    pending_reasons: dict[str, int]


@dataclass
class ClusterStatusResponse:
    partitions: dict[str, PartitionResourcesResponse]
    queue: dict[str, QueueStatsResponse]
    timestamp: str  # ISO format string


@get("/api/cluster/{profile_name:str}/status", guards=ENDPOINT_GUARDS)
async def get_cluster_status(profile_name: str) -> ClusterStatusResponse:
    """Get current cluster resource availability for a Slurm profile."""
    try:
        profile = deserialize_profile(blackfish_config.HOME_DIR, profile_name)
    except FileNotFoundError:
        raise NotFoundException(detail="Profile config not found.")

    if profile is None:
        raise NotFoundException(detail=f"Profile '{profile_name}' not found.")

    if not isinstance(profile, SlurmProfile):
        raise ValidationException(
            detail=f"Profile '{profile_name}' is not a Slurm profile. "
            "Cluster status is only available for Slurm profiles."
        )

    try:
        cluster_info = SlurmClusterInfo(user=profile.user, host=profile.host)
        status = await cluster_info.get_status_async()
    except ClusterQueryError as e:
        logger.warning(f"Cluster query failed for {profile_name}: {e.error_type}")
        raise InternalServerException(detail=e.user_message())
    except Exception as e:
        logger.error(f"Unexpected error querying cluster {profile_name}: {e}")
        raise InternalServerException(detail="Failed to query cluster status.")

    # Convert to response format (sets -> lists for JSON)
    partitions = {
        name: PartitionResourcesResponse(
            name=p.name,
            state=p.state,
            nodes_total=p.nodes_total,
            nodes_idle=p.nodes_idle,
            nodes_allocated=p.nodes_allocated,
            nodes_down=p.nodes_down,
            cpus_total=p.cpus_total,
            cpus_idle=p.cpus_idle,
            cpus_allocated=p.cpus_allocated,
            memory_total_mb=p.memory_total_mb,
            memory_allocated_mb=p.memory_allocated_mb,
            gpus=[
                GpuAvailabilityResponse(
                    gpu_type=g.gpu_type, total=g.total, used=g.used, idle=g.idle
                )
                for g in p.gpus
            ],
            max_time_minutes=p.max_time_minutes,
            features=sorted(p.features),
        )
        for name, p in status.partitions.items()
    }

    queue = {
        name: QueueStatsResponse(
            running=q.running,
            pending=q.pending,
            pending_reasons=q.pending_reasons,
        )
        for name, q in status.queue.items()
    }

    return ClusterStatusResponse(
        partitions=partitions,
        queue=queue,
        timestamp=status.timestamp.isoformat(),
    )


# --- Config ---
BASE_DIR = module_to_os_path("blackfish.server")

# Use NullPool in test environment to prevent connection leaks across test runs
# PYTEST_CURRENT_TEST is automatically set by pytest when tests are running
engine_config_params: dict[str, Any] = {}
if os.getenv("PYTEST_CURRENT_TEST"):
    from sqlalchemy.pool import NullPool

    engine_config_params["poolclass"] = NullPool

db_config = SQLAlchemyAsyncConfig(
    connection_string=f"sqlite+aiosqlite:///{blackfish_config.HOME_DIR}/app.sqlite",
    metadata=UUIDAuditBase.metadata,
    create_all=True,
    engine_config=EngineConfig(**engine_config_params),
    alembic_config=AlembicAsyncConfig(
        version_table_name="ddl_version",
        script_config=f"{BASE_DIR}/db/migrations/alembic.ini",
        script_location=f"{BASE_DIR}/db/migrations",
    ),
)


async def session_provider(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncSession, None]:
    try:
        async with db_session.begin():
            yield db_session
    except IntegrityError as e:
        raise ClientException(
            status_code=HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


cors_config = CORSConfig(
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Disposition"],
)

openapi_config = OpenAPIConfig(
    title="Blackfish API",
    version="0.0.1",
    path="/docs",
    render_plugins=[SwaggerRenderPlugin()],
)

template_config = TemplateConfig(
    directory=blackfish_config.STATIC_DIR / "build",
    engine=JinjaTemplateEngine,
)

session_config = CookieBackendConfig(
    secret=urandom(16),
    key="bf_user",
    # samesite="none",
)

assets_server = create_static_files_router(
    path="assets",
    directories=[blackfish_config.STATIC_DIR / "build" / "assets"],
    html_mode=True,
)

img_server = create_static_files_router(
    path="img",
    directories=[blackfish_config.STATIC_DIR / "build" / "img"],
    html_mode=True,
)


def not_found_exception_handler(
    request: Request[Any, Any, Any], exc: NotFoundException
) -> Response[Any] | Template:
    """Handle 404 errors - return JSON for API routes, HTML for web routes."""
    if request.url.path.startswith("/api/"):
        return Response(
            content={"detail": exc.detail or "Not found"},
            status_code=HTTP_404_NOT_FOUND,
            media_type="application/json",
        )
    return Template(template_name="index.html", status_code=HTTP_404_NOT_FOUND)


def internal_server_exception_handler(
    request: Request[Any, Any, Any], exc: InternalServerException
) -> Response[Any]:
    """Handle 500 errors - return JSON with detail for API routes."""
    if request.url.path.startswith("/api/"):
        return Response(
            content={"detail": exc.detail or "Internal server error"},
            status_code=500,
            media_type="application/json",
        )
    return Response(
        content={"detail": "Internal server error"},
        status_code=500,
        media_type="application/json",
    )


app = Litestar(
    path=blackfish_config.BASE_PATH,
    route_handlers=[
        dashboard,
        dashboard_login,
        text_generation,
        speech_recognition,
        file_manager,
        index,
        info,
        login,
        logout,
        get_ports,
        RemoteFileBrowserSession,
        get_files,
        upload_image,
        get_image,
        update_image,
        delete_image,
        upload_text,
        get_text,
        update_text,
        delete_text,
        upload_audio,
        get_audio,
        update_audio,
        delete_audio,
        run_service,
        stop_service,
        fetch_service,
        fetch_services,
        delete_service,
        prune_services,
        proxy_service,
        list_tasks,
        get_task,
        run_job,
        fetch_jobs,
        get_job,
        stop_job,
        delete_job,
        create_model,
        get_model,
        get_models,
        delete_model,
        delete_models,
        read_profiles,
        read_profile,
        create_profile,
        update_profile,
        delete_profile,
        repair_profile,
        get_cluster_status,
        assets_server,
        img_server,
    ],
    dependencies={"session": session_provider},
    plugins=[SQLAlchemyPlugin(db_config)],
    logging_config=None,  # disable Litestar logger (we're using our own)
    state=State(blackfish_config.as_dict()),
    cors_config=cors_config,
    openapi_config=openapi_config,
    template_config=template_config,
    middleware=[session_config.middleware],
    exception_handlers={
        NotFoundException: not_found_exception_handler,
        InternalServerException: internal_server_exception_handler,
    },
)
