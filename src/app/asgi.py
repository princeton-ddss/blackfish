import os
from os import urandom
from base64 import b64encode
from dataclasses import dataclass
from collections.abc import AsyncGenerator
from typing import Optional
import asyncio
import itertools
from pathlib import Path
from secrets import compare_digest

from fabric.connection import Connection

import sqlalchemy as sa
from sqlalchemy.orm import Mapped
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from litestar import Litestar, Request, get, post, put, delete
from litestar.utils.module_loader import module_to_os_path
from litestar.datastructures import State
from litestar.dto import DTOConfig, DataclassDTO
from advanced_alchemy.extensions.litestar import (
    AsyncSessionConfig,
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
)
from litestar.status_codes import HTTP_409_CONFLICT
from litestar.config.cors import CORSConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.static_files import create_static_files_router
from litestar.template.config import TemplateConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template, Redirect
from litestar.connection import ASGIConnection
from litestar.handlers.base import BaseRouteHandler
from litestar.response.redirect import ASGIRedirectResponse
from litestar.types import ASGIApp, Scope, Receive, Send
from litestar.datastructures.secret_values import SecretString
from litestar.middleware.base import MiddlewareProtocol
from litestar.middleware.session.client_side import CookieBackendConfig

from app.logger import logger
from app.services.base import Service
from app.services.speech_recognition import SpeechRecognition
from app.services.text_generation import TextGeneration
from app.config import config as blackfish_config
from app.config import BlackfishProfile, SlurmRemote, LocalProfile


class Model(UUIDAuditBase):
    __tablename__ = "model"
    repo: Mapped[str]  # e.g., bigscience/bloom-560m
    profile: Mapped[str]  # e.g.,  hpc
    revision: Mapped[str]


# --- Auth ---
AUTH_TOKEN = b64encode(urandom(32)).decode("utf-8")


class AuthMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if Request(scope).session is None:
            logger.debug(
                "from AuthMiddleware: no session found => redirect to dashboard login"
            )
            response = ASGIRedirectResponse(path="/ui/login")
            await response(scope, receive, send)
        elif Request(scope).session.get("token") is None:
            logger.debug(
                "from AuthMiddleware: no token found => redirect to dashboard login"
            )
            response = ASGIRedirectResponse(path="/ui/login")
            await response(scope, receive, send)
        else:
            logger.debug(f"from AuthMiddleware: {Request(scope).session}")
            await self.app(scope, receive, send)


def auth_guard(
    connection: ASGIConnection, _: BaseRouteHandler
) -> Optional[NotAuthorizedException]:
    if connection.session is None:
        logger.debug("from auth_guard: session is None => NotAuthorizedException")
        raise NotAuthorizedException
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
    logger.info(f"Blackfish API is protected with AUTH_TOKEN={AUTH_TOKEN}.")
