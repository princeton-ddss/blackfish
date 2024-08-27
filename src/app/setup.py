import os
import configparser
import subprocess
from yaspin import yaspin
from log_symbols.symbols import LogSymbols

import app
from app.logger import logger


def create_local_home_dir(home_dir: str) -> None:
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
                spinner.text = ""
                spinner.ok(f"{LogSymbols.SUCCESS.value} Set up default Blackfish home directory {home_dir}!")
            except OSError as e:
                spinner.text = ""
                spinner.fail(
                    f"{LogSymbols.ERROR.value} Failed to set up Blackfish home directory: {e}."
                )
                raise Exception
        else:
            spinner.text = ""
            spinner.ok(
                f"{LogSymbols.SUCCESS.value} Blackfish home directory already exists."
            )


def create_remote_home_dir(remote_type, host, user, home_dir) -> None:
    """Attempt to construct root directory to store core application data *remotely* and
    raise an exception if creation fails and the directory does not already exist.

    This method should called run when a new remote profile is created.
    """
    if remote_type == "slurm":
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
                spinner.text = ""
                spinner.fail(
                    f"{LogSymbols.ERROR.value} Failed to set up Blackfish remote home:"
                    f" {e}."
                )
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
                    spinner.text = ""
                    spinner.ok(f"{LogSymbols.SUCCESS.value} Done!")
                except Exception as e:
                    spinner.text = ""
                    spinner.fail(
                        f"{LogSymbols.ERROR.value} Failed to set up Blackfish remote:"
                        f" {e}."
                    )
            else:
                spinner.text = ""
                spinner.ok(
                    f"{LogSymbols.SUCCESS.value} Blackfish remote home directory"
                    " already exists."
                )
    else:
        raise NotImplementedError


def check_local_cache_exists(cache_dir):
    """Check that the local cache directory exists and raise and exception if not."""
    if os.path.exists(cache_dir):
        print(f"{LogSymbols.SUCCESS.value} Blackfish cache directory already exists.")
        return True
    else:
        print(f"{LogSymbols.ERROR.value} Unable to find local cache dir {cache_dir}.")
        raise Exception


def check_remote_cache_exists(remote_type, host, user, cache_dir):
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
            spinner.text = ""
            if remote_exists == "1":
                spinner.ok(
                    f"{LogSymbols.SUCCESS.value} Blackfish remote cache directory"
                    " exists."
                )
            else:
                spinner.fail(
                    f"{LogSymbols.ERROR.value} Unable to find remote cache dir"
                    f" {cache_dir}."
                )
                raise Exception
        except Exception as e:
            spinner.text = ""
            spinner.fail(
                f"{LogSymbols.ERROR.value} Failed to set up Blackfish remote home: {e}."
            )
            raise Exception


def migrate_db() -> None:
    logger.info("running database migration")
    _ = subprocess.check_output(
        [
            "litestar",
            "--app-dir",
            os.path.abspath(os.path.join(app.__file__, "..", "..")),
            "database",
            "upgrade",
            "--no-prompt",
        ]
    )
