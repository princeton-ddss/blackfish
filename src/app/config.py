import os
import configparser
from copy import deepcopy


DEFAULT_HOST        = '127.0.0.1'
DEFAULT_PORT        = 8000
DEFAULT_HOME_DIR    = os.path.expanduser("~/.blackfish")
DEFAULT_CACHE_DIR   = os.path.expanduser("~/.blackfish/cache")
DEFAULT_DEBUG       = True


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
        

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        inner = ", ".join([f"{k}: {v}" for k, v in self.__dict__.items()])
        return f"BlackfishConfig({inner})"
    
    def as_dict(self) -> dict:
        return deepcopy(self.__dict__)


class BlackfishProfileStore:
    def __init__(self, loc):
        self.config = configparser.ConfigParser()
        self.config.read(loc)


config = BlackfishConfig()
profiles = configparser.ConfigParser()
profiles.read(os.path.join(config.BLACKFISH_HOME_DIR, "config"))
