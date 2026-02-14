"""API tests for resource tier endpoints.

These tests focus on the HTTP layer: authentication, routing, parameter handling,
and response structure. Tier selection logic is tested in unit/test_tiers.py.
"""

import pytest
from unittest.mock import patch
from litestar.testing import AsyncTestClient

from blackfish.server.models.tiers import TierSource
from blackfish.server.models.metadata import ModelMetadata

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


class TestGetModelTierAPI:
    """Test cases for GET /api/models/{model_id}/tier endpoint."""

    async def test_requires_authentication(self, no_auth_client: AsyncTestClient):
        """Test that endpoint requires authentication."""
        model_id = "cc64bbef-816c-4070-941d-3dabece7a3b9"
        response = await no_auth_client.get(f"/api/models/{model_id}/tier")
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_model_not_found(self, client: AsyncTestClient):
        """Test 404 when model doesn't exist."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/models/{fake_id}/tier")
        assert response.status_code == 404

    async def test_invalid_uuid(self, client: AsyncTestClient):
        """Test validation error for invalid UUID."""
        response = await client.get("/api/models/not-a-uuid/tier")
        assert response.status_code == 400

    async def test_returns_expected_structure(self, client: AsyncTestClient):
        """Test response has required fields."""
        model_id = "cc64bbef-816c-4070-941d-3dabece7a3b9"

        mock_metadata = ModelMetadata(
            model_size_gb=13.5,
            size_source="safetensors",
        )

        with patch(
            "blackfish.server.asgi.get_cached_metadata", return_value=mock_metadata
        ):
            response = await client.get(f"/api/models/{model_id}/tier")

        assert response.status_code == 200
        result = response.json()

        # Verify structure
        assert "partition" in result
        assert "tier" in result
        assert "model_size_gb" in result
        assert "source" in result

    async def test_no_metadata_source(self, client: AsyncTestClient):
        """Test source is NO_METADATA when no cached metadata exists."""
        model_id = "cc64bbef-816c-4070-941d-3dabece7a3b9"

        with patch("blackfish.server.asgi.get_cached_metadata", return_value=None):
            response = await client.get(f"/api/models/{model_id}/tier")

        assert response.status_code == 200
        result = response.json()
        assert result["tier"] is None
        assert result["source"] == TierSource.NO_METADATA.value

    async def test_refresh_parameter_triggers_fetch(self, client: AsyncTestClient):
        """Test that refresh=true calls refresh_metadata."""
        model_id = "cc64bbef-816c-4070-941d-3dabece7a3b9"

        mock_metadata = ModelMetadata(
            model_size_gb=26.0,
            size_source="safetensors",
        )

        with patch(
            "blackfish.server.asgi.refresh_metadata", return_value=mock_metadata
        ) as mock_refresh:
            response = await client.get(f"/api/models/{model_id}/tier?refresh=true")

        assert response.status_code == 200
        mock_refresh.assert_called_once()

    async def test_partition_parameter_passed_through(self, client: AsyncTestClient):
        """Test that partition parameter is used."""
        model_id = "cc64bbef-816c-4070-941d-3dabece7a3b9"

        mock_metadata = ModelMetadata(
            model_size_gb=10.0,
            size_source="safetensors",
        )

        with patch(
            "blackfish.server.asgi.get_cached_metadata", return_value=mock_metadata
        ):
            with patch(
                "blackfish.server.asgi.get_partition_by_name", return_value=None
            ) as mock_get_partition:
                response = await client.get(
                    f"/api/models/{model_id}/tier?partition=custom-gpu"
                )

        # Should have tried to get the specified partition
        mock_get_partition.assert_called()
        call_args = mock_get_partition.call_args
        assert call_args[0][1] == "custom-gpu"
