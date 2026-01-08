import pytest
from litestar.testing import AsyncTestClient
from unittest.mock import patch

pytestmark = pytest.mark.anyio


class TestNoAuthTokenAPI:
    """Test API behavior when AUTH_TOKEN is not set in the environment."""

    @patch("blackfish.server.asgi.AUTH_TOKEN", None)
    async def test_dashboard_login_page_no_auth_token(
        self, no_auth_client: AsyncTestClient
    ):
        """Test dashboard login page when AUTH_TOKEN is not set."""

        response = await no_auth_client.get("/login", follow_redirects=False)

        # Should redirect to dashboard (AUTH_TOKEN not used by page middleware)
        assert response.status_code == 302
        assert response.next_request.url.path == "/dashboard"

    @patch("blackfish.server.asgi.AUTH_TOKEN", None)
    async def test_protected_api_endpoint_no_auth_token(
        self, no_auth_client: AsyncTestClient
    ):
        """Test protected endpoint /api/info when AUTH_TOKEN is not set."""
        response = await no_auth_client.get("/api/info")

        # Should return internal server error when AUTH_TOKEN is None
        assert response.status_code == 500
