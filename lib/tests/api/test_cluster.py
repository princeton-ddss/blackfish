"""Tests for the cluster status API endpoint."""

from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
from litestar.testing import AsyncTestClient

from blackfish.server.cluster import (
    ClusterStatus,
    GpuAvailability,
    PartitionResources,
    QueueStats,
)

pytestmark = pytest.mark.anyio


class TestClusterStatusAPI:
    """Test cases for the GET /api/cluster/{profile_name}/status endpoint."""

    async def test_cluster_status_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that cluster status endpoint requires authentication."""
        response = await no_auth_client.get("/api/cluster/hpc/status")
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_cluster_status_profile_not_found(self, client: AsyncTestClient):
        """Test that nonexistent profile returns 404."""
        response = await client.get("/api/cluster/nonexistent-profile/status")
        assert response.status_code == 404

    async def test_cluster_status_local_profile_rejected(self, client: AsyncTestClient):
        """Test that local profiles return 422 (not a Slurm profile)."""
        # "default" profile in tests/profiles.cfg is a local profile
        response = await client.get("/api/cluster/default/status")
        assert response.status_code == 400  # ValidationException
        assert "not a Slurm profile" in response.json().get("detail", "")

    async def test_cluster_status_success(self, client: AsyncTestClient):
        """Test successful cluster status retrieval with mocked Slurm query."""
        # Create mock cluster status
        mock_status = ClusterStatus(
            partitions={
                "gpu": PartitionResources(
                    name="gpu",
                    state="UP",
                    nodes_total=10,
                    nodes_idle=3,
                    nodes_allocated=7,
                    nodes_down=0,
                    cpus_total=1000,
                    cpus_idle=300,
                    cpus_allocated=700,
                    memory_total_mb=500000,
                    memory_allocated_mb=350000,
                    gpus=[
                        GpuAvailability(gpu_type="a100", total=40, used=35, idle=5),
                        GpuAvailability(gpu_type="h100", total=20, used=18, idle=2),
                    ],
                    max_time_minutes=21600,
                    features={"a100", "h100", "nvme", "rh9"},
                ),
                "cpu": PartitionResources(
                    name="cpu",
                    state="UP",
                    nodes_total=100,
                    nodes_idle=20,
                    nodes_allocated=80,
                    nodes_down=0,
                    cpus_total=10000,
                    cpus_idle=2000,
                    cpus_allocated=8000,
                    memory_total_mb=5000000,
                    memory_allocated_mb=4000000,
                    gpus=[],
                    max_time_minutes=43200,
                    features={"intel", "cascade", "rh9"},
                ),
            },
            queue={
                "gpu": QueueStats(
                    running=50,
                    pending=25,
                    pending_reasons={"Priority": 20, "Resources": 5},
                ),
                "cpu": QueueStats(
                    running=200,
                    pending=100,
                    pending_reasons={"Priority": 80, "QOSMaxCpuPerUserLimit": 20},
                ),
            },
            timestamp=datetime(2026, 1, 29, 12, 0, 0),
        )

        with patch("blackfish.server.asgi.SlurmClusterInfo") as MockSlurmClusterInfo:
            mock_instance = MagicMock()
            mock_instance.get_status.return_value = mock_status
            MockSlurmClusterInfo.return_value = mock_instance

            # "hpc" profile in tests/profiles.cfg is a Slurm profile
            response = await client.get("/api/cluster/hpc/status")

            assert response.status_code == 200
            result = response.json()

            # Verify structure
            assert "partitions" in result
            assert "queue" in result
            assert "timestamp" in result

            # Verify partitions
            assert "gpu" in result["partitions"]
            assert "cpu" in result["partitions"]

            gpu_partition = result["partitions"]["gpu"]
            assert gpu_partition["name"] == "gpu"
            assert gpu_partition["state"] == "UP"
            assert gpu_partition["nodes_total"] == 10
            assert gpu_partition["nodes_idle"] == 3
            assert gpu_partition["cpus_total"] == 1000
            assert gpu_partition["cpus_idle"] == 300

            # Verify GPUs
            assert len(gpu_partition["gpus"]) == 2
            gpu_types = {g["gpu_type"]: g for g in gpu_partition["gpus"]}
            assert "a100" in gpu_types
            assert gpu_types["a100"]["total"] == 40
            assert gpu_types["a100"]["idle"] == 5

            # Verify features are converted to list (from set)
            assert isinstance(gpu_partition["features"], list)
            assert "a100" in gpu_partition["features"]

            # Verify queue
            assert "gpu" in result["queue"]
            gpu_queue = result["queue"]["gpu"]
            assert gpu_queue["running"] == 50
            assert gpu_queue["pending"] == 25
            assert gpu_queue["pending_reasons"]["Priority"] == 20

            # Verify timestamp is ISO format
            assert result["timestamp"] == "2026-01-29T12:00:00"

            # Verify SlurmClusterInfo was called with correct args
            MockSlurmClusterInfo.assert_called_once_with(
                user="test", host="hpc.example.com"
            )

    async def test_cluster_status_query_fails(self, client: AsyncTestClient):
        """Test that cluster query failure returns 500."""
        with patch("blackfish.server.asgi.SlurmClusterInfo") as MockSlurmClusterInfo:
            mock_instance = MagicMock()
            mock_instance.get_status.side_effect = Exception("SSH connection failed")
            MockSlurmClusterInfo.return_value = mock_instance

            response = await client.get("/api/cluster/hpc/status")

            # Should return 500 Internal Server Error
            assert response.status_code == 500

    async def test_cluster_status_empty_partitions(self, client: AsyncTestClient):
        """Test handling of cluster with no partitions."""
        mock_status = ClusterStatus(
            partitions={},
            queue={},
            timestamp=datetime(2026, 1, 29, 12, 0, 0),
        )

        with patch("blackfish.server.asgi.SlurmClusterInfo") as MockSlurmClusterInfo:
            mock_instance = MagicMock()
            mock_instance.get_status.return_value = mock_status
            MockSlurmClusterInfo.return_value = mock_instance

            response = await client.get("/api/cluster/hpc/status")

            assert response.status_code == 200
            result = response.json()
            assert result["partitions"] == {}
            assert result["queue"] == {}
