"""Unit tests for the non-streaming proxy helper (`asyncpost`).

Regression coverage for #453: a downstream 4xx/5xx must surface as an
`HTTPException` with the upstream status, not be returned as a successful
JSON body.
"""

from __future__ import annotations

import httpx
import pytest
from litestar.exceptions import HTTPException

pytestmark = pytest.mark.anyio


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_asyncpost_returns_json_on_success():
    from blackfish.server.asgi import asyncpost

    def handler(request):
        return httpx.Response(200, json={"ok": True})

    async with _client(handler) as client:
        result = await asyncpost(client, "http://svc/x", b"{}", {})

    assert result == {"ok": True}


async def test_asyncpost_forwards_upstream_status_and_message():
    from blackfish.server.asgi import asyncpost

    def handler(request):
        return httpx.Response(422, json={"message": "bad audio format"})

    async with _client(handler) as client:
        with pytest.raises(HTTPException) as exc_info:
            await asyncpost(client, "http://svc/x", b"{}", {})

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "bad audio format"


async def test_asyncpost_falls_back_to_text_when_body_is_not_json():
    from blackfish.server.asgi import asyncpost

    def handler(request):
        return httpx.Response(500, content=b"upstream crashed")

    async with _client(handler) as client:
        with pytest.raises(HTTPException) as exc_info:
            await asyncpost(client, "http://svc/x", b"{}", {})

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "upstream crashed"


class TestServiceAuthHeaders:
    """`_service_auth_headers` resolves a port to the credential to replay.

    The proxy is addressed by port rather than service id, so the row has to be
    recovered from the database on each call (#534).
    """

    async def _session_with(self, services):
        """An in-memory session seeded with `services`."""
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from advanced_alchemy.base import UUIDAuditBase
        import blackfish.server.services.text_generation  # noqa: F401
        import blackfish.server.services.speech_recognition  # noqa: F401

        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(UUIDAuditBase.metadata.create_all)
        session = async_sessionmaker(engine, expire_on_commit=False)()
        for svc in services:
            session.add(svc)
        await session.commit()
        return session

    def _service(self, cls, image, port, status, api_key):
        svc = cls(
            name="svc",
            image=image,
            model="m",
            profile="default",
            host="localhost",
            grace_period=600,
            port=port,
            status=status,
        )
        svc._api_key = api_key
        return svc

    async def test_text_generation_uses_bearer_scheme(self):
        """vLLM's AuthenticationMiddleware requires `Authorization: Bearer`."""
        from blackfish.server.asgi import _service_auth_headers
        from blackfish.server.services.base import ServiceStatus
        from blackfish.server.services.text_generation import TextGeneration

        session = await self._session_with(
            [
                self._service(
                    TextGeneration,
                    "text_generation",
                    8080,
                    ServiceStatus.HEALTHY,
                    "sk-secret",
                )
            ]
        )
        try:
            assert await _service_auth_headers(session, 8080) == {
                "Authorization": "Bearer sk-secret"
            }
        finally:
            await session.close()

    async def test_speech_recognition_uses_bare_token_header(self):
        """speech-recognition-inference compares a bare `Token` header."""
        from blackfish.server.asgi import _service_auth_headers
        from blackfish.server.services.base import ServiceStatus
        from blackfish.server.services.speech_recognition import SpeechRecognition

        session = await self._session_with(
            [
                self._service(
                    SpeechRecognition,
                    "speech_recognition",
                    8081,
                    ServiceStatus.HEALTHY,
                    "sk-secret",
                )
            ]
        )
        try:
            assert await _service_auth_headers(session, 8081) == {"Token": "sk-secret"}
        finally:
            await session.close()

    async def test_no_headers_when_service_has_no_key(self):
        from blackfish.server.asgi import _service_auth_headers
        from blackfish.server.services.base import ServiceStatus
        from blackfish.server.services.text_generation import TextGeneration

        session = await self._session_with(
            [
                self._service(
                    TextGeneration, "text_generation", 8082, ServiceStatus.HEALTHY, None
                )
            ]
        )
        try:
            assert await _service_auth_headers(session, 8082) == {}
        finally:
            await session.close()

    async def test_no_headers_when_no_service_on_port(self):
        """The proxy forwards to anything listening; upstream returns 401."""
        from blackfish.server.asgi import _service_auth_headers

        session = await self._session_with([])
        try:
            assert await _service_auth_headers(session, 9999) == {}
        finally:
            await session.close()

    async def test_stopped_service_is_not_used_as_a_key_source(self):
        """Ports are reused, so a stale row would supply the wrong credential."""
        from blackfish.server.asgi import _service_auth_headers
        from blackfish.server.services.base import ServiceStatus
        from blackfish.server.services.text_generation import TextGeneration

        session = await self._session_with(
            [
                self._service(
                    TextGeneration,
                    "text_generation",
                    8083,
                    ServiceStatus.STOPPED,
                    "sk-stale",
                )
            ]
        )
        try:
            assert await _service_auth_headers(session, 8083) == {}
        finally:
            await session.close()
