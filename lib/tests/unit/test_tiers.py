"""Unit tests for resource tier configuration and selection."""

from pathlib import Path
from tempfile import TemporaryDirectory

from blackfish.server.models.tiers import (
    Tier,
    Partition,
    TimeConstraints,
    ResourceSpecs,
    TierSource,
    load_resource_specs,
    get_default_partition,
    get_partition_by_name,
    select_tier_for_model,
    get_slurm_flags,
    get_default_specs,
)


class TestTierDataclasses:
    """Test Tier, Partition, and ResourceSpecs dataclasses."""

    def test_tier_to_dict(self):
        """Test Tier serialization."""
        tier = Tier(
            name="Small",
            description="Small models",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type="a100",
            cpu_cores=4,
            memory_gb=32,
        )
        result = tier.to_dict()

        assert result["name"] == "Small"
        assert result["description"] == "Small models"
        assert result["max_model_size_gb"] == 16.0
        assert result["gpu_count"] == 1
        assert result["gpu_type"] == "a100"
        assert result["cpu_cores"] == 4
        assert result["memory_gb"] == 32

    def test_tier_with_no_size_limit(self):
        """Test Tier with no max size (catch-all)."""
        tier = Tier(
            name="Large",
            description="Large models",
            max_model_size_gb=None,
            gpu_count=4,
            gpu_type=None,
            cpu_cores=16,
            memory_gb=128,
        )
        result = tier.to_dict()

        assert result["max_model_size_gb"] is None

    def test_partition_to_dict(self):
        """Test Partition serialization."""
        tier = Tier(
            name="Small",
            description="Small",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=32,
        )
        partition = Partition(name="gpu", default=True, tiers=[tier])
        result = partition.to_dict()

        assert result["name"] == "gpu"
        assert result["default"] is True
        assert len(result["tiers"]) == 1
        assert result["tiers"][0]["name"] == "Small"

    def test_time_constraints_to_dict(self):
        """Test TimeConstraints serialization."""
        time = TimeConstraints(default=30, max=180)
        result = time.to_dict()

        assert result["default"] == 30
        assert result["max"] == 180

    def test_resource_specs_to_dict(self):
        """Test ResourceSpecs serialization."""
        tier = Tier(
            name="Small",
            description="Small",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=32,
        )
        partition = Partition(name="gpu", default=True, tiers=[tier])
        specs = ResourceSpecs(
            time=TimeConstraints(default=30, max=180),
            partitions=[partition],
            models={"model/repo": "gpu.Small"},
        )
        result = specs.to_dict()

        assert result["time"]["default"] == 30
        assert len(result["partitions"]) == 1
        # Note: models are not included in to_dict (internal use only)


class TestLoadResourceSpecs:
    """Test loading resource specs from YAML."""

    def test_load_resource_specs_file_not_found(self):
        """Test loading when file doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            result = load_resource_specs(tmpdir)
            assert result is None

    def test_load_resource_specs_empty_file(self):
        """Test loading empty YAML file."""
        with TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "resource_specs.yaml"
            specs_path.write_text("")

            result = load_resource_specs(tmpdir)
            assert result is None

    def test_load_resource_specs_valid(self):
        """Test loading valid resource specs."""
        yaml_content = """
time:
  default: 60
  max: 240

partitions:
  gpu:
    default: true
    tiers:
      - name: Small
        description: Small models
        max_model_size_gb: 16
        gpu_count: 1
        cpu_cores: 4
        memory_gb: 32
      - name: Large
        description: Large models
        gpu_count: 4
        cpu_cores: 16
        memory_gb: 128

models:
  meta-llama/Llama-2-70b: gpu.Large
"""
        with TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "resource_specs.yaml"
            specs_path.write_text(yaml_content)

            result = load_resource_specs(tmpdir)

            assert result is not None
            assert result.time.default == 60
            assert result.time.max == 240
            assert len(result.partitions) == 1
            assert result.partitions[0].name == "gpu"
            assert result.partitions[0].default is True
            assert len(result.partitions[0].tiers) == 2
            assert result.partitions[0].tiers[0].name == "Small"
            assert result.partitions[0].tiers[0].max_model_size_gb == 16
            assert result.partitions[0].tiers[1].name == "Large"
            assert result.partitions[0].tiers[1].max_model_size_gb is None
            assert "meta-llama/Llama-2-70b" in result.models

    def test_load_resource_specs_multiple_partitions(self):
        """Test loading specs with multiple partitions."""
        yaml_content = """
