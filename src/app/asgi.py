import os
from os import urandom
import json
import aiohttp
from aiohttp.typedefs import StrOrURL
import requests
from datetime import datetime
from base64 import b64encode
from dataclasses import dataclass
from collections.abc import AsyncGenerator
from typing import Optional, Tuple, Any
from enum import StrEnum
import asyncio
import itertools
from pathlib import Path
from secrets import compare_digest
from fabric.connection import Connection
from paramiko.sftp_client import SFTPClient
from pydantic import BaseModel

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Result

from litestar import Litestar, Request, get, post, put, delete
from litestar.utils.module_loader import module_to_os_path
from litestar.datastructures import State
from advanced_alchemy.extensions.litestar import (
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
    AlembicAsyncConfig,
)
from advanced_alchemy.base import UUIDAuditBase
from litestar.exceptions import (
    ClientException,
    NotFoundException,
    NotAuthorizedException,
    InternalServerException,
    HTTPException,
    ValidationException,
)
from litestar.status_codes import HTTP_409_CONFLICT
from litestar.config.cors import CORSConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.static_files import create_static_files_router
from litestar.template.config import TemplateConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template, Redirect, Stream
from litestar.connection import ASGIConnection
from litestar.handlers.base import BaseRouteHandler
from litestar.response.redirect import ASGIRedirectResponse
from litestar.types import ASGIApp, Scope, Receive, Send
from litestar.datastructures.secret_values import SecretString
from litestar.middleware.base import MiddlewareProtocol
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.response import File

from app.logger import logger
from app.services.base import Service, ServiceStatus
from app.services.speech_recognition import SpeechRecognition, SpeechRecognitionConfig
from app.services.text_generation import TextGeneration, TextGenerationConfig
from app.config import config as blackfish_config, ContainerProvider
from app.utils import find_port
from app.models.profile import (
    serialize_profiles,
    serialize_profile,
    SlurmProfile,
    LocalProfile,
    BlackfishProfile as Profile,
)
from app.models.model import Model
from app.job import JobConfig, LocalJobConfig, SlurmJobConfig, JobScheduler


# --- Auth ---
AUTH_TOKEN = b64encode(urandom(32)).decode("utf-8")


class AuthMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__()
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if Request(scope).session is None:
            logger.debug(
                "from AuthMiddleware: no session found => redirect to dashboard login"
            )
            response = ASGIRedirectResponse(path="/login")
            await response(scope, receive, send)
        elif Request(scope).session.get("token") is None:
            logger.debug(
                "from AuthMiddleware: no token found => redirect to dashboard login"
            )
            response = ASGIRedirectResponse(path="/login")
            await response(scope, receive, send)
        else:
            logger.debug(f"from AuthMiddleware: {Request(scope).session}")
            await self.app(scope, receive, send)


def auth_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:  # type: ignore
    token = connection.session.get("token")
    if token is None:
        logger.debug("from auth_guard: session.token is None => NotAuthorizedException")
        raise NotAuthorizedException
    if not compare_digest(token, AUTH_TOKEN):
        logger.debug("from auth_guard: invalid token => NotAuthorizedException")
        raise NotAuthorizedException


SERVICE_TYPES = ["text_generation", "speech_recognition"]


PAGE_MIDDLEWARE = [] if blackfish_config.DEV_MODE else [AuthMiddleware]
ENDPOINT_GUARDS = [] if blackfish_config.DEV_MODE else [auth_guard]
if not blackfish_config.DEV_MODE:
    logger.info(f"Blackfish API is protected with AUTH_TOKEN = {AUTH_TOKEN}")
else:
    logger.warning(
        """Blackfish is running in debug mode. API endpoints are unprotected. In a production
          environment, set BLACKFISH_DEV_MODE=0 to require user authentication."""
    )


# --- Utils ---
async def get_service(service_id: str, session: AsyncSession) -> Service:
    """Query a single service ID from the application database and raise a `NotFoundException`
    if the service is missing.
    """
    query = sa.select(Service).where(Service.id == service_id)
    res = await session.execute(query)
    try:
        return res.scalar_one()
    except NoResultFound as e:
        raise NotFoundException(detail=f"Service {service_id} not found") from e


ModelInfoResult = dict[str, str]


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
    return Redirect("/dashboard")


@get(path="/dashboard", middleware=PAGE_MIDDLEWARE)
async def dashboard() -> Template:
    return Template(template_name="dashboard.html")


