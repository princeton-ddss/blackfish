"""Unit tests for cluster module."""

import json
from unittest import mock

import pytest

from blackfish.server.cluster import (
    JobState,
    PartitionState,
    SinfoNodeGroup,
    SlurmClusterInfo,
    SqueueJob,
    _get_number,
    parse_gres,
    parse_sinfo_entry,
    parse_squeue_job,
)


class TestParseGres:
    """Tests for the parse_gres function."""

    def test_empty_string(self):
        assert parse_gres("") == {}

    def test_single_gpu_type(self):
        assert parse_gres("gpu:a100:2(S:0-1)") == {"a100": 2}

    def test_h100(self):
        assert parse_gres("gpu:h100:4(S:0-1)") == {"h100": 4}

    def test_h200(self):
        assert parse_gres("gpu:h200:8(S:0-1)") == {"h200": 8}

    def test_mig_partition(self):
        # MIG partitions have names like "3g.40gb"
        assert parse_gres("gpu:3g.40gb:8(S:0-1)") == {"3g.40gb": 8}

    def test_small_mig(self):
        assert parse_gres("gpu:1g.10gb:28(S:0-1)") == {"1g.10gb": 28}

    def test_no_socket_affinity(self):
        # Some GRES strings may not have socket affinity
        assert parse_gres("gpu:a100:4") == {"a100": 4}

    def test_gh200(self):
        assert parse_gres("gpu:gh200:1(S:0)") == {"gh200": 1}


class TestGetNumber:
    """Tests for the _get_number helper function."""

    def test_none(self):
        assert _get_number(None) is None

    def test_int(self):
        assert _get_number(42) == 42

    def test_float(self):
        assert _get_number(3.14) == 3

    def test_set_true(self):
        assert _get_number({"set": True, "infinite": False, "number": 100}) == 100

    def test_set_false(self):
        assert _get_number({"set": False, "infinite": False, "number": 100}) is None

    def test_infinite(self):
        assert _get_number({"set": True, "infinite": True, "number": 0}) is None

    def test_empty_dict(self):
        assert _get_number({}) is None


class TestParseSinfoEntry:
    """Tests for parse_sinfo_entry function."""

    def test_parse_basic_entry(self):
        """Test parsing a basic sinfo entry."""
        entry = {
            "nodes": {"total": 8, "idle": 2, "allocated": 6, "other": 0},
            "cpus": {"total": 1024, "idle": 500, "allocated": 524},
            "memory": {"minimum": 768000, "maximum": 768000, "allocated": 200000},
            "gres": {"total": "gpu:a100:2(S:0-1)", "used": "gpu:a100:1(IDX:0)"},
            "features": {"total": "amd,rome,a100,rh9"},
            "partition": {
                "name": "gpu",
                "partition": {"state": ["UP"]},
                "maximums": {"time": {"set": True, "infinite": False, "number": 21600}},
            },
        }

        result = parse_sinfo_entry(entry)

        assert isinstance(result, SinfoNodeGroup)
        assert result.partition_name == "gpu"
        assert result.partition_state == PartitionState.UP
        assert result.max_time_minutes == 21600
        assert result.nodes_total == 8
        assert result.nodes_idle == 2
        assert result.cpus_total == 1024
        assert result.gpus_total == {"a100": 2}
        assert result.gpus_used == {"a100": 1}
        assert result.features == {"amd", "rome", "a100", "rh9"}

    def test_parse_entry_no_gpus(self):
        """Test parsing an entry without GPUs."""
        entry = {
            "nodes": {"total": 10, "idle": 5, "allocated": 5, "other": 0},
            "cpus": {"total": 1000, "idle": 500, "allocated": 500},
            "memory": {"minimum": 256000, "maximum": 256000, "allocated": 100000},
            "gres": {"total": "", "used": ""},
            "features": {"total": "intel,cascade"},
            "partition": {
                "name": "cpu",
                "partition": {"state": ["UP"]},
                "maximums": {"time": {"set": True, "infinite": False, "number": 43200}},
            },
        }

        result = parse_sinfo_entry(entry)

        assert result.partition_name == "cpu"
        assert result.gpus_total == {}
        assert result.gpus_used == {}

    def test_parse_entry_missing_fields(self):
        """Test parsing handles missing optional fields gracefully."""
        entry = {
            "nodes": {},
            "cpus": {},
            "memory": {},
            "gres": {},
            "features": {},
            "partition": {"name": "test"},
        }

        result = parse_sinfo_entry(entry)

        assert result.partition_name == "test"
        assert result.partition_state == PartitionState.UNKNOWN
        assert result.nodes_total == 0
        assert result.features == set()


