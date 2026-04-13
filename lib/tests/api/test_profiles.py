import pytest
from unittest.mock import patch, AsyncMock, MagicMock
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
        """Test creating a Slurm profile successfully."""
        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi._save_profiles_config") as mock_save_config,
            patch("blackfish.server.asgi.ProfileManager") as mock_profile_mgr_cls,
            patch("blackfish.server.asgi.TigerFlowClient") as mock_tf_client_cls,
        ):
            mock_get_config.return_value = MagicMock()
            mock_get_config.return_value.__contains__ = MagicMock(return_value=False)

            mock_profile_mgr = AsyncMock()
            mock_profile_mgr_cls.return_value = mock_profile_mgr

            mock_tf_client = AsyncMock()
            mock_tf_client_cls.return_value = mock_tf_client

            response = await client.post(
                "/api/profiles",
                json={
                    "name": "new-slurm",
                    "schema_type": "slurm",
                    "host": "cluster.edu",
                    "user": "testuser",
                    "home_dir": "/home/testuser/.blackfish",
                    "cache_dir": "/scratch/cache",
                    "python_path": "/opt/python/bin/python3",
                },
            )

            assert response.status_code == 201
            result = response.json()
            assert result["name"] == "new-slurm"
            assert result["host"] == "cluster.edu"
            assert result["user"] == "testuser"
            mock_profile_mgr.create_directories.assert_called_once()
            mock_tf_client.setup.assert_called_once()
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
            patch("blackfish.server.asgi.TigerFlowClient") as mock_tf_client_cls,
            patch("blackfish.server.asgi.LocalRunner") as mock_local_runner_cls,
            patch("blackfish.server.asgi.SSHRunner") as mock_ssh_runner_cls,
        ):
            mock_get_config.return_value = MagicMock()
            mock_get_config.return_value.__contains__ = MagicMock(return_value=False)

            mock_profile_mgr = AsyncMock()
            mock_profile_mgr_cls.return_value = mock_profile_mgr

            mock_tf_client = AsyncMock()
            mock_tf_client_cls.return_value = mock_tf_client

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
            mock_tf_client.setup.assert_called_once()

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

    async def test_create_slurm_profile_tigerflow_error(self, client: AsyncTestClient):
        """Test that TigerFlowError during Slurm profile creation returns 500."""
        from blackfish.server.jobs.client import TigerFlowError

        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi.ProfileManager") as mock_profile_mgr_cls,
            patch("blackfish.server.asgi.TigerFlowClient") as mock_tf_client_cls,
        ):
            mock_get_config.return_value = MagicMock()
            mock_get_config.return_value.__contains__ = MagicMock(return_value=False)

            mock_profile_mgr = AsyncMock()
            mock_profile_mgr_cls.return_value = mock_profile_mgr

            mock_tf_client = AsyncMock()
            mock_tf_client.setup.side_effect = TigerFlowError(
                "install", "cluster.edu", "pip install failed"
            )
            mock_tf_client_cls.return_value = mock_tf_client

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
            assert "pip install failed" in response.json()["detail"]

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
            patch("blackfish.server.asgi.TigerFlowClient") as mock_tf_client_cls,
        ):
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config

            mock_profile_mgr = AsyncMock()
            mock_profile_mgr_cls.return_value = mock_profile_mgr

            mock_tf_client = AsyncMock()
            mock_tf_client.check_version.return_value = (True, "0.1.0")
            mock_tf_client_cls.return_value = mock_tf_client

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