time:
  default: 30
  max: 180

partitions:
  gpu:
    default: true
    tiers:
      - name: Small
        description: GPU small
        max_model_size_gb: 16
        gpu_count: 1
        cpu_cores: 4
        memory_gb: 32
  cpu:
    default: false
    tiers:
      - name: Standard
        description: CPU only
        max_model_size_gb: 1
        gpu_count: 0
        cpu_cores: 8
        memory_gb: 16
"""
        with TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "resource_specs.yaml"
            specs_path.write_text(yaml_content)

            result = load_resource_specs(tmpdir)

            assert result is not None
            assert len(result.partitions) == 2

    def test_load_resource_specs_with_slurm_config(self):
        """Test loading specs with SLURM-specific config."""
        yaml_content = """
time:
  default: 30
  max: 180

partitions:
  gpu:
    default: true
    tiers:
      - name: A100
        description: A100 GPUs
        max_model_size_gb: 80
        gpu_count: 1
        cpu_cores: 4
        memory_gb: 32
        slurm:
          constraint: gpu80
          gres: gpu:a100
"""
        with TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "resource_specs.yaml"
            specs_path.write_text(yaml_content)

            result = load_resource_specs(tmpdir)

            assert result is not None
            tier = result.partitions[0].tiers[0]
            assert tier.slurm["constraint"] == "gpu80"
            assert tier.slurm["gres"] == "gpu:a100"

    def test_load_resource_specs_invalid_yaml(self):
        """Test loading invalid YAML."""
        with TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "resource_specs.yaml"
            specs_path.write_text("invalid: yaml: content: [")

            result = load_resource_specs(tmpdir)
            assert result is None


class TestPartitionSelection:
    """Test partition selection functions."""

    def test_get_default_partition(self):
        """Test getting default partition."""
        tier = Tier(
            name="Small",
            description="Small",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=32,
        )
        partition1 = Partition(name="cpu", default=False, tiers=[tier])
        partition2 = Partition(name="gpu", default=True, tiers=[tier])
        specs = ResourceSpecs(
            time=TimeConstraints(default=30, max=180),
            partitions=[partition1, partition2],
        )

        result = get_default_partition(specs)

        assert result is not None
        assert result.name == "gpu"

    def test_get_default_partition_fallback_to_first(self):
        """Test fallback to first partition when none marked default."""
        tier = Tier(
            name="Small",
            description="Small",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=32,
        )
        partition1 = Partition(name="cpu", default=False, tiers=[tier])
        partition2 = Partition(name="gpu", default=False, tiers=[tier])
        specs = ResourceSpecs(
            time=TimeConstraints(default=30, max=180),
            partitions=[partition1, partition2],
        )

        result = get_default_partition(specs)

        assert result is not None
        assert result.name == "cpu"  # First partition

    def test_get_default_partition_empty(self):
        """Test when no partitions exist."""
        specs = ResourceSpecs(
            time=TimeConstraints(default=30, max=180),
            partitions=[],
        )

        result = get_default_partition(specs)
        assert result is None

    def test_get_partition_by_name(self):
        """Test getting partition by name."""
        tier = Tier(
            name="Small",
            description="Small",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=32,
        )
        partition1 = Partition(name="cpu", default=False, tiers=[tier])
        partition2 = Partition(name="gpu", default=True, tiers=[tier])
        specs = ResourceSpecs(
            time=TimeConstraints(default=30, max=180),
            partitions=[partition1, partition2],
        )

        result = get_partition_by_name(specs, "gpu")

        assert result is not None
        assert result.name == "gpu"

    def test_get_partition_by_name_not_found(self):
        """Test when partition name doesn't exist."""
        tier = Tier(
            name="Small",
            description="Small",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=32,
        )
        partition = Partition(name="gpu", default=True, tiers=[tier])
        specs = ResourceSpecs(
            time=TimeConstraints(default=30, max=180),
            partitions=[partition],
        )

        result = get_partition_by_name(specs, "nonexistent")
        assert result is None


