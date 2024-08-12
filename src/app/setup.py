import os
import configparser
import subprocess
from yaspin import yaspin
from log_symbols.symbols import LogSymbols

import app
from app.logger import logger


def create_local_home_dir(home_dir: str) -> None:
    with yaspin(text=f"Setting up home directory {home_dir}") as spinner:
        if not os.path.isdir(home_dir):
            try:
                os.mkdir(home_dir)
                os.mkdir(os.path.join(home_dir, "models"))
                os.mkdir(os.path.join(home_dir, "images"))
                spinner.text = ""
                spinner.ok(f"{LogSymbols.SUCCESS.value} Done!")
            except OSError as e:
                spinner.text = ""
                spinner.fail(
                    f"{LogSymbols.ERROR.value} Failed to setup Blackfish home: {e}."
                )
        else:
            spinner.text = ""
            spinner.ok(
                f"{LogSymbols.SUCCESS.value} Blackfish home directory already exists."
            )


def create_remote_home_dir(remote_type, host, user, home_dir) -> None:
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
                    f"{LogSymbols.ERROR.value} Failed to setup Blackfish remote home:"
                    f" {e}."
                )
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
                        f"{LogSymbols.ERROR.value} Failed to setup Blackfish remote:"
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


def check_remote_cache_exists(remote_type, host, user, cache_dir):
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
        except Exception as e:
            spinner.text = ""
            spinner.fail(
                f"{LogSymbols.ERROR.value} Failed to setup Blackfish remote home: {e}."
            )


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


def create_or_modify_profile(home_dir: str, modify: bool = False) -> None:
    """Create a new profile."""

    profiles_exists = os.path.isfile(os.path.join(home_dir, "profiles"))

    profiles = configparser.ConfigParser()
    profiles.read(f"{home_dir}/profiles")

    print("  Create or modify an existing profile:")
    name = input("> name [default]: ")
    name = "default" if name == "" else name

    if name in profiles:
        profile = profiles[name]
        profile_type = profile["type"]
        if profile_type == "slurm":
            host = input(f"> host [{profile['host']}]: ")
            host = profile["host"] if host == "" else host
            user = input(f"> user [{profile['user']}]: ")
            user = profile["user"] if user == "" else user
            remote_dir = input(f"> home [{profile['home_dir']}]: ")
            remote_dir = profile["home_dir"] if remote_dir == "" else remote_dir
            cache_dir = input(f"> cache [{profile['cache_dir']}]: ")
            cache_dir = profile["cache_dir"] if cache_dir == "" else cache_dir
        elif profile_type == "local":
            user = input(f"> user [{profile['user']}]: ")
            user = profile["user"] if user == "" else user
            remote_dir = input(f"> home [{profile['home_dir']}]: ")
            remote_dir = profile["home_dir"] if remote_dir == "" else remote_dir
            cache_dir = input(f"> cache [{profile['cache_dir']}]: ")
            cache_dir = profile["cache_dir"] if cache_dir == "" else cache_dir
        else:
            raise NotImplementedError
    else:
        profile_type = input("> type [slurm]: ")
        profile_type = "slurm" if profile_type == "" else profile_type
        if profile_type == "slurm":
            host = input("> host: ")
            while host == "":
                print("Host is required.")
                host = input("> host: ")
            user = input("> user: ")
            while user == "":
                print("User is required.")
                user = input("> user: ")
            remote_dir = input(f"> home [/home/{user}/.blackfish]: ")
            remote_dir = f"/home/{user}/.blackfish" if remote_dir == "" else remote_dir
            cache_dir = input(f"> cache [/scratch/gpfs/{user}/.cache]: ")
            cache_dir = f"/scratch/gpfs/{user}/.cache" if cache_dir == "" else cache_dir
            create_remote_home_dir("slurm", host=host, user=user, home_dir=remote_dir)
            check_remote_cache_exists(
                "slurm", host=host, user=user, cache_dir=cache_dir
            )
        elif profile_type == "local":
            user = input("> user: ")
            while user == "":
                print("User is required.")
                user = input("> user: ")
            remote_dir = input(f"> home [/home/{user}/.blackfish]: ")
            remote_dir = f"/home/{user}/.blackfish" if remote_dir == "" else remote_dir
            cache_dir = input(f"> cache [/scratch/gpfs/{user}/.cache]: ")
            cache_dir = f"/scratch/gpfs/{user}/.cache" if cache_dir == "" else cache_dir
        else:
            raise NotImplementedError

    if profile_type == "slurm":
        profiles[name] = {
            "type": profile_type,
            "user": user,
            "host": host,
            "home_dir": remote_dir,
            "cache_dir": cache_dir,
        }
    elif profile_type == "local":
        profiles[name] = {
            "type": profile_type,
            "user": user,
            "home_dir": remote_dir,
            "cache_dir": cache_dir,
        }
    else:
        raise NotImplementedError

    with open(os.path.join(home_dir, "profiles"), "w") as f:
        profiles.write(f)
        if not profiles_exists:
            print(f"{LogSymbols.SUCCESS.value} Created {home_dir}/profiles.")
        else:
            print(f"{LogSymbols.SUCCESS.value} Updated {home_dir}/profiles.")
