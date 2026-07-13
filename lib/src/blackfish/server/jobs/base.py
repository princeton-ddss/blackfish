from __future__ import annotations

import os
from enum import StrEnum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import yaml
from advanced_alchemy.base import UUIDAuditBase
from jinja2 import Environment, PackageLoader
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from blackfish.server import remote
from blackfish.server.job import JobState, SlurmJob, SlurmJobConfig, parse_state
from blackfish.server.jobs.client import (
    DEFAULT_IDLE_TIMEOUT,
    LocalRunner,
    SSHRunner,
    TigerFlowClient,
)
from blackfish.server.jobs.tasks import (
    build_pipeline_config,
    get_default_input_ext,
    get_default_output_ext,
)
from blackfish.server.logger import logger
from blackfish.server.models.profile import SlurmProfile, deserialize_profile

if TYPE_CHECKING:
    from litestar.datastructures import State

    from blackfish.server.config import BlackfishConfig


# Default sbatch resources for a batch allocation when the request omits them.
DEFAULT_JOB_RESOURCES: dict[str, Any] = {
    "cpus": 4,
    "mem": 32,
    "gres": 1,
    "time": "01:00:00",
}

# Default restart-loop bounds.
DEFAULT_MAX_RESTARTS = 20
DEFAULT_MAX_STALLED_RESTARTS = 1


class BatchJobStatus(StrEnum):
    RUNNING = auto()
    STOPPED = auto()
    BROKEN = auto()  # Metadata missing - unable to determine job state
    STALLED = auto()  # Restarts made no forward progress
    EXHAUSTED = auto()  # Restart budget exhausted with work remaining


def format_status(status: BatchJobStatus | None) -> str:
    """Format job status for display."""
    return status.upper() if status else "NONE"


def _resolve_image_and_provider(
    app_config: "State | BlackfishConfig",
) -> tuple[Any, Any]:
    """Resolve the tigerflow-ml ImageSpec and container provider from app config.

    Both litestar ``State`` and ``BlackfishConfig`` expose ``IMAGES`` and
    ``CONTAINER_PROVIDER``; fall back to the module-level config if not.
    """
    from blackfish.server.config import ContainerProvider

    images = getattr(app_config, "IMAGES", None)
    provider = getattr(app_config, "CONTAINER_PROVIDER", None)
    if images is None or provider is None:
        from blackfish.server.config import config as _config

        images = images or _config.IMAGES
        provider = provider or _config.CONTAINER_PROVIDER
    # Cluster batch jobs default to Apptainer when no provider is detected.
    return images["tigerflow_ml"], provider or ContainerProvider.Apptainer


def create_tigerflow_client_for_profile(
    profile_name: str,
    app_config: "State | BlackfishConfig",
) -> TigerFlowClient:
    """Create a TigerFlowClient for a profile.

    Args:
        profile_name: Name of the profile to use
        app_config: Application configuration with HOME_DIR, IMAGES, provider

    Returns:
        Configured TigerFlowClient

    Raises:
        FileNotFoundError: If profile does not exist
    """
    profile = deserialize_profile(app_config.HOME_DIR, profile_name)
    if profile is None:
        raise FileNotFoundError(f"Profile '{profile_name}' not found")

    if isinstance(profile, SlurmProfile) and not profile.is_local():
        runner: SSHRunner | LocalRunner = SSHRunner(
            user=profile.user, host=profile.host
        )
    else:
        runner = LocalRunner()

    image, provider = _resolve_image_and_provider(app_config)
    return TigerFlowClient(
        runner=runner,
        home_dir=profile.home_dir,
        image=image,
        provider=provider,
        cache_dir=profile.cache_dir,
    )


def create_tigerflow_client(
    job: "BatchJob",
    app_config: "State | BlackfishConfig",
) -> TigerFlowClient:
    """Create a TigerFlowClient for a batch job.

    Args:
        job: The batch job to create a client for
        app_config: Application configuration with HOME_DIR, IMAGES, provider

    Returns:
        Configured TigerFlowClient
    """
    profile = deserialize_profile(app_config.HOME_DIR, job.profile)

    if job.host == "localhost":
        runner: SSHRunner | LocalRunner = LocalRunner()
    else:
        if not job.user or not job.host:
            raise ValueError("Missing user or host for remote profile")
        runner = SSHRunner(user=job.user, host=job.host)

    home_dir = job.home_dir or (profile.home_dir if profile else "~/.blackfish")
    cache_dir = job.cache_dir or (profile.cache_dir if profile else home_dir)

    image, provider = _resolve_image_and_provider(app_config)
    return TigerFlowClient(
        runner=runner,
        home_dir=home_dir,
        image=image,
        provider=provider,
        cache_dir=cache_dir,
    )