class TestTierSelection:
    """Test tier selection logic."""

    def test_select_tier_by_size_small(self):
        """Test selecting tier for small model."""
        small_tier = Tier(
            name="Small",
            description="Small",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=32,
        )
        large_tier = Tier(
            name="Large",
            description="Large",
            max_model_size_gb=None,
            gpu_count=4,
            gpu_type=None,
            cpu_cores=16,
            memory_gb=128,
        )
        partition = Partition(name="gpu", default=True, tiers=[small_tier, large_tier])

        result = select_tier_for_model(10.0, partition)

        assert result is not None
        tier, source = result
        assert tier.name == "Small"
        assert source == TierSource.SIZE_MATCH

    def test_select_tier_by_size_large(self):
        """Test selecting tier for large model."""
        small_tier = Tier(
            name="Small",
            description="Small",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=32,
        )
        large_tier = Tier(
            name="Large",
            description="Large",
            max_model_size_gb=None,
            gpu_count=4,
            gpu_type=None,
            cpu_cores=16,
            memory_gb=128,
        )
        partition = Partition(name="gpu", default=True, tiers=[small_tier, large_tier])

        result = select_tier_for_model(50.0, partition)

        assert result is not None
        tier, source = result
        assert tier.name == "Large"
        assert source == TierSource.SIZE_MATCH

    def test_select_tier_exact_boundary(self):
        """Test selecting tier at exact size boundary."""
        small_tier = Tier(
            name="Small",
            description="Small",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=32,
        )
        partition = Partition(name="gpu", default=True, tiers=[small_tier])

        result = select_tier_for_model(16.0, partition)

        assert result is not None
        tier, source = result
        assert tier.name == "Small"

    def test_select_tier_with_model_override(self):
        """Test tier selection with model-specific override."""
        small_tier = Tier(
            name="Small",
            description="Small",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=32,
        )
        large_tier = Tier(
            name="Large",
            description="Large",
            max_model_size_gb=None,
            gpu_count=4,
            gpu_type=None,
            cpu_cores=16,
            memory_gb=128,
        )
        partition = Partition(name="gpu", default=True, tiers=[small_tier, large_tier])
        specs = ResourceSpecs(
            time=TimeConstraints(default=30, max=180),
            partitions=[partition],
            models={"meta-llama/Llama-2-7b": "gpu.Large"},
        )

        # Model is 13GB, would normally match Small, but has override
        result = select_tier_for_model(
            13.0, partition, repo_id="meta-llama/Llama-2-7b", specs=specs
        )

        assert result is not None
        tier, source = result
        assert tier.name == "Large"
        assert source == TierSource.MODEL_OVERRIDE

    def test_select_tier_override_different_partition(self):
        """Test that override for different partition is ignored."""
        small_tier = Tier(
            name="Small",
            description="Small",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=32,
        )
        partition = Partition(name="gpu", default=True, tiers=[small_tier])
        specs = ResourceSpecs(
            time=TimeConstraints(default=30, max=180),
            partitions=[partition],
            models={"meta-llama/Llama-2-7b": "other_partition.Large"},
        )

        result = select_tier_for_model(
            10.0, partition, repo_id="meta-llama/Llama-2-7b", specs=specs
        )

        assert result is not None
        tier, source = result
        assert tier.name == "Small"
        assert source == TierSource.SIZE_MATCH

    def test_select_tier_override_tier_name_only(self):
        """Test override with just tier name (no partition)."""
        small_tier = Tier(
            name="Small",
            description="Small",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=32,
        )
        large_tier = Tier(
            name="Large",
            description="Large",
            max_model_size_gb=None,
            gpu_count=4,
            gpu_type=None,
            cpu_cores=16,
            memory_gb=128,
        )
        partition = Partition(name="gpu", default=True, tiers=[small_tier, large_tier])
        specs = ResourceSpecs(
            time=TimeConstraints(default=30, max=180),
            partitions=[partition],
            models={"meta-llama/Llama-2-7b": "Large"},
        )

        result = select_tier_for_model(
            10.0, partition, repo_id="meta-llama/Llama-2-7b", specs=specs
        )

        assert result is not None
        tier, source = result
        assert tier.name == "Large"
        assert source == TierSource.MODEL_OVERRIDE

    def test_select_tier_empty_partition(self):
        """Test tier selection with no tiers."""
        partition = Partition(name="gpu", default=True, tiers=[])

        result = select_tier_for_model(10.0, partition)
        assert result is None