class TestParseSqueueJob:
    """Tests for parse_squeue_job function."""

    def test_parse_running_job(self):
        """Test parsing a running job."""
        job = {
            "partition": "gpu",
            "job_state": ["RUNNING"],
            "state_reason": "None",
        }

        result = parse_squeue_job(job)

        assert isinstance(result, SqueueJob)
        assert result.partition == "gpu"
        assert result.state == JobState.RUNNING
        assert result.state_reason == "None"

    def test_parse_pending_job(self):
        """Test parsing a pending job with reason."""
        job = {
            "partition": "cpu",
            "job_state": ["PENDING"],
            "state_reason": "Priority",
        }

        result = parse_squeue_job(job)

        assert result.partition == "cpu"
        assert result.state == JobState.PENDING
        assert result.state_reason == "Priority"

    def test_parse_job_empty_state(self):
        """Test parsing handles empty job_state list."""
        job = {
            "partition": "gpu",
            "job_state": [],
            "state_reason": None,
        }

        result = parse_squeue_job(job)

        assert result.state == JobState.UNKNOWN
        assert result.state_reason == "None"


class TestAggregateNodeGroups:
    """Tests for partition aggregation logic."""

    @pytest.fixture
    def sample_node_groups(self) -> list[SinfoNodeGroup]:
        """Sample parsed node groups for testing."""
        return [
            # First group in 'gpu' partition - 8 nodes with A100s
            SinfoNodeGroup(
                partition_name="gpu",
                partition_state=PartitionState.UP,
                max_time_minutes=21600,
                nodes_total=8,
                nodes_idle=2,
                nodes_allocated=6,
                nodes_other=0,
                cpus_total=1024,
                cpus_idle=500,
                cpus_allocated=524,
                memory_max_per_node_mb=768000,
                memory_allocated_mb=200000,
                gpus_total={"a100": 2},
                gpus_used={"a100": 1},
                features={"amd", "rome", "a100", "rh9"},
            ),
            # Second group in 'gpu' partition - 4 nodes with H100s
            SinfoNodeGroup(
                partition_name="gpu",
                partition_state=PartitionState.UP,
                max_time_minutes=21600,
                nodes_total=4,
                nodes_idle=0,
                nodes_allocated=4,
                nodes_other=0,
                cpus_total=512,
                cpus_idle=100,
                cpus_allocated=412,
                memory_max_per_node_mb=512000,
                memory_allocated_mb=400000,
                gpus_total={"h100": 4},
                gpus_used={"h100": 4},
                features={"intel", "icelake", "h100", "rh9"},
            ),
            # 'cpu' partition
            SinfoNodeGroup(
                partition_name="cpu",
                partition_state=PartitionState.UP,
                max_time_minutes=43200,
                nodes_total=100,
                nodes_idle=10,
                nodes_allocated=85,
                nodes_other=5,
                cpus_total=10000,
                cpus_idle=2000,
                cpus_allocated=8000,
                memory_max_per_node_mb=256000,
                memory_allocated_mb=1000000,
                gpus_total={},
                gpus_used={},
                features={"intel", "cascade", "rh9"},
            ),
        ]

    def test_aggregate_partitions(self, sample_node_groups):
        """Test that node groups are correctly aggregated by partition."""
        result = SlurmClusterInfo._aggregate_node_groups(sample_node_groups)

        assert len(result) == 2
        assert "gpu" in result
        assert "cpu" in result

    def test_aggregate_gpu_partition_nodes(self, sample_node_groups):
        """Test node count aggregation for gpu partition."""
        result = SlurmClusterInfo._aggregate_node_groups(sample_node_groups)
        gpu = result["gpu"]

        # 8 + 4 = 12 total nodes
        assert gpu.nodes_total == 12
        assert gpu.nodes_idle == 2
        assert gpu.nodes_allocated == 10
        assert gpu.nodes_down == 0

    def test_aggregate_gpu_partition_cpus(self, sample_node_groups):
        """Test CPU count aggregation for gpu partition."""
        result = SlurmClusterInfo._aggregate_node_groups(sample_node_groups)
        gpu = result["gpu"]

        assert gpu.cpus_total == 1536  # 1024 + 512
        assert gpu.cpus_idle == 600  # 500 + 100
        assert gpu.cpus_allocated == 936  # 524 + 412

    def test_aggregate_gpu_partition_gpus(self, sample_node_groups):
        """Test GPU aggregation for gpu partition."""
        result = SlurmClusterInfo._aggregate_node_groups(sample_node_groups)
        gpu = result["gpu"]

        # Should have both a100 and h100
        gpu_types = {g.gpu_type: g for g in gpu.gpus}
        assert "a100" in gpu_types
        assert "h100" in gpu_types

        # A100: 2 per node * 8 nodes = 16 total, 1 per node * 8 = 8 used
        assert gpu_types["a100"].total == 16
        assert gpu_types["a100"].used == 8
        assert gpu_types["a100"].idle == 8

        # H100: 4 per node * 4 nodes = 16 total, all used
        assert gpu_types["h100"].total == 16
        assert gpu_types["h100"].used == 16
        assert gpu_types["h100"].idle == 0

    def test_aggregate_features(self, sample_node_groups):
        """Test that features are unioned across node groups."""
        result = SlurmClusterInfo._aggregate_node_groups(sample_node_groups)
        gpu = result["gpu"]

        # Should have features from both groups
        assert "amd" in gpu.features
        assert "intel" in gpu.features
        assert "a100" in gpu.features
        assert "h100" in gpu.features
        assert "rh9" in gpu.features

    def test_cpu_partition_no_gpus(self, sample_node_groups):
        """Test that CPU partition has no GPUs."""
        result = SlurmClusterInfo._aggregate_node_groups(sample_node_groups)
        cpu = result["cpu"]

        assert cpu.gpus == []

    def test_max_time(self, sample_node_groups):
        """Test max time extraction."""
        result = SlurmClusterInfo._aggregate_node_groups(sample_node_groups)

        assert result["gpu"].max_time_minutes == 21600
        assert result["cpu"].max_time_minutes == 43200

    def test_all_partition_state_reflects_cluster(self):
        """Test that 'all' partition shows UP if any other partition is UP."""
        node_groups = [
            # "all" partition is DOWN (as Slurm often reports it)
            SinfoNodeGroup(
                partition_name="all",
                partition_state=PartitionState.DOWN,
                max_time_minutes=None,
                nodes_total=10,
                nodes_idle=5,
                nodes_allocated=5,
                nodes_other=0,
                cpus_total=1000,
                cpus_idle=500,
                cpus_allocated=500,
                memory_max_per_node_mb=256000,
                memory_allocated_mb=128000,
                gpus_total={},
                gpus_used={},
                features=set(),
            ),
            # "gpu" partition is UP
            SinfoNodeGroup(
                partition_name="gpu",
                partition_state=PartitionState.UP,
                max_time_minutes=21600,
                nodes_total=10,
                nodes_idle=5,
                nodes_allocated=5,
                nodes_other=0,
                cpus_total=1000,
                cpus_idle=500,
                cpus_allocated=500,
                memory_max_per_node_mb=256000,
                memory_allocated_mb=128000,
                gpus_total={"a100": 4},
                gpus_used={"a100": 2},
                features={"a100"},
            ),
        ]

        result = SlurmClusterInfo._aggregate_node_groups(node_groups)

        # "all" should be UP because "gpu" is UP
        assert result["all"].state == PartitionState.UP
        assert result["gpu"].state == PartitionState.UP

    def test_all_partition_stays_down_if_all_down(self):
        """Test that 'all' partition stays DOWN if all partitions are DOWN."""
        node_groups = [
            SinfoNodeGroup(
                partition_name="all",
                partition_state=PartitionState.DOWN,
                max_time_minutes=None,
                nodes_total=10,
                nodes_idle=0,
                nodes_allocated=0,
                nodes_other=10,
                cpus_total=1000,
                cpus_idle=0,
                cpus_allocated=0,
                memory_max_per_node_mb=256000,
                memory_allocated_mb=0,
                gpus_total={},
                gpus_used={},
                features=set(),
            ),
            SinfoNodeGroup(
                partition_name="gpu",
                partition_state=PartitionState.DOWN,
                max_time_minutes=21600,
                nodes_total=10,
                nodes_idle=0,
                nodes_allocated=0,
                nodes_other=10,
                cpus_total=1000,
                cpus_idle=0,
                cpus_allocated=0,
                memory_max_per_node_mb=256000,
                memory_allocated_mb=0,
                gpus_total={},
                gpus_used={},
                features=set(),
            ),
        ]

        result = SlurmClusterInfo._aggregate_node_groups(node_groups)

        # "all" should stay DOWN because no partition is UP
        assert result["all"].state == PartitionState.DOWN
        assert result["gpu"].state == PartitionState.DOWN


