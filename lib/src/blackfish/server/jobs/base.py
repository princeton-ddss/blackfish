from __future__ import annotations

import asyncio
import os
import shlex
from enum import StrEnum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import yaml
from advanced_alchemy.base import UUIDAuditBase
from jinja2 import Environment, PackageLoader
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from blackfish.server import remote
from blackfish.server.job import (
    JobState,
    SlurmJobConfig,
    format_state,
    parse_state,
)
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
from blackfish.server.models.profile import (
    BlackfishProfile,
    SlurmProfile,
    deserialize_profile,
)

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
    SUBMITTED = auto()  # first sbatch; Slurm hasn't confirmed the allocation yet
    RESUBMITTED = auto()  # a restart's sbatch; Slurm hasn't confirmed it yet
    PENDING = auto()  # allocation queued, awaiting resources
    RUNNING = auto()  # allocation running the pipeline
    STOPPED = auto()
    BROKEN = auto()  # Metadata missing - unable to determine job state
    STALLED = auto()  # Restarts made no forward progress
    EXHAUSTED = auto()  # Restart budget exhausted with work remaining


# Statuses from which a job never transitions again — used to short-circuit
# the polling `update()` so it doesn't do remote work or mutate restart
# counters after the job has settled.
_TERMINAL_STATUSES = frozenset(
    {
        BatchJobStatus.STOPPED,
        BatchJobStatus.STALLED,
        BatchJobStatus.EXHAUSTED,
        BatchJobStatus.BROKEN,
    }
)

# Slurm states in which the allocation is still holding (or awaiting) resources.
_ALIVE_STATES = frozenset(
    {
        JobState.RUNNING,
        JobState.PENDING,
        JobState.REQUEUED,
        JobState.RESIZING,
        JobState.SUSPENDED,
    }
)

# Slurm states in which the allocation has *definitely* ended. Only these
# trigger a restart. A pid that sacct doesn't yet know (just resubmitted) reads
# as MISSING, which is "unknown" — NOT terminal — so it never resubmits: we wait
# for the next poll rather than double-allocate.
_TERMINAL_SLURM_STATES = frozenset(
    {
        JobState.COMPLETED,
        JobState.TIMEOUT,
        JobState.FAILED,
        JobState.CANCELLED,
        JobState.NODE_FAIL,
        JobState.OUT_OF_MEMORY,
        JobState.DEADLINE,
        JobState.BOOT_FAIL,
        JobState.PREEMPTED,
        JobState.REVOKED,
    }
)


def format_status(status: BatchJobStatus | None) -> str:
    """Format job status for display."""
    return status.upper() if status else "NONE"