class TestSlurmFlags:
    """Test SLURM flag generation."""

    def test_get_slurm_flags_basic(self):
        """Test basic SLURM flag generation."""
        tier = Tier(
            name="Small",
            description="Small",
            max_model_size_gb=16.0,
            gpu_count=1,
            gpu_type=None,
            cpu_cores=4,
            memory_gb=32,
        )

        flags = get_slurm_flags(tier, "gpu")

        assert flags["ntasks_per_node"] == 4
        assert flags["mem"] == 32
        assert flags["gres"] == 1
        assert flags["partition"] == "gpu"
        assert flags["constraint"] is None
        assert flags["gres_str"] == "gpu:1"

    def test_get_slurm_flags_with_constraint(self):
        """Test SLURM flags with constraint."""
        tier = Tier(
            name="A100",
            description="A100 GPUs",
            max_model_size_gb=80.0,
            gpu_count=2,
            gpu_type="a100",
            cpu_cores=8,
            memory_gb=64,
            slurm={"constraint": "gpu80"},
        )

        flags = get_slurm_flags(tier, "gpu")

        assert flags["constraint"] == "gpu80"

    def test_get_slurm_flags_with_gres_type(self):
        """Test SLURM flags with gres type specification."""
        tier = Tier(
            name="A100",
            description="A100 GPUs",
            max_model_size_gb=80.0,
            gpu_count=2,
            gpu_type="a100",
            cpu_cores=8,
            memory_gb=64,
            slurm={"gres": "gpu:a100"},
        )

        flags = get_slurm_flags(tier, "gpu")

        assert flags["gres_str"] == "gpu:a100:2"

    def test_get_slurm_flags_no_gpu(self):
        """Test SLURM flags for CPU-only tier."""
        tier = Tier(
            name="CPU",
            description="CPU only",
            max_model_size_gb=1.0,
            gpu_count=0,
            gpu_type=None,
            cpu_cores=8,
            memory_gb=16,
        )

        flags = get_slurm_flags(tier, "cpu")

        assert flags["gres"] == 0
        assert flags["gres_str"] is None


class TestDefaultSpecs:
    """Test default resource specifications."""

    def test_get_default_specs(self):
        """Test default specs structure."""
        specs = get_default_specs()

        assert specs.time.default == 30
        assert specs.time.max == 180
        assert len(specs.partitions) == 1
        assert specs.partitions[0].name == "default"
        assert specs.partitions[0].default is True
        assert len(specs.partitions[0].tiers) == 4

    def test_get_default_specs_tier_ordering(self):
        """Test that default tiers are ordered by size."""
        specs = get_default_specs()
        tiers = specs.partitions[0].tiers

        assert tiers[0].name == "CPU Only"
        assert tiers[0].gpu_count == 0
        assert tiers[1].name == "Small"
        assert tiers[1].gpu_count == 1
        assert tiers[2].name == "Medium"
        assert tiers[2].gpu_count == 2
        assert tiers[3].name == "Large"
        assert tiers[3].gpu_count == 4

    def test_get_default_specs_size_limits(self):
        """Test default tier size limits."""
        specs = get_default_specs()
        tiers = specs.partitions[0].tiers

        assert tiers[0].max_model_size_gb == 1.0
        assert tiers[1].max_model_size_gb == 32.0
        assert tiers[2].max_model_size_gb == 128.0
        assert tiers[3].max_model_size_gb is None  # Catch-all
