import os
import configparser
from dataclasses import dataclass
from copy import deepcopy


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_HOME_DIR = os.path.expanduser("~/.blackfish")
DEFAULT_CACHE_DIR = os.path.expanduser("~/.blackfish/cache")
DEFAULT_DEBUG = True


class BlackfishProfile: ...


@dataclass
class SlurmRemote(BlackfishProfile):
    name: str
    host: str
    user: str
    home_dir: str
    cache_dir: str


class BlackfishConfig:
    """Blackfish app configuration.

    Create a configuration object based on a provided profile. Environment variables
    take precedence over profile values and default values; profile values are
    preferred over defaults.

    # Arguments
    - profile: str. Leave empty to generate baseline config variables.
    """

    def __init__(self):
        self.BLACKFISH_HOST = os.getenv("BLACKFISH_HOST", DEFAULT_HOST)
        self.BLACKFISH_PORT = os.getenv("BLACKFISH_PORT", DEFAULT_PORT)
        self.BLACKFISH_HOME_DIR = os.getenv("BLACKFISH_HOME", DEFAULT_HOME_DIR)
        self.BLACKFISH_CACHE_DIR = os.getenv("BLACKFISH_CACHE", DEFAULT_CACHE_DIR)
        self.BLACKFISH_DEBUG = os.getenv("BLACKFISH_DEBUG", DEFAULT_DEBUG)
        self.BLACKFISH_PROFILES = {}

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
