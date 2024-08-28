import os
import configparser
import subprocess
from dataclasses import dataclass
from copy import deepcopy


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_HOME_DIR = os.path.expanduser("~/.blackfish")
DEFAULT_DEBUG = True


def get_container_provider():
    """Determine which container platform to use: Docker (preferred) or Apptainer.

    Raises an exception if neither container platform is available.
    """
    try:
        _ = subprocess.run(["which", "docker"], check=True, capture_output=True)
        return "docker"
    except subprocess.CalledProcessError:
        try:
            _ = subprocess.run(["which", "apptainer"], check=True, capture_output=True)
            return "apptainer"
        except subprocess.CalledProcessError:
            raise Exception(
                "No supported container platforms available. Please install one of:"
                " docker, apptainer."
            )


class BlackfishProfile:
    ...


@dataclass
class SlurmRemote(BlackfishProfile):
    name: str
    host: str
    user: str
    home_dir: str
    cache_dir: str


@dataclass
class LocalProfile(BlackfishProfile):
    name: str
    home_dir: str
    cache_dir: str


class BlackfishConfig:
    """Blackfish app configuration.

    Most values are pulled from local environment or a default if no environment
    variable is set.

    These values are passed to the Blackfish application on start up and used by
    the Blackfish CLI. Therefore, it's possible for the CLI config and app config
    to get out of sync.
    """

    def __init__(self):
        self.BLACKFISH_HOST = os.getenv("BLACKFISH_HOST", DEFAULT_HOST)
        self.BLACKFISH_PORT = os.getenv("BLACKFISH_PORT", DEFAULT_PORT)
        self.BLACKFISH_HOME_DIR = os.getenv("BLACKFISH_HOME_DIR", DEFAULT_HOME_DIR)
        self.BLACKFISH_DEBUG = os.getenv("BLACKFISH_DEBUG", DEFAULT_DEBUG)
        self.BLACKFISH_PROFILES = {}
        self.BLACKFISH_CONTAINER_PROVIDER = os.getenv(
            "BLACKFISH_CONTAINER_PROVIER", get_container_provider()
        )

        parser = configparser.ConfigParser()
        parser.read(os.path.join(self.BLACKFISH_HOME_DIR, "profiles"))
        for section in parser.sections():
            profile = {k: v for k, v in parser[section].items()}
            if profile["type"] == "slurm":
                self.BLACKFISH_PROFILES[section] = SlurmRemote(
                    name=section,
                    host=profile["host"],
                    user=profile["user"],
                    home_dir=profile["home_dir"],
                    cache_dir=profile["cache_dir"],
                )
            elif profile["type"] == "local":
                self.BLACKFISH_PROFILES[section] = LocalProfile(
                    name=section,
                    home_dir=profile["home_dir"],
                    cache_dir=profile["cache_dir"],
                )
            else:
                pass

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        inner = ", ".join([f"{k}: {v}" for k, v in self.__dict__.items()])
        return f"BlackfishConfig({inner})"

    def as_dict(self) -> dict:
        return deepcopy(self.__dict__)


config = BlackfishConfig()