class TestUpgradeProfileAPI:
    """Test cases for the PUT /api/profiles/{name}/upgrade endpoint."""

    async def test_upgrade_profile_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that upgrading a profile requires authentication."""
        response = await no_auth_client.put("/api/profiles/test-profile/upgrade")
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_upgrade_slurm_profile_success(self, client: AsyncTestClient):
        """Test upgrading a Slurm profile successfully."""
        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi.TigerFlowClient") as mock_tf_client_cls,
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

            mock_tf_client = AsyncMock()
            mock_tf_client_cls.return_value = mock_tf_client

            response = await client.put("/api/profiles/my-slurm/upgrade")

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "ok"
            assert "upgraded" in result["message"].lower()
            mock_tf_client.upgrade.assert_called_once_with(
                tigerflow_spec="tigerflow",
                tigerflow_ml_spec="tigerflow-ml",
            )

    async def test_upgrade_slurm_profile_with_custom_specs(
        self, client: AsyncTestClient
    ):
        """Test upgrading a Slurm profile with custom package specs."""
        from urllib.parse import quote

        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi.TigerFlowClient") as mock_tf_client_cls,
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

            mock_tf_client = AsyncMock()
            mock_tf_client_cls.return_value = mock_tf_client

            custom_tf = "git+https://github.com/org/tigerflow@feature"
            custom_ml = "git+https://github.com/org/tigerflow-ml@feature"

            # URL encode the params for the query string
            response = await client.put(
                f"/api/profiles/my-slurm/upgrade"
                f"?tigerflow_spec={quote(custom_tf, safe='')}"
                f"&tigerflow_ml_spec={quote(custom_ml, safe='')}"
            )

            assert response.status_code == 200
            # The server will decode the URL-encoded params back to the original values
            mock_tf_client.upgrade.assert_called_once_with(
                tigerflow_spec=custom_tf,
                tigerflow_ml_spec=custom_ml,
            )

    async def test_upgrade_slurm_profile_localhost_uses_local_runner(
        self, client: AsyncTestClient
    ):
        """Test upgrading a Slurm profile with localhost uses LocalRunner.

        This is the Open OnDemand scenario.
        """
        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi.TigerFlowClient") as mock_tf_client_cls,
            patch("blackfish.server.asgi.LocalRunner") as mock_local_runner_cls,
            patch("blackfish.server.asgi.SSHRunner") as mock_ssh_runner_cls,
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

            mock_tf_client = AsyncMock()
            mock_tf_client_cls.return_value = mock_tf_client

            mock_local_runner = MagicMock()
            mock_local_runner_cls.return_value = mock_local_runner

            response = await client.put("/api/profiles/ondemand-slurm/upgrade")

            assert response.status_code == 200
            # Verify LocalRunner was used, not SSHRunner
            mock_local_runner_cls.assert_called_once()
            mock_ssh_runner_cls.assert_not_called()
            mock_tf_client.upgrade.assert_called_once()

    async def test_upgrade_profile_not_found(self, client: AsyncTestClient):
        """Test upgrading a nonexistent profile returns 404."""
        with patch("blackfish.server.asgi._get_profiles_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.__contains__ = MagicMock(return_value=False)
            mock_get_config.return_value = mock_config

            response = await client.put("/api/profiles/nonexistent/upgrade")

            assert response.status_code == 404

    async def test_upgrade_local_profile_not_allowed(self, client: AsyncTestClient):
        """Test that upgrading a local profile returns 400."""
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

            response = await client.put("/api/profiles/my-local/upgrade")

            assert response.status_code == 400

    async def test_upgrade_profile_missing_required_fields(
        self, client: AsyncTestClient
    ):
        """Test that upgrade fails when profile has missing fields."""
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

            response = await client.put("/api/profiles/broken-profile/upgrade")

            assert response.status_code == 400

    async def test_upgrade_profile_tigerflow_error(self, client: AsyncTestClient):
        """Test that TigerFlowError during upgrade returns 500."""
        from blackfish.server.jobs.client import TigerFlowError

        with (
            patch("blackfish.server.asgi._get_profiles_config") as mock_get_config,
            patch("blackfish.server.asgi.TigerFlowClient") as mock_tf_client_cls,
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

            mock_tf_client = AsyncMock()
            mock_tf_client.upgrade.side_effect = TigerFlowError(
                "upgrade", "cluster.edu", "Failed to upgrade tigerflow"
            )
            mock_tf_client_cls.return_value = mock_tf_client

            response = await client.put("/api/profiles/my-slurm/upgrade")

            assert response.status_code == 500
            assert "Failed to upgrade tigerflow" in response.json()["detail"]
