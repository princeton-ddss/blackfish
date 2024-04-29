import os
import configparser
from copy import deepcopy


DEFAULT_HOME = os.path.expanduser("~/.blackfish")
DEFAULT_CACHE = os.path.expanduser("~/.blackfish/cache")


class BlackfishConfig:
    """Blackfish app configuration.

    Create a configuration object based on a provided profile. Environment variables
    take precedence over profile values and default values; profile values are
    preferred over defaults.

    # Arguments
    - profile: str. Leave empty to generate baseline config variables.
    """

    def __init__(self, profile=None):
        if profile is None:
            self.BLACKFISH_USER = os.getenv("BLACKFISH_USER", None)
            self.BLACKFISH_HOST = os.getenv("BLACKFISH_HOST", None)
            self.BLACKFISH_HOME = os.getenv("BLACKFISH_HOME", DEFAULT_HOME)
            self.BLACKFISH_CACHE = os.getenv("BLACKFISH_CACHE", DEFAULT_CACHE)
            self.BLACKFISH_DEBUG = os.getenv("BLACKFISH_DEBUG", True)
        else:
            config = configparser.ConfigParser()
            config.read(os.path.expanduser("~/.blackfish/config"))
            if profile in config:
                self.BLACKFISH_USER = os.getenv(
                    "BLACKFISH_USER", config[profile].get("user", None)
                )
                self.BLACKFISH_HOST = os.getenv(
                    "BLACKFISH_HOST", config[profile].get("host", None)
                )
                self.BLACKFISH_HOME = os.getenv(
                    "BLACKFISH_HOME", config[profile].get("home", DEFAULT_HOME)
                )
                self.BLACKFISH_CACHE = os.getenv(
                    "BLACKFISH_CACHE", config[profile].get("cache", DEFAULT_CACHE)
                )
                self.BLACKFISH_DEBUG = os.getenv(
                    "BLACKFISH_DEBUG", config[profile].get("debug", True)
                )
            else:
                raise Exception(f"Profile {profile} does not exist. Available sections are: {config.sections()}")

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        inner = ", ".join([f"{k}: {v}" for k, v in self.__dict__.items()])
        return f"BlackfishConfig({inner})"
    
    def as_dict(self) -> dict:
        return deepcopy(self.__dict__)


base_config = BlackfishConfig()
default_config = BlackfishConfig(profile="default")
