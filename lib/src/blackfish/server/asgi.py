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
from typing import Optional, Tuple, Any, Type, Annotated, Callable
import asyncio
from pathlib import Path
import bcrypt
from importlib import import_module
from uuid import UUID
from PIL import Image, UnidentifiedImageError
from io import BytesIO

from fabric.connection import Connection
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
from blackfish.server.models.model import (
    Model,
    PIPELINE_IMAGES,
    get_pipeline,
    validate_repo_id,
    InvalidRepoIdError,
)
from blackfish.server.models.download import DownloadTask, DownloadStatus
from blackfish.server.models.metadata import (
    fetch_model_metadata,
)
from huggingface_hub import model_info as hf_model_info
from huggingface_hub.errors import HfHubHTTPError, RepositoryNotFoundError
from blackfish.server.models.tiers import (
    ResourceSpecs,
    load_resource_specs,
    parse_resource_specs,
    get_default_specs,
)
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


def fetch_model_info_from_hub(
    repo_id: str, token: Optional[str] = None
) -> Tuple[str, Optional[dict[str, Any]]]:
    """Fetch image (pipeline tag) and metadata from HuggingFace Hub.

    Args:
        repo_id: The model repository ID (e.g., "meta-llama/Llama-2-7b")
        token: Optional HuggingFace token for gated models

    Returns:
        Tuple of (image, metadata_dict) where image is the pipeline type
        and metadata_dict contains model_size_gb etc.
    """
    try:
        info = hf_model_info(repo_id, token=token)
        pipeline = get_pipeline(info)

        # Convert pipeline tag to image name
        if pipeline is not None and pipeline in PIPELINE_IMAGES:
            image = PIPELINE_IMAGES[pipeline]
        else:
            image = pipeline if pipeline else "unknown"
            if pipeline and pipeline not in PIPELINE_IMAGES:
                logger.warning(f"Unknown pipeline tag for {repo_id}: {pipeline}")

        # Fetch metadata (model size, etc.)
        metadata = fetch_model_metadata(repo_id, token)
        metadata_dict = metadata.to_dict() if metadata else None

        logger.debug(
            f"Fetched info for {repo_id}: image={image}, size={metadata.model_size_gb if metadata else 'unknown'}GB"
        )
        return image, metadata_dict

    except HfHubHTTPError as e:
        logger.warning(f"Failed to fetch info for {repo_id} from HuggingFace Hub: {e}")
        return "unknown", None
    except Exception as e:
        logger.error(f"Error fetching info for {repo_id}: {e}")
        return "unknown", None


