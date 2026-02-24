from __future__ import annotations

import configparser
import os
import subprocess
from collections.abc import Callable
from typing import TYPE_CHECKING

from yaspin import yaspin
from log_symbols.symbols import LogSymbols

import blackfish.server as server
from blackfish.server.logger import logger

if TYPE_CHECKING:
    from blackfish.server.jobs.client import CommandRunner


class ProfileSetupError(Exception):
    """Error raised when profile setup fails."""

    def __init__(self, message: str, details: str | None = None):
        self.message = message
        self.details = details
        super().__init__(self.user_message())

    def user_message(self) -> str:
        if self.details:
            return f"{self.message} ({self.details})"
        return self.message


class ProfileManager:
    """Manages profile setup and configuration.

    Handles directory creation, cache validation, and config file operations.
    Uses a CommandRunner to execute commands either locally or via SSH.
    """

    def __init__(
        self,
        runner: "CommandRunner",
        home_dir: str,
        cache_dir: str,
        config_path: str | None = None,
        on_progress: Callable[[str], None] | None = None,
    ):
        """Initialize ProfileManager.

        Args:
            runner: CommandRunner for executing commands (SSHRunner or LocalRunner)
            home_dir: Home directory for the profile
            cache_dir: Cache directory for the profile
            config_path: Path to profiles.cfg (defaults to ~/.blackfish/profiles.cfg)
            on_progress: Optional callback for progress updates. Defaults to logger.info.
        """
        self.runner = runner
        self.home_dir = home_dir
        self.cache_dir = cache_dir
        self.config_path = config_path
        self._on_progress = on_progress or logger.info

    @property
    def host(self) -> str:
        return self.runner.host

    async def create_directories(self) -> None:
        """Create home directory structure (home_dir/models, home_dir/images).

        Raises:
            ProfileSetupError: If directory creation fails
        """
        self._on_progress(f"Creating directories on {self.host}...")

        try:
            returncode, _, stderr = await self.runner.run(f"mkdir -p {self.home_dir}")
            if returncode != 0:
                raise ProfileSetupError(
                    "Failed to create home directory",
                    stderr.decode("utf-8").strip() if stderr else None,
                )

            returncode, _, stderr = await self.runner.run(
                f"mkdir -p {self.home_dir}/models {self.home_dir}/images"
            )
            if returncode != 0:
                raise ProfileSetupError(
                    "Failed to create subdirectories",
                    stderr.decode("utf-8").strip() if stderr else None,
                )
        except ProfileSetupError:
            raise
        except Exception as e:
            raise ProfileSetupError("Failed to create directories", str(e))

    async def check_cache(self) -> None:
        """Verify cache directory exists.

        Raises:
            ProfileSetupError: If cache directory does not exist
        """
        self._on_progress(f"Checking cache directory on {self.host}...")

        try:
            returncode, stdout, _ = await self.runner.run(
                f'test -d {self.cache_dir} && echo "exists"'
            )
            if returncode != 0 or b"exists" not in stdout:
                raise ProfileSetupError(
                    f"Cache directory does not exist: {self.cache_dir}"
                )
        except ProfileSetupError:
            raise
        except Exception as e:
            raise ProfileSetupError("Failed to check cache directory", str(e))

    @staticmethod
    def get_profiles_config(config_path: str) -> configparser.ConfigParser:
        """Load the profiles configuration file.

        Args:
            config_path: Path to profiles.cfg

        Returns:
            ConfigParser with loaded profiles
        """
        config = configparser.ConfigParser()
        if os.path.isfile(config_path):
            config.read(config_path)
        return config

    @staticmethod
    def save_profiles_config(
        config: configparser.ConfigParser, config_path: str
    ) -> None:
        """Save the profiles configuration file.

        Args:
            config: ConfigParser to save
            config_path: Path to profiles.cfg
        """
        with open(config_path, "w") as f:
            config.write(f)


