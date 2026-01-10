import pytest
from unittest.mock import patch
from litestar.testing import AsyncTestClient

pytestmark = pytest.mark.anyio


class TestFetchProfilesAPI:
    """Test cases for the GET /api/profiles endpoint."""

    async def test_fetch_profiles_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that /api/profiles requires authentication."""
        response = await no_auth_client.get("/api/profiles")

        # Should require authentication
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_fetch_all_profiles(self, client: AsyncTestClient):
        """Test fetching all profiles."""
        response = await client.get("/api/profiles")

        # Should return profiles list
        assert response.status_code == 200

        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, list)
            # Each profile should have required fields
            for profile in result:
                assert isinstance(profile, dict)
                assert "name" in profile
                assert "schema" in profile or "type" in profile
                # Schema should be either "local" or "slurm"
                schema = profile.get("schema") or profile.get("type")
                assert schema in ["local", "slurm"]

                # Common fields for both profile types
                assert "home_dir" in profile
                assert "cache_dir" in profile

                # Slurm-specific fields
                if schema == "slurm":
                    assert "host" in profile
                    assert "user" in profile

    async def test_fetch_profiles_file_not_found(self, client: AsyncTestClient):
        """Test behavior when profiles.cfg file doesn't exist."""

        # Should handle missing profiles.cfg gracefully
        with patch(
            "blackfish.server.asgi.deserialize_profiles"
        ) as mock_deserialize_profiles:
            mock_deserialize_profiles.side_effect = FileNotFoundError(
                "Profiles config not found."
            )
            response = await client.get("/api/profiles")
            assert response.status_code == 404

    async def test_fetch_profiles_empty_list(self, client: AsyncTestClient):
        """Test that endpoint can handle empty profiles list."""
        response = await client.get("/api/profiles")

        # Should return valid response even if no profiles exist
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)


class TestGetSingleProfileAPI:
    """Test cases for the GET /api/profiles/{name} endpoint."""

    async def test_get_profile_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that individual profile endpoint requires authentication."""
        test_name = "test-profile"
        response = await no_auth_client.get(f"/api/profiles/{test_name}")

        # Should require authentication
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_get_profile_nonexistent_name(self, client: AsyncTestClient):
        """Test fetching a profile that doesn't exist."""
        nonexistent_name = "nonexistent-profile"

        response = await client.get(f"/api/profiles/{nonexistent_name}")

        # Should return does not exist error
        assert response.status_code == 404

    async def test_get_profile_by_name_success(self, client: AsyncTestClient):
        """Test successfully fetching a single profile by name."""

        profile_name = "default"
        response = await client.get(f"/api/profiles/{profile_name}")

        assert response.status_code == 200
        result = response.json()

        # Verify it return the default fixture profile
        assert isinstance(result, dict)
        assert result["name"] == profile_name
        schema = result.get("schema") or result.get("type")
        assert schema == "local"

    async def test_get_profile_file_not_found(self, client: AsyncTestClient):
        with patch(
            "blackfish.server.asgi.deserialize_profile"
        ) as mock_deserialize_profile:
            mock_deserialize_profile.side_effect = FileNotFoundError(
                "Profile config not found."
            )
            response = await client.get("/api/profiles/default")
            assert response.status_code == 404