async def find_models(profile: Profile) -> list[Model]:
    """Find all model revisions on the filesystem for a given profile.

    Scans `profile.home_dir` and `profile.cache_dir` for HuggingFace-style
    model directories. Returns Model objects with repo, revision, model_dir,
    and profile set. Image and metadata are not set here - they should be
    populated from the database or fetched from HuggingFace Hub.

    Returns:
        List of Model objects found on filesystem (image and metadata_ are None)
    """
    models = []
    seen_revisions: set[str] = set()

    def scan_directory(base_dir: str, listdir_fn: Callable[[str], list[str]]) -> None:
        """Scan a directory for model folders and revisions."""
        logger.debug(f"Scanning directory: {base_dir}")
        try:
            model_dirs = listdir_fn(base_dir)
        except (FileNotFoundError, OSError) as e:
            logger.debug(f"Directory not found or inaccessible: {base_dir} ({e})")
            return

        for model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
            try:
                _, namespace, model_name = model_dir.split("--")
            except ValueError:
                logger.warning(f"Invalid model directory format: {model_dir}")
                continue

            repo = f"{namespace}/{model_name}"
            snapshots_path = os.path.join(base_dir, model_dir, "snapshots")
            logger.debug(f"Found model {repo}, scanning snapshots")

            try:
                revisions = listdir_fn(snapshots_path)
            except (FileNotFoundError, OSError) as e:
                logger.warning(f"No snapshots found for {repo}: {e}")
                continue

            for revision in revisions:
                if revision in seen_revisions:
                    continue
                seen_revisions.add(revision)
                logger.debug(f"Found revision {revision} for {repo}")
                models.append(
                    Model(
                        repo=repo,
                        profile=profile.name,
                        revision=revision,
                        image="unknown",  # Will be populated from DB or HF Hub
                        model_dir=os.path.join(base_dir, model_dir),
                        metadata_=None,  # Will be populated from DB or HF Hub
                    )
                )

    if isinstance(profile, SlurmProfile) and not profile.is_local():
        # Remote profile: use SFTP
        logger.debug(f"Connecting to sftp::{profile.user}@{profile.host}")
        with (
            Connection(host=profile.host, user=profile.user) as conn,
            conn.sftp() as sftp,
        ):
            cache_dir = os.path.join(profile.cache_dir, "models")
            home_dir = os.path.join(profile.home_dir, "models")
            scan_directory(cache_dir, sftp.listdir)
            scan_directory(home_dir, sftp.listdir)
    else:
        # Local profile: use os.listdir
        cache_dir = os.path.join(profile.cache_dir, "models")
        home_dir = os.path.join(profile.home_dir, "models")
        scan_directory(cache_dir, os.listdir)
        scan_directory(home_dir, os.listdir)

    logger.debug(f"Found {len(models)} models for profile {profile.name}")
    return models


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
        details = e.details or ""
        if "not found" in details.lower() or "unknown task" in details.lower():
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
        # 1. Scan filesystem to get current models
        if profile is not None:
            matched = next((p for p in profiles if p.name == profile), None)
            if matched is None:
                logger.warning(
                    f"Profile '{profile}' not found. Returning an empty list."
                )
                return list()
            fs_models = await find_models(matched)
        else:
            gathered = await asyncio.gather(
                *[find_models(p) for p in profiles], return_exceptions=True
            )
            fs_models = []
            for p, result in zip(profiles, gathered):
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to find models for profile '{p.name}': {result}"
                    )
                elif isinstance(result, list):
                    fs_models.extend(result)

        # 2. Fetch existing models from DB
        if profile is not None:
            existing_query = sa.select(Model).where(Model.profile == profile)
        else:
            existing_query = sa.select(Model)
        existing_result = await session.execute(existing_query)
        db_models = list(existing_result.scalars().all())

        # Create lookups by (repo, profile, revision)
        fs_keys = {(m.repo, m.profile, m.revision) for m in fs_models}
        db_lookup = {(m.repo, m.profile, m.revision): m for m in db_models}

        # 3. Delete models in DB but not on filesystem
        to_delete = [
            m for m in db_models if (m.repo, m.profile, m.revision) not in fs_keys
        ]
        if to_delete:
            logger.debug(f"Deleting {len(to_delete)} stale models from DB...")
            for m in to_delete:
                await session.delete(m)
            try:
                await session.flush()
            except Exception as e:
                logger.error(f"Failed to delete stale models: {e}")

        # 4. Add models on filesystem but not in DB (fetch info from HF Hub)
        to_add = [
            m for m in fs_models if (m.repo, m.profile, m.revision) not in db_lookup
        ]
        if to_add:
            logger.debug(
                f"Adding {len(to_add)} new models to DB, fetching info from HuggingFace Hub..."
            )
            # Get tokens for each profile for gated model access
            profile_tokens = {p.name: getattr(p, "token", None) for p in profiles}

            for m in to_add:
                token = profile_tokens.get(m.profile)
                image, metadata_dict = fetch_model_info_from_hub(m.repo, token)
                m.image = image
                m.metadata_ = metadata_dict

            session.add_all(to_add)
            try:
                await session.flush()
            except Exception as e:
                logger.error(f"Failed to add new models: {e}")

        # 5. Update existing models with missing metadata
        to_update = [
            m
            for m in db_models
            if (m.repo, m.profile, m.revision) in fs_keys and m.metadata_ is None
        ]
        if to_update:
            logger.debug(f"Updating {len(to_update)} models with missing metadata...")
            profile_tokens = {p.name: getattr(p, "token", None) for p in profiles}

            for m in to_update:
                token = profile_tokens.get(m.profile)
                hub_image, metadata_dict = fetch_model_info_from_hub(m.repo, token)
                # Only update if we got valid data
                if metadata_dict is not None:
                    m.metadata_ = metadata_dict
                if m.image in ("unknown", "missing") and hub_image not in ("unknown",):
                    m.image = hub_image
                session.add(m)

            try:
                await session.flush()
            except Exception as e:
                logger.error(f"Failed to update model metadata: {e}")

        # Re-query to get fresh state after all modifications
        logger.debug(f"Re-querying models (profile={profile}, image={image})")
        final_query = sa.select(Model)
        if profile is not None:
            final_query = final_query.where(Model.profile == profile)
        if image is not None:
            compatible = COMPATIBLE_PIPELINES.get(image, [image])
            final_query = final_query.where(Model.image.in_(compatible))

        final_query = final_query.order_by(sa.func.lower(Model.repo))
        final_result = await session.execute(final_query)
        models = list(final_result.scalars().all())
        logger.debug(f"Final query returned {len(models)} models")
        return models
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
async def create_model(data: CreateModelRequest, session: AsyncSession) -> Model:
    """Create a model record in the database, or return existing if already present.

    This endpoint is used by the CLI after downloading a model locally.
    The web UI uses the /api/models/download endpoint instead, which handles
    both downloading and database insertion in a background task.

    If a model with the same repo/profile/revision already exists, the existing
    record is returned (idempotent behavior for CLI re-runs).

    Args:
        data: Model creation request with repo, profile, revision, image, model_dir
        session: Database session (injected)

    Returns:
        The created or existing Model object
    """
    # Check for existing model with same repo, profile, and revision
    existing_query = sa.select(Model).where(
        Model.repo == data.repo,
        Model.profile == data.profile,
        Model.revision == data.revision,
    )
    result = await session.execute(existing_query)
    existing_model = result.scalar_one_or_none()
    if existing_model is not None:
        # Return existing model (idempotent)
        return existing_model

    model = Model(
        repo=data.repo,
        profile=data.profile,
        revision=data.revision,
        image=data.image,
        model_dir=data.model_dir,
        metadata_=data.metadata_,
    )
    session.add(model)
    await session.flush()  # Populate ID before returning
    return model


