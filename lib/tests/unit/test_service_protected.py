"""`protected` survives the trip to a CLI client.

`blackfish details` reconstructs a Service from the response body. Anything
derived from the API key cannot survive that round trip — the key is never
serialized, so the rebuilt row has none — which means `details` has to read
such fields from the payload rather than the object it rebuilt.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest
from litestar import get
from litestar.testing import create_test_client
from advanced_alchemy.extensions.litestar import (
    SQLAlchemyPlugin,
    SQLAlchemyAsyncConfig,
)

from blackfish.server.services.base import Service
from blackfish.server.services.text_generation import TextGeneration


def _payload(api_key: str | None) -> dict:
    @get("/s")
    async def handler() -> Service:
        svc = TextGeneration(
            name="x",
            image="text_generation",
            model="m",
            profile="p",
            host="h",
            grace_period=600,
        )
        svc.id = UUID("cd91fa6b1fe0494e940eec06b23dba01")
        svc.created_at = svc.updated_at = datetime.now()
        svc._api_key = api_key
        return svc

    config = SQLAlchemyAsyncConfig(connection_string="sqlite+aiosqlite:///:memory:")
    with create_test_client([handler], plugins=[SQLAlchemyPlugin(config)]) as client:
        response = client.get("/s")
        return response.json(), response.text


@pytest.mark.parametrize("api_key,expected", [("sk-secret", True), (None, False)])
def test_payload_reports_protection(api_key, expected):
    body, _ = _payload(api_key)

    assert body["protected"] is expected


def test_key_is_never_serialized():
    _, text = _payload("sk-secret")

    assert "sk-secret" not in text


def test_rebuilt_service_does_not_carry_protection():
    """Why `details` must read the payload, not the object it reconstructs.

    The setter is a no-op and the key is absent, so a rebuilt row reports
    False for a service that is in fact protected. Reading `service.protected`
    here would tell every user their service is open.
    """
    body, _ = _payload("sk-secret")
    assert body["protected"] is True

    body["created_at"] = datetime.fromisoformat(body["created_at"])
    body["updated_at"] = datetime.fromisoformat(body["updated_at"])
    body["id"] = UUID(body["id"])
    rebuilt = Service(**body)

    assert rebuilt.protected is False