class TestAggregateJobs:
    """Tests for job aggregation logic."""

    @pytest.fixture
    def sample_jobs(self) -> list[SqueueJob]:
        """Sample parsed jobs for testing."""
        return [
            SqueueJob(partition="gpu", state=JobState.RUNNING, state_reason="None"),
            SqueueJob(partition="gpu", state=JobState.RUNNING, state_reason="None"),
            SqueueJob(partition="gpu", state=JobState.PENDING, state_reason="Priority"),
            SqueueJob(partition="gpu", state=JobState.PENDING, state_reason="Priority"),
            SqueueJob(
                partition="gpu", state=JobState.PENDING, state_reason="Resources"
            ),
            SqueueJob(partition="cpu", state=JobState.RUNNING, state_reason="None"),
            SqueueJob(partition="cpu", state=JobState.PENDING, state_reason="Priority"),
        ]

    def test_aggregate_jobs(self, sample_jobs):
        """Test job aggregation."""
        result = SlurmClusterInfo._aggregate_jobs(sample_jobs)

        assert len(result) == 2
        assert "gpu" in result
        assert "cpu" in result

    def test_gpu_queue_counts(self, sample_jobs):
        """Test GPU partition queue counts."""
        result = SlurmClusterInfo._aggregate_jobs(sample_jobs)
        gpu_queue = result["gpu"]

        assert gpu_queue.running == 2
        assert gpu_queue.pending == 3

    def test_pending_reasons(self, sample_jobs):
        """Test pending reason aggregation."""
        result = SlurmClusterInfo._aggregate_jobs(sample_jobs)
        gpu_queue = result["gpu"]

        assert gpu_queue.pending_reasons["Priority"] == 2
        assert gpu_queue.pending_reasons["Resources"] == 1

    def test_cpu_queue(self, sample_jobs):
        """Test CPU partition queue."""
        result = SlurmClusterInfo._aggregate_jobs(sample_jobs)
        cpu_queue = result["cpu"]

        assert cpu_queue.running == 1
        assert cpu_queue.pending == 1


