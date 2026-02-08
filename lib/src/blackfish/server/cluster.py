"""Slurm cluster information provider.

This module provides classes for querying Slurm cluster resource availability
at the partition level.
"""

import re
import json
import subprocess
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Any


class PartitionState(StrEnum):
    """Slurm partition states."""

    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


class JobState(StrEnum):
    """Slurm job states."""

    RUNNING = "RUNNING"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"


@dataclass
class SinfoNodeGroup:
    """Parsed node group from sinfo --json.

    Each sinfo entry represents a group of nodes with identical properties.
    """

    # Partition info
    partition_name: str
    partition_state: PartitionState
    max_time_minutes: int | None

    # Node counts for this group
    nodes_total: int
    nodes_idle: int
    nodes_allocated: int
    nodes_other: int  # down, drained, etc.

    # CPU counts (summed across nodes in group)
    cpus_total: int
    cpus_idle: int
    cpus_allocated: int

    # Memory
    memory_max_per_node_mb: int  # max memory per node
    memory_allocated_mb: int  # total allocated across group

    # GPUs (parsed from GRES strings)
    gpus_total: dict[str, int]  # gpu_type -> count per node
    gpus_used: dict[str, int]  # gpu_type -> count per node

    # Node features
    features: set[str]


@dataclass
class SqueueJob:
    """Parsed job from squeue --json."""

    partition: str
    state: JobState
    state_reason: str  # "Priority", "Resources", "None", etc.


@dataclass
class GpuAvailability:
    """GPU availability for a specific GPU type."""

    gpu_type: str  # e.g., "a100", "h100", "h200", "3g.40gb" (MIG)
    total: int  # total GPUs of this type
    used: int  # currently allocated
    idle: int  # available now


@dataclass
class PartitionResources:
    """Current resource availability for a partition."""

    name: str
    state: PartitionState

    # Node counts
    nodes_total: int
    nodes_idle: int
    nodes_allocated: int
    nodes_down: int

    # CPU availability
    cpus_total: int
    cpus_idle: int
    cpus_allocated: int

    # Memory (MB)
    memory_total_mb: int
    memory_allocated_mb: int

    # GPU availability by type
    gpus: list[GpuAvailability]

    # Limits
    max_time_minutes: int | None

    # Features available (union of all node features)
    features: set[str] = field(default_factory=set)


@dataclass
class QueueStats:
    """Queue statistics for a partition."""

    running: int
    pending: int
    pending_reasons: dict[str, int]  # reason -> count


@dataclass
class ClusterStatus:
    """Complete cluster status."""

    partitions: dict[str, PartitionResources]
    queue: dict[str, QueueStats]  # partition -> stats
    timestamp: datetime


# Regex to parse GRES strings like "gpu:a100:4(S:0-1)" or "gpu:3g.40gb:8(S:0-1)"
GRES_PATTERN = re.compile(r"gpu:([^:]+):(\d+)")


def parse_gres(gres_str: str) -> dict[str, int]:
    """Parse GRES string into {gpu_type: count}.

    Examples:
        "gpu:a100:2(S:0-1)" -> {"a100": 2}
        "gpu:h100:4(S:0-1)" -> {"h100": 4}
        "gpu:3g.40gb:8(S:0-1)" -> {"3g.40gb": 8}
        "" -> {}
    """
    if not gres_str:
        return {}

    result: dict[str, int] = {}
    for match in GRES_PATTERN.finditer(gres_str):
        gpu_type = match.group(1)
        count = int(match.group(2))
        result[gpu_type] = result.get(gpu_type, 0) + count

    return result


def _get_number(obj: Any) -> int | None:
    """Extract number from Slurm's value wrapper pattern.

    Slurm uses {"set": bool, "infinite": bool, "number": int} for many values.
    Returns None if not set or infinite.
    """
    if obj is None:
        return None
    if isinstance(obj, (int, float)):
        return int(obj)
    if isinstance(obj, dict):
        if obj.get("infinite", False):
            return None
        if obj.get("set", False):
            return obj.get("number")
        return None
    return None


