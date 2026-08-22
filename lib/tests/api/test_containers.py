"""Tests for the GET /api/containers endpoint.

Note this is about *container* images. `test_images.py` covers /api/image,
which serves uploaded image files — a different endpoint entirely, which is
why this route is named `containers`.
"""

from unittest.mock import patch

import pytest
from litestar.testing import AsyncTestClient

from blackfish.server.images import ImageSpec
from blackfish.server.jobs.client import TigerFlowError

pytestmark = pytest.mark.anyio

IMAGES = {
    "text_generation": ImageSpec(repo="vllm/vllm-openai", tag="v0.20.0"),
    "tigerflow_ml": ImageSpec(repo="ghcr.io/princeton-ddss/tigerflow-ml", tag="0.1.1"),
}


class TestListContainersAPI:
    async def test_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ) -> None:
        response = await no_auth_client.get("/api/containers?profile=default")
        assert response.status_code in (401, 403) or response.is_redirect

    async def test_unknown_profile_returns_404(self, client: AsyncTestClient) -> None:
        response = await client.get("/api/containers?profile=nonexistent")
        assert response.status_code == 404

    async def test_lists_staged_tags_per_service(self, client: AsyncTestClient) -> None:
        staged = {
            "text_generation": ["v0.8.4", "v0.20.0"],
            "tigerflow_ml": ["0.1.1"],
        }
        with (
            patch("blackfish.server.asgi.blackfish_config.IMAGES", IMAGES),
            patch(
                "blackfish.server.asgi.list_staged_tags",
                new=_returns(staged),
            ),
        ):
            response = await client.get("/api/containers?profile=default")

        assert response.status_code == 200
        body = {row["service"]: row for row in response.json()}
        assert body["text_generation"]["tags"] == ["v0.8.4", "v0.20.0"]
        # The repo always comes from config: a .sif filename cannot yield one.
        assert body["tigerflow_ml"]["repo"] == "ghcr.io/princeton-ddss/tigerflow-ml"

    async def test_every_service_reports_its_configured_default(
        self, client: AsyncTestClient
    ) -> None:
        """config.IMAGES always has a default per service, so every row names
        one — whether or not it is staged."""
        staged = {"text_generation": ["v0.20.0"], "tigerflow_ml": []}
        with (
            patch("blackfish.server.asgi.blackfish_config.IMAGES", IMAGES),
            patch("blackfish.server.asgi.list_staged_tags", new=_returns(staged)),
        ):
            response = await client.get("/api/containers?profile=default")

        body = {row["service"]: row for row in response.json()}
        assert body["text_generation"]["default"] == "v0.20.0"
        assert body["tigerflow_ml"]["default"] == "0.1.1"

    async def test_default_staged_reflects_whether_the_file_exists(
        self, client: AsyncTestClient
    ) -> None:
        """The configured default can be absent from disk — an admin deleted
        it, or an env override names a tag nobody staged. The response must
        name the expected tag so a caller can say which one is missing."""
        staged = {"text_generation": ["v0.8.4"], "tigerflow_ml": ["0.1.1"]}
        with (
            patch("blackfish.server.asgi.blackfish_config.IMAGES", IMAGES),
            patch("blackfish.server.asgi.list_staged_tags", new=_returns(staged)),
        ):
            response = await client.get("/api/containers?profile=default")

        body = {row["service"]: row for row in response.json()}
        # v0.20.0 is configured but not in the staged list.
        assert body["text_generation"]["default"] == "v0.20.0"
        assert body["text_generation"]["default_staged"] is False
        assert body["tigerflow_ml"]["default_staged"] is True

    async def test_profile_with_no_images_directory_returns_empty_tags(
        self, client: AsyncTestClient
    ) -> None:
        """A fresh profile is a valid state, not an error."""
        staged = {"text_generation": [], "tigerflow_ml": []}
        with (
            patch("blackfish.server.asgi.blackfish_config.IMAGES", IMAGES),
            patch("blackfish.server.asgi.list_staged_tags", new=_returns(staged)),
        ):
            response = await client.get("/api/containers?profile=default")

        assert response.status_code == 200
        assert all(row["tags"] == [] for row in response.json())

    async def test_unreachable_profile_returns_a_friendly_500(
        self, client: AsyncTestClient
    ) -> None:
        with (
            patch("blackfish.server.asgi.blackfish_config.IMAGES", IMAGES),
            patch(
                "blackfish.server.asgi.list_staged_tags",
                new=_raises(TigerFlowError("timeout", "hpc.example.com")),
            ),
        ):
            response = await client.get("/api/containers?profile=hpc")

        assert response.status_code == 500
        # The friendly message, not a raw traceback.
        assert "timed out" in response.json()["detail"].lower()


def _returns(value):
    async def _fn(*args, **kwargs):
        return value

    return _fn


def _raises(exc):
    async def _fn(*args, **kwargs):
        raise exc

    return _fn
