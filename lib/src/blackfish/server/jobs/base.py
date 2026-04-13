from __future__ import annotations

from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, Optional

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from blackfish.server.jobs.tasks import (
    build_pipeline_config,
    get_default_input_ext,
    get_default_output_ext,
)
from blackfish.server.logger import logger
from blackfish.server.models.profile import SlurmProfile, deserialize_profile
from blackfish.server.jobs.client import (
    LocalRunner,
    SSHRunner,
    TigerFlowClient,
)

if TYPE_CHECKING:
    from litestar.datastructures import State

    from blackfish.server.config import BlackfishConfig


class BatchJobStatus(StrEnum):
    RUNNING = auto()
    STOPPED = auto()
    BROKEN = auto()  # Metadata missing - unable to determine job state


def format_status(status: BatchJobStatus | None) -> str:
    """Format job status for display."""
    return status.upper() if status else "NONE"


def create_tigerflow_client_for_profile(
    profile_name: str,
    app_config: "State | BlackfishConfig",
) -> TigerFlowClient:
    """Create a TigerFlowClient for a profile.

    Factory function that creates the appropriate runner (SSH or local)
    based on the profile configuration.

    Args:
        profile_name: Name of the profile to use
        app_config: Application configuration with HOME_DIR

    Returns:
        Configured TigerFlowClient

    Raises:
        FileNotFoundError: If profile does not exist
    """
    profile = deserialize_profile(app_config.HOME_DIR, profile_name)
    if profile is None:
        raise FileNotFoundError(f"Profile '{profile_name}' not found")

    if isinstance(profile, SlurmProfile):
        runner: SSHRunner | LocalRunner = SSHRunner(
            user=profile.user, host=profile.host
        )
        python_path = profile.python_path
    else:
        runner = LocalRunner()
        python_path = "python3"

    return TigerFlowClient(
        runner=runner,
        home_dir=profile.home_dir,
        python_path=python_path,
    )


def create_tigerflow_client(
    job: "BatchJob",
    app_config: "State | BlackfishConfig",
) -> TigerFlowClient:
    """Create a TigerFlowClient for a batch job.

    Factory function that creates the appropriate runner (SSH or local)
    based on the job's profile configuration.

    Args:
        job: The batch job to create a client for
        app_config: Application configuration with HOME_DIR

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

    # Get python_path from SlurmProfile, default to python3
    python_path = "python3"
    if profile and isinstance(profile, SlurmProfile):
        python_path = profile.python_path

    return TigerFlowClient(
        runner=runner,
        home_dir=home_dir,
        python_path=python_path,
    )


class BatchJob(UUIDAuditBase):
    """Batch job for TigerFlow-based ML task execution.

    TigerFlow manages Slurm jobs internally, so we only need to track:
    - What task to run and its configuration
    - Where the input/output data lives
    - Current status and progress
    """

    __tablename__ = "jobs"

    # Job identity
    name: Mapped[str]
    task: Mapped[str]  # e.g., "transcribe", "summarize"
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

    # Profile info (denormalized for convenience)
    profile: Mapped[str]
    user: Mapped[Optional[str]]
    host: Mapped[Optional[str]]
    home_dir: Mapped[Optional[str]]

    # Job state
    status: Mapped[Optional[BatchJobStatus]]
    pid: Mapped[Optional[str]]  # TigerFlow process ID

    # Progress tracking
    staged: Mapped[Optional[int]]  # Total items to process
    finished: Mapped[Optional[int]]  # Successfully processed
    errored: Mapped[Optional[int]]  # Failed items

    # TigerFlow versions (for reproducibility)
    tigerflow_version: Mapped[Optional[str]]
    tigerflow_ml_version: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"<BatchJob(name={self.name}, task={self.task}, status={self.status})>"

    async def start(self, client: TigerFlowClient) -> None:
        """Start the batch job using TigerFlow.

        Builds pipeline config and starts TigerFlow execution.
        Caller is responsible for persistence.

        Args:
            client: TigerFlowClient for remote operations

        Raises:
            TigerFlowError: If job fails to start
        """
        logger.info(
            f"Starting batch job {self.id}: task={self.task}, model={self.repo_id}"
        )

        # Check TigerFlow environment and record versions for reproducibility
        versions = await client.check_health()
        self.tigerflow_version = versions.tigerflow
        self.tigerflow_ml_version = versions.tigerflow_ml

        # Verify required features are available
        await client.check_capabilities()

        # Build params - model/revision/cache merged with user params
        params: dict[str, Any] = {"model": self.repo_id}
        if self.revision:
            params["revision"] = self.revision
        if self.cache_dir:
            params["cache_dir"] = self.cache_dir
        if self.params:
            params.update(self.params)

        # Build pipeline config
        input_ext = self.input_ext or get_default_input_ext(self.task)
        output_ext = self.output_ext or get_default_output_ext(self.task)
        config = build_pipeline_config(
            task=self.task,
            input_ext=input_ext,
            venv_path=client.venv_path,
            params=params,
            resources=self.resources,
            max_workers=self.max_workers,
            cache_dir=self.cache_dir,
            output_ext=output_ext,
        )

        # Start TigerFlow job
        await client.run(
            config=config,
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            config_name=f"pipeline-{self.id}.yaml",
        )

        self.status = BatchJobStatus.RUNNING
        logger.info(f"Batch job {self.id} started successfully")

    async def stop(self, client: TigerFlowClient) -> None:
        """Stop the batch job.

        Sends stop command to TigerFlow. Call update() separately to
        get final status and progress.

        Args:
            client: TigerFlowClient for remote operations
        """
        logger.debug(f"Stopping batch job {self.id}")

        if self.status == BatchJobStatus.STOPPED:
            logger.debug("Batch job is already stopped. Skipping stop command.")
            return

        await client.stop(self.output_dir)

    async def update(self, client: TigerFlowClient) -> BatchJobStatus:
        """Update job status from TigerFlow.

        Polls TigerFlow for current status and updates job fields.
        Caller is responsible for persistence.

        Args:
            client: TigerFlowClient for remote operations

        Returns:
            Current batch job status

        Raises:
            TigerFlowError: If report command fails
        """
        logger.debug(
            f"Checking status of batch job {self.id}. "
            f"Current status is {format_status(self.status)}."
        )

        report = await client.report(self.output_dir)

        # Update progress from report
        # staged = items waiting + items actively processing (both are "not yet finished")
        # pipeline.staged is None when pipeline is stopped (no items waiting)
        pipeline = report.progress.pipeline
        self.staged = (pipeline.staged or 0) + pipeline.in_progress
        self.finished = pipeline.finished
        self.errored = pipeline.errored
        self.pid = str(report.status.pid) if report.status.pid else None

        # Map TigerFlow running state to BatchJobStatus
        if report.status.running:
            self.status = BatchJobStatus.RUNNING
        else:
            self.status = BatchJobStatus.STOPPED

        logger.debug(
            f"Status check complete for job {self.id}: "
            f"status={format_status(self.status)}, "
            f"staged={self.staged}, finished={self.finished}, errored={self.errored}"
        )

        return self.status
