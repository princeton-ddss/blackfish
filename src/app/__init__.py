from dataclasses import dataclass
from collections.abc import AsyncGenerator
from typing import Optional


import sqlalchemy as sa
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
from litestar.exceptions import ClientException, NotFoundException
from litestar.status_codes import HTTP_409_CONFLICT

from app.logger import logger
from app.models.base import Service
from app.models.nlp.text_generation import TextGeneration
from app.config import default_config as blackfish_config


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
    
BLACKFISH_USER: {state.BLACKFISH_USER}
BLACKFISH_HOST: {state.BLACKFISH_HOST}
BLACKFISH_HOME: {state.BLACKFISH_HOME}
BLACKFISH_CACHE: {state.BLACKFISH_CACHE}
"""


@post("/services", dto=ServiceRequestDTO)
async def run_service(data: ServiceRequest, session: AsyncSession, state: State) -> Service:
    try:
        service = build_service(data)
    except Exception as e:
        print(e)
    try:
        await service.start(
            session,
            state,
            container_options=data.container_options,
            job_options=data.job_options
        )
    except Exception as e:
        print(e)

    return service


@put("/services/{service_id:str}/stop")
async def stop_service(
    service_id: str, data: StopServiceRequest, session: AsyncSession
) -> Service:
    service = await get_service(service_id, session)
    logger.error("Hello!")
    # await service.stop(session, delay=data.delay, timeout=data.timeout, failed=data.failed)

    return service


@get("/services/{service_id:str}")
async def refresh_service(service_id: str, session: AsyncSession) -> Service:
    service = await get_service(service_id, session)
    # await service.refresh(session)

    return service


@get("/services")
async def fetch_services(
    session: AsyncSession,
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

    # await asyncio.gather(*[s.refresh() for s in services])

    return services


@delete("/services/{service_id:str}")
async def delete_service(service_id: str, session: AsyncSession) -> None:
    query = sa.delete(Service).where(Service.id == service_id)
    await session.execute(query)


@get("/models")
async def get_models():
    pass


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


app = Litestar(
    route_handlers=[
        index,
        run_service,
        stop_service,
        refresh_service,
        fetch_services,
        delete_service,
    ],
    dependencies={"session": session_provider},
    plugins=[SQLAlchemyPlugin(db_config)],
    logging_config=None,  # disable Litestar logger (we're using our own)
    state=State(blackfish_config.as_dict()),
)
