import os
import configparser
import subprocess

import app
from app.config import BlackfishConfig
from app.logger import logger


# def setup():
#     """Setup up the blackfish CLI. Called by CLI command `blackfish setup`."""
#     make_local_dir()
#     migrate_db()
#     create_or_modify_config()


def make_local_dir(home_dir: str) -> None:
    if not os.path.isdir(home_dir):
        logger.info(f"setting up blackfish home directory {home_dir}")
        try:
            os.mkdir(home_dir)
            os.mkdir(os.path.join(home_dir, "cache"))
        except OSError as e:
            logger.error("unable to make blackfish home directory: ", e)
    else:
        logger.info("blackfish home directory already exists. Skipping.")


def make_remote_dir(user, host, cache):
    """
    NOTE: setting up della also sets up della-gpu. On other systems these might
    require separate profiles.
    """

    config = BlackfishConfig(user=user, host=host, cache=cache)

    logger.debug(f"setting up new remote for user {user} at {host}.")
    try:
        res = subprocess.check_output(
            [
                "ssh",
                f"{user}@{host}",
                f"""if [ -d {config.BLACKFISH_REMOTE} ]; then echo 1; fi""",
            ]
        )
        remote_exists = int(res.decode("utf-8").strip())
    except Exception as e:
        logger.error(
            f"Failed to setup remote blackfish home for user {user} at"
            f" {host}:{config.BLACKFISH_REMOTE}."
        )
        raise e

    if not remote_exists:
        try:
            logger.debug(f"making blackfish home directory {config.BLACKFISH_HOME}")
            _ = subprocess.check_output(
                ["ssh", f"{user}@{host}", "mkdir", config.BLACKFISH_REMOTE]
            )

            logger.debug(
                "copying blackfish config to remote home directory"
                f" {config.BLACKFISH_REMOTE}"
            )
            _ = subprocess.check_output(
                [
                    "scp",
                    os.path.join(config.BLACKFISH_HOME, "config"),
                    f"{user}@{host}:{os.path.join(config.BLACKFISH_REMOTE, 'config')}",
                ]
            )
        except Exception as e:
            logger.error(
                f"Failed to setup remote blackfish home for user {user} at"
                f" {host}:{config.BLACKFISH_REMOTE}."
            )
            raise e
    else:
        logger.info("blackfish remote home directory already exists. Skipping.")


def migrate_db():
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


def create_or_modify_config(home_dir: str, modify=False) -> None:
    config_exists = os.path.isfile(os.path.join(home_dir, "config"))

    if modify or not config_exists:

        name = input("> name [default]: ")
        name = "default" if name == "" else name

        if config_exists:
            config = configparser.ConfigParser()
            config.read(f"{home_dir}/config")
            if name in config:
                # Modifying an existing profile
                profile = config[name]
                profile_type = profile["type"]
            else:
                # Creating a new profile
                profile_type = input("> type [slurm]: ")
                profile_type = "slurm" if profile_type == "" else profile_type
        else:
            # Creating a config
            profile_type = input("> type [slurm]: ")
            profile_type = "slurm" if profile_type == "" else profile_type

        if profile_type == "slurm":
            if name in config:
                user = input(f"> user [{profile['user']}]: ")
                user = profile["user"] if user == "" else user
                host = input(f"> host [{profile['host']}]: ")
                host = profile["host"] if host == "" else host
                home_dir = input(f"> home [{profile['home_dir']}]: ")
                home_dir = profile["home_dir"] if home_dir == "" else home_dir
                cache_dir = input(f"> cache [{profile['cache_dir']}]: ")
                cache_dir = profile["cache_dir"] if cache_dir == "" else cache_dir
            else:
                user = input("> user: ")
                while user == "":
                    print("User is required.")
                    user = input("> user: ")
                host = input("> host [della.princeton.edu]: ")
                host = "della.princeton.edu" if host == "" else host
                home_dir = input(f"> home [/home/{user}/.blackfish]: ")
                home_dir = f"/home/{user}/.blackfish" if home_dir == "" else home_dir
                cache_dir = input(f"> cache [/scratch/gpfs/{user}]: ")
                cache_dir = f"/scratch/gpfs/{user}" if cache_dir == "" else cache_dir

                config[name] = {
                    "type": profile_type,
                    "user": user,
                    "host": host,
                    "home_dir": home_dir,
                    "cache_dir": cache_dir,
                }
        else:
            raise NotImplementedError

        with open(os.path.join(home_dir, "config"), "w") as f:
            config.write(f)
    else:
        logger.info("blackfish config already exists. Skipping.")
    print("\n🎉 All done--let's fish! 🎉")