else:
    logger.warning(
        """Blackfish is running in debug mode. API endpoints are unprotected. In a production
          environment, set BLACKFISH_DEV_MODE=False to require user authentication."""
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


async def find_models(profile: BlackfishProfile) -> list[Model]:
    """Find all model revisions associated with a given profile.

    The model files associated with a given profile are determined by the contents
    found in `profile.home_dir` and `profile.cache_dir`. We assume that model files
    are stored using the same schema as Hugging Face.
    """
    models = []
    if isinstance(profile, SlurmRemote):
        logger.debug(f"Connecting to sftp::{profile.user}@{profile.host}")
        with Connection(
            host=profile.host, user=profile.user
        ) as conn, conn.sftp() as sftp:
            default_dir = os.path.join(profile.cache_dir, "models")
            logger.debug(f"Searching default directory {default_dir}")
            try:
                model_dirs = sftp.listdir(default_dir)
                logger.debug(f"Found model directories: {model_dirs}")
                for model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                    _, namespace, model = model_dir.split("--")
                    repo = f"{namespace}/{model}"
                    revisions = sftp.listdir(
                        os.path.join(default_dir, model_dir, "snapshots")
                    )
                    for revision in revisions:
                        models.append(
                            Model(
                                repo=repo,
                                profile=profile.name,
                                revision=revision,
                            )
                        )
            except FileNotFoundError as e:
                logger.error(f"Failed to list directory: {e}")
            backup_dir = os.path.join(profile.home_dir, "models")
            logger.debug(f"Searching backup directory: {backup_dir}")
            try:
                model_dirs = sftp.listdir(backup_dir)
                logger.debug(f"Found model directories: {model_dirs}")
                for model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                    _, namespace, model = model_dir.split("--")
                    repo = f"{namespace}/{model}"
                    revisions = sftp.listdir(
                        os.path.join(backup_dir, model_dir, "snapshots")
                    )
                    for revision in revisions:
                        models.append(
                            Model(
                                repo=repo,
                                profile=profile.name,
                                revision=revision,
                            )
                        )
            except FileNotFoundError as e:
                logger.error(f"Failed to list directory: {e}")
            return models
    elif isinstance(profile, LocalProfile):
        default_dir = os.path.join(profile.cache_dir, "models")
        logger.debug(f"Searching default directory {default_dir}")
        try:
            model_dirs = os.listdir(default_dir)
            logger.debug(f"Found model directories: {model_dirs}")
            for model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                _, namespace, model = model_dir.split("--")
                repo = f"{namespace}/{model}"
                revisions = os.listdir(
                    os.path.join(default_dir, model_dir, "snapshots")
                )
                for revision in revisions:
                    models.append(
                        Model(
                            repo=repo,
                            profile=profile.name,
                            revision=revision,
                        )
                    )
        except FileNotFoundError as e:
            logger.error(f"Failed to list directory: {e}")

        backup_dir = os.path.join(profile.home_dir, "models")
        logger.debug(f"Searching backup directory: {backup_dir}")
        try:
            model_dirs = os.listdir(backup_dir)
            logger.debug(f"Found model directories: {model_dirs}")
            for model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                _, namespace, model = model_dir.split("--")
                repo = f"{namespace}/{model}"
                revisions = os.listdir(os.path.join(backup_dir, model_dir, "snapshots"))
                for revision in revisions:
                    models.append(
                        Model(
                            repo=repo,
                            profile=profile.name,
                            revision=revision,
                        )
                    )
        except FileNotFoundError as e:
            logger.error(f"Failed to list directory: {e}")
        return models
    else:
        raise NotImplementedError


# --- Pages ---
@get(path="/ui", middleware=PAGE_MIDDLEWARE)
async def dashboard() -> Template:
    return Template(template_name="index.html")


@get(path="/ui/login")
async def dashboard_login(request: Request) -> Template | Redirect:
    token = request.session.get("token")
    if token is not None:
        if compare_digest(token, AUTH_TOKEN):
            logger.debug(
                "from dashboard_login: user already authenticated => redirect dashboard"
            )
            return Redirect("/ui")
    return Template(template_name="login.html")


@get(path="/ui/text-generation", middleware=PAGE_MIDDLEWARE)
async def text_generation() -> Template:
    return Template(template_name="text-generation.html")


@get(path="/ui/speech-recognition", middleware=PAGE_MIDDLEWARE)
async def speech_recognition() -> Template:
    return Template(template_name="speech-recognition.html")


# --- Endpoints ---
@get("/", guards=ENDPOINT_GUARDS)
async def index(state: State) -> dict:
    return {
        "BLACKFISH_HOST": state.BLACKFISH_HOST,
        "BLACKFISH_PORT": state.BLACKFISH_PORT,
        "BLACKFISH_HOME_DIR": state.BLACKFISH_HOME_DIR,
        "BLACKFISH_DEBUG": state.BLACKFISH_DEBUG,
    }


@dataclass
class LoginPayload:
    token: SecretString


@post("/login")
async def login(data: LoginPayload, request: Request) -> Optional[Redirect]:
    token = request.session.get("token")
    if token is not None:
        if compare_digest(token, AUTH_TOKEN):
            logger.debug("from login: user already logged int => return None")
            return None
    token = data.token.get_secret()
    if compare_digest(token, AUTH_TOKEN):
        request.set_session({"token": token})
        logger.debug(f"from login: added token:{token} to session => redirect /ui")
    else:
        logger.debug("from login: invalid token => return None")
        return Redirect("/ui/login/?success=false")
    return Redirect("/ui")


@post("/logout", guards=ENDPOINT_GUARDS)
async def logout(request: Request) -> Redirect:
    token = request.session.get("token")
    if token is not None:
        request.set_session({"token": None})
        logger.debug("from logout: reset session => redirect /ui/login")
    return Redirect("/ui/login")


@dataclass
class ServiceRequest:
    name: str  # TODO: optional w/ default by name generator
    image: str
    model: str
    job_type: str
    container_options: dict
    job_options: dict
    user: Optional[str] = None
    host: Optional[str] = "localhost"
    port: Optional[str] = None


class ServiceRequestDTO(DataclassDTO[ServiceRequest]):
    config = DTOConfig()


@dataclass
class StopServiceRequest:
    delay: int = 0
    timeout: bool = False
    failed: bool = False


def build_service(data: ServiceRequest):
    """Convert a service request into a service object based on the requested image."""

    if data.image == "text_generation":
        return TextGeneration(
            name=data.name,  # optional
            image=data.image,
            model=data.model,
            user=data.user,  # optional (required to run remote services)
            host=data.host,  # optional (required to run remote services)
            job_type=data.job_type,
        )
    elif data.image == "speech_recognition":
        return SpeechRecognition(
            name=data.name,  # optional
            image=data.image,
            model=data.model,
            user=data.user,  # optional (required to run remote services)
            host=data.host,  # optional (required to run remote services)
            job_type=data.job_type,
        )
    else:
        raise Exception(f"Service image should be one of: {SERVICE_TYPES}")


@post("/services", dto=ServiceRequestDTO, guards=ENDPOINT_GUARDS)
async def run_service(
    data: ServiceRequest, session: AsyncSession, state: State
) -> Service:
    try:
        service = build_service(data)
    except Exception as e:
        logger.error(e)
    try:
        await service.start(
            session,
            state,
            container_options=data.container_options,
            job_options=data.job_options,
        )
    except Exception as e:
        logger.error(f"Unable to start service. Error: {e}")
        return InternalServerException()

    return service


@put("/services/{service_id:str}/stop", guards=ENDPOINT_GUARDS)
async def stop_service(
    service_id: str, data: StopServiceRequest, session: AsyncSession, state: State
) -> Service:
    service = await get_service(service_id, session)
    await service.stop(
        session, state, delay=data.delay, timeout=data.timeout, failed=data.failed
    )

    return service


@get("/services/{service_id:str}", guards=ENDPOINT_GUARDS)
async def refresh_service(
    service_id: str, session: AsyncSession, state: State
) -> Service:
    service = await get_service(service_id, session)
    try:
        await service.refresh(session, state)
    except Exception as e:
        logger.error(f"Failed to refresh service: {e}")

    return service


@get("/services", guards=ENDPOINT_GUARDS)
async def fetch_services(
    session: AsyncSession,
    state: State,
    image: Optional[str] = None,
    status: Optional[str] = None,
    host: Optional[str] = None,
    backend: Optional[str] = None,
) -> list[Service]:
    query_filter = {}
    if image is not None:
        query_filter["image"] = image
    if status is not None:
        query_filter["status"] = status
    if host is not None:
        query_filter["host"] = host
    if backend is not None:
        query_filter["backend"] = backend

    query = sa.select(Service)  # .filter_by(**query_filter)
    res = await session.execute(query)
    services = res.scalars().all()

    await asyncio.gather(*[s.refresh(session, state) for s in services])

    return services


@delete("/services/{service_id:str}", guards=ENDPOINT_GUARDS)
async def delete_service(service_id: str, session: AsyncSession, state: State) -> None:
    service = await get_service(service_id, session)
    await service.refresh(session, state)
    if service.status in ["STOPPED", "TIMEOUT", "FAILED"]:
        query = sa.delete(Service).where(Service.id == service_id)
        await session.execute(query)
    else:
        logger.warning(
            f"Service is still running (status={service.status}). Aborting delete."
        )
        # TODO: return failure status code and message


@get("/models", guards=ENDPOINT_GUARDS)
async def get_models(
    session: AsyncSession,
    state: State,
    profile: Optional[str] = None,
    refresh: Optional[bool] = False,
) -> list[Model]:
    query_filter = {}
    if profile is not None:
        query_filter["profile"] = profile

    if refresh:
        # TODO: combine delete and add into single transaction?
        if profile is not None:
            models = await find_models(state.BLACKFISH_PROFILES[profile])
            logger.debug("Deleting existing models...")
            query = sa.delete(Model).where(Model.profile == profile)
            await session.execute(query)
        else:
            res = await asyncio.gather(
                *[find_models(profile) for profile in state.BLACKFISH_PROFILES.values()]
            )
            models = list(itertools.chain(*res))  # list[list[dict]] -> list[dict]
            logger.debug("Deleting existing models...")
            query = sa.delete(Model)
            await session.execute(query)
        logger.debug("Inserting refreshed models...")
        session.add_all(models)
        await session.flush()
        return models
    else:
        query = sa.select(Model).filter_by(**query_filter)
        res = await session.execute(query)
        return res.scalars().all()  # list[Model]


@get("/models/{model_id:str}", guards=ENDPOINT_GUARDS)
async def get_model(model_id: str, session: AsyncSession) -> Model:
    logger.info(f"Model={model_id}")
    query = sa.select(Model).where(Model.id == model_id)
    res = await session.execute(query)
    try:
        return res.scalar_one()
    except NoResultFound as e:
        raise NotFoundException(detail=f"Model {model_id} not found") from e


@post("/models", guards=ENDPOINT_GUARDS)
async def create_model(data: Model, session: AsyncSession) -> Model:
    session.add(data)
    return data


@delete("/models/{model_id:str}", guards=ENDPOINT_GUARDS)
async def delete_model(model_id: str, session: AsyncSession) -> None:
    query = sa.delete(Model).where(Model.id == model_id)
    await session.execute(query)


@get("/images", guards=ENDPOINT_GUARDS)
async def get_images():
    pass


@get("/images/{image_id:str}", guards=ENDPOINT_GUARDS)
async def get_image_details():
    pass


# --- Config ---
session_config = AsyncSessionConfig(expire_on_commit=False)

BASE_DIR = module_to_os_path("app")

db_config = SQLAlchemyAsyncConfig(
    connection_string=(
        f"sqlite+aiosqlite:///{blackfish_config.BLACKFISH_HOME_DIR}/app.sqlite"
    ),
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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
    directory=Path(__file__).parent.parent / "dist",
    engine=JinjaTemplateEngine,
)

session_config = CookieBackendConfig(secret=urandom(16))

next_server = create_static_files_router(
    path="/_next", directories=["src/dist/_next"], html_mode=True
)

img_server = create_static_files_router(
    path="/img", directories=["src/dist/img"], html_mode=True
)


app = Litestar(
    route_handlers=[
        dashboard,
        dashboard_login,
        text_generation,
        speech_recognition,
        index,
        login,
        logout,
        run_service,
        stop_service,
        refresh_service,
        fetch_services,
        delete_service,
        create_model,
        get_model,
        get_models,
        delete_model,
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
