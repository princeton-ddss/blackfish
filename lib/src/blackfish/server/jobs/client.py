"""TigerFlow client for monitoring TigerFlow batch jobs via the container image.

Batch jobs launch through a rendered Slurm/local script that runs the
tigerflow-ml container (see ``BatchJob.start``). This client runs the tigerflow
CLI *through the same image* (``apptainer exec <sif> tigerflow ...`` / the Docker
equivalent) to check the image is staged and to report/stop running pipelines —
no managed Python environment is involved.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Optional, Protocol

from pydantic import BaseModel, ValidationError

from blackfish.server.config import ContainerProvider
from blackfish.server.logger import logger

if TYPE_CHECKING:
    from blackfish.server.images import ImageSpec


# Default idle timeout for TigerFlow jobs (minutes)
DEFAULT_IDLE_TIMEOUT = 10


class TigerFlowReportStatus(BaseModel):
    """Status section from tigerflow report."""

    running: bool
    pid: Optional[int]


class TigerFlowPipelineProgress(BaseModel):
    """Pipeline progress from tigerflow report."""

    finished: int
    in_progress: int
    staged: Optional[int]  # None when pipeline is stopped
    errored: int


class TigerFlowTaskProgress(BaseModel):
    """Per-task progress from tigerflow report."""

    name: str
    processed: int
    staged: int
    failed: int


class TigerFlowProgress(BaseModel):
    """Progress section from tigerflow report."""

    pipeline: TigerFlowPipelineProgress
    tasks: list[TigerFlowTaskProgress]


class TigerFlowFileMetric(BaseModel):
    """Per-file metric from tigerflow report."""

    file: str
    started_at: str
    finished_at: str
    duration_ms: float
    status: str  # "success" | "error"


class TigerFlowTaskMetrics(BaseModel):
    """Per-task metrics summary from tigerflow report."""

    count: int
    avg_ms: float
    min_ms: float
    max_ms: float
    durations: list[float]
    files: list[TigerFlowFileMetric]


class TigerFlowErrorDetail(BaseModel):
    """Error detail for a single file from tigerflow report."""

    file: str
    path: str
    timestamp: Optional[str]
    exception_type: str
    message: str
    traceback: str


class TigerFlowReport(BaseModel):
    """Full report from tigerflow report --json."""

    status: TigerFlowReportStatus
    progress: TigerFlowProgress
    metrics: dict[str, TigerFlowTaskMetrics]
    errors: dict[str, list[TigerFlowErrorDetail]]


class TigerFlowVersions(BaseModel):
    """Installed TigerFlow package versions."""

    tigerflow: str
    tigerflow_ml: str


class TigerFlowError(Exception):
    """Error raised when TigerFlow operations fail.

    Args:
        error_type: Type of error (ssh, command, missing, report, stop, unsupported)
        host: The target host where the error occurred
        details: Optional additional context
    """

    def __init__(self, error_type: str, host: str, details: str | None = None):
        self.error_type = error_type
        self.host = host
        self.details = details
        super().__init__(self.user_message())

    def user_message(self) -> str:
        """Return a user-friendly error message."""
        messages = {
            "ssh": f"SSH connection to {self.host} failed.",
            "timeout": f"SSH connection to {self.host} timed out.",
            "command": f"Command failed on {self.host}.",
            "missing": (
                f"tigerflow-ml image not found on {self.host}. "
                "Stage the SIF (see `blackfish image ls`)."
            ),
            "report": f"Failed to get TigerFlow job report on {self.host}.",
            "stop": f"Failed to stop TigerFlow job on {self.host}.",
            "unsupported": f"Required tigerflow features not available on {self.host}. Upgrade the image.",
        }
        message = messages.get(self.error_type, "TigerFlow operation failed.")
        if self.details:
            # Clean up details: use the first meaningful line
            lines = [
                line.strip()
                for line in self.details.strip().split("\n")
                if line.strip()
            ]
            detail = lines[0].replace("ERROR: ", "") if lines else None
            if detail:
                # Remove trailing period from main message, append detail
                message = message.rstrip(".")
                detail = detail.rstrip(".")
                message = f"{message}: {detail}."
        return message


# -----------------------------------------------------------------------------
# Command Runners
# -----------------------------------------------------------------------------


class CommandRunner(Protocol):
    """Protocol for running commands either locally or remotely."""

    @property
    def host(self) -> str:
        """Return the host identifier (hostname or 'localhost')."""
        ...

    async def run(self, command: str) -> tuple[int, bytes, bytes]:
        """Run a command and return (returncode, stdout, stderr)."""
        ...


class SSHRunner:
    """Run commands on a remote host via SSH.

    Args:
        user: SSH username
        host: SSH hostname
        timeout: Command timeout in seconds (default: 60)
    """

    SSH_ERROR_EXIT_CODE = 255

    def __init__(self, user: str, host: str, timeout: float = 120):
        self.user = user
        self._host = host
        self.timeout = timeout

    @property
    def host(self) -> str:
        return self._host

    async def run(self, command: str) -> tuple[int, bytes, bytes]:
        """Run command via SSH.

        Returns:
            Tuple of (returncode, stdout, stderr) for successful SSH connections.
            The returncode reflects the remote command's exit status.

        Raises:
            TigerFlowError: If SSH connection fails or times out
        """
        proc = await asyncio.create_subprocess_exec(
            "ssh",
            f"{self.user}@{self._host}",
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise TigerFlowError(
                "timeout", self._host, f"Timed out after {self.timeout}s"
            )

        returncode = proc.returncode or 0

        # Exit code 255 indicates SSH transport failure (not remote command failure)
        if returncode == self.SSH_ERROR_EXIT_CODE:
            stderr_str = (
                stderr.decode("utf-8").strip() if stderr else "Connection failed"
            )
            raise TigerFlowError("ssh", self._host, stderr_str)

        return (returncode, stdout, stderr)


class LocalRunner:
    """Run commands locally."""

    @property
    def host(self) -> str:
        return "localhost"

    async def run(self, command: str) -> tuple[int, bytes, bytes]:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return (proc.returncode or 0, stdout, stderr)


# -----------------------------------------------------------------------------
# TigerFlow Client
# -----------------------------------------------------------------------------


class TigerFlowClient:
    """Monitor TigerFlow batch jobs by running the tigerflow CLI in the image.

    Batch jobs are launched via a rendered Slurm/local script (see
    ``BatchJob.start``); this client only *monitors* them. It runs the tigerflow
    CLI through the tigerflow-ml container (``apptainer exec <sif> tigerflow ...``
    or the Docker equivalent) to verify the image is staged and to
    report/stop/inspect pipelines. No Python environment is managed.

    Uses a CommandRunner to execute commands either locally or via SSH.
    """

    def __init__(
        self,
        runner: CommandRunner,
        home_dir: str,
        image: "ImageSpec",
        provider: ContainerProvider,
        cache_dir: str,
        on_progress: Callable[[str], None] | None = None,
    ):
        """Initialize TigerFlowClient.

        Args:
            runner: CommandRunner for executing commands (SSHRunner or LocalRunner)
            home_dir: Home directory on the cluster (e.g., ~/.blackfish)
            image: The tigerflow-ml image spec (repo/tag, provides ``.sif`` and
                ``.docker_ref``).
            provider: Container provider (Apptainer or Docker) used to run the CLI.
            cache_dir: Profile cache directory; the SIF is expected at
                ``{cache_dir}/images/{image.sif}``.
            on_progress: Optional callback for progress updates. Defaults to
                ``logger.info``.
        """
        self.runner = runner
        self.home_dir = home_dir
        self.image = image
        self.provider = provider
        self.cache_dir = cache_dir
        self._sif = f"{cache_dir}/images/{image.sif}"
        self._on_progress = on_progress or logger.info

    @property
    def host(self) -> str:
        return self.runner.host

    @property
    def sif_path(self) -> str:
        """Path to the tigerflow-ml SIF on the cluster (cache location)."""
        return self._sif

    def _tigerflow_cmd(self, subcmd: str, binds: list[str] | None = None) -> str:
        """Build the shell command to run ``tigerflow <subcmd>`` in the image.

        The orchestrator/CLI operations are CPU-only, so no ``--nv`` is added.
        Host paths that the CLI must read/write (e.g. the output dir) are bound
        into the container via ``binds``.

        Args:
            subcmd: The tigerflow subcommand and arguments (e.g. "report /out --json").
            binds: Host paths to bind into the container.

        Returns:
            A single shell command string.
        """
        binds = binds or []
        if self.provider is ContainerProvider.Apptainer:
            parts = ["SINGULARITY_NO_EVAL=1", "apptainer", "exec"]
            for src in binds:
                parts += ["--bind", src]
            parts += ["--env", "PYTHONNOUSERSITE=1", self._sif, "tigerflow", subcmd]
            return " ".join(parts)
        else:  # Docker
            parts = ["docker", "run", "--rm"]
            for src in binds:
                parts += ["-v", f"{src}:{src}"]
            parts += [self.image.docker_ref, "tigerflow", subcmd]
            return " ".join(parts)

    async def _run(self, command: str) -> tuple[bytes, bytes]:
        """Run a command and check for success.

        Returns:
            Tuple of (stdout, stderr) bytes

        Raises:
            TigerFlowError: If command fails
        """
        returncode, stdout, stderr = await self.runner.run(command)

        if returncode != 0:
            raise TigerFlowError(
                "command",
                self.host,
                stderr.decode("utf-8").strip() if stderr else f"Exit code {returncode}",
            )

        return stdout, stderr

    # -------------------------------------------------------------------------
    # Image / environment checks
    # -------------------------------------------------------------------------

    async def _sif_exists(self) -> bool:
        """Return whether the SIF is present at the cache or home location.

        Mirrors ``cli/image.py:_sif_paths`` two-location convention.
        """
        home_sif = f"{self.home_dir}/images/{self.image.sif}"
        returncode, _, _ = await self.runner.run(
            f"test -f {self._sif} || test -f {home_sif}"
        )
        return returncode == 0

    async def check_health(self) -> TigerFlowVersions:
        """Verify the tigerflow-ml image is staged and return its versions.

        Checks that the SIF exists, then reads the tigerflow and tigerflow-ml
        versions from inside the container (recorded on the job for
        reproducibility).

        Returns:
            TigerFlowVersions with the image's installed package versions.

        Raises:
            TigerFlowError: If the image is not staged.
        """
        if not await self._sif_exists():
            raise TigerFlowError("missing", self.host)

        tf_version = await self._container_package_version("tigerflow")
        tfml_version = await self._container_package_version("tigerflow-ml")

        return TigerFlowVersions(
            tigerflow=tf_version or "unknown",
            tigerflow_ml=tfml_version or "unknown",
        )

    async def _container_package_version(self, package: str) -> str | None:
        """Read an installed package version from inside the image.

        Args:
            package: Distribution name (e.g. "tigerflow" or "tigerflow-ml").

        Returns:
            Version string, or None if it could not be determined.
        """
        code_snippet = f"import importlib.metadata as m; print(m.version('{package}'))"
        command = self._tigerflow_cmd_python(f'-c "{code_snippet}"')
        returncode, stdout, _ = await self.runner.run(command)
        if returncode != 0:
            return None
        version = stdout.decode("utf-8").strip()
        return version or None

    def _tigerflow_cmd_python(self, args: str) -> str:
        """Build a command to run ``python <args>`` inside the image.

        Used to introspect the container (e.g. read package versions), since the
        image entrypoint is ``tigerflow`` rather than ``python``.
        """
        if self.provider is ContainerProvider.Apptainer:
            return (
                f"SINGULARITY_NO_EVAL=1 apptainer exec "
                f"--env PYTHONNOUSERSITE=1 {self._sif} python {args}"
            )
        else:  # Docker
            return f"docker run --rm --entrypoint python {self.image.docker_ref} {args}"

    # -------------------------------------------------------------------------
    # Job Operations
    # -------------------------------------------------------------------------

    async def report(self, output_dir: str) -> TigerFlowReport:
        """Get a job report (status, progress, metrics, errors).

        The report is computed from on-disk state in ``output_dir`` and is valid
        even after the pipeline process has exited.

        Args:
            output_dir: Path to the pipeline output directory on the cluster.

        Returns:
            TigerFlowReport with current job state and progress.

        Raises:
            TigerFlowError: If the report command fails.
        """
        logger.debug(f"Fetching TigerFlow report for {output_dir}")

        command = self._tigerflow_cmd(f"report {output_dir} --json", binds=[output_dir])

        try:
            stdout, _ = await self._run(command)
            output = stdout.decode("utf-8").strip()

            if not output:
                raise TigerFlowError(
                    "report", self.host, "Empty response from tigerflow report"
                )

            data = json.loads(output)
            return TigerFlowReport.model_validate(data)
        except TigerFlowError:
            raise
        except json.JSONDecodeError as e:
            raise TigerFlowError("report", self.host, f"Invalid JSON response: {e}")
        except ValidationError as e:
            raise TigerFlowError("report", self.host, f"Invalid report format: {e}")

    async def stop(self, output_dir: str) -> None:
        """Stop a running pipeline.

        Args:
            output_dir: Path to the pipeline output directory on the cluster.

        Raises:
            TigerFlowError: If the stop command fails.
        """
        logger.info(f"Stopping TigerFlow job for {output_dir}")

        command = self._tigerflow_cmd(f"stop {output_dir}", binds=[output_dir])

        try:
            await self._run(command)
        except TigerFlowError as e:
            raise TigerFlowError("stop", self.host, e.details)

        logger.info("TigerFlow job stopped")

    # -------------------------------------------------------------------------
    # Task Operations
    # -------------------------------------------------------------------------

    async def list_tasks(self) -> list[dict[str, Any]]:
        """List available tasks from the tigerflow-ml image.

        Returns:
            List of task info dicts.

        Raises:
            TigerFlowError: If the command fails.
        """
        command = self._tigerflow_cmd("tasks list --json")

        try:
            stdout, _ = await self._run(command)
            result: list[dict[str, Any]] = json.loads(stdout.decode("utf-8"))
            return result
        except TigerFlowError as e:
            raise TigerFlowError(
                "command", self.host, f"Failed to list tasks: {e.details}"
            )
        except json.JSONDecodeError as e:
            raise TigerFlowError(
                "command", self.host, f"Invalid JSON from tasks list: {e}"
            )

    async def get_task_info(self, task: str) -> dict[str, Any]:
        """Get details for a specific task.

        Args:
            task: Task name (e.g., "transcribe").

        Returns:
            Task info dict.

        Raises:
            TigerFlowError: If the command fails or the task is not found.
        """
        command = self._tigerflow_cmd(f"tasks info {task} --json")

        try:
            stdout, _ = await self._run(command)
            result: dict[str, Any] = json.loads(stdout.decode("utf-8"))
            return result
        except TigerFlowError as e:
            raise TigerFlowError(
                "command", self.host, f"Failed to get task info: {e.details}"
            )
        except json.JSONDecodeError as e:
            raise TigerFlowError(
                "command", self.host, f"Invalid JSON from task info: {e}"
            )
