import configparser
import pytest
import sqlalchemy as sa
from unittest.mock import patch, AsyncMock, MagicMock
from litestar.testing import AsyncTestClient

from blackfish.server.models.model import Model
from blackfish.server.models.download import DownloadTask
from blackfish.server.services.base import Service
from blackfish.server.jobs.base import BatchJob

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


class TestCreateProfileAPI:
    """Test cases for the POST /api/profiles endpoint."""

    async def test_create_profile_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that creating a profile requires authentication."""
        response = await no_auth_client.post(
            "/api/profiles",
            json={
                "name": "test-profile",
                "schema_type": "local",
                "home_dir": "/tmp/test",
                "cache_dir": "/tmp/cache",
            },
        )
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_create_profile_invalid_name(self, client: AsyncTestClient):
        """A profile name with ConfigParser-meaningful characters is rejected."""
        response = await client.post(
            "/api/profiles",
            json={
                "name": "bad[name",
                "schema_type": "local",
                "home_dir": "/tmp/test",
                "cache_dir": "/tmp/cache",
            },
        )
        assert response.status_code == 400
        assert "Invalid profile name" in response.json()["detail"]

    async def test_create_local_profile_success(self, client: AsyncTestClient):
        """Test creating a local profile successfully."""
        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi._save_profiles_config") as mock_save_config,
            patch("blackfish.server.asgi.ProfileManager") as mock_profile_mgr_cls,
        ):
            mock_get_config.return_value = MagicMock()
            mock_get_config.return_value.__contains__ = MagicMock(return_value=False)

            mock_profile_mgr = AsyncMock()
            mock_profile_mgr_cls.return_value = mock_profile_mgr

            response = await client.post(
                "/api/profiles",
                json={
                    "name": "new-local",
                    "schema_type": "local",
                    "home_dir": "/home/test/.blackfish",
                    "cache_dir": "/tmp/cache",
                },
            )

            assert response.status_code == 201
            result = response.json()
            assert result["name"] == "new-local"
            assert result["home_dir"] == "/home/test/.blackfish"
            mock_profile_mgr.create_directories.assert_called_once()
            mock_profile_mgr.check_cache.assert_called_once()
            mock_save_config.assert_called_once()

    async def test_create_slurm_profile_success(self, client: AsyncTestClient):
        """Test creating a Slurm profile successfully.

        Profile creation only sets up directories/cache; the tigerflow-ml image
        is staged separately, so no package install is performed.
        """
        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi._save_profiles_config") as mock_save_config,
            patch("blackfish.server.asgi.ProfileManager") as mock_profile_mgr_cls,
        ):
            mock_get_config.return_value = MagicMock()
            mock_get_config.return_value.__contains__ = MagicMock(return_value=False)

            mock_profile_mgr = AsyncMock()
            mock_profile_mgr_cls.return_value = mock_profile_mgr

            response = await client.post(
                "/api/profiles",
                json={
                    "name": "new-slurm",
                    "schema_type": "slurm",
                    "host": "cluster.edu",
                    "user": "testuser",
                    "home_dir": "/home/testuser/.blackfish",
                    "cache_dir": "/scratch/cache",
                },
            )

            assert response.status_code == 201
            result = response.json()
            assert result["name"] == "new-slurm"
            assert result["host"] == "cluster.edu"
            assert result["user"] == "testuser"
            mock_profile_mgr.create_directories.assert_called_once()
            mock_profile_mgr.check_cache.assert_called_once()
            mock_save_config.assert_called_once()

    async def test_create_slurm_profile_localhost_uses_local_runner(
        self, client: AsyncTestClient
    ):
        """Test creating a Slurm profile with localhost uses LocalRunner.

        This is the Open OnDemand scenario where blackfish runs on the
        cluster's login node and Slurm is accessed locally.
        """
        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi.ProfileManager") as mock_profile_mgr_cls,
            patch("blackfish.server.asgi.LocalRunner") as mock_local_runner_cls,
            patch("blackfish.server.asgi.SSHRunner") as mock_ssh_runner_cls,
        ):
            mock_get_config.return_value = MagicMock()
            mock_get_config.return_value.__contains__ = MagicMock(return_value=False)

            mock_profile_mgr = AsyncMock()
            mock_profile_mgr_cls.return_value = mock_profile_mgr

            mock_local_runner = MagicMock()
            mock_local_runner_cls.return_value = mock_local_runner

            response = await client.post(
                "/api/profiles",
                json={
                    "name": "ondemand-slurm",
                    "schema_type": "slurm",
                    "host": "localhost",
                    "user": "ondemand",
                    "home_dir": "/home/ondemand/.blackfish",
                    "cache_dir": "/scratch/cache",
                },
            )

            assert response.status_code == 201
            # Verify LocalRunner was used, not SSHRunner
            mock_local_runner_cls.assert_called_once()
            mock_ssh_runner_cls.assert_not_called()
            mock_profile_mgr.create_directories.assert_called_once()

    async def test_create_profile_already_exists(self, client: AsyncTestClient):
        """Test that creating a duplicate profile returns 409."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config

            response = await client.post(
                "/api/profiles",
                json={
                    "name": "existing",
                    "schema_type": "local",
                    "home_dir": "/tmp/test",
                    "cache_dir": "/tmp/cache",
                },
            )

            assert response.status_code == 409

    async def test_create_slurm_profile_missing_host(self, client: AsyncTestClient):
        """Test that Slurm profile requires host."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()
            mock_get_config.return_value.__contains__ = MagicMock(return_value=False)

            response = await client.post(
                "/api/profiles",
                json={
                    "name": "bad-slurm",
                    "schema_type": "slurm",
                    "user": "testuser",
                    "home_dir": "/tmp/test",
                    "cache_dir": "/tmp/cache",
                },
            )

            assert response.status_code == 400

    async def test_create_slurm_profile_missing_user(self, client: AsyncTestClient):
        """Test that Slurm profile requires user."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()
            mock_get_config.return_value.__contains__ = MagicMock(return_value=False)

            response = await client.post(
                "/api/profiles",
                json={
                    "name": "bad-slurm",
                    "schema_type": "slurm",
                    "host": "cluster.edu",
                    "home_dir": "/tmp/test",
                    "cache_dir": "/tmp/cache",
                },
            )

            assert response.status_code == 400

    async def test_create_profile_invalid_schema_type(self, client: AsyncTestClient):
        """Test that invalid schema_type returns 400."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()
            mock_get_config.return_value.__contains__ = MagicMock(return_value=False)

            response = await client.post(
                "/api/profiles",
                json={
                    "name": "bad-profile",
                    "schema_type": "invalid",
                    "home_dir": "/tmp/test",
                    "cache_dir": "/tmp/cache",
                },
            )

            assert response.status_code == 400

    async def test_create_slurm_profile_setup_error(self, client: AsyncTestClient):
        """Test that ProfileSetupError during Slurm profile creation returns 500."""
        from blackfish.server.setup import ProfileSetupError

        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi.ProfileManager") as mock_profile_mgr_cls,
        ):
            mock_get_config.return_value = MagicMock()
            mock_get_config.return_value.__contains__ = MagicMock(return_value=False)

            mock_profile_mgr = AsyncMock()
            mock_profile_mgr.create_directories.side_effect = ProfileSetupError(
                "Failed to create directories", "Permission denied"
            )
            mock_profile_mgr_cls.return_value = mock_profile_mgr

            response = await client.post(
                "/api/profiles",
                json={
                    "name": "failing-slurm",
                    "schema_type": "slurm",
                    "host": "cluster.edu",
                    "user": "testuser",
                    "home_dir": "/home/testuser/.blackfish",
                    "cache_dir": "/scratch/cache",
                },
            )

            assert response.status_code == 500
            assert "Permission denied" in response.json()["detail"]

    async def test_create_local_profile_setup_error(self, client: AsyncTestClient):
        """Test that ProfileSetupError during local profile creation returns 500."""
        from blackfish.server.setup import ProfileSetupError

        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi.ProfileManager") as mock_profile_mgr_cls,
        ):
            mock_get_config.return_value = MagicMock()
            mock_get_config.return_value.__contains__ = MagicMock(return_value=False)

            mock_profile_mgr = AsyncMock()
            mock_profile_mgr.create_directories.side_effect = ProfileSetupError(
                "Failed to create directories", "Disk full"
            )
            mock_profile_mgr_cls.return_value = mock_profile_mgr

            response = await client.post(
                "/api/profiles",
                json={
                    "name": "failing-local",
                    "schema_type": "local",
                    "home_dir": "/home/user/.blackfish",
                    "cache_dir": "/tmp/cache",
                },
            )

            assert response.status_code == 500
            assert "Disk full" in response.json()["detail"]


class TestUpdateProfileAPI:
    """Test cases for the PUT /api/profiles/{name} endpoint."""

    async def test_update_profile_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that updating a profile requires authentication."""
        response = await no_auth_client.put(
            "/api/profiles/test-profile",
            json={
                "name": "test-profile",
                "schema_type": "local",
                "home_dir": "/tmp/test",
                "cache_dir": "/tmp/cache",
            },
        )
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_update_local_profile_success(self, client: AsyncTestClient):
        """Test updating a local profile successfully."""
        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi._save_profiles_config") as mock_save_config,
            patch("blackfish.server.asgi.ProfileManager") as mock_profile_mgr_cls,
        ):
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config

            mock_profile_mgr = AsyncMock()
            mock_profile_mgr_cls.return_value = mock_profile_mgr

            response = await client.put(
                "/api/profiles/my-local",
                json={
                    "name": "my-local",
                    "schema_type": "local",
                    "home_dir": "/home/updated/.blackfish",
                    "cache_dir": "/tmp/new-cache",
                },
            )

            assert response.status_code == 200
            result = response.json()
            assert result["name"] == "my-local"
            assert result["home_dir"] == "/home/updated/.blackfish"
            mock_profile_mgr.create_directories.assert_called_once()
            mock_profile_mgr.check_cache.assert_called_once()
            mock_save_config.assert_called_once()

    async def test_update_slurm_profile_success(self, client: AsyncTestClient):
        """Test updating a Slurm profile successfully."""
        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi._save_profiles_config") as mock_save_config,
            patch("blackfish.server.asgi.ProfileManager") as mock_profile_mgr_cls,
        ):
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config

            mock_profile_mgr = AsyncMock()
            mock_profile_mgr_cls.return_value = mock_profile_mgr

            response = await client.put(
                "/api/profiles/my-slurm",
                json={
                    "name": "my-slurm",
                    "schema_type": "slurm",
                    "host": "new-cluster.edu",
                    "user": "newuser",
                    "home_dir": "/home/newuser/.blackfish",
                    "cache_dir": "/scratch/new-cache",
                },
            )

            assert response.status_code == 200
            result = response.json()
            assert result["name"] == "my-slurm"
            assert result["host"] == "new-cluster.edu"
            assert result["user"] == "newuser"
            mock_profile_mgr.create_directories.assert_called_once()
            mock_profile_mgr.check_cache.assert_called_once()
            mock_save_config.assert_called_once()

    async def test_update_profile_not_found(self, client: AsyncTestClient):
        """Test updating a nonexistent profile returns 404."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=False)
            mock_get_config.return_value = mock_config

            response = await client.put(
                "/api/profiles/nonexistent",
                json={
                    "name": "nonexistent",
                    "schema_type": "local",
                    "home_dir": "/tmp/test",
                    "cache_dir": "/tmp/cache",
                },
            )

            assert response.status_code == 404

    async def test_update_profile_name_change_not_allowed(
        self, client: AsyncTestClient
    ):
        """Test that profile name cannot be changed."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config

            response = await client.put(
                "/api/profiles/original-name",
                json={
                    "name": "different-name",
                    "schema_type": "local",
                    "home_dir": "/tmp/test",
                    "cache_dir": "/tmp/cache",
                },
            )

            assert response.status_code == 400
            assert "cannot be changed" in response.json()["detail"]

    async def test_update_slurm_profile_missing_host(self, client: AsyncTestClient):
        """Test that updating Slurm profile requires host."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config

            response = await client.put(
                "/api/profiles/my-slurm",
                json={
                    "name": "my-slurm",
                    "schema_type": "slurm",
                    "user": "testuser",
                    "home_dir": "/tmp/test",
                    "cache_dir": "/tmp/cache",
                },
            )

            assert response.status_code == 400

    async def test_update_profile_invalid_schema_type(self, client: AsyncTestClient):
        """Test that invalid schema_type returns 400."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config

            response = await client.put(
                "/api/profiles/my-profile",
                json={
                    "name": "my-profile",
                    "schema_type": "invalid",
                    "home_dir": "/tmp/test",
                    "cache_dir": "/tmp/cache",
                },
            )

            assert response.status_code == 400


