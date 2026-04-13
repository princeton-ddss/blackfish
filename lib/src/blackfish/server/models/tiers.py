"""Resource tiers for HPC job configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml


class TierSource(str, Enum):
    """Source of tier selection."""

    MODEL_OVERRIDE = "model_override"
    SIZE_MATCH = "size_match"
    NO_METADATA = "no_metadata"
    NO_PARTITION = "no_partition"
    NO_MATCH = "no_match"


@dataclass
class Tier:
    """A resource tier bundling HPC job settings."""

    name: str
    description: str
    max_model_size_gb: Optional[float]
    gpu_count: int
    gpu_type: Optional[str]
    cpu_cores: int
    memory_gb: int
    slurm: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "max_model_size_gb": self.max_model_size_gb,
            "gpu_count": self.gpu_count,
            "gpu_type": self.gpu_type,
            "cpu_cores": self.cpu_cores,
            "memory_gb": self.memory_gb,
        }
        if self.slurm:
            result["slurm"] = self.slurm
        return result


@dataclass
class Partition:
    """A SLURM partition with its available tiers."""

    name: str
    default: bool
    tiers: list[Tier]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "default": self.default,
            "tiers": [t.to_dict() for t in self.tiers],
        }


@dataclass
class TimeConstraints:
    """Time constraints for job submission."""

    default: int  # minutes
    max: int  # minutes

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary for JSON serialization."""
        return {"default": self.default, "max": self.max}


@dataclass
class ResourceSpecs:
    """Complete resource specifications from config."""

    time: TimeConstraints
    partitions: list[Partition]
    models: dict[str, str] = field(default_factory=dict)  # repo_id -> "partition.tier"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "time": self.time.to_dict(),
            "partitions": [p.to_dict() for p in self.partitions],
        }
        if self.models:
            result["models"] = self.models
        return result


def _parse_tier(data: dict[str, Any]) -> Tier:
    """Parse a tier from YAML data."""
    return Tier(
        name=data.get("name", "Unknown"),
        description=data.get("description", ""),
        max_model_size_gb=data.get("max_model_size_gb"),
        gpu_count=data.get("gpu_count", 0),
        gpu_type=data.get("gpu_type"),
        cpu_cores=data.get("cpu_cores", 8),
        memory_gb=data.get("memory_gb", 16),
        slurm=data.get("slurm", {}),
    )


def _parse_partition(name: str, data: dict[str, Any]) -> Partition:
    """Parse a partition from YAML data."""
    tiers = [_parse_tier(t) for t in data.get("tiers", [])]
    return Partition(
        name=name,
        default=data.get("default", False),
        tiers=tiers,
    )


def parse_resource_specs(content: bytes | str) -> Optional[ResourceSpecs]:
    """Parse resource specifications from YAML content.

    Args:
        content: YAML content as bytes or string

    Returns:
        ResourceSpecs if parsing succeeds, None otherwise
    """
    try:
        data = yaml.safe_load(content)

        if not data:
            return None

        # Parse time constraints
        time_data = data.get("time", {})
        time_constraints = TimeConstraints(
            default=time_data.get("default", 30),
            max=time_data.get("max", 180),
        )

        # Parse partitions
        partitions_data = data.get("partitions", {})
        partitions = []
        for name, partition_data in partitions_data.items():
            partitions.append(_parse_partition(name, partition_data))

        # Parse model overrides
        models = data.get("models", {})

        return ResourceSpecs(
            time=time_constraints,
            partitions=partitions,
            models=models,
        )
    except (yaml.YAMLError, KeyError, TypeError) as e:
        print(f"Warning: Failed to parse resource_specs.yaml: {e}")
        return None