def parse_sinfo_entry(entry: dict[str, Any]) -> SinfoNodeGroup:
    """Parse a single sinfo JSON entry into a typed SinfoNodeGroup."""
    partition_info = entry.get("partition", {})
    state_list = partition_info.get("partition", {}).get("state", [])

    nodes = entry.get("nodes", {})
    cpus = entry.get("cpus", {})
    memory = entry.get("memory", {})
    gres = entry.get("gres", {})
    features_str = entry.get("features", {}).get("total", "")

    # Convert state string to enum, defaulting to UNKNOWN
    try:
        partition_state = (
            PartitionState(state_list[0]) if state_list else PartitionState.UNKNOWN
        )
    except ValueError:
        partition_state = PartitionState.UNKNOWN

    return SinfoNodeGroup(
        partition_name=partition_info.get("name", "unknown"),
        partition_state=partition_state,
        max_time_minutes=_get_number(
            partition_info.get("maximums", {}).get("time", {})
        ),
        nodes_total=nodes.get("total", 0),
        nodes_idle=nodes.get("idle", 0),
        nodes_allocated=nodes.get("allocated", 0),
        nodes_other=nodes.get("other", 0),
        cpus_total=cpus.get("total", 0),
        cpus_idle=cpus.get("idle", 0),
        cpus_allocated=cpus.get("allocated", 0),
        memory_max_per_node_mb=memory.get("maximum", 0),
        memory_allocated_mb=memory.get("allocated", 0),
        gpus_total=parse_gres(gres.get("total", "")),
        gpus_used=parse_gres(gres.get("used", "")),
        features=set(features_str.split(",")) if features_str else set(),
    )


def parse_squeue_job(job: dict[str, Any]) -> SqueueJob:
    """Parse a single squeue JSON job entry into a typed SqueueJob."""
    states = job.get("job_state", [])

    # Convert state string to enum, defaulting to UNKNOWN
    try:
        job_state = JobState(states[0]) if states else JobState.UNKNOWN
    except ValueError:
        job_state = JobState.UNKNOWN

    return SqueueJob(
        partition=job.get("partition", "unknown"),
        state=job_state,
        state_reason=job.get("state_reason", "None") or "None",
    )