class TestSlurmClusterInfo:
    """Tests for SlurmClusterInfo class."""

    def test_is_local_true(self):
        info = SlurmClusterInfo(user="test", host="localhost")
        assert info.is_local() is True

    def test_is_local_false(self):
        info = SlurmClusterInfo(user="test", host="della.princeton.edu")
        assert info.is_local() is False

    @mock.patch("subprocess.check_output")
    def test_run_command_local(self, mock_check_output):
        """Test local command execution."""
        mock_check_output.return_value = b"test output"
        info = SlurmClusterInfo(user="test", host="localhost")

        result = info._run_command(["sinfo", "--json"])

        mock_check_output.assert_called_once_with(["sinfo", "--json"], timeout=10)
        assert result == b"test output"

    @mock.patch("subprocess.check_output")
    def test_run_command_remote(self, mock_check_output):
        """Test remote command execution via SSH."""
        mock_check_output.return_value = b"test output"
        info = SlurmClusterInfo(user="testuser", host="cluster.example.com")

        result = info._run_command(["sinfo", "--json"])

        mock_check_output.assert_called_once_with(
            ["ssh", "testuser@cluster.example.com", "sinfo", "--json"], timeout=10
        )
        assert result == b"test output"

    @mock.patch("subprocess.check_output")
    def test_get_status(self, mock_check_output):
        """Test full get_status integration."""
        sinfo_response = {
            "sinfo": [
                {
                    "nodes": {"total": 10, "idle": 5, "allocated": 5, "other": 0},
                    "cpus": {"total": 1000, "idle": 500, "allocated": 500},
                    "memory": {
                        "minimum": 100000,
                        "maximum": 100000,
                        "allocated": 50000,
                    },
                    "gres": {
                        "total": "gpu:a100:4(S:0-1)",
                        "used": "gpu:a100:2(IDX:0-1)",
                    },
                    "features": {"total": "a100,rh9"},
                    "partition": {
                        "name": "gpu",
                        "partition": {"state": ["UP"]},
                        "maximums": {
                            "time": {"set": True, "infinite": False, "number": 1440}
                        },
                    },
                }
            ]
        }
        squeue_response = {
            "jobs": [
                {"partition": "gpu", "job_state": ["RUNNING"], "state_reason": "None"},
                {
                    "partition": "gpu",
                    "job_state": ["PENDING"],
                    "state_reason": "Priority",
                },
            ]
        }

        mock_check_output.side_effect = [
            json.dumps(sinfo_response).encode(),
            json.dumps(squeue_response).encode(),
        ]

        info = SlurmClusterInfo(user="test", host="localhost")
        status = info.get_status()

        assert "gpu" in status.partitions
        assert status.partitions["gpu"].cpus_total == 1000
        assert status.partitions["gpu"].cpus_idle == 500
        assert len(status.partitions["gpu"].gpus) == 1
        assert status.partitions["gpu"].gpus[0].gpu_type == "a100"

        assert "gpu" in status.queue
        assert status.queue["gpu"].running == 1
        assert status.queue["gpu"].pending == 1
