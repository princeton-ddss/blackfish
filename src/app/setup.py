import os
import configparser
import subprocess

import app
from app.logger import logger


def create_local_home_dir(home_dir: str) -> None:
    if not os.path.isdir(home_dir):
        logger.info(f"setting up blackfish home directory {home_dir}")
        try:
            os.mkdir(home_dir)
            os.mkdir(os.path.join(home_dir, ".cache"))
        except OSError as e:
            logger.error("unable to setup blackfish home directory: ", e)
    else:
        logger.info("blackfish home directory already exists. Skipping.")


def create_remote_home_dir(
    remote_type, host, user, home_dir, cache_dir=".cache"
) -> None:
    if remote_type == "slurm":
        logger.debug(f"setting up new remote for user {user} at {host}.")
        try:
            res = subprocess.check_output(
                [
                    "ssh",
                    f"{user}@{host}",
                    f"""if [ -d {home_dir} ]; then echo 1; fi""",
                ]
            )
            remote_exists = int(res.decode("utf-8").strip())
        except Exception as e:
            logger.error(
                f"Failed to setup remote blackfish home for user {user} at"
                f" {host}:{home_dir}."
            )
            raise e

        if not remote_exists:
            try:
                logger.debug(f"making blackfish home directory {home_dir}")
                _ = subprocess.check_output(
                    ["ssh", f"{user}@{host}", "mkdir", home_dir]
                )
            except Exception as e:
                logger.error(
                    f"Failed to setup remote blackfish home for user {user} at"
                    f" {host}:{home_dir}."
                )
                raise e
            try:
                logger.debug(f"making blackfish cache directory {home_dir}/{cache_dir}")
                _ = subprocess.check_output(
                    ["ssh", f"{user}@{host}", "mkdir", f"{home_dir}/{cache_dir}"]
                )
            except Exception as e:
                logger.error(
                    f"Failed to setup remote blackfish cache for user {user} at"
                    f" {host}:{home_dir}/{cache_dir}."
                )
                raise e
        else:
            logger.info("blackfish remote home directory already exists. Skipping.")
    else:
        raise NotImplementedError


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
    profiles_exists = os.path.isfile(os.path.join(home_dir, "profiles"))

    if modify or not profiles_exists:

        name = input("> name [default]: ")
        name = "default" if name == "" else name

        if profiles_exists:
            profiles = configparser.ConfigParser()
            profiles.read(f"{home_dir}/profiles")
            if name in profiles:
                profile = profiles[name]
                profile_type = profile["type"]
            else:
                profile_type = input("> type [slurm]: ")
                profile_type = "slurm" if profile_type == "" else profile_type
        else:
            profile_type = input("> type [slurm]: ")
            profile_type = "slurm" if profile_type == "" else profile_type

        if profile_type == "slurm":
            if name in profiles:
                host = input(f"> host [{profile['host']}]: ")
                host = profile["host"] if host == "" else host
                user = input(f"> user [{profile['user']}]: ")
                user = profile["user"] if user == "" else user
                home_dir = input(f"> home [{profile['home_dir']}]: ")
                home_dir = profile["home_dir"] if home_dir == "" else home_dir
                cache_dir = input(f"> cache [{profile['cache_dir']}]: ")
                cache_dir = profile["cache_dir"] if cache_dir == "" else cache_dir
            else:
                host = input("> host: ")
                while host == "":
                    print("Host is required.")
                    host = input("> host: ")
                user = input("> user: ")
                while user == "":
                    print("User is required.")
                    user = input("> user: ")
                home_dir = input(f"> home [/home/{user}/.blackfish]: ")
                home_dir = f"/home/{user}/.blackfish" if home_dir == "" else home_dir
                cache_dir = input(f"> cache [/scratch/gpfs/{user}]: ")
                cache_dir = f"/scratch/gpfs/{user}" if cache_dir == "" else cache_dir

                profiles[name] = {
                    "type": profile_type,
                    "user": user,
                    "host": host,
                    "home_dir": home_dir,
                    "cache_dir": cache_dir,
                }
        else:
            raise NotImplementedError

        with open(os.path.join(home_dir, "proflies"), "w") as f:
            profiles.write(f)
    else:
        logger.info(
            "blackfish profiles already exists (set modify=True to modify profiles)."
        )
    print("\n🎉 All done--let's fish! 🎉")