class TestScopedProvisioning:
    """`PUT /api/profiles/{name}` runs only the setup steps whose inputs changed.

    Provisioning is now directory/cache setup only; the tigerflow-ml image is
    staged separately, so profile updates never install packages.
    """

    SLURM = {
        "schema": "slurm",
        "host": "cluster.edu",
        "user": "alice",
        "home_dir": "/home/alice/.blackfish",
        "cache_dir": "/scratch/alice",
        "default": "true",
    }
    LOCAL = {
        "schema": "local",
        "home_dir": "/home/alice/.blackfish",
        "cache_dir": "/tmp/cache",
        "default": "true",
    }

    @classmethod
    def _config(cls, name, section):
        cfg = configparser.ConfigParser()
        cfg[name] = dict(section)
        return cfg

    @staticmethod
    def _slurm_body(**overrides):
        body = {
            "name": "prof",
            "schema_type": "slurm",
            "host": "cluster.edu",
            "user": "alice",
            "home_dir": "/home/alice/.blackfish",
            "cache_dir": "/scratch/alice",
        }
        body.update(overrides)
        return body

    async def _put(self, client, name, section, body):
        """PUT with mocked config + provisioning; returns (response, mgr)."""
        with (
            patch(
                "blackfish.server.asgi._get_profiles_config",
                return_value=self._config(name, section),
            ),
            patch("blackfish.server.asgi._save_profiles_config"),
            patch("blackfish.server.asgi.ProfileManager") as mgr_cls,
        ):
            mgr = AsyncMock()
            mgr_cls.return_value = mgr
            response = await client.put(f"/api/profiles/{name}", json=body)
        return response, mgr

    async def test_cache_only_change_checks_cache_not_dirs(self, client):
        response, mgr = await self._put(
            client, "prof", self.SLURM, self._slurm_body(cache_dir="/scratch/new")
        )
        assert response.status_code == 200
        mgr.check_cache.assert_called_once()
        mgr.create_directories.assert_not_called()

    async def test_home_change_recreates_dirs_only(self, client):
        response, mgr = await self._put(
            client,
            "prof",
            self.SLURM,
            self._slurm_body(home_dir="/home/alice/bf"),
        )
        assert response.status_code == 200
        mgr.create_directories.assert_called_once()
        mgr.check_cache.assert_not_called()

    async def test_no_change_skips_all_provisioning(self, client):
        response, mgr = await self._put(client, "prof", self.SLURM, self._slurm_body())
        assert response.status_code == 200
        mgr.create_directories.assert_not_called()
        mgr.check_cache.assert_not_called()

    async def test_host_change_runs_full_chain(self, client):
        response, mgr = await self._put(
            client, "prof", self.SLURM, self._slurm_body(host="other.edu")
        )
        assert response.status_code == 200
        mgr.create_directories.assert_called_once()
        mgr.check_cache.assert_called_once()

    async def test_local_cache_only_change_skips_dirs(self, client):
        body = {
            "name": "prof",
            "schema_type": "local",
            "home_dir": "/home/alice/.blackfish",
            "cache_dir": "/tmp/other",
        }
        response, mgr = await self._put(client, "prof", self.LOCAL, body)
        assert response.status_code == 200
        mgr.check_cache.assert_called_once()
        mgr.create_directories.assert_not_called()