@get(path="/login")
async def dashboard_login(request: Request) -> Template | Redirect:  # type: ignore
    token = request.session.get("token")
    if token is not None:
        if compare_digest(token, AUTH_TOKEN):
            logger.debug(
                "from dashboard_login: user already authenticated => redirect dashboard"
            )
            return Redirect("/dashboard")
    return Template(template_name="login.html")


@get(path="/text-generation", middleware=PAGE_MIDDLEWARE)
async def text_generation() -> Template:
    return Template(template_name="text-generation.html")


@get(path="/speech-recognition", middleware=PAGE_MIDDLEWARE)
async def speech_recognition() -> Template:
    return Template(template_name="speech-recognition.html")


# --- Endpoints ---
@get("/api/info", guards=ENDPOINT_GUARDS)
async def info(state: State) -> dict[str, Any]:
    return {
        "HOST": state.HOST,
        "PORT": state.PORT,
        "STATIC_DIR": state.STATIC_DIR,
        "HOME_DIR": state.HOME_DIR,
        "DEBUG": state.DEBUG,
        "DEV_MODE": state.DEV_MODE,
        "CONTAINER_PROVIDER": state.CONTAINER_PROVIDER,
    }


@dataclass
class LoginPayload:
    token: SecretString


@post("/api/login")
async def login(data: LoginPayload, request: Request) -> Optional[Redirect]:  # type: ignore
    token = request.session.get("token")
    if token is not None:
        if compare_digest(token, AUTH_TOKEN):
            logger.debug("from login: user already logged int => return None")
            return None
    token = data.token.get_secret()
    if compare_digest(token, AUTH_TOKEN):
        request.set_session({"token": token})
        logger.debug(
            f"from login: added token:{token} to session => redirect /dashboard"
        )
    else:
        logger.debug("from login: invalid token => return None")
        return Redirect("/login/?success=false")
    return Redirect("/dashboard")


@post("/api/logout", guards=ENDPOINT_GUARDS)
async def logout(request: Request) -> Redirect:  # type: ignore
    token = request.session.get("token")
    if token is not None:
        request.set_session({"token": None})
        logger.debug("from logout: reset session => redirect /login")
    return Redirect("/login")


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
    path: str,
    hidden: bool = False,
) -> list[FileStats] | HTTPException:
    if os.path.isdir(path):
        try:
            return listdir(path, hidden=hidden)
        except PermissionError:
            logger.debug("Permission error raised")
            raise NotAuthorizedException(f"User not authorized to access {path}")
    else:
        logger.debug("Not found error")
        raise NotFoundException(detail=f"Path {path} does not exist.")


@get("/api/audio", guards=ENDPOINT_GUARDS, media_type="audio/wav")
async def get_audio(path: str) -> File | None:
    if os.path.isfile(path):
        if path.endswith(".wav") or path.endswith(".mp3"):
            return File(path=path)
        else:
            raise ValidationException("Path should specify a .wav or .mp3 file.")
    else:
        raise NotFoundException(f"{path} not found.")


@get("/api/ports", guards=ENDPOINT_GUARDS)
async def get_ports(request: Request) -> int:  # type: ignore
    """Find an available port on the server. This endpoint allows a UI to run local services."""
    return find_port()


ContainerConfig = TextGenerationConfig | SpeechRecognitionConfig


class Task(StrEnum):
    TextGeneration = "text_generation"
    SpeechRecognition = "speech_recognition"


class ServiceRequest(BaseModel):
    name: str
    image: Task
    repo_id: str
    profile: Profile
    container_config: ContainerConfig
    job_config: JobConfig
    provider: Optional[ContainerProvider] = None
    mount: Optional[str] = None
    grace_period: int = 180  # seconds


@dataclass
class LocalTextGenerationServiceRequest:
    name: str
    repo_id: str
    profile: LocalProfile
    container_config: TextGenerationConfig
    job_config: LocalJobConfig
    provider: ContainerProvider
    mount: Optional[str] = None
    grace_period: int = 180  # seconds


@dataclass
class SlurmTextGenerationServiceRequest:
    name: str
    repo_id: str
    container_config: TextGenerationConfig
    job_config: SlurmJobConfig
    profile: SlurmProfile
    mount: Optional[str] = None
    grace_period: int = 180  # seconds


@dataclass
class LocalSpeechRecognitionServiceRequest:
    name: str
    repo_id: str
    profile: LocalProfile
    container_config: SpeechRecognitionConfig
    job_config: LocalJobConfig
    provider: ContainerProvider
    mount: Optional[str] = None
    grace_period: int = 180  # seconds


