import os
import configparser
import subprocess

from app.config import BlackfishConfig, base_config
from app.logger import logger


def setup():
    """Setup up the blackfish CLI. Called by CLI command `blackfish setup`."""
    make_local_dir()
    migrate_db()
    create_or_modify_config()


def make_local_dir():
    if not os.path.isdir(base_config.BLACKFISH_HOME):
        logger.info(f"making blackfish home directory {base_config.BLACKFISH_HOME}")
        try:
            os.mkdir(base_config.BLACKFISH_HOME)
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
    # TODO: run database migrations
    # in command-line, this is just:
    # litestar database upgrade
    pass


def create_or_modify_config(modify=False):
    created = os.path.isfile(os.path.join(base_config.BLACKFISH_HOME, "config"))
    if not created or modify:
        if created:
            print("Create a new profile:")
        else:
            print("Modify a profile:")
        name = input("> name [default]: ")
        name = "default" if name == "" else name
        user = input("> user: ")
        host = input("> host [della.princeton.edu]: ")
        host = "della.princeton.edu" if host == "" else host
        cache = input(f"> cache [/scratch/gpfs/{user}]: ")
        cache = f"/scratch/gpfs/{user}" if cache == "" else cache

        if name == "base":
            raise Exception("Profile name 'base' is not allowed.")
        if user == "":
            raise Exception("User is required.")
        if host != "della.princeton.edu" or "della-gpu.princeton.edu":
            raise Exception("Host is unknown.")
        if cache == "":
            raise Exception("Cache is required.")

        config = configparser.ConfigParser()
        config.read(f"{base_config.BLACKFISH_HOME}/config")
        profile_exists = name in config

        config[name] = {
            "user": user,
            "host": host,
            "cache": cache,
        }
        with open(os.path.join(base_config.BLACKFISH_HOME, "config"), "w") as f:
            config.write(f)

        if not profile_exists:
            try:
                make_remote_dir(user, host, cache)
            except Exception as e:
                logger.error(e)
                logger.info("rolling back changes to blackfish config.")
                config = configparser.ConfigParser()
                # TODO: need to write a copy of original config!!
                with open(os.path.join(base_config.BLACKFISH_HOME, "config"), "w") as f:
                    config.write(f)

    else:
        logger.info("blackfish config already exists. Skipping.")
    print("\n🎉 All done--let's fish! 🎉")