def _resolve_image_and_provider(
    app_config: "State | BlackfishConfig",
    profile: "BlackfishProfile | None",
) -> tuple[Any, Any]:
    """Resolve the tigerflow-ml ImageSpec and container provider.

    The cluster runs Apptainer, so only a LocalProfile consults the locally
    detected ``CONTAINER_PROVIDER``; everything else is Apptainer.
    """
    from blackfish.server.config import ContainerProvider, config as _config

    images = getattr(app_config, "IMAGES", None) or _config.IMAGES

    if isinstance(profile, SlurmProfile):
        provider = ContainerProvider.Apptainer
    else:
        provider = (
            getattr(app_config, "CONTAINER_PROVIDER", None)
            or _config.CONTAINER_PROVIDER
            or ContainerProvider.Apptainer
        )

    return images["tigerflow_ml"], provider


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

    image, provider = _resolve_image_and_provider(app_config, profile)
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
    # SIF location uses the profile cache_dir, not job.cache_dir (the HF cache).
    cache_dir = profile.cache_dir if profile else home_dir

    image, provider = _resolve_image_and_provider(app_config, profile)
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
    staged: Mapped[Optional[int]]  # Items remaining (total - finished - errored)
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
        """Build the sbatch resource config from ``self.resources``.

        GPU count accepts either ``gpus`` (what the launcher/services send) or
        ``gres``. This is resolved against the *raw* request resources, not a
        dict pre-merged with ``DEFAULT_JOB_RESOURCES`` — otherwise the default
        ``gres`` would always shadow an explicit ``gpus``.
        """
        req = self.resources or {}
        gpu_count = req.get("gres", req.get("gpus", DEFAULT_JOB_RESOURCES["gres"]))
        res = {**DEFAULT_JOB_RESOURCES, **req}
        return SlurmJobConfig(
            name=self.name,
            time=str(res.get("time", DEFAULT_JOB_RESOURCES["time"])),
            nodes=int(res.get("nodes", 1)),
            ntasks_per_node=int(res.get("cpus", DEFAULT_JOB_RESOURCES["cpus"])),
            mem=int(res.get("mem", DEFAULT_JOB_RESOURCES["mem"])),
            gres=int(gpu_count),
            partition=res.get("partition"),
            constraint=res.get("constraint"),
            account=res.get("account"),
        )

    def _is_slurm(self, profile: "BlackfishProfile | None") -> bool:
        """Whether this job runs under Slurm (sbatch), independent of transport.

        Determined by profile *type*: a ``SlurmProfile`` uses Slurm even when
        reached over a local runner (``host == "localhost"``, the Open OnDemand
        pattern); a ``LocalProfile`` never does. This is orthogonal to the
        SSH-vs-local transport decision, which keys off ``host``.
        """
        return isinstance(profile, SlurmProfile)

    def _render_script(self, app_config: "State | BlackfishConfig") -> str:
        """Render the batch launch script for this job."""
        profile = deserialize_profile(app_config.HOME_DIR, self.profile)
        if profile is None:
            raise ValueError(f"Profile '{self.profile}' not found")

        scheduler = "slurm" if self._is_slurm(profile) else "local"
        home_dir = self.home_dir or profile.home_dir
        pipeline_path = os.path.join(
            home_dir, "jobs", self.id.hex, f"pipeline-{self.id}.yaml"
        )

        image, provider = _resolve_image_and_provider(app_config, profile)
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
        """Render, stage, and launch the batch script.

        The launch mechanism is chosen by profile *type* (Slurm → ``sbatch``,
        Local → ``bash``), and the transport by ``host`` (local vs SSH):
        - SlurmProfile, host=localhost (Open OnDemand): ``sbatch`` locally.
        - SlurmProfile, remote: scp the script, then ``sbatch`` over SSH.
        - LocalProfile: run the script directly with ``bash`` (no Slurm).

        Returns:
            The Slurm job id for Slurm profiles, or a ``local-<uuid>`` sentinel
            for LocalProfile (which has no Slurm allocation).
        """
        profile = deserialize_profile(app_config.HOME_DIR, self.profile)
        is_slurm = self._is_slurm(profile)
        script = self._render_script(app_config)

        local_script_path = Path(
            os.path.join(app_config.HOME_DIR, "jobs", self.id.hex, "start.sh")
        )
        os.makedirs(local_script_path.parent, exist_ok=True)
        with open(local_script_path, "w") as f:
            f.write(script)

        if self.host == "localhost":
            if is_slurm:
                result = await remote.run(
                    [
                        "sbatch",
                        "--chdir",
                        str(local_script_path.parent),
                        str(local_script_path),
                    ]
                )
                return result.stdout.decode("utf-8").strip().split()[-1]
            # LocalProfile: run the container directly; there is no Slurm job id.
            await remote.run(["bash", str(local_script_path)])
            return f"local-{self.id.hex}"

        # Remote SlurmProfile: copy the script and submit via SSH.
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
            ValueError: If ``input_dir`` does not exist.
        """
        logger.info(
            f"Starting batch job {self.id}: task={self.task}, model={self.repo_id}"
        )

        versions = await client.check_health()
        self.tigerflow_version = versions.tigerflow
        self.tigerflow_ml_version = versions.tigerflow_ml

        await self._ensure_directories(client)

        job_id = await self._submit(app_config)
        self.pid = job_id
        self.status = BatchJobStatus.SUBMITTED
        logger.info(f"Batch job {self.id} started (Slurm job {job_id})")

    async def _ensure_directories(self, client: TigerFlowClient) -> None:
        """Validate ``input_dir`` exists and create ``output_dir``.

        ``input_dir`` is the user's assertion of where their data lives — a
        missing one is a mistake, so fail fast rather than silently create it
        (which would run a no-op job). ``output_dir`` is a destination we create
        (also required: apptainer's ``--bind`` needs the source to exist).

        Raises:
            ValueError: If ``input_dir`` does not exist.
        """
        returncode, _, _ = await client.runner.run(
            f"test -d {shlex.quote(self.input_dir)}"
        )
        if returncode != 0:
            raise ValueError(
                f"Input directory does not exist on {client.host}: {self.input_dir}"
            )

        logger.debug(f"Ensuring output directory {self.output_dir}")
        await client.runner.run(f"mkdir -p {shlex.quote(self.output_dir)}")

    # -------------------------------------------------------------------------
    # Stop / update
    # -------------------------------------------------------------------------

    async def stop(self, client: TigerFlowClient) -> None:
        """Stop the batch job: halt the pipeline and cancel its allocation.

        ``client.stop`` only halts the in-container tigerflow pipeline; the
        sbatch allocation (``self.pid``) must also be cancelled or it keeps
        holding resources until walltime. Sets the job STOPPED.

        Args:
            client: TigerFlowClient for remote operations
        """
        logger.debug(f"Stopping batch job {self.id}")

        if self.status == BatchJobStatus.STOPPED:
            logger.debug("Batch job is already stopped. Skipping stop command.")
            return

        await client.stop(self.output_dir)
        await self._cancel_allocation()
        self.status = BatchJobStatus.STOPPED

    async def _cancel_allocation(self) -> None:
        """Cancel the Slurm allocation, if any. Best-effort."""
        if not self.pid or str(self.pid).startswith("local-"):
            return
        scancel_cmd = ["scancel", str(self.pid)]
        try:
            if self.host == "localhost":
                await remote.run(scancel_cmd)
            else:
                await remote.ssh(f"{self.user}@{self.host}", scancel_cmd)
        except Exception as e:  # noqa: BLE001 - cancellation is best-effort
            logger.warning(f"Failed to scancel job {self.pid} for {self.id}: {e}")

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

    async def _count_input_files(self, client: TigerFlowClient) -> int | None:
        """Count input files matching the input extension in ``input_dir``.

        This is the restart denominator (the report has no total-input field).
        Returns ``None`` if the count could not be determined (e.g. a transient
        SSH/``find`` failure), so callers don't treat it as a genuine zero.
        """
        ext = self._resolved_input_ext()
        # `find` avoids the "argument list too long" a shell glob would hit.
        cmd = (
            f"find {shlex.quote(self.input_dir)} -maxdepth 1 -type f "
            f"-name {shlex.quote('*' + ext)} | wc -l"
        )
        returncode, stdout, _ = await client.runner.run(cmd)
        if returncode != 0:
            # Command failure (transient SSH/find error) is not a genuine zero;
            # return None so callers don't mistake it for "no work remaining".
            return None
        try:
            return int(stdout.decode("utf-8").strip())
        except ValueError:
            return None

    async def _observe(
        self, client: TigerFlowClient
    ) -> tuple[int, int | None, JobState]:
        """Fetch the three independent status inputs concurrently.

        Updates progress fields from the report and returns
        ``(processed, total, slurm_state)`` for the caller's status decision.
        ``total`` is ``None`` when the input count could not be determined.
        """
        report, total, state = await asyncio.gather(
            client.report(self.output_dir),
            self._count_input_files(client),
            self._slurm_state(),
        )
        processed = report.progress.pipeline.finished
        self.finished = processed
        self.errored = report.progress.pipeline.errored
        # "staged" is what remains, so finished + errored + staged == total (the
        # CLI progress denominator). Left unchanged when the count is unknown.
        if total is not None:
            self.staged = max(0, total - processed - (self.errored or 0))
        logger.debug(
            f"Batch job {self.id}: processed={processed}/{total}, "
            f"errored={self.errored}, slurm_state={format_state(state)}, "
            f"restarts={self.restarts}, stalled={self.stalled_restarts}"
        )
        return processed, total, state

    def _status_from_observation(
        self, processed: int, total: int | None, state: JobState
    ) -> BatchJobStatus:
        """Read-only status decision from an observation (no restart, no I/O).

        Does NOT touch ``processed_highwater``: that mark is the ``processed``
        count as of the last restart *boundary*, advanced only in ``poll`` when
        an allocation ends. Bumping it on every running poll would make the stall
        guard always see "no progress since high-water" (the running polls would
        have already raised it to the current count), stalling every restart.
        """
        # Done: as many .finished markers as there are inputs.
        if total is not None and total > 0 and processed >= total:
            logger.info(f"Batch job {self.id} complete ({processed}/{total}).")
            return BatchJobStatus.STOPPED

        if state == JobState.PENDING:
            return BatchJobStatus.PENDING

        if state in _ALIVE_STATES:  # RUNNING and other holding states
            return BatchJobStatus.RUNNING

        # Allocation ended with an empty/misconfigured input dir: nothing to
        # restart for, so it's done (rather than a misleading STALLED).
        if total == 0:
            logger.info(
                f"Batch job {self.id}: no inputs matching {self._resolved_input_ext()} "
                f"in {self.input_dir}; marking complete."
            )
            return BatchJobStatus.STOPPED

        # Slurm state is unknown (MISSING — the pid isn't registered yet, e.g. a
        # just-(re)submitted allocation). Keep the current pre-running status
        # (SUBMITTED/RESUBMITTED) so it isn't misreported as RUNNING; poll's
        # restart decision also waits for a definite state.
        if self.status == BatchJobStatus.RESUBMITTED:
            return BatchJobStatus.RESUBMITTED
        return BatchJobStatus.SUBMITTED

    async def refresh(self, client: TigerFlowClient) -> BatchJobStatus:
        """Read-only status refresh — never resubmits or mutates restart counters.

        Reads the tigerflow report (durable ``processed`` count) and Slurm
        liveness and updates progress fields. Safe to call after ``stop()`` or
        before deletion. Use ``poll()`` to also advance the restart loop.

        Caller is responsible for persistence.
        """
        logger.debug(
            f"Refreshing batch job {self.id} (status={format_status(self.status)})"
        )

        # Terminal jobs never change again; skip the remote work.
        current = self.status
        if current is not None and current in _TERMINAL_STATUSES:
            return current

        processed, total, state = await self._observe(client)
        status = self._status_from_observation(processed, total, state)
        self.status = status
        return status

    async def poll(
        self,
        client: TigerFlowClient,
        app_config: "State | BlackfishConfig",
    ) -> BatchJobStatus:
        """Refresh status and advance the restart loop when the allocation has
        ended with work remaining.

        This is the caller that may resubmit — used by the periodic status poll,
        not by stop/delete (those use the read-only ``refresh()``).

        Caller is responsible for persistence.
        """
        logger.debug(
            f"Polling batch job {self.id} (status={format_status(self.status)})"
        )

        current = self.status
        if current is not None and current in _TERMINAL_STATUSES:
            return current

        # The high-water is the processed count as of the last restart boundary.
        # Comparing this allocation's processed count against it tells the stall
        # guard whether *this* allocation made forward progress.
        prev_highwater = self.processed_highwater

        processed, total, state = await self._observe(client)
        status = self._status_from_observation(processed, total, state)

        # Restart only when the allocation has DEFINITELY ended and work remains.
        # A non-terminal state — alive, or "unknown" (MISSING: a just-(re)submitted
        # pid sacct hasn't registered yet) — must not resubmit, or we
        # double-allocate; report the derived status and wait for the next poll.
        # An inconclusive input count (total is None) is likewise not a boundary.
        if (
            state not in _TERMINAL_SLURM_STATES
            or status in _TERMINAL_STATUSES
            or total is None
        ):
            self.status = status
            return status

        # Allocation ended with work remaining. Evaluate the restart guards at
        # this boundary: did this allocation make progress since the last one?
        # Advance the high-water only here, at the boundary, so the next
        # allocation is measured against where this one finished.
        if processed > prev_highwater:
            self.stalled_restarts = 0
            self.processed_highwater = processed
        else:
            self.stalled_restarts += 1

        if self.restarts >= self.max_restarts:
            logger.warning(
                f"Batch job {self.id} exhausted restart budget "
                f"({self.restarts}/{self.max_restarts}) at {processed}/{total} processed."
            )
            self.status = BatchJobStatus.EXHAUSTED
            return BatchJobStatus.EXHAUSTED
        if self.stalled_restarts >= self.max_stalled_restarts:
            logger.warning(
                f"Batch job {self.id} stalled: no progress for "
                f"{self.stalled_restarts} restart(s) at {processed}/{total} processed."
            )
            self.status = BatchJobStatus.STALLED
            return BatchJobStatus.STALLED

        logger.info(
            f"Resubmitting batch job {self.id} "
            f"(processed={processed}/{total}, restart {self.restarts + 1})"
        )
        job_id = await self._submit(app_config)
        self.pid = job_id
        self.restarts += 1
        self.status = BatchJobStatus.RESUBMITTED
        return BatchJobStatus.RESUBMITTED