@dataclass
class SlurmSpeechRecognitionServiceRequest:
    name: str
    repo_id: str
    container_config: SpeechRecognitionConfig
    job_config: SlurmJobConfig
    profile: SlurmProfile
    mount: Optional[str] = None
    grace_period: int = 180  # seconds


@dataclass
class StopServiceRequest:
    timeout: bool = False
    failed: bool = False


def build_service(data: ServiceRequest) -> Optional[Service]:
    """Convert a service request into a service object based on the requested image."""

    try:
        if data.image == Task.TextGeneration:
            if isinstance(data.profile, LocalProfile):
                return TextGeneration(
                    name=data.name,
                    model=data.repo_id,
                    profile=data.profile.name,
                    host="localhost",
                    home_dir=data.profile.home_dir,
                    cache_dir=data.profile.cache_dir,
                    provider=data.provider,
                    mount=data.mount,
                    grace_period=data.grace_period,
                )
            else:
                return TextGeneration(
                    name=data.name,
                    model=data.repo_id,
                    profile=data.profile.name,
                    host=data.profile.host,
                    user=data.profile.user,
                    home_dir=data.profile.home_dir,
                    cache_dir=data.profile.cache_dir,
                    scheduler=JobScheduler.Slurm,
                    mount=data.mount,
                    grace_period=data.grace_period,
                )
        elif data.image == Task.SpeechRecognition:
            if isinstance(data.profile, LocalProfile):
                return SpeechRecognition(
                    name=data.name,
                    image=Task.SpeechRecognition,
                    model=data.repo_id,
                    profile=data.profile.name,
                    host="localhost",
                    home_dir=data.profile.home_dir,
                    cache_dir=data.profile.cache_dir,
                    provider=data.provider,
                    mount=data.mount,
                    grace_period=data.grace_period,
                )
            else:
                return SpeechRecognition(
                    name=data.name,
                    image=Task.SpeechRecognition,
                    model=data.repo_id,
                    profile=data.profile.name,
                    host=data.profile.host,
                    user=data.profile.user,
                    home_dir=data.profile.home_dir,
                    cache_dir=data.profile.cache_dir,
                    scheduler=JobScheduler.Slurm,
                    mount=data.mount,
                    grace_period=data.grace_period,
                )
    except Exception:
        return None


@post("/api/services", guards=ENDPOINT_GUARDS)
async def run_service(
    data: ServiceRequest,
    session: AsyncSession,
    state: State,
) -> Optional[Service]:
    logger.debug(f"data={data}")
    service = build_service(data)

    if service is not None:
        try:
            await service.start(
                session,
                state,
                container_options=data.container_config,
                job_options=data.job_config,
            )
        except Exception as e:
            detail = f"Unable to start service. Error: {e}"
            logger.error(detail)
            raise InternalServerException(detail=detail)

    return service


def build_service_endpoints() -> None:
    """Create endpoints to run each profile-task combination."""
    pass


@post("/api/services/slurm/text-generation", guards=ENDPOINT_GUARDS)
async def run_slurm_text_generation_service(
    data: SlurmTextGenerationServiceRequest,
    session: AsyncSession,
    state: State,
) -> Optional[TextGeneration]:
    try:
        service = TextGeneration(
            name=data.name,
            image=Task.TextGeneration,
            model=data.repo_id,
            profile=data.profile.name,
            host=data.profile.host,
            user=data.profile.user,
            home_dir=data.profile.home_dir,
            cache_dir=data.profile.cache_dir,
            scheduler=JobScheduler.Slurm,
            mount=data.mount,
            grace_period=data.grace_period,
        )
    except Exception as e:
        logger.error(f"{e}")

    try:
        await service.start(
            session,
            state,
            container_options=data.container_config,
            job_options=data.job_config,
        )
    except Exception as e:
        detail = f"Unable to start service. Error: {e}"
        logger.error(detail)
        raise InternalServerException(detail=detail)

    return service


@post("/api/services/local/text-generation", guards=ENDPOINT_GUARDS)
async def run_local_text_generation_service(
    data: LocalTextGenerationServiceRequest,
    session: AsyncSession,
    state: State,
) -> Optional[TextGeneration]:
    service = TextGeneration(
        name=data.name,
        image=Task.TextGeneration,
        model=data.repo_id,
        profile=data.profile.name,
        host="localhost",
        home_dir=data.profile.home_dir,
        cache_dir=data.profile.cache_dir,
        provider=data.provider,
        mount=data.mount,
        grace_period=data.grace_period,
    )

    try:
        await service.start(
            session,
            state,
            container_options=data.container_config,
            job_options=data.job_config,
        )
    except Exception as e:
        detail = f"Unable to start service. Error: {e}"
        logger.error(detail)
        raise InternalServerException(detail=detail)

    return service


