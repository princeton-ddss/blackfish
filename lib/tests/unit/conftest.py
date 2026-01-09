import pytest

from litestar.testing import AsyncTestClient
from litestar.datastructures import State

from collections.abc import AsyncGenerator

pytestmark = pytest.mark.anyio


@pytest.fixture(name="client")
async def client_fixture(app) -> AsyncGenerator[AsyncTestClient, None]:
    async with AsyncTestClient(app=app, state=State()) as client:
        yield client


@pytest.fixture(name="state")
def state_fixture() -> State:
    return State()
