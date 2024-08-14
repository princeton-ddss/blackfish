import os
from dataclasses import dataclass
from collections.abc import AsyncGenerator
from typing import Optional
import asyncio
import itertools

from fabric.connection import Connection

import sqlalchemy as sa
from sqlalchemy.orm import Mapped
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from litestar import Litestar, get, post, put, delete
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
    InternalServerException,
)
from litestar.status_codes import HTTP_409_CONFLICT
from litestar.config.cors import CORSConfig

from app.logger import logger
from app.services.base import Service
from app.services.nlp.text_generation import TextGeneration
from app.config import config as blackfish_config
from app.config import BlackfishProfile, SlurmRemote, LocalProfile


class Model(UUIDAuditBase):
    __tablename__ = "model"
    repo: Mapped[str]  # e.g., bigscience/bloom-560m
    profile: Mapped[str]  # e.g.,  hpc
    revision: Mapped[str]


JOB_TYPES = ["text_generation"]

# -------------------------------------------------------------------------------------------- #
# API                                                                                          #
# -------------------------------------------------------------------------------------------- #
# run               POST        /services              Start the job and create the service.   #
# stop              PUT         /services/:id/stop     Stop the job and update the service.    #
# ls                GET         /services              Check all jobs and update all services. #
# ls                GET         /services/:id          Check the job and update the service.   #
# rm                DELETE      /services/:id          Delete the service.                     #
# models            GET         /models                List all models available.              #
# images            GET         /images                List all images available.              #
# image_details     GET         /images/:name/details  Provide details for a specific image.   #
# -------------------------------------------------------------------------------------------- #


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


async def get_service(service_id: str, session: AsyncSession) -> Service:
    query = sa.select(Service).where(Service.id == service_id)
    res = await session.execute(query)
    try:
        return res.scalar_one()
    except NoResultFound as e:
        raise NotFoundException(detail=f"Service {service_id} not found") from e


async def find_models(profile: BlackfishProfile) -> list[Model]:
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


def build_service(data: ServiceRequest):
    if data.image == "text_generation":
        return TextGeneration(
            name=data.name,  # optional
            image=data.image,
            model=data.model,
            user=data.user,  # optional (required to run remote services)
            host=data.host,  # optional (required to run remote services)
            job_type=data.job_type,
        )
    else:
        raise Exception(f"Service image should be one of: {JOB_TYPES}")


@get("/")
async def index(state: State) -> dict:
    return f"""Welcome to Blackfish!

BLACKFISH_HOST: {state.BLACKFISH_HOST}
BLACKFISH_PORT: {state.BLACKFISH_PORT}
BLACKFISH_HOME_DIR: {state.BLACKFISH_HOME_DIR}
BLACKFISH_DEBUG: {state.BLACKFISH_DEBUG}

PROFILES:
{state.BLACKFISH_PROFILES}
"""


@post("/services", dto=ServiceRequestDTO)
async def run_service(
    data: ServiceRequest, session: AsyncSession, state: State
) -> Service:
    try:
        service = build_service(data)
    except Exception as e:
        print(e)
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


@put("/services/{service_id:str}/stop")
async def stop_service(
    service_id: str, data: StopServiceRequest, session: AsyncSession, state: State
) -> Service:
    service = await get_service(service_id, session)
    await service.stop(
        session, state, delay=data.delay, timeout=data.timeout, failed=data.failed
    )

    return service


@get("/services/{service_id:str}")
async def refresh_service(
    service_id: str, session: AsyncSession, state: State
) -> Service:
    service = await get_service(service_id, session)
    try:
        await service.refresh(session, state)
    except Exception as e:
        logger.error(f"Failed to refresh service: {e}")

    return service


@get("/services")
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


@delete("/services/{service_id:str}")
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


@get("/models")
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


@get("/models/{model_id:str}")
async def get_model(model_id: str, session: AsyncSession) -> Model:
    logger.info(f"Model={model_id}")
    query = sa.select(Model).where(Model.id == model_id)
    res = await session.execute(query)
    try:
        return res.scalar_one()
    except NoResultFound as e:
        raise NotFoundException(detail=f"Model {model_id} not found") from e


@post("/models")
async def create_model(data: Model, session: AsyncSession) -> Model:
    session.add(data)
    return data


@delete("/models/{model_id:str}")
async def delete_model(model_id: str, session: AsyncSession) -> None:
    query = sa.delete(Model).where(Model.id == model_id)
    await session.execute(query)


@get("/images")
async def get_images():
    pass


@get("/images/{image_id:str}")
async def get_image_details():
    pass


session_config = AsyncSessionConfig(expire_on_commit=False)

db_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///app.sqlite",
    metadata=UUIDAuditBase.metadata,
    create_all=True,
    alembic_config=AlembicAsyncConfig(
        version_table_name="ddl_version",
        script_config="migrations/alembic.ini",
        script_location="migrations",
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

app = Litestar(
    route_handlers=[
        index,
        run_service,
        stop_service,
        refresh_service,
        fetch_services,
        delete_service,
        create_model,
        get_model,
        get_models,
        delete_model,
    ],
    dependencies={"session": session_provider},
    plugins=[SQLAlchemyPlugin(db_config)],
    logging_config=None,  # disable Litestar logger (we're using our own)
    state=State(blackfish_config.as_dict()),
    cors_config=cors_config,
)