class TestDeleteProfileAPI:
    """Test cases for the DELETE /api/profiles/{name} endpoint."""

    async def test_delete_profile_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that deleting a profile requires authentication."""
        response = await no_auth_client.delete("/api/profiles/test-profile")
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_delete_profile_success(self, client: AsyncTestClient):
        """Test deleting a profile successfully."""
        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi._save_profiles_config") as mock_save_config,
        ):
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config

            response = await client.delete("/api/profiles/to-delete")

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "ok"
            assert "deleted" in result["message"].lower()
            mock_save_config.assert_called_once()

    async def test_delete_profile_not_found(self, client: AsyncTestClient):
        """Test deleting a nonexistent profile returns 404."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=False)
            mock_get_config.return_value = mock_config

            response = await client.delete("/api/profiles/nonexistent")

            assert response.status_code == 404


class TestDefaultFlagAPI:
    """Tests for default-flag behavior across the profile endpoints."""

    async def test_delete_refuses_default(self, client: AsyncTestClient):
        """DELETE refuses to remove the default profile without force=true."""
        with (
            patch(
                "blackfish.server.asgi.resolve_default_section", return_value="myprof"
            ),
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
        ):
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config

            response = await client.delete("/api/profiles/myprof")

            assert response.status_code == 409
            assert "default profile" in response.json()["detail"]

    async def test_delete_default_with_force(self, client: AsyncTestClient):
        """DELETE removes the default profile when force=true."""
        with (
            patch(
                "blackfish.server.asgi.resolve_default_section", return_value="myprof"
            ),
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi._save_profiles_config") as mock_save_config,
        ):
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config

            response = await client.delete("/api/profiles/myprof?force=true")

            assert response.status_code == 200
            mock_save_config.assert_called_once()

    async def test_set_default_endpoint(self, client: AsyncTestClient):
        """PUT /api/profiles/{name}/default flags the named profile exclusively."""
        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi._save_profiles_config") as mock_save_config,
            patch("blackfish.server.asgi.set_exclusive_default") as mock_set_exclusive,
        ):
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config

            response = await client.put("/api/profiles/myprof/default")

            assert response.status_code == 200
            assert response.json()["status"] == "ok"
            mock_set_exclusive.assert_called_once_with(mock_config, "myprof")
            mock_save_config.assert_called_once()

    async def test_set_default_not_found(self, client: AsyncTestClient):
        """PUT /api/profiles/{name}/default returns 404 if the profile is missing."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=False)
            mock_get_config.return_value = mock_config

            response = await client.put("/api/profiles/nope/default")

            assert response.status_code == 404


class TestRenameProfileAPI:
    """Test cases for the PUT /api/profiles/{name}/rename endpoint."""

    @staticmethod
    def _config(*sections):
        """Build a ConfigParser with the given local-profile sections."""
        cfg = configparser.ConfigParser()
        for s in sections:
            cfg[s] = {"schema": "local", "home_dir": "/h", "cache_dir": "/c"}
        return cfg

    @staticmethod
    async def _count(session, model, profile):
        res = await session.execute(
            sa.select(sa.func.count())
            .select_from(model)
            .where(model.profile == profile)
        )
        return res.scalar()

    async def test_rename_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        response = await no_auth_client.put(
            "/api/profiles/test/rename", json={"new_name": "x"}
        )
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_rename_sweeps_db_tables(self, client: AsyncTestClient, session):
        """Rename cascades the new name to all four profile-referencing tables."""
        # The seeded fixtures cover model/service/job but not download_task,
        # so add one download task against the "test" profile.
        session.add(DownloadTask(repo_id="org/model", profile="test"))
        await session.commit()

        tables = (Model, DownloadTask, Service, BatchJob)
        for model in tables:
            assert await self._count(session, model, "test") > 0

        with (
            patch(
                "blackfish.server.asgi._get_profiles_config",
                return_value=self._config("test", "default"),
            ),
            patch("blackfish.server.asgi._save_profiles_config") as mock_save,
        ):
            response = await client.put(
                "/api/profiles/test/rename", json={"new_name": "renamed"}
            )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        mock_save.assert_called_once()

        for model in tables:
            assert await self._count(session, model, "test") == 0
            assert await self._count(session, model, "renamed") > 0

    async def test_rename_preserves_profile_order(self, client: AsyncTestClient):
        """Renaming keeps the profile in its original position in the file."""
        with (
            patch(
                "blackfish.server.asgi._get_profiles_config",
                return_value=self._config("test", "middle", "default"),
            ),
            patch("blackfish.server.asgi._save_profiles_config") as mock_save,
        ):
            response = await client.put(
                "/api/profiles/test/rename", json={"new_name": "renamed"}
            )

        assert response.status_code == 200
        saved_config = mock_save.call_args.args[0]
        assert saved_config.sections() == ["renamed", "middle", "default"]

    async def test_rename_collision_returns_409(self, client: AsyncTestClient):
        """Renaming onto an existing profile name is rejected."""
        with patch(
            "blackfish.server.asgi._get_profiles_config",
            return_value=self._config("test", "default"),
        ):
            response = await client.put(
                "/api/profiles/test/rename", json={"new_name": "default"}
            )
        assert response.status_code == 409

    async def test_rename_not_found_returns_404(self, client: AsyncTestClient):
        with patch(
            "blackfish.server.asgi._get_profiles_config",
            return_value=self._config("default"),
        ):
            response = await client.put(
                "/api/profiles/missing/rename", json={"new_name": "x"}
            )
        assert response.status_code == 404

    async def test_rename_to_same_name_returns_400(self, client: AsyncTestClient):
        with patch(
            "blackfish.server.asgi._get_profiles_config",
            return_value=self._config("test"),
        ):
            response = await client.put(
                "/api/profiles/test/rename", json={"new_name": "test"}
            )
        assert response.status_code == 400

    async def test_rename_to_invalid_name_returns_400(self, client: AsyncTestClient):
        with patch(
            "blackfish.server.asgi._get_profiles_config",
            return_value=self._config("test"),
        ):
            response = await client.put(
                "/api/profiles/test/rename", json={"new_name": "bad[name"}
            )
        assert response.status_code == 400
        assert "Invalid profile name" in response.json()["detail"]

    async def test_rename_collision_does_not_sweep_db(
        self, client: AsyncTestClient, session
    ):
        """A rejected rename leaves the DB profile names untouched."""
        before = await self._count(session, Model, "test")
        assert before > 0

        with patch(
            "blackfish.server.asgi._get_profiles_config",
            return_value=self._config("test", "default"),
        ):
            await client.put("/api/profiles/test/rename", json={"new_name": "default"})

        # The collision is rejected before any DB write, so counts are unchanged.
        assert await self._count(session, Model, "test") == before


class TestRepairProfileAPI:
    """Test cases for the PUT /api/profiles/{name}/repair endpoint."""

    async def test_repair_profile_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that repairing a profile requires authentication."""
        response = await no_auth_client.put("/api/profiles/test-profile/repair")
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_repair_slurm_profile_success(self, client: AsyncTestClient):
        """Test repairing a Slurm profile with force=true."""
        from blackfish.server.setup import RepairResult

        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi.repair_slurm_profile") as mock_repair,
        ):
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_config.__getitem__ = MagicMock(
                return_value={
                    "schema": "slurm",
                    "host": "cluster.edu",
                    "user": "testuser",
                    "home_dir": "/home/testuser/.blackfish",
                    "cache_dir": "/scratch/cache",
                }
            )
            mock_get_config.return_value = mock_config
            mock_repair.return_value = RepairResult(
                repaired=True, message="Profile repaired on cluster.edu."
            )

            response = await client.put("/api/profiles/my-slurm/repair?force=true")

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "ok"
            assert "repaired" in result["message"].lower()
            mock_repair.assert_called_once()

    async def test_repair_skips_healthy_profile(self, client: AsyncTestClient):
        """Test that repair skips if profile is already healthy."""
        from blackfish.server.setup import RepairResult

        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi.repair_slurm_profile") as mock_repair,
        ):
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_config.__getitem__ = MagicMock(
                return_value={
                    "schema": "slurm",
                    "host": "cluster.edu",
                    "user": "testuser",
                    "home_dir": "/home/testuser/.blackfish",
                    "cache_dir": "/scratch/cache",
                }
            )
            mock_get_config.return_value = mock_config
            mock_repair.return_value = RepairResult(
                repaired=False,
                message="Profile is healthy (tigerflow 0.1.0, tigerflow-ml 0.1.0).",
            )

            response = await client.put("/api/profiles/my-slurm/repair")

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "ok"
            assert "healthy" in result["message"].lower()

    async def test_repair_slurm_profile_localhost(self, client: AsyncTestClient):
        """Test repairing a Slurm profile with localhost (Open OnDemand scenario)."""
        from blackfish.server.setup import RepairResult

        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi.repair_slurm_profile") as mock_repair,
        ):
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_config.__getitem__ = MagicMock(
                return_value={
                    "schema": "slurm",
                    "host": "localhost",
                    "user": "ondemand",
                    "home_dir": "/home/ondemand/.blackfish",
                    "cache_dir": "/scratch/cache",
                }
            )
            mock_get_config.return_value = mock_config
            mock_repair.return_value = RepairResult(
                repaired=True, message="Profile repaired on localhost."
            )

            response = await client.put(
                "/api/profiles/ondemand-slurm/repair?force=true"
            )

            assert response.status_code == 200
            # Verify repair_slurm_profile was called with host="localhost"
            mock_repair.assert_called_once()
            call_kwargs = mock_repair.call_args.kwargs
            assert call_kwargs["host"] == "localhost"

    async def test_repair_profile_not_found(self, client: AsyncTestClient):
        """Test repairing a nonexistent profile returns 404."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=False)
            mock_get_config.return_value = mock_config

            response = await client.put("/api/profiles/nonexistent/repair")

            assert response.status_code == 404

    async def test_repair_local_profile_not_allowed(self, client: AsyncTestClient):
        """Test that repairing a local profile returns 400."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_config.__getitem__ = MagicMock(
                return_value={
                    "schema": "local",
                    "home_dir": "/home/user/.blackfish",
                    "cache_dir": "/tmp/cache",
                }
            )
            mock_get_config.return_value = mock_config

            response = await client.put("/api/profiles/my-local/repair")

            assert response.status_code == 400

    async def test_repair_profile_missing_required_fields(
        self, client: AsyncTestClient
    ):
        """Test that repair fails when profile has missing fields."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_config.__getitem__ = MagicMock(
                return_value={
                    "schema": "slurm",
                    # Missing host, user, home_dir
                }
            )
            mock_get_config.return_value = mock_config

            response = await client.put("/api/profiles/broken-profile/repair")

            assert response.status_code == 400

    async def test_repair_profile_tigerflow_error(self, client: AsyncTestClient):
        """Test that TigerFlowError during repair returns 500."""
        from blackfish.server.jobs.client import TigerFlowError

        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi.repair_slurm_profile") as mock_repair,
        ):
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_config.__getitem__ = MagicMock(
                return_value={
                    "schema": "slurm",
                    "host": "cluster.edu",
                    "user": "testuser",
                    "home_dir": "/home/testuser/.blackfish",
                    "cache_dir": "/scratch/cache",
                }
            )
            mock_get_config.return_value = mock_config
            mock_repair.side_effect = TigerFlowError(
                "install", "cluster.edu", "Failed to install tigerflow"
            )

            response = await client.put("/api/profiles/my-slurm/repair?force=true")

            assert response.status_code == 500
            assert "Failed to install tigerflow" in response.json()["detail"]