def load_resource_specs(cache_dir: str) -> Optional[ResourceSpecs]:
    """Load resource specifications from YAML file.

    Args:
        cache_dir: Path to cache directory containing resource_specs.yaml

    Returns:
        ResourceSpecs if file exists, None otherwise
    """
    specs_path = Path(cache_dir) / "resource_specs.yaml"

    if not specs_path.exists():
        return None

    try:
        with open(specs_path) as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        # Parse time constraints
        time_data = data.get("time", {})
        time_constraints = TimeConstraints(
            default=time_data.get("default", 30),
            max=time_data.get("max", 180),
        )

        # Parse partitions
        partitions_data = data.get("partitions", {})
        partitions = []
        for name, partition_data in partitions_data.items():
            partitions.append(_parse_partition(name, partition_data))

        # Parse model overrides
        models = data.get("models", {})

        return ResourceSpecs(
            time=time_constraints,
            partitions=partitions,
            models=models,
        )
    except (yaml.YAMLError, KeyError, TypeError) as e:
        print(f"Warning: Failed to load resource_specs.yaml: {e}")
        return None


def get_default_partition(specs: ResourceSpecs) -> Optional[Partition]:
    """Get the partition marked as default.

    Args:
        specs: Resource specifications

    Returns:
        Default partition or first partition if none marked default
    """
    for partition in specs.partitions:
        if partition.default:
            return partition

    # Fall back to first partition
    if specs.partitions:
        return specs.partitions[0]

    return None


def get_partition_by_name(specs: ResourceSpecs, name: str) -> Optional[Partition]:
    """Get a partition by name.

    Args:
        specs: Resource specifications
        name: Partition name

    Returns:
        Partition if found, None otherwise
    """
    for partition in specs.partitions:
        if partition.name == name:
            return partition
    return None


def select_tier_for_model(
    model_size_gb: float,
    partition: Partition,
    repo_id: Optional[str] = None,
    specs: Optional[ResourceSpecs] = None,
) -> Optional[tuple[Tier, TierSource]]:
    """Select appropriate tier for a model based on size.

    Args:
        model_size_gb: Model size in GB
        partition: Partition to select tier from
        repo_id: Optional repo ID to check for model-specific overrides
        specs: Optional specs to check for model overrides

    Returns:
        Tuple of (Tier, TierSource) or None if no suitable tier found
    """
    # Check for model-specific override
    if repo_id and specs and repo_id in specs.models:
        override = specs.models[repo_id]
        # Format is "partition.tier" or just "tier"
        if "." in override:
            part_name, tier_name = override.split(".", 1)
            # Only use override if it matches current partition
            if part_name == partition.name:
                for tier in partition.tiers:
                    if tier.name == tier_name:
                        return (tier, TierSource.MODEL_OVERRIDE)
        else:
            # Just tier name, match in current partition
            for tier in partition.tiers:
                if tier.name == override:
                    return (tier, TierSource.MODEL_OVERRIDE)

    # Match by size
    for tier in partition.tiers:
        if tier.max_model_size_gb is None:
            # Catch-all tier (no size limit)
            return (tier, TierSource.SIZE_MATCH)
        if model_size_gb <= tier.max_model_size_gb:
            return (tier, TierSource.SIZE_MATCH)

    # If no tier matches, return the last tier (largest) or None
    if partition.tiers:
        return (partition.tiers[-1], TierSource.SIZE_MATCH)

    return None


def get_default_specs() -> ResourceSpecs:
    """Get fallback default resource specifications.

    Used when no resource_specs.yaml is configured.
    Provides tiers with 0, 1, 2, and 4 GPUs.
    """
    default_tiers = [
        Tier(
            name="CPU Only",
            description="For testing or CPU-only models",
            max_model_size_gb=1.0,
            gpu_count=0,
            gpu_type=None,
            cpu_cores=2,
            memory_gb=4,
        ),
        Tier(
            name="Small",
            description="Small GPU models (up to 32GB)",
            max_model_size_gb=32.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=8,
        ),
        Tier(
            name="Medium",
            description="Medium models (up to 128GB)",
            max_model_size_gb=128.0,
            gpu_count=2,
            gpu_type=None,
            cpu_cores=6,
            memory_gb=16,
        ),
        Tier(
            name="Large",
            description="Large models (128GB+)",
            max_model_size_gb=None,
            gpu_count=4,
            gpu_type=None,
            cpu_cores=8,
            memory_gb=32,
        ),
    ]

    default_partition = Partition(
        name="default",
        default=True,
        tiers=default_tiers,
    )

    return ResourceSpecs(
        time=TimeConstraints(default=30, max=180),
        partitions=[default_partition],
        models={},
    )