class BatchJob(UUIDAuditBase):
    """Batch job that runs a tigerflow ``local`` pipeline in the tigerflow-ml
    container as a Slurm allocation.

    The pipeline is resumable: re-running on the same output directory skips
    finished files. Blackfish resubmits the allocation until the input directory
    is fully processed (see ``update``).
    """

    __tablename__ = "jobs"

    # Job identity
    name: Mapped[str]
    task: Mapped[str]  # e.g., "transcribe", "detect"
    repo_id: Mapped[str]  # Model ID (e.g., "openai/whisper-large-v3")
    revision: Mapped[Optional[str]]  # Model revision/version

    # Data paths and file types
    input_dir: Mapped[str]  # Input directory on cluster
    output_dir: Mapped[str]  # Output directory on cluster
    input_ext: Mapped[Optional[str]]  # Input file extension (e.g., ".wav")
    output_ext: Mapped[Optional[str]]  # Output file extension (e.g., ".json")
    cache_dir: Mapped[Optional[str]]  # Model cache directory on cluster

    # Configuration (stored as JSON)
    params: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True, default=None
    )
    resources: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True, default=None
    )
    max_workers: Mapped[int] = mapped_column(default=1)
    idle_timeout: Mapped[Optional[int]] = mapped_column(default=None)  # minutes

    # Profile info (denormalized for convenience)
    profile: Mapped[str]
    user: Mapped[Optional[str]]
    host: Mapped[Optional[str]]
    home_dir: Mapped[Optional[str]]

    # Job state
    status: Mapped[Optional[BatchJobStatus]]
    pid: Mapped[Optional[str]]  # Slurm job ID of the current allocation

    # Progress tracking
    staged: Mapped[Optional[int]]  # Total items to process
    finished: Mapped[Optional[int]]  # Successfully processed
    errored: Mapped[Optional[int]]  # Failed items (transient; reset each run)

    # Restart bookkeeping
    restarts: Mapped[int] = mapped_column(default=0)
    max_restarts: Mapped[int] = mapped_column(default=DEFAULT_MAX_RESTARTS)
    stalled_restarts: Mapped[int] = mapped_column(default=0)
    max_stalled_restarts: Mapped[int] = mapped_column(
        default=DEFAULT_MAX_STALLED_RESTARTS
    )
    processed_highwater: Mapped[int] = mapped_column(default=0)

    # TigerFlow versions (for reproducibility)
    tigerflow_version: Mapped[Optional[str]]
    tigerflow_ml_version: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"<BatchJob(name={self.name}, task={self.task}, status={self.status})>"

    # -------------------------------------------------------------------------
    # Launch
    # -------------------------------------------------------------------------

    def _resolved_input_ext(self) -> str:
        return self.input_ext or get_default_input_ext(self.task)

    def _pipeline_yaml(self) -> str:
        """Build the tigerflow ``local`` pipeline YAML for this job."""
        params: dict[str, Any] = {"model": self.repo_id}
        if self.revision:
            params["revision"] = self.revision
        if self.cache_dir:
            params["cache_dir"] = self.cache_dir
        if self.params:
            params.update(self.params)

        output_ext = self.output_ext or get_default_output_ext(self.task)
        config = build_pipeline_config(
            task=self.task,
            input_ext=self._resolved_input_ext(),
            params=params,
            output_ext=output_ext,
        )
        return yaml.dump(config, default_flow_style=False)

    def _job_config(self) -> SlurmJobConfig:
        """Build the sbatch resource config from ``self.resources``."""
        res = {**DEFAULT_JOB_RESOURCES, **(self.resources or {})}
        return SlurmJobConfig(
            name=self.name,
            time=str(res.get("time", DEFAULT_JOB_RESOURCES["time"])),
            nodes=int(res.get("nodes", 1)),
            ntasks_per_node=int(res.get("cpus", DEFAULT_JOB_RESOURCES["cpus"])),
            mem=int(res.get("mem", DEFAULT_JOB_RESOURCES["mem"])),
            gres=int(res.get("gres", res.get("gpus", DEFAULT_JOB_RESOURCES["gres"]))),
            partition=res.get("partition"),
            constraint=res.get("constraint"),
            account=res.get("account"),
        )

    def _render_script(self, app_config: "State | BlackfishConfig") -> str:
        """Render the batch launch script for this job."""
        profile = deserialize_profile(app_config.HOME_DIR, self.profile)
        if profile is None:
            raise ValueError(f"Profile '{self.profile}' not found")

        scheduler = "slurm" if not profile.is_local() else "local"
        home_dir = self.home_dir or profile.home_dir
        pipeline_path = os.path.join(
            home_dir, "jobs", self.id.hex, f"pipeline-{self.id}.yaml"
        )

        image, provider = _resolve_image_and_provider(app_config)
        env = Environment(loader=PackageLoader("blackfish.server", "templates"))
        template = env.get_template(f"batch_{scheduler}.sh")
        return template.render(
            uuid=self.id.hex,
            name=self.name,
            image=image,
            provider=str(provider),
            profile=profile,
            job_config=self._job_config(),
            pipeline_yaml=self._pipeline_yaml(),
            pipeline_path=pipeline_path,
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            cache_dir=self.cache_dir or profile.cache_dir,
            idle_timeout=self.idle_timeout
            if self.idle_timeout is not None
            else DEFAULT_IDLE_TIMEOUT,
        )

    async def _submit(self, app_config: "State | BlackfishConfig") -> str:
        """Render, stage, and submit the batch script; return the Slurm job ID."""
        script = self._render_script(app_config)

        local_script_path = Path(
            os.path.join(app_config.HOME_DIR, "jobs", self.id.hex, "start.sh")
        )
        os.makedirs(local_script_path.parent, exist_ok=True)
        with open(local_script_path, "w") as f:
            f.write(script)

        if self.host == "localhost":
            result = await remote.run(
                [
                    "sbatch",
                    "--chdir",
                    str(local_script_path.parent),
                    str(local_script_path),
                ]
            )
            return result.stdout.decode("utf-8").strip().split()[-1]

        # Remote: copy the script and submit via SSH.
        profile = deserialize_profile(app_config.HOME_DIR, self.profile)
        home_dir = self.home_dir or (profile.home_dir if profile else "~/.blackfish")
        remote_script_dir = os.path.join(home_dir, "jobs", self.id.hex)
        await remote.ssh(f"{self.user}@{self.host}", ["mkdir", "-p", remote_script_dir])
        await remote.scp(
            str(local_script_path),
            f"{self.user}@{self.host}:{remote_script_dir}",
        )
        result = await remote.ssh(
            f"{self.user}@{self.host}",
            [
                "sbatch",
                "--chdir",
                remote_script_dir,
                os.path.join(remote_script_dir, "start.sh"),
            ],
        )
        return result.stdout.decode("utf-8").strip().split()[-1]

    async def start(
        self,
        app_config: "State | BlackfishConfig",
        client: TigerFlowClient,
    ) -> None:
        """Start the batch job by submitting a containerized Slurm allocation.

        Verifies the image is staged (recording its versions), then renders and
        submits the launch script. Caller is responsible for persistence.

        Args:
            app_config: Application configuration (HOME_DIR, IMAGES, provider).
            client: TigerFlowClient for the image-availability/version check.

        Raises:
            TigerFlowError: If the image is not staged.
        """
        logger.info(
            f"Starting batch job {self.id}: task={self.task}, model={self.repo_id}"
        )

        versions = await client.check_health()
        self.tigerflow_version = versions.tigerflow
        self.tigerflow_ml_version = versions.tigerflow_ml

        job_id = await self._submit(app_config)
        self.pid = job_id
        self.status = BatchJobStatus.RUNNING
        logger.info(f"Batch job {self.id} started (Slurm job {job_id})")

    # -------------------------------------------------------------------------
    # Stop / update
    # -------------------------------------------------------------------------

    async def stop(self, client: TigerFlowClient) -> None:
        """Stop the batch job's pipeline.

        Args:
            client: TigerFlowClient for remote operations
        """
        logger.debug(f"Stopping batch job {self.id}")

        if self.status == BatchJobStatus.STOPPED:
            logger.debug("Batch job is already stopped. Skipping stop command.")
            return

        await client.stop(self.output_dir)

    async def _slurm_state(self) -> JobState:
        """Return the current Slurm state of this job's allocation."""
        if not self.pid:
            return JobState.MISSING
        sacct_cmd = [
            "sacct",
            "-n",
            "-P",
            "-X",
            "-j",
            str(self.pid),
            "-o",
            "State",
        ]
        try:
            if self.host == "localhost":
                result = await remote.run(sacct_cmd)
            else:
                result = await remote.ssh(f"{self.user}@{self.host}", sacct_cmd)
            return parse_state(result.stdout)
        except Exception as e:  # noqa: BLE001 - liveness check is best-effort
            logger.warning(f"Failed to read Slurm state for job {self.id}: {e}")
            return JobState.MISSING

    async def _count_input_files(self, client: TigerFlowClient) -> int:
        """Count input files matching the input extension in ``input_dir``.

        This is the restart denominator (the report has no total-input field).
        """
        ext = self._resolved_input_ext()
        # `find` avoids "argument list too long" that a glob would hit.
        cmd = f"find {self.input_dir} -maxdepth 1 -type f -name '*{ext}' | wc -l"
        returncode, stdout, _ = await client.runner.run(cmd)
        if returncode != 0:
            return 0
        try:
            return int(stdout.decode("utf-8").strip())
        except ValueError:
            return 0

    async def update(
        self,
        client: TigerFlowClient,
        app_config: "State | BlackfishConfig",
    ) -> BatchJobStatus:
        """Update job status, resubmitting the allocation until work is done.

        Reads the tigerflow report (durable ``processed`` count) plus Slurm
        liveness, and applies the restart policy. ``processed`` is the only
        cross-restart-durable "done" signal; ``.err`` files (``errored``) are
        wiped each restart, so they are not used in the restart decision.

        Caller is responsible for persistence.

        Args:
            client: TigerFlowClient for the report.
            app_config: Application configuration (needed to resubmit).

        Returns:
            Current batch job status.
        """
        logger.debug(
            f"Updating batch job {self.id} (status={format_status(self.status)})"
        )

        report = await client.report(self.output_dir)
        processed = report.progress.pipeline.finished
        self.finished = processed
        self.errored = report.progress.pipeline.errored
        self.staged = (
            report.progress.pipeline.staged or 0
        ) + report.progress.pipeline.in_progress

        total = await self._count_input_files(client)

        # Completed: every input has a durable .finished marker.
        if total > 0 and processed >= total:
            self.status = BatchJobStatus.STOPPED
            return BatchJobStatus.STOPPED

        state = await self._slurm_state()
        alive = state in (
            JobState.RUNNING,
            JobState.PENDING,
            JobState.REQUEUED,
            JobState.RESIZING,
            JobState.SUSPENDED,
        )
        if alive:
            if processed > self.processed_highwater:
                self.processed_highwater = processed
            self.status = BatchJobStatus.RUNNING
            return BatchJobStatus.RUNNING

        # The allocation has ended with work remaining. Evaluate the guards at
        # this allocation boundary.
        if processed > self.processed_highwater:
            self.processed_highwater = processed
            self.stalled_restarts = 0
        else:
            self.stalled_restarts += 1

        if self.restarts >= self.max_restarts:
            logger.warning(f"Batch job {self.id} exhausted restart budget.")
            self.status = BatchJobStatus.EXHAUSTED
            return BatchJobStatus.EXHAUSTED
        if self.stalled_restarts >= self.max_stalled_restarts:
            logger.warning(f"Batch job {self.id} stalled (no forward progress).")
            self.status = BatchJobStatus.STALLED
            return BatchJobStatus.STALLED

        logger.info(
            f"Resubmitting batch job {self.id} "
            f"(processed={processed}/{total}, restart {self.restarts + 1})"
        )
        job_id = await self._submit(app_config)
        self.pid = job_id
        self.restarts += 1
        self.status = BatchJobStatus.RUNNING
        return BatchJobStatus.RUNNING

    async def refresh_slurm_job(self) -> SlurmJob | None:
        """Return a SlurmJob view of the current allocation (for callers that
        want raw Slurm state), or None if no allocation is tracked."""
        if not self.pid or not self.host:
            return None
        return SlurmJob(
            job_id=int(self.pid),
            user=self.user or "",
            host=self.host,
            data_dir=os.path.join(self.home_dir or "", "jobs", self.id.hex),
            name=self.name,
        )
