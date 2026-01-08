import pytest
from litestar.testing import AsyncTestClient
from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from collections.abc import AsyncGenerator
from blackfish.server.models.model import Model


pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _seed_db(
    engine: AsyncEngine,
    sessionmaker: async_sessionmaker[AsyncSession],
    services,
    jobs,
    models,
) -> AsyncGenerator[None, None]:
    """Populate the test database for API tests."""

    metadata = UUIDAuditBase.registry.metadata

    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)

    # Add services to the database
    async with sessionmaker() as db:
        db.add_all([s["class"](**s["data"]) for s in services])
        await db.commit()

    # Add batch jobs to the database
    async with sessionmaker() as db:
        db.add_all([j["class"](**j["data"]) for j in jobs])
        await db.commit()

    # Add models to the database
    async with sessionmaker() as db:
        db.add_all([Model(**m) for m in models])
        await db.commit()

    yield


@pytest.fixture(name="no_auth_client")
async def no_auth_client_fixture(app) -> AsyncGenerator[AsyncTestClient, None]:
    """Create a test client without authentication."""
    async with AsyncTestClient(app=app) as client:
        yield client


@pytest.fixture(name="client")
async def client_fixture(app) -> AsyncGenerator[AsyncTestClient, None]:
    """Create an authenticated test client."""
    async with AsyncTestClient(app=app) as client:
        # Authenticate the client
        await client.post("/api/login?token=sealsaretasty")

        yield client
