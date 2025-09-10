import pytest
from litestar.testing import AsyncTestClient
from unittest.mock import patch, Mock

pytestmark = pytest.mark.anyio


class TestAuthenticationAPI:
    """Test cases for authentication endpoints."""

    @patch('app.asgi.AUTH_TOKEN', None)
    async def test_login_no_auth_token_set(self, no_auth_client: AsyncTestClient):
        """Test /api/login when AUTH_TOKEN is not set."""
        response = await no_auth_client.post("/api/login")
        
        # Should return internal server error because AUTH_TOKEN is None
        assert response.status_code == 500

    @patch('app.asgi.AUTH_TOKEN', None)
    async def test_logout_no_auth_token_set(self, no_auth_client: AsyncTestClient):
        """Test /api/logout when AUTH_TOKEN is not set.""" 
        response = await no_auth_client.post("/api/logout")
        
        # Should return internal server error because the auth_guard will fail if AUTH_TOKEN is None
        assert response.status_code == 500

    async def test_login(self, no_auth_client: AsyncTestClient):
        """Test basic authentication workflow."""
        response = await no_auth_client.post("/api/login?token=sealsaretasty", follow_redirects=False)
        
        # Should redirect to dashboard and set cookie 
        assert response.status_code == 302
        assert response.next_request.url.path == '/dashboard'
        assert 'bf_user' in response.cookies

    async def test_login_with_incorrect_token(self, no_auth_client: AsyncTestClient):
        """Test authentication with incorrect credentials."""
        response = await no_auth_client.post("/api/login?token=not_correct", follow_redirects=False)
        
        # Should redirect to login
        assert response.status_code == 302
        assert response.next_request.url.path == '/login'
        assert len(response.cookies) == 0

    async def test_login_without_token(self, no_auth_client: AsyncTestClient):
        """Test authentication with incorrect credentials."""
        response = await no_auth_client.post("/api/login", follow_redirects=False)
        
        # Should redirect to login
        assert response.status_code == 302
        assert response.next_request.url.path == '/login'
        assert len(response.cookies) == 0

    async def test_login_with_authenticated_client_and_no_token(self, client: AsyncTestClient):
        response = await client.post("/api/login", follow_redirects=False)

        # Should redirect to dashboard
        assert response.status_code == 302
        assert response.next_request.url.path == '/dashboard'

    async def test_login_with_authenticated_client_and_token(self, client: AsyncTestClient):
        response = await client.post("/api/login?token=any_token_will_do", follow_redirects=False)

        # Should redirect to dashboard
        assert response.status_code == 302
        assert response.next_request.url.path == '/dashboard'

    async def test_login_post_method_only(self, no_auth_client: AsyncTestClient):
        """Test that login only accepts POST method."""

        response = await no_auth_client.get("/api/login")
        
        # Should return method not allowed
        assert response.status_code == 405

    async def test_logout(self, client: AsyncTestClient):
        """Test logout workflow with an authenticated client."""
        # Mock the request.set_session method to verify it's called correctly
        with patch('litestar.Request.set_session') as mock_set_session:
            response = await client.post("/api/logout", follow_redirects=False)
        
            # Should redirect to login page and unset session token
            assert response.status_code == 302
            assert response.next_request.url.path == '/login'
            
            # Verify that set_session was called to clear the token
            mock_set_session.assert_called_once_with({"token": None})
    
    async def test_logout_with_unauthenticated_client(self, no_auth_client: AsyncTestClient):
        """Test that logout endpoint exists but requires authentication."""
        response = await no_auth_client.post("/api/logout")
        
        # Should require authentication (401)
        assert response.status_code == 401
