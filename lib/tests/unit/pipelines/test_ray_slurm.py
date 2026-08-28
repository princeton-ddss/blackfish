"""Unit tests for the parts of the Ray-on-Slurm backend that do not need Ray.

The actor lifecycle needs a live Ray cluster and a scheduler, so what is pinned
here is the sizing arithmetic and the sbatch script -- the two places where a
mistake is silent rather than loud. An allocation that misreports its resources
does not fail; it oversubscribes GPUs and everything just gets slower.
"""

import pytest

from blackfish.pipelines.backends.ray_slurm import (
    RayClusterConfig,
    SlurmRayNodePool,
    actors_per_node,
    nodes_required,
    render_node_script,
)
from blackfish.pipelines.spec import JobSpec


def config(**kwargs) -> RayClusterConfig:
    defaults = dict(
        head_address="login01:6379",
        coordinator_url="http://login01:8000",
        payload_dir="/scratch/pipelines/payloads",
    )
    return RayClusterConfig(**{**defaults, **kwargs})


class TestPacking:
    def test_a_single_gpu_job_gets_one_worker_per_gpu(self):
        job = JobSpec(name="a", fn="m:f", resources={"gpus": 1})
        assert actors_per_node(job, {"gpus": 4}) == 4

    def test_a_multi_gpu_job_packs_by_whole_workers(self):
        job = JobSpec(name="a", fn="m:f", resources={"gpus": 3})
        assert actors_per_node(job, {"gpus": 4}) == 1

    def test_a_cpu_job_packs_by_cpu(self):
        job = JobSpec(name="a", fn="m:f", resources={"cpus": 4})
        assert actors_per_node(job, {"cpus": 16, "gpus": 0}) == 4

    def test_a_node_too_small_still_reports_one(self):
        """Better to let the scheduler explain the mismatch than to divide to zero."""
        job = JobSpec(name="a", fn="m:f", resources={"gpus": 8})
        assert actors_per_node(job, {"gpus": 2}) == 1

    @pytest.mark.parametrize(
        "workers,per_node,expected",
        [(0, 4, 0), (1, 4, 1), (4, 4, 1), (5, 4, 2), (9, 4, 3), (3, 1, 3)],
    )
    def test_nodes_required_rounds_up(self, workers, per_node, expected):
        assert nodes_required(workers, per_node) == expected

    def test_no_workers_needs_no_allocations(self):
        assert nodes_required(-1, 4) == 0


class TestNodeScript:
    def test_requests_the_configured_resources(self):
        script = render_node_script(
            config(
                node_resources={"cpus": 16, "mem": 128, "gpus": 2, "time": "08:00:00"}
            ),
            name="bf-ray-abcd1234",
        )
        assert "#SBATCH --cpus-per-task=16" in script
        assert "#SBATCH --mem=128G" in script
        assert "#SBATCH --time=08:00:00" in script
        assert "#SBATCH --gres=gpu:2" in script

    def test_omits_gres_when_no_gpu_is_requested(self):
        script = render_node_script(config(node_resources={"gpus": 0}), name="n")
        assert "--gres" not in script

    def test_joins_the_existing_head_rather_than_starting_one(self):
        script = render_node_script(config(), name="n")
        assert '--address="login01:6379"' in script
        assert "--head" not in script

    def test_bounds_ray_to_what_slurm_granted(self):
        """Ray otherwise reads the whole physical node and oversubscribes it."""
        script = render_node_script(config(node_resources={"gpus": 2}), name="n")
        assert 'NUM_CPUS="${SLURM_CPUS_PER_TASK:-1}"' in script
        assert 'NUM_GPUS="2"' in script

    def test_runs_in_the_container_when_one_is_configured(self):
        script = render_node_script(
            config(image="/scratch/images/blackfish.sif"), name="n"
        )
        assert "apptainer exec" in script
        assert "/scratch/images/blackfish.sif" in script
        assert "--nv" in script

    def test_runs_bare_when_no_container_is_configured(self):
        script = render_node_script(config(), name="n")
        assert "apptainer" not in script
        assert 'ray start "${RAY_ARGS[@]}"' in script

    def test_binds_the_payload_directory_into_the_container(self):
        script = render_node_script(
            config(image="/img.sif", payload_dir="/scratch/payloads"), name="n"
        )
        assert '--bind "/scratch/payloads"' in script

    def test_includes_the_account_when_the_site_requires_one(self):
        assert "#SBATCH --account=ddss" in render_node_script(
            config(account="ddss"), name="n"
        )

    def test_stops_ray_when_the_allocation_ends(self):
        script = render_node_script(config(), name="n")
        assert "trap cleanup EXIT" in script
        assert "ray stop --force" in script


class TestNodePool:
    @pytest.mark.anyio
    async def test_submits_and_cancels_to_reach_the_target(self, tmp_path, monkeypatch):
        submitted: list[list[str]] = []

        class Result:
            stdout = b"12345;cluster\n"

        async def fake_run(cmd, **kwargs):
            submitted.append(cmd)
            return Result()

        monkeypatch.setattr(
            "blackfish.pipelines.backends.ray_slurm.remote.run", fake_run
        )
        pool = SlurmRayNodePool(config(profile_home=str(tmp_path)), "run-1234abcd")

        await pool.ensure(2)
        assert len(pool.job_ids) == 2
        assert all(cmd[0] == "sbatch" for cmd in submitted)

        await pool.ensure(0)
        assert pool.job_ids == []
        assert submitted[-1][0] == "scancel"

    @pytest.mark.anyio
    async def test_each_allocation_gets_its_own_script(self, tmp_path, monkeypatch):
        class Result:
            stdout = b"1\n"

        async def fake_run(cmd, **kwargs):
            return Result()

        monkeypatch.setattr(
            "blackfish.pipelines.backends.ray_slurm.remote.run", fake_run
        )
        pool = SlurmRayNodePool(config(profile_home=str(tmp_path)), "run-1234abcd")
        await pool.ensure(2)
        scripts = sorted(
            p.name for p in (tmp_path / "pipelines" / "run-1234abcd").iterdir()
        )
        assert scripts == ["ray-node-0.sh", "ray-node-1.sh"]