@delete("/api/models/{model_id:str}", guards=ENDPOINT_GUARDS)
async def delete_model(model_id: str, session: AsyncSession, state: State) -> None:
    """Delete a specific model by its database ID (UUID).

    This endpoint removes a single model from the database and deletes the model files
    from disk for local profiles. For remote profiles, only the database record is removed.

    Args:
        model_id: The UUID of the model to delete (e.g., "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        session: Database session (injected)
        state: Application state (injected)

    Returns:
        None (204 No Content on success)

    Raises:
        ValidationException: If model_id is not a valid UUID
        NotFoundException: If no model exists with the given ID

    Example:
        DELETE /api/models/a1b2c3d4-e5f6-7890-abcd-ef1234567890
    """
    from blackfish.server.models.model import remove_model

    # First fetch the model to get its details
    try:
        select_query = sa.select(Model).where(Model.id == model_id)
        result = await session.execute(select_query)
        model = result.scalar_one()
    except StatementError:
        logger.error(f"{model_id} is not a valid UUID.")
        raise ValidationException(detail=f"{model_id} is not a valid UUID.")
    except NoResultFound:
        raise NotFoundException(detail=f"Model {model_id} not found.")

    # Look up the profile to delete files
    profiles = deserialize_profiles(state.HOME_DIR)
    profile_obj = next((p for p in profiles if p.name == model.profile), None)

    # Delete files from disk for local profiles
    if profile_obj is not None and profile_obj.is_local():
        # Determine if model is in cache_dir or home_dir
        use_cache = model.model_dir.startswith(profile_obj.cache_dir)
        try:
            await asyncio.to_thread(
                remove_model,
                repo_id=model.repo,
                profile=profile_obj,
                revision=model.revision,
                use_cache=use_cache,
            )
            logger.debug(
                f"Deleted files for model {model.repo} revision {model.revision}"
            )
        except FileNotFoundError:
            logger.warning(
                f"Files not found for model {model.repo}, continuing with DB deletion"
            )
        except PermissionError as e:
            logger.error(
                f"Permission denied deleting files for model {model.repo}: {e}"
            )
            raise ValidationException(
                detail="Permission denied: cannot delete model files. Check file permissions."
            )
        except OSError as e:
            logger.error(f"OS error deleting files for model {model.repo}: {e}")
            raise ValidationException(detail=f"Failed to delete model files: {e}")

    # Delete from database
    try:
        delete_query = sa.delete(Model).where(Model.id == model_id)
        await session.execute(delete_query)
    except Exception as e:
        logger.error(f"Failed to delete model {model_id} from database: {e}")
        raise


