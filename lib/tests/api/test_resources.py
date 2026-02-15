"""API tests for resource tier endpoints.

These tests focus on the HTTP layer: authentication, routing, parameter handling,
and response structure. Tier selection logic is tested in unit/test_tiers.py.
"""

import pytest
from unittest.mock import patch
from litestar.testing import AsyncTestClient

pytestmark = pytest.mark.anyio


class TestGetProfileResourcesAPI:
    """Test cases for GET /api/profiles/{name}/resources endpoint."""

    async def test_requires_authentication(self, no_auth_client: AsyncTestClient):
        """Test that endpoint requires authentication."""
        response = await no_auth_client.get("/api/profiles/default/resources")
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_profile_not_found(self, client: AsyncTestClient):
        """Test 404 when profile doesn't exist."""
        response = await client.get("/api/profiles/nonexistent/resources")
        assert response.status_code == 404

    async def test_local_profile_not_supported(self, client: AsyncTestClient):
        """Test 404 for local profiles (resource tiers only apply to Slurm)."""
        response = await client.get("/api/profiles/default/resources")
        assert response.status_code == 404
        assert "Slurm" in response.json()["detail"]

    async def test_returns_expected_structure(self, client: AsyncTestClient):
        """Test response has required fields (uses defaults when no remote specs)."""
        from litestar.exceptions import NotFoundException

        # Mock SFTP to simulate no resource_specs.yaml on remote
        with patch(
            "blackfish.server.asgi.sftp.read_file",
            side_effect=NotFoundException(detail="File not found"),
        ):
            response = await client.get("/api/profiles/hpc/resources")

        assert response.status_code == 200
        result = response.json()

        # Verify structure
        assert "time" in result
        assert "default" in result["time"]
        assert "max" in result["time"]
        assert "partitions" in result
        assert isinstance(result["partitions"], list)

        # Each partition should have expected fields
        for partition in result["partitions"]:
            assert "name" in partition
            assert "default" in partition
            assert "tiers" in partition

            # Each tier should have expected fields
            for tier in partition["tiers"]:
                assert "name" in tier
                assert "gpu_count" in tier
                assert "memory_gb" in tier

    async def test_returns_remote_specs(self, client: AsyncTestClient):
        """Test that remote resource_specs.yaml is fetched and parsed."""
        yaml_content = b"""
time:
  default: 60
  max: 240
partitions:
  gpu:
    default: true
    tiers:
      - name: TestTier
        description: Test tier
        max_model_size_gb: 50
        gpu_count: 2
        cpu_cores: 8
        memory_gb: 32
"""
        with patch(
            "blackfish.server.asgi.sftp.read_file",
            return_value=yaml_content,
        ):
            response = await client.get("/api/profiles/hpc/resources")

        assert response.status_code == 200
        result = response.json()

        # Verify custom values from YAML
        assert result["time"]["default"] == 60
        assert result["time"]["max"] == 240
        assert len(result["partitions"]) == 1
        assert result["partitions"][0]["name"] == "gpu"
        assert result["partitions"][0]["tiers"][0]["name"] == "TestTier"