@post("/api/services/slurm/speech-recognition", guards=ENDPOINT_GUARDS)
async def run_slurm_speech_recognition_service(
    data: SlurmSpeechRecognitionServiceRequest,
    session: AsyncSession,
    state: State,
) -> Optional[SpeechRecognition]:
    try:
        service = SpeechRecognition(
            name=data.name,
            image=Task.SpeechRecognition,
            model=data.repo_id,
            profile=data.profile.name,
            host=data.profile.host,
            user=data.profile.user,
            home_dir=data.profile.home_dir,
            cache_dir=data.profile.cache_dir,
            scheduler=JobScheduler.Slurm,
            mount=data.mount,
            grace_period=data.grace_period,
        )
    except Exception as e:
        logger.error(f"{e}")

    try:
        await service.start(
            session,
            state,
            container_options=data.container_config,
            job_options=data.job_config,
        )
    except Exception as e:
        detail = f"Unable to start service. Error: {e}"
        logger.error(detail)
        raise InternalServerException(detail=detail)

    return service


@post("/api/services/local/speech-recognition", guards=ENDPOINT_GUARDS)
async def run_local_speech_recognition_service(
    data: LocalSpeechRecognitionServiceRequest,
    session: AsyncSession,
    state: State,
) -> Optional[SpeechRecognition]:
    service = SpeechRecognition(
        name=data.name,
        image=Task.SpeechRecognition,
        model=data.repo_id,
        profile=data.profile.name,
        host="localhost",
        home_dir=data.profile.home_dir,
        cache_dir=data.profile.cache_dir,
        provider=data.provider,
        mount=data.mount,
        grace_period=data.grace_period,
    )

    try:
        await service.start(
            session,
            state,
            container_options=data.container_config,
            job_options=data.job_config,
        )
    except Exception as e:
        detail = f"Unable to start service. Error: {e}"
        logger.error(detail)
        raise InternalServerException(detail=detail)

    return service


@put("/api/services/{service_id:str}/stop", guards=ENDPOINT_GUARDS)
async def stop_service(
    service_id: str, data: StopServiceRequest, session: AsyncSession, state: State
) -> Service:
    try:
        service = await get_service(service_id, session)
    except Exception as e:
        logger.error(f"Failed to fetch service: {e}.")

    await service.stop(session, state, timeout=data.timeout, failed=data.failed)
    return service


@get("/api/services/{service_id:str}", guards=ENDPOINT_GUARDS)
async def refresh_service(
    service_id: str, session: AsyncSession, state: State
) -> Service:
    try:
        service = await get_service(service_id, session)
    except Exception as e:
        logger.error(f"Failed to fetch service: {e}")
    try:
        await service.refresh(session, state)
    except Exception as e:
        logger.error(f"Failed to refresh service: {e}")

    return service


@get("/api/services", guards=ENDPOINT_GUARDS)
async def fetch_services(
    session: AsyncSession,
    state: State,
    id: Optional[str] = None,
    image: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    port: Optional[int] = None,
    name: Optional[str] = None,
    profile: Optional[str] = None,
) -> list[Service]:
    query_params = {
        "id": id,
        "image": image,
        "model": model,
        "status": status,
        "port": port,
        "name": name,
        "profile": profile,
    }

    query_params = {k: v for k, v in query_params.items() if v is not None}
    query = sa.select(Service).filter_by(**query_params)
    res = await session.execute(query)
    services = res.scalars().all()

    await asyncio.gather(*[s.refresh(session, state) for s in services])

    return list(services)


@delete("/api/services/{service_id:str}", guards=ENDPOINT_GUARDS)
async def delete_service(service_id: str, session: AsyncSession, state: State) -> None:
    try:
        service = await get_service(service_id, session)
    except Exception as e:
        logger.error(f"Failed to fetch service: {e}")
    await service.refresh(session, state)
    if service.status in [
        ServiceStatus.STOPPED,
        ServiceStatus.TIMEOUT,
        ServiceStatus.FAILED,
    ]:
        query = sa.delete(Service).where(Service.id == service_id)
        await session.execute(query)
    else:
        logger.warning(
            f"Service is still running (status={service.status}). Aborting delete."
        )
        # TODO: return failure status code and message


async def asyncget(url: StrOrURL) -> Any:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()


async def asyncpost(url: StrOrURL, data: Any, headers: Any) -> Any:
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, headers=headers) as response:
            return await response.json()