class SlurmClusterInfo:
    """Query Slurm cluster for resource information.

    Usage:
        info = SlurmClusterInfo(user="cs7101", host="della.princeton.edu")
        status = info.get_status()

        for name, partition in status.partitions.items():
            print(f"{name}: {partition.cpus_idle}/{partition.cpus_total} CPUs idle")
            for gpu in partition.gpus:
                print(f"  {gpu.gpu_type}: {gpu.idle}/{gpu.total} available")
    """

    def __init__(self, user: str, host: str):
        self.user = user
        self.host = host

    def is_local(self) -> bool:
        """Check if this is a local connection."""
        return self.host == "localhost"

    def _run_command(self, cmd: list[str], timeout: int = 10) -> bytes:
        """Run command locally or via SSH (sync/blocking)."""
        if self.is_local():
            return subprocess.check_output(cmd, timeout=timeout)
        else:
            return subprocess.check_output(
                ["ssh", f"{self.user}@{self.host}"] + cmd, timeout=timeout
            )

    def get_status(self) -> ClusterStatus:
        """Query sinfo and squeue, return aggregated partition-level status."""
        # Query sinfo for node/partition info
        sinfo_raw = self._run_command(["sinfo", "--json"])
        sinfo_data = json.loads(sinfo_raw)

        # Query squeue for queue info
        squeue_raw = self._run_command(["squeue", "--json"])
        squeue_data = json.loads(squeue_raw)

        # Parse into typed structures
        node_groups = [
            parse_sinfo_entry(entry) for entry in sinfo_data.get("sinfo", [])
        ]
        jobs = [parse_squeue_job(job) for job in squeue_data.get("jobs", [])]

        # Aggregate data
        partitions = self._aggregate_node_groups(node_groups)
        queue = self._aggregate_jobs(jobs)

        return ClusterStatus(
            partitions=partitions,
            queue=queue,
            timestamp=datetime.now(),
        )

    @staticmethod
    def _aggregate_node_groups(
        node_groups: list[SinfoNodeGroup],
    ) -> dict[str, PartitionResources]:
        """Aggregate node groups into partition-level summaries."""
        # Intermediate aggregation structure
        partitions: dict[str, dict[str, Any]] = {}

        for group in node_groups:
            name = group.partition_name

            if name not in partitions:
                partitions[name] = {
                    "state": group.partition_state,
                    "max_time_minutes": group.max_time_minutes,
                    "nodes_total": 0,
                    "nodes_idle": 0,
                    "nodes_allocated": 0,
                    "nodes_down": 0,
                    "cpus_total": 0,
                    "cpus_idle": 0,
                    "cpus_allocated": 0,
                    "memory_total_mb": 0,
                    "memory_allocated_mb": 0,
                    "gpus": {},  # gpu_type -> {"total": int, "used": int}
                    "features": set(),
                }

            p = partitions[name]

            # Aggregate node counts
            p["nodes_total"] += group.nodes_total
            p["nodes_idle"] += group.nodes_idle
            p["nodes_allocated"] += group.nodes_allocated
            p["nodes_down"] += group.nodes_other

            # Aggregate CPU counts
            p["cpus_total"] += group.cpus_total
            p["cpus_idle"] += group.cpus_idle
            p["cpus_allocated"] += group.cpus_allocated

            # Aggregate memory
            # Memory values are per-node; we use max * node count as approximation
            p["memory_total_mb"] += group.memory_max_per_node_mb * group.nodes_total
            p["memory_allocated_mb"] += group.memory_allocated_mb

            # Aggregate GPUs (scale by node count since GRES is per-node)
            for gpu_type, count in group.gpus_total.items():
                if gpu_type not in p["gpus"]:
                    p["gpus"][gpu_type] = {"total": 0, "used": 0}
                p["gpus"][gpu_type]["total"] += count * group.nodes_total

            for gpu_type, count in group.gpus_used.items():
                if gpu_type not in p["gpus"]:
                    p["gpus"][gpu_type] = {"total": 0, "used": 0}
                p["gpus"][gpu_type]["used"] += count * group.nodes_total

            # Aggregate features
            p["features"].update(group.features)

        # Convert to PartitionResources dataclasses
        result: dict[str, PartitionResources] = {}
        for name, p in partitions.items():
            # Convert GPU dict to list of GpuAvailability
            gpus = []
            for gpu_type, counts in p["gpus"].items():
                total = counts["total"]
                used = counts["used"]
                gpus.append(
                    GpuAvailability(
                        gpu_type=gpu_type,
                        total=total,
                        used=used,
                        idle=total - used,
                    )
                )

            # Sort GPUs by type name for consistent ordering
            gpus.sort(key=lambda g: g.gpu_type)

            result[name] = PartitionResources(
                name=name,
                state=p["state"],
                nodes_total=p["nodes_total"],
                nodes_idle=p["nodes_idle"],
                nodes_allocated=p["nodes_allocated"],
                nodes_down=p["nodes_down"],
                cpus_total=p["cpus_total"],
                cpus_idle=p["cpus_idle"],
                cpus_allocated=p["cpus_allocated"],
                memory_total_mb=p["memory_total_mb"],
                memory_allocated_mb=p["memory_allocated_mb"],
                gpus=gpus,
                max_time_minutes=p["max_time_minutes"],
                features=p["features"],
            )

        # "all" partition state should reflect if any partition is UP
        if "all" in result:
            any_up = any(
                p.state == PartitionState.UP
                for name, p in result.items()
                if name != "all"
            )
            if any_up:
                result["all"] = replace(result["all"], state=PartitionState.UP)

        return result

    @staticmethod
    def _aggregate_jobs(jobs: list[SqueueJob]) -> dict[str, QueueStats]:
        """Aggregate jobs into per-partition queue statistics."""
        partitions: dict[str, dict[str, Any]] = {}

        for job in jobs:
            if job.partition not in partitions:
                partitions[job.partition] = {
                    "running": 0,
                    "pending": 0,
                    "pending_reasons": {},
                }

            p = partitions[job.partition]

            if job.state == JobState.RUNNING:
                p["running"] += 1
            elif job.state == JobState.PENDING:
                p["pending"] += 1
                p["pending_reasons"][job.state_reason] = (
                    p["pending_reasons"].get(job.state_reason, 0) + 1
                )

        # Convert to QueueStats
        return {
            name: QueueStats(
                running=p["running"],
                pending=p["pending"],
                pending_reasons=p["pending_reasons"],
            )
            for name, p in partitions.items()
        }