@dataclass
class DeleteModelResponse:
    model_id: str
    status: str
    message: Optional[str] = None


@delete("/api/models", guards=ENDPOINT_GUARDS, status_code=200)
async def delete_models(
    session: AsyncSession,
    state: State,
    repo_id: Optional[str] = None,
    profile: Optional[str] = None,
    revision: Optional[str] = None,
) -> list[DeleteModelResponse]:
    """Bulk delete models matching query parameters.

    This endpoint deletes multiple models based on their attributes (repo_id, profile,
    revision) rather than database IDs. Also deletes model files from disk for local
    profiles when possible.

    At least one query parameter must be provided to prevent accidental deletion of all
    models. The operation attempts to delete each matching model individually and reports
    success or failure for each. Partial success is possible - some models may be deleted
    successfully while others fail, allowing you to identify and address specific issues.

    Args:
        session: Database session (injected)
        state: Application state (injected)
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
    from blackfish.server.models.model import remove_model

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

    # Load profiles once for file deletion
    profiles = deserialize_profiles(state.HOME_DIR)
    profile_map = {p.name: p for p in profiles}

    # Delete models
    res = []
    for model in models:
        logger.debug(f"Attempting to delete model {model.id}")

        # Delete files from disk first (files are source of truth)
        profile_obj = profile_map.get(model.profile)
        if profile_obj is not None and profile_obj.is_local():
            use_cache = model.model_dir.startswith(profile_obj.cache_dir)
            try:
                await asyncio.to_thread(
                    remove_model,
                    repo_id=model.repo,
                    profile=profile_obj,
                    revision=model.revision,
                    use_cache=use_cache,
                )
                logger.debug(
                    f"Deleted files for model {model.repo} revision {model.revision}"
                )
            except FileNotFoundError:
                # Files already gone - proceed with DB cleanup
                logger.debug(
                    f"Files already removed for {model.repo} revision {model.revision}"
                )
            except PermissionError as e:
                logger.error(f"Permission denied deleting {model.repo}: {e}")
                res.append(
                    DeleteModelResponse(
                        model_id=str(model.id),
                        status="error",
                        message="Permission denied: cannot delete model files",
                    )
                )
                continue
            except OSError as e:
                logger.error(f"OS error deleting {model.repo}: {e}")
                res.append(
                    DeleteModelResponse(
                        model_id=str(model.id),
                        status="error",
                        message=f"OS error: {e}",
                    )
                )
                continue

        # Delete from database (only if file deletion succeeded or files already gone)
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
            logger.error(f"Failed to delete model {model.id} from database: {e}")
            res.append(
                DeleteModelResponse(
                    model_id=str(model.id),
                    status="error",
                    message=f"Failed to delete from database: {e}",
                )
            )

    return res


@dataclass
class ModelUpdateResponse:
    model_id: str
    status: str  # "updated", "up_to_date", "update_available", "error"
    old_revision: str | None = None
    new_revision: str | None = None
    message: str | None = None


@put("/api/models/{model_id:str}", guards=ENDPOINT_GUARDS)
async def update_model(
    model_id: str,
    session: AsyncSession,
    check_only: bool = False,
) -> ModelUpdateResponse:
    """Check for and optionally download the latest revision of a model.

    Args:
        model_id: UUID of the model to update
        check_only: If True, only check for updates without downloading

    Returns:
        ModelUpdateResponse with status and revision info
    """
    from huggingface_hub import model_info as hf_model_info
    from blackfish.server.models.model import add_model

    # 1. Get model from database
    query = sa.select(Model).where(Model.id == model_id)
    try:
        res = await session.execute(query)
    except StatementError:
        logger.error(f"{model_id} is not a valid UUID.")
        raise ValidationException(detail=f"{model_id} is not a valid UUID.")
    try:
        model = res.scalar_one()
    except NoResultFound:
        raise NotFoundException(detail=f"Model {model_id} not found")

    # 2. Get profile
    profiles = deserialize_profiles(blackfish_config.HOME_DIR)
    profile = next((p for p in profiles if p.name == model.profile), None)
    if profile is None:
        raise NotFoundException(detail=f"Profile {model.profile} not found")

    # 3. Only support local profiles for now
    if not isinstance(profile, LocalProfile):
        return ModelUpdateResponse(
            model_id=str(model.id),
            status="error",
            message="Update only supported for local profiles",
        )

    # 4. Get latest revision from Hugging Face
    try:
        token = getattr(profile, "token", None)
        info = hf_model_info(repo_id=model.repo, token=token)
        latest_revision = info.sha
        if latest_revision is None:
            return ModelUpdateResponse(
                model_id=str(model.id),
                status="error",
                message="Model info does not contain a revision SHA",
            )
    except Exception as e:
        logger.error(f"Failed to fetch model info for {model.repo}: {e}")
        return ModelUpdateResponse(
            model_id=str(model.id),
            status="error",
            message=f"Failed to fetch model info: {e}",
        )

    # 5. Check if we already have the latest revision (in any row for this repo/profile)
    existing_latest = await session.execute(
        sa.select(Model).where(
            Model.repo == model.repo,
            Model.profile == model.profile,
            Model.revision == latest_revision,
        )
    )
    if existing_latest.scalar_one_or_none():
        return ModelUpdateResponse(
            model_id=str(model.id),
            status="up_to_date",
            old_revision=model.revision,
            new_revision=latest_revision,
        )

    # 6. If check_only, return update available status
    if check_only:
        return ModelUpdateResponse(
            model_id=str(model.id),
            status="update_available",
            old_revision=model.revision,
            new_revision=latest_revision,
        )

    # 7. Download new revision using existing add_model function
    try:
        result = add_model(
            repo_id=model.repo,
            profile=profile,
            revision=latest_revision,
        )
        if result is None:
            raise Exception("Download failed - add_model returned None")
        new_model, path = result

        # 8. Update database record with new revision and path
        old_revision = model.revision
        model.revision = latest_revision
        model.model_dir = path
        session.add(model)

        return ModelUpdateResponse(
            model_id=str(model.id),
            status="updated",
            old_revision=old_revision,
            new_revision=latest_revision,
        )
    except Exception as e:
        logger.error(f"Failed to download update for {model.repo}: {e}")
        return ModelUpdateResponse(
            model_id=str(model.id),
            status="error",
            message=f"Failed to download update: {e}",
        )


# ============================================================================
# Model Download Endpoints
# ============================================================================


@dataclass
class CreateModelRequest:
    """Request to create a model record (used by CLI after local download)."""

    repo: str
    profile: str
    revision: str
    image: str
    model_dir: str
    metadata_: Optional[dict[str, Any]] = None


@dataclass
class DownloadModelRequest:
    """Request to download a model from Hugging Face."""

    repo_id: str
    profile: str
    revision: Optional[str] = None
    use_cache: bool = False


@dataclass
class DownloadModelResponse:
    """Response containing download task information."""

    task_id: str
    status: str
    repo_id: str
    message: Optional[str] = None


async def _run_download_task(
    task_id: str,
    repo_id: str,
    profile: Profile,
    revision: Optional[str],
    db_url: str,
    use_cache: bool = False,
) -> None:
    """Background task to download a model.

    Runs in a thread pool to avoid blocking the event loop.
    Updates the DownloadTask record with status as it progresses.
    """
    from sqlalchemy.ext.asyncio import (
        create_async_engine,
        AsyncSession,
        async_sessionmaker,
    )
    from blackfish.server.models.model import add_model

    engine = create_async_engine(db_url)
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def update_task_status(
        status: str, error_message: str | None = None, model_id: UUID | None = None
    ) -> None:
        async with async_session_factory() as session:
            task = await session.get(DownloadTask, task_id)
            if task:
                task.status = status
                if error_message:
                    task.error_message = error_message
                if model_id:
                    task.model_id = model_id
                await session.commit()

    try:
        # Update status to DOWNLOADING
        await update_task_status(DownloadStatus.DOWNLOADING)

        # Run the blocking download in a thread pool
        new_model, snapshot_path = await asyncio.to_thread(
            add_model, repo_id, profile, revision, use_cache
        )

        # model_dir is the parent of snapshots directory (2 levels up from snapshot path)
        model_dir = str(Path(snapshot_path).parent.parent)
        new_model.model_dir = model_dir

        # Add model to database
        async with async_session_factory() as session:
            # Check if model already exists
            query = sa.select(Model).where(
                Model.repo == repo_id,
                Model.profile == profile.name,
                Model.revision == new_model.revision,
            )
            existing = (await session.execute(query)).scalar_one_or_none()

            if existing:
                completed_model_id = existing.id
            else:
                session.add(new_model)
                await session.commit()
                completed_model_id = new_model.id

        await update_task_status(DownloadStatus.COMPLETED, model_id=completed_model_id)

    except Exception as e:
        logger.error(f"Download task {task_id} failed: {e}")
        await update_task_status(DownloadStatus.FAILED, error_message=str(e))
    finally:
        await engine.dispose()


@post("/api/models/download", guards=ENDPOINT_GUARDS)
async def download_model(
    data: DownloadModelRequest,
    session: AsyncSession,
) -> DownloadModelResponse:
    """Initiate a background model download.

    Creates a download task and starts downloading the model in the background.
    Use GET /api/models/downloads/{task_id} to poll for status.

    Args:
        data: Download request with repo_id, profile, and optional revision

    Returns:
        DownloadModelResponse with task_id to poll for status
    """
    # Validate repo_id format
    try:
        validate_repo_id(data.repo_id)
    except InvalidRepoIdError as e:
        raise ValidationException(detail=str(e))

    # Validate profile exists and is local
    profiles = deserialize_profiles(blackfish_config.HOME_DIR)
    profile = next((p for p in profiles if p.name == data.profile), None)
    if profile is None:
        raise NotFoundException(detail=f"Profile '{data.profile}' not found")
    if not isinstance(profile, LocalProfile):
        raise ValidationException(detail="Downloads only supported for local profiles")

    # Validate model exists on HuggingFace Hub before starting download
    token = getattr(profile, "token", None)
    try:
        hf_model_info(repo_id=data.repo_id, token=token, revision=data.revision)
    except RepositoryNotFoundError:
        raise NotFoundException(
            detail=f"Model '{data.repo_id}' not found on HuggingFace Hub"
        )

    # Check for existing in-progress download
    existing_query = sa.select(DownloadTask).where(
        DownloadTask.repo_id == data.repo_id,
        DownloadTask.profile == data.profile,
        DownloadTask.status.in_([DownloadStatus.PENDING, DownloadStatus.DOWNLOADING]),
    )
    if data.revision:
        existing_query = existing_query.where(DownloadTask.revision == data.revision)
    existing_task = (await session.execute(existing_query)).scalar_one_or_none()
    if existing_task:
        raise ValidationException(
            detail=f"Download already in progress for '{data.repo_id}'"
        )

    # Create download task record
    task = DownloadTask(
        repo_id=data.repo_id,
        profile=data.profile,
        revision=data.revision,
        status=DownloadStatus.PENDING,
    )
    session.add(task)
    await session.flush()
    task_id = str(task.id)

    # Get database URL for background task
    db_url = f"sqlite+aiosqlite:///{blackfish_config.HOME_DIR}/app.sqlite"

    # Start background download
    asyncio.create_task(
        _run_download_task(
            task_id, data.repo_id, profile, data.revision, db_url, data.use_cache
        )
    )

    return DownloadModelResponse(
        task_id=task_id,
        status=DownloadStatus.PENDING,
        repo_id=data.repo_id,
        message="Download started",
    )


@get("/api/models/downloads/{task_id:str}", guards=ENDPOINT_GUARDS)
async def get_download_task(task_id: str, session: AsyncSession) -> DownloadTask:
    """Get the status of a download task.

    Args:
        task_id: UUID of the download task

    Returns:
        DownloadTask with current status
    """
    try:
        task = await session.get(DownloadTask, task_id)
    except StatementError:
        raise ValidationException(detail=f"{task_id} is not a valid UUID.")

    if task is None:
        raise NotFoundException(detail=f"Download task {task_id} not found")

    return task


@get("/api/models/downloads", guards=ENDPOINT_GUARDS)
async def list_download_tasks(
    session: AsyncSession,
    status: Optional[str] = None,
    profile: Optional[str] = None,
) -> list[DownloadTask]:
    """List download tasks, optionally filtered by status or profile.

    Args:
        status: Filter by status (pending, downloading, completed, failed)
        profile: Filter by profile name

    Returns:
        List of DownloadTask objects
    """
    query = sa.select(DownloadTask).order_by(DownloadTask.created_at.desc())

    if status:
        query = query.where(DownloadTask.status == status)
    if profile:
        query = query.where(DownloadTask.profile == profile)

    result = await session.execute(query)
    return list(result.scalars().all())


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


@get("/api/profiles/{name: str}/resources", guards=ENDPOINT_GUARDS)
async def get_profile_resources(name: str) -> dict[str, Any]:
    """Get resource tiers and time constraints for a profile.

    Returns partitions with their available tiers, and time constraints.
    Used by the frontend to populate the tier selection UI.
    """
    try:
        profile = deserialize_profile(blackfish_config.HOME_DIR, name)
    except FileNotFoundError:
        raise NotFoundException(detail="Profile config not found.")

    if profile is None:
        raise NotFoundException(detail="Profile not found.")

    if not isinstance(profile, SlurmProfile):
        raise NotFoundException(
            detail="Resource tiers are only available for Slurm profiles."
        )

    # Load resource specs from profile's cache directory
    specs: Optional[ResourceSpecs] = None

    if profile.host in ("localhost", "127.0.0.1"):
        specs = load_resource_specs(profile.cache_dir)
    else:
        specs_path = f"{profile.cache_dir}/resource_specs.yaml"
        try:
            content = sftp.read_file(profile, specs_path)
            specs = parse_resource_specs(content)
        except NotFoundException:
            logger.debug(f"No resource_specs.yaml found at {specs_path}")
        except Exception as e:
            logger.warning(f"Failed to fetch remote resource_specs.yaml: {e}")

    if specs is None:
        logger.debug(f"Using default resource specs for profile '{name}'")
        specs = get_default_specs()

    return specs.to_dict()


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


async def resume_incomplete_downloads(app: Litestar) -> None:
    """Resume any downloads that were interrupted by server shutdown.

    Called on app startup. Finds PENDING or DOWNLOADING tasks and restarts them.
    """
    from sqlalchemy.ext.asyncio import (
        create_async_engine,
        AsyncSession,
        async_sessionmaker,
    )

    db_url = f"sqlite+aiosqlite:///{blackfish_config.HOME_DIR}/app.sqlite"
    engine = create_async_engine(db_url)
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        async with async_session_factory() as session:
            # Find incomplete downloads
            query = sa.select(DownloadTask).where(
                DownloadTask.status.in_(
                    [DownloadStatus.PENDING, DownloadStatus.DOWNLOADING]
                )
            )
            result = await session.execute(query)
            incomplete_tasks = list(result.scalars().all())

            if not incomplete_tasks:
                logger.debug("No incomplete downloads to resume")
                return

            logger.info(f"Resuming {len(incomplete_tasks)} incomplete download(s)")

            profiles = deserialize_profiles(blackfish_config.HOME_DIR)

            for task in incomplete_tasks:
                profile = next((p for p in profiles if p.name == task.profile), None)
                if profile is None:
                    logger.warning(
                        f"Profile {task.profile} not found, marking task {task.id} as failed"
                    )
                    task.status = DownloadStatus.FAILED
                    task.error_message = f"Profile {task.profile} not found"
                    continue

                if not isinstance(profile, LocalProfile):
                    logger.warning(
                        f"Profile {task.profile} is not local, marking task {task.id} as failed"
                    )
                    task.status = DownloadStatus.FAILED
                    task.error_message = "Downloads only supported for local profiles"
                    continue

                # Reset status to PENDING and restart
                task.status = DownloadStatus.PENDING
                logger.info(
                    f"Resuming download: {task.repo_id} for profile {task.profile}"
                )

                asyncio.create_task(
                    _run_download_task(
                        str(task.id),
                        task.repo_id,
                        profile,
                        task.revision,
                        db_url,
                    )
                )

            await session.commit()
    finally:
        await engine.dispose()


app = Litestar(
    path=blackfish_config.BASE_PATH,
    on_startup=[resume_incomplete_downloads],
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
        get_model,
        get_models,
        create_model,
        update_model,
        delete_model,
        delete_models,
        download_model,
        get_download_task,
        list_download_tasks,
        read_profiles,
        read_profile,
        create_profile,
        update_profile,
        delete_profile,
        repair_profile,
        get_cluster_status,
        get_profile_resources,
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
