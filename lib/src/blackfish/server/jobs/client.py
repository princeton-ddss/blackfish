"""TigerFlow client for managing TigerFlow on remote clusters."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any, Optional, Protocol

import yaml  # type: ignore[import-untyped]
from packaging.version import Version
from pydantic import BaseModel, ValidationError

from blackfish.server.logger import logger


# Minimum required package versions (alpha versions accepted during development)
MIN_TIGERFLOW_VERSION = "0.1.0a1"
MIN_TIGERFLOW_ML_VERSION = "0.1.0a0"

# Venv location on remote cluster (relative to home_dir)
VENV_PATH = ".venv"


class TigerFlowStatus(BaseModel):
    """Status returned by tigerflow status command."""

    pid: Optional[int]
    running: bool
    staged: int
    finished: int
    failed: int


class TigerFlowVersions(BaseModel):
    """Installed TigerFlow package versions."""

    tigerflow: str
    tigerflow_ml: str


class TigerFlowError(Exception):
    """Error raised when TigerFlow operations fail.

    Args:
        error_type: Type of error (ssh, command, setup, install, version, missing, run, status, stop)
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
            "setup": f"Failed to set up TigerFlow environment on {self.host}.",
            "install": f"Failed to install TigerFlow on {self.host}.",
            "version": f"TigerFlow version on {self.host} is too old. Run profile setup to upgrade.",
            "missing": f"TigerFlow is not installed on {self.host}. Run profile setup to install.",
            "run": f"Failed to start TigerFlow job on {self.host}.",
            "status": f"Failed to get TigerFlow job status on {self.host}.",
            "stop": f"Failed to stop TigerFlow job on {self.host}.",
            "unsupported": f"Required tigerflow features not available on {self.host}. Upgrade tigerflow.",
        }
        message = messages.get(self.error_type, "TigerFlow operation failed.")
        if self.details:
            # Clean up details: extract the most meaningful line
            lines = [
                line.strip()
                for line in self.details.strip().split("\n")
                if line.strip()
            ]
            # For pip errors, prefer "No matching distribution" as it's clearest
            detail = None
            for line in lines:
                if "No matching distribution" in line:
                    detail = line.replace("ERROR: ", "")
                    break
            # Fall back to first non-empty line
            if detail is None and lines:
                detail = lines[0].replace("ERROR: ", "")
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
    """Client for managing TigerFlow on a cluster.

    Handles venv creation, package installation, and job operations.
    Uses a CommandRunner to execute commands either locally or via SSH.
    """

    def __init__(
        self,
        runner: CommandRunner,
        home_dir: str,
        python_path: str = "python3",
        on_progress: Callable[[str], None] | None = None,
    ):
        """Initialize TigerFlowClient.

        Args:
            runner: CommandRunner for executing commands (SSHRunner or LocalRunner)
            home_dir: Home directory on the cluster (e.g., ~/.blackfish)
            python_path: Path to Python on the cluster (e.g., "python3" or
                "/usr/local/bin/python3.11"). May also include module load commands
                like "module load python && python3".
            on_progress: Optional callback for progress updates. Called with status
                messages during setup, upgrade, and other operations. If None, uses
                logger.info for API compatibility.
        """
        self.runner = runner
        self.home_dir = home_dir
        self.python_path = python_path
        self._venv_path = f"{home_dir}/{VENV_PATH}"
        self._tigerflow_bin = f"{self._venv_path}/bin/tigerflow"
        self._pip_bin = f"{self._venv_path}/bin/pip"
        self._on_progress = on_progress or logger.info

    @property
    def host(self) -> str:
        return self.runner.host

    @property
    def venv_path(self) -> str:
        return self._venv_path

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
    # Venv Management
    # -------------------------------------------------------------------------

    async def setup(
        self,
        tigerflow_spec: str = "tigerflow",
        tigerflow_ml_spec: str = "tigerflow-ml",
    ) -> None:
        """Create venv and install tigerflow + tigerflow-ml.

        Creates the virtual environment at ~/.blackfish/.venv and installs
        the required packages.

        Args:
            tigerflow_spec: Package spec for tigerflow (default: "tigerflow").
                Can be a git URL like "git+https://github.com/org/tigerflow@branch"
            tigerflow_ml_spec: Package spec for tigerflow-ml (default: "tigerflow-ml").
                Can be a git URL like "git+https://github.com/org/tigerflow-ml@branch"

        Raises:
            TigerFlowError: If venv creation or package installation fails
        """
        self._on_progress(f"Setting up TigerFlow on {self.host}")

        # Create parent directory if needed
        try:
            await self._run(f"mkdir -p {self.home_dir}/.blackfish")
        except TigerFlowError:
            raise TigerFlowError("setup", self.host, "Failed to create directory")

        # Create venv
        try:
            self._on_progress("Creating virtual environment...")
            await self._run(f"{self.python_path} -m venv {self._venv_path}")
        except TigerFlowError as e:
            raise TigerFlowError(
                "setup", self.host, f"Failed to create venv: {e.details}"
            )

        # Install packages
        try:
            self._on_progress("Upgrading pip...")
            await self._run(f"{self._pip_bin} install --upgrade pip")
            self._on_progress("Installing tigerflow packages...")
            await self._run(
                f"{self._pip_bin} install {tigerflow_spec} {tigerflow_ml_spec}"
            )
        except TigerFlowError as e:
            raise TigerFlowError("install", self.host, e.details)

        self._on_progress("TigerFlow setup complete")

    async def check_version(self) -> tuple[bool, str | None]:
        """Check if tigerflow meets minimum version.

        Returns:
            Tuple of (version_ok, current_version).
            version_ok is True if installed and meets minimum version.
            current_version is None if not installed.

        Raises:
            TigerFlowError: If version output cannot be parsed (possible corrupt install)
        """
        returncode, stdout, stderr = await self.runner.run(
            f"{self._tigerflow_bin} --version"
        )

        if returncode != 0:
            return (False, None)

        # Parse version from output (e.g., "tigerflow 0.1.0" or "tigerflow 0.1.0a1")
        output = stdout.decode("utf-8").strip()
        match = re.search(r"(\d+\.\d+\.\d+(?:[ab]|rc)?\d*)", output)
        if not match:
            raise TigerFlowError(
                "version",
                self.host,
                f"Could not parse version from: {output}. Try running profile repair.",
            )

        current_version = match.group(1)
        version_ok = Version(current_version) >= Version(MIN_TIGERFLOW_VERSION)

        return (version_ok, current_version)

    async def upgrade(
        self,
        tigerflow_spec: str = "tigerflow",
        tigerflow_ml_spec: str = "tigerflow-ml",
    ) -> str:
        """Upgrade tigerflow + tigerflow-ml to latest.

        Args:
            tigerflow_spec: Package spec for tigerflow (default: "tigerflow").
            tigerflow_ml_spec: Package spec for tigerflow-ml (default: "tigerflow-ml").

        Returns:
            Completion message describing what happened.

        Raises:
            TigerFlowError: If upgrade fails
        """
        # For git URLs, always upgrade (can't check for updates)
        if tigerflow_spec.startswith("git+") or tigerflow_ml_spec.startswith("git+"):
            try:
                self._on_progress("Uninstalling existing packages...")
                await self._run(
                    f"{self._pip_bin} uninstall -y tigerflow tigerflow-ml"
                )
                self._on_progress("Installing packages...")
                await self._run(
                    f"{self._pip_bin} install {tigerflow_spec} {tigerflow_ml_spec}"
                )
            except TigerFlowError as e:
                raise TigerFlowError("install", self.host, e.details)
            return "TigerFlow upgraded."

        # For PyPI packages, check if outdated first
        self._on_progress(f"Checking for updates on {self.host}...")
        try:
            returncode, stdout, _ = await self.runner.run(
                f"{self._pip_bin} list --outdated --format=json"
            )
            if returncode == 0:
                outdated = json.loads(stdout.decode("utf-8"))
                outdated_names = {pkg["name"].lower() for pkg in outdated}
                if "tigerflow" not in outdated_names and "tigerflow-ml" not in outdated_names:
                    return "TigerFlow up-to-date."

            # Upgrade needed
            self._on_progress("Upgrading TigerFlow...")
            await self._run(
                f"{self._pip_bin} install --upgrade {tigerflow_spec} {tigerflow_ml_spec}"
            )
        except TigerFlowError as e:
            raise TigerFlowError("install", self.host, e.details)

        return "TigerFlow upgraded."

    async def cleanup(
        self,
        tigerflow_spec: str = "tigerflow",
        tigerflow_ml_spec: str = "tigerflow-ml",
    ) -> None:
        """Remove and recreate venv (for broken setups).

        Completely removes the existing venv and creates a fresh one
        with tigerflow installed.

        Args:
            tigerflow_spec: Package spec for tigerflow (default: "tigerflow").
            tigerflow_ml_spec: Package spec for tigerflow-ml (default: "tigerflow-ml").

        Raises:
            TigerFlowError: If cleanup fails
        """
        self._on_progress(f"Cleaning up TigerFlow venv on {self.host}...")
        try:
            await self._run(f"rm -rf {self._venv_path}")
        except TigerFlowError as e:
            raise TigerFlowError(
                "setup", self.host, f"Failed to remove venv: {e.details}"
            )

        # Recreate venv
        await self.setup(tigerflow_spec, tigerflow_ml_spec)

    async def _get_package_version(self, package: str) -> str | None:
        """Get installed version of a pip package.

        Args:
            package: Package name (e.g., "tigerflow" or "tigerflow-ml")

        Returns:
            Version string if installed, None otherwise
        """
        returncode, stdout, _ = await self.runner.run(f"{self._pip_bin} show {package}")
        if returncode != 0:
            return None

        # Parse "Version: X.Y.Z" from pip show output
        match = re.search(r"^Version:\s*(.+)$", stdout.decode("utf-8"), re.MULTILINE)
        return match.group(1).strip() if match else None

    async def check_health(self) -> TigerFlowVersions:
        """Verify TigerFlow environment is ready and return installed versions.

        Checks:
        1. Venv exists
        2. tigerflow is installed and meets minimum version
        3. tigerflow-ml is installed and meets minimum version

        Returns:
            TigerFlowVersions with installed package versions (for reproducibility)

        Raises:
            TigerFlowError: If environment is not ready
        """
        # Check venv exists
        returncode, _, _ = await self.runner.run(f"test -d {self._venv_path}")
        if returncode != 0:
            raise TigerFlowError(
                "missing", self.host, "Venv not found. Run profile setup."
            )

        # Check tigerflow
        tf_version = await self._get_package_version("tigerflow")
        if tf_version is None:
            raise TigerFlowError(
                "missing", self.host, "tigerflow not installed. Run profile repair."
            )
        if Version(tf_version) < Version(MIN_TIGERFLOW_VERSION):
            raise TigerFlowError(
                "version",
                self.host,
                f"tigerflow {tf_version} < {MIN_TIGERFLOW_VERSION}. Run profile repair.",
            )

        # Check tigerflow-ml
        tfml_version = await self._get_package_version("tigerflow-ml")
        if tfml_version is None:
            raise TigerFlowError(
                "missing",
                self.host,
                "tigerflow-ml not installed. Run profile repair.",
            )
        if Version(tfml_version) < Version(MIN_TIGERFLOW_ML_VERSION):
            raise TigerFlowError(
                "version",
                self.host,
                f"tigerflow-ml {tfml_version} < {MIN_TIGERFLOW_ML_VERSION}. Run profile repair.",
            )

        return TigerFlowVersions(tigerflow=tf_version, tigerflow_ml=tfml_version)

    async def check_capabilities(self) -> None:
        """Verify that required tigerflow features are available.

        Checks for:
        - Tasks commands (tigerflow tasks list)
        - Pipeline commands (tigerflow status)

        Raises:
            TigerFlowError: If required features are not available
        """
        # Check tasks support by trying 'tigerflow tasks list --json'
        returncode, _, stderr = await self.runner.run(
            f"{self._tigerflow_bin} tasks list --json"
        )
        if returncode != 0:
            stderr_str = stderr.decode("utf-8", errors="replace").lower()
            if "unknown command" in stderr_str or "no such command" in stderr_str:
                raise TigerFlowError(
                    "unsupported",
                    self.host,
                    "tigerflow tasks command not available",
                )

        # Check pipeline support by trying 'tigerflow status --help'
        returncode, _, stderr = await self.runner.run(
            f"{self._tigerflow_bin} status --help"
        )
        if returncode != 0:
            stderr_str = stderr.decode("utf-8", errors="replace").lower()
            if "unknown command" in stderr_str or "no such command" in stderr_str:
                raise TigerFlowError(
                    "unsupported",
                    self.host,
                    "tigerflow status command not available",
                )

    # -------------------------------------------------------------------------
    # Job Operations
    # -------------------------------------------------------------------------

    async def run(
        self,
        config: dict[str, Any],
        input_dir: str,
        output_dir: str,
        idle_timeout: int = 10,
        config_name: str = "pipeline.yaml",
    ) -> None:
        """Start tigerflow job in background.

        Args:
            config: Pipeline configuration dict (will be written as YAML)
            input_dir: Path to input directory on cluster
            output_dir: Path to output directory on cluster
            idle_timeout: Minutes of inactivity before auto-terminating (default: 10)
            config_name: Name of config file (default: pipeline.yaml)

        Raises:
            TigerFlowError: If job fails to start
        """
        logger.info(f"Starting TigerFlow job: input={input_dir}, output={output_dir}")

        # Write config to output_dir/{config_name}
        config_path = f"{output_dir}/{config_name}"
        yaml_content = yaml.dump(config, default_flow_style=False)

        # Create output directory and write config
        try:
            await self._run(f"mkdir -p {output_dir}")
            # Use heredoc to write YAML content
            write_cmd = f"cat > {config_path} << 'TIGERFLOW_CONFIG_EOF'\n{yaml_content}TIGERFLOW_CONFIG_EOF"
            await self._run(write_cmd)
        except TigerFlowError as e:
            raise TigerFlowError(
                "run", self.host, f"Failed to write config: {e.details}"
            )

        # Run tigerflow
        command = (
            f"{self._tigerflow_bin} run {config_path} {input_dir} {output_dir} "
            f"--idle-timeout {idle_timeout} --background"
        )
        logger.debug(f"Running command: {command}")

        try:
            await self._run(command)
        except TigerFlowError as e:
            raise TigerFlowError("run", self.host, e.details)

        logger.info("TigerFlow job started successfully")

    async def status(self, output_dir: str) -> TigerFlowStatus:
        """Get job status.

        Args:
            output_dir: Path to output directory on cluster

        Returns:
            TigerFlowStatus with current job state and progress

        Raises:
            TigerFlowError: If status check fails
        """
        logger.debug(f"Checking TigerFlow status for {output_dir}")

        command = f"{self._tigerflow_bin} status {output_dir} --json"

        # Use runner.run() directly instead of _run() because tigerflow status
        # returns exit code 1 for stopped pipelines but still outputs valid JSON
        try:
            returncode, stdout, stderr = await self.runner.run(command)
            output = stdout.decode("utf-8").strip()

            # Try to parse JSON even on non-zero exit code
            # tigerflow returns exit code 1 for stopped pipelines with valid output
            if output:
                try:
                    data = json.loads(output)
                    return TigerFlowStatus.model_validate(data)
                except (json.JSONDecodeError, ValidationError):
                    pass  # Fall through to error handling

            # No valid JSON output - report the error
            if returncode != 0:
                error_detail = stderr.decode("utf-8").strip() if stderr else f"Exit code {returncode}"
                raise TigerFlowError("status", self.host, error_detail)

            raise TigerFlowError("status", self.host, "Empty response from tigerflow status")
        except json.JSONDecodeError as e:
            raise TigerFlowError("status", self.host, f"Invalid JSON response: {e}")
        except ValidationError as e:
            raise TigerFlowError("status", self.host, f"Invalid status format: {e}")

    async def stop(self, output_dir: str) -> None:
        """Stop a running job.

        Args:
            output_dir: Path to output directory on cluster

        Raises:
            TigerFlowError: If stop command fails
        """
        logger.info(f"Stopping TigerFlow job for {output_dir}")

        command = f"{self._tigerflow_bin} stop {output_dir}"

        try:
            await self._run(command)
        except TigerFlowError as e:
            raise TigerFlowError("stop", self.host, e.details)

        logger.info("TigerFlow job stopped")

    # -------------------------------------------------------------------------
    # Task Operations
    # -------------------------------------------------------------------------

    async def list_tasks(self) -> list[dict[str, Any]]:
        """List available tasks from tigerflow-ml.

        Returns:
            List of task info dicts with name, description, etc.

        Raises:
            TigerFlowError: If command fails
        """
        command = f"{self._tigerflow_bin} tasks list --json"

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
            task: Task name (e.g., "transcribe")

        Returns:
            Task info dict with name, description, params, etc.

        Raises:
            TigerFlowError: If command fails or task not found
        """
        command = f"{self._tigerflow_bin} tasks info {task} --json"

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
