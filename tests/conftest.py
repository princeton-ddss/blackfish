from pathlib import Path
from dotenv import load_dotenv
import pytest

from litestar import Litestar
from app import config
from app.config import BlackfishConfig, ContainerProvider
from pytest import MonkeyPatch

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool
from collections.abc import AsyncGenerator


@pytest.fixture
def anyio_backend():
    return "asyncio"


pytestmark = pytest.mark.anyio

pytest_plugins = [
    "tests.data_fixtures",
]

load_dotenv(".env.test", override=True)


@pytest.fixture(autouse=True)
def _patch_config(monkeypatch: MonkeyPatch) -> None:
    """Patch app configuration for testing."""

    monkeypatch.setattr(
        config,
        "config",
        BlackfishConfig(
            base_path="",
            host="localhost",
            port=8000,
            static_dir=Path(__file__).parent.parent / "src",
            home_dir=Path(__file__).parent.parent / "tests",
            debug=0,  # False
            auth_token="sealsaretasty",
            container_provider=ContainerProvider.Docker,
        ),
    )


@pytest.fixture(name="app")
def app_fixture() -> Litestar:
    from app.asgi import app

    return app


@pytest.fixture(name="engine")
async def engine_fixture() -> AsyncEngine:
    return create_async_engine(
        "sqlite+aiosqlite:///tests/app.sqlite",
        echo=False,
        poolclass=NullPool,
    )


@pytest.fixture(name="sessionmaker")
async def sessionmaker_fixture(
    engine: AsyncEngine,
) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    yield async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture(name="session")
async def session_fixture(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with sessionmaker() as session:
        yield session