@post("/proxy/{port:int}/{cmd:str}", guards=ENDPOINT_GUARDS)
async def proxy_service(
    data: dict[Any, Any],
    port: int,
    cmd: str,
    streaming: Optional[bool],
    session: AsyncSession,
    state: State,
) -> Any | Stream:
    """Call a service via proxy and return the response.

    Setting query parameter `streaming` to `True` streams the response.
    """

    if streaming:

        async def generator() -> AsyncGenerator:  # type: ignore
            url = f"http://localhost:{port}/{cmd}"
            headers = {"Content-Type": "application/json"}
            with requests.post(url, json=data, headers=headers, stream=True) as res:
                for x in res.iter_content(chunk_size=None):
                    if x:
                        yield x

        return Stream(generator)
    else:
        res = await asyncpost(
            f"http://localhost:{port}/{cmd}",
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
    profiles = serialize_profiles(state.HOME_DIR)

    res: list[list[Model]] | Result[Tuple[Model]]
    if refresh:
        if profile is not None:
            models = await find_models(next(p for p in profiles if p.name == profile))
            logger.debug(
                "Deleting existing models WHERE model.profile == '{profile}'..."
            )
            try:
                delete_query = sa.delete(Model).where(Model.profile == profile)
                await session.execute(delete_query)
            except Exception as e:
                logger.error(f"Failed to execute query: {e}")
        else:
            res = await asyncio.gather(*[find_models(profile) for profile in profiles])
            models = list(itertools.chain(*res))  # list[list[dict]] -> list[dict]
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
            return list(filter(lambda x: x.image == image, models))
        else:
            return models
    else:
        logger.info("Querying model table...")

        query_filter = {}
        if profile is not None:
            query_filter["profile"] = profile
        if image is not None:
            query_filter["image"] = image

        select_query = sa.select(Model).filter_by(**query_filter)
        try:
            res = await session.execute(select_query)
            return list(res.scalars().all())
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return []


@get("/api/models/{model_id:str}", guards=ENDPOINT_GUARDS)
async def get_model(model_id: str, session: AsyncSession) -> Model:
    logger.info(f"Model={model_id}")
    query = sa.select(Model).where(Model.id == model_id)
    res = await session.execute(query)
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
    query = sa.delete(Model).where(Model.id == model_id)
    await session.execute(query)


@get("/api/profiles", guards=ENDPOINT_GUARDS)
async def read_profiles() -> list[Profile]:
    try:
        return serialize_profiles(blackfish_config.HOME_DIR)
    except FileNotFoundError:
        raise NotFoundException(detail="Profiles config not found.")


@get("/api/profiles/{name: str}", guards=ENDPOINT_GUARDS)
async def read_profile(name: str) -> Profile | None:
    try:
        profile = serialize_profile(blackfish_config.HOME_DIR, name)
    except Exception as e:
        raise InternalServerException(detail=f"Failed to serialize profile: {e}.")

    if profile is not None:
        return profile
    else:
        logger.error("Profile not found.")
        raise NotFoundException(detail="Profile not found.")


# --- Config ---
BASE_DIR = module_to_os_path("app")

db_config = SQLAlchemyAsyncConfig(
    connection_string=f"sqlite+aiosqlite:///{blackfish_config.HOME_DIR}/app.sqlite",
    metadata=UUIDAuditBase.metadata,
    create_all=True,
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
)

openapi_config = OpenAPIConfig(
    title="Blackfish API",
    version="0.0.1",
    render_plugins=[SwaggerRenderPlugin(path="/swagger")],
)

template_config = TemplateConfig(
    directory=blackfish_config.STATIC_DIR / "build",
    engine=JinjaTemplateEngine,
)

session_config = CookieBackendConfig(secret=urandom(16))

next_server = create_static_files_router(
    path="_next",
    directories=[blackfish_config.STATIC_DIR / "build" / "_next"],
    html_mode=True,
)

img_server = create_static_files_router(
    path="img",
    directories=[blackfish_config.STATIC_DIR / "build" / "img"],
    html_mode=True,
)


app = Litestar(
    route_handlers=[
        dashboard,
        dashboard_login,
        text_generation,
        speech_recognition,
        index,
        info,
        login,
        logout,
        get_ports,
        get_files,
        get_audio,
        run_service,
        run_slurm_text_generation_service,
        run_slurm_speech_recognition_service,
        run_local_text_generation_service,
        run_local_speech_recognition_service,
        stop_service,
        refresh_service,
        fetch_services,
        delete_service,
        proxy_service,
        create_model,
        get_model,
        get_models,
        delete_model,
        read_profiles,
        read_profile,
        next_server,
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
)