def create_local_home_dir(home_dir: str | os.PathLike[str]) -> None:
    """Attempt to construct root directory to store core application data and raise an
    exception if creation fails and the directory does not already exist.

    This method should be called when the application is initialized or a local profile
    is created.
    """
    with yaspin(text=f"Setting up home directory {home_dir}") as spinner:
        if not os.path.isdir(home_dir):
            try:
                os.mkdir(home_dir)
                os.mkdir(os.path.join(home_dir, "models"))
                os.mkdir(os.path.join(home_dir, "images"))
                spinner.text = f"Set up default Blackfish home directory {home_dir}"
                spinner.ok(f"{LogSymbols.SUCCESS.value}")
            except OSError as e:
                spinner.text = f"Failed to set up Blackfish home directory: {e}"
                spinner.fail(f"{LogSymbols.ERROR.value}")
                raise Exception
        else:
            spinner.text = "Blackfish home directory already exists."
            spinner.ok(f"{LogSymbols.SUCCESS.value}")


def create_remote_home_dir(
    host: str, user: str, home_dir: str | os.PathLike[str]
) -> None:
    """Attempt to construct root directory to store core application data *remotely* and
    raise an exception if creation fails and the directory does not already exist.

    This method should called run when a new remote profile is created.
    """

    with yaspin(
        text=f"Setting up remote home directory for user {user} at {host}"
    ) as spinner:
        try:
            res = subprocess.check_output(
                [
                    "ssh",
                    f"{user}@{host}",
                    f"""if [ -d {home_dir} ]; then echo 1; fi""",
                ]
            )
            remote_exists = res.decode("utf-8").strip()
        except Exception as e:
            spinner.text = f"Failed to set up Blackfish remote home: {e}."
            spinner.fail(f"{LogSymbols.ERROR.value}")
            raise Exception
        if not remote_exists == "1":
            try:
                _ = subprocess.check_output(
                    ["ssh", f"{user}@{host}", "mkdir", home_dir]
                )
                _ = subprocess.check_output(
                    ["ssh", f"{user}@{host}", "mkdir", f"{home_dir}/models"]
                )
                _ = subprocess.check_output(
                    ["ssh", f"{user}@{host}", "mkdir", f"{home_dir}/images"]
                )
                spinner.text = "Done."
                spinner.ok(f"{LogSymbols.SUCCESS.value}")
            except Exception as e:
                spinner.text = f"Failed to set up Blackfish remote: {e}."
                spinner.fail(f"{LogSymbols.ERROR.value}")
        else:
            spinner.text = "Blackfish remote home directory already exists."
            spinner.ok(f"{LogSymbols.SUCCESS.value}")


def check_local_cache_exists(cache_dir: str | os.PathLike[str]) -> None:
    """Check that the local cache directory exists and raise and exception if not."""
    if os.path.exists(cache_dir):
        print(f"{LogSymbols.SUCCESS.value} Local cache directory already exists.")
    else:
        print(
            f"{LogSymbols.ERROR.value} Unable to find local cache directory {cache_dir}."
        )
        raise Exception


def check_remote_cache_exists(
    host: str, user: str, cache_dir: str | os.PathLike[str]
) -> None:
    """Check that the remote cache directory exists and raise and exception if not."""
    with yaspin(text="Looking for remote cache") as spinner:
        try:
            res = subprocess.check_output(
                [
                    "ssh",
                    f"{user}@{host}",
                    f"""if [ -d {cache_dir} ]; then echo 1; fi""",
                ]
            )
            remote_exists = res.decode("utf-8").strip()
            if remote_exists == "1":
                spinner.text = "Remote cache already directory exists."
                spinner.ok(f"{LogSymbols.SUCCESS.value}")
            else:
                spinner.text = f"Unable to find remote cache directory {cache_dir}."
                spinner.fail(f"{LogSymbols.ERROR.value}")
                raise Exception
        except Exception as e:
            spinner.text = f"Failed to set up Blackfish remote home: {e}."
            spinner.fail(f"{LogSymbols.ERROR.value}")
            raise Exception


def migrate_db() -> None:
    logger.info("running database migration")
    _ = subprocess.check_output(
        [
            "litestar",
            "--app-dir",
            os.path.abspath(os.path.join(server.__file__, "..", "..")),
            "database",
            "upgrade",
            "--no-prompt",
        ]
    )
