import os
from pathlib import Path
from enum import StrEnum, auto
from typing import Optional, Any
import subprocess
from copy import deepcopy


DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000
DEFAULT_STATIC_DIR = Path(__file__).parent.parent
DEFAULT_HOME_DIR = os.path.expanduser("~/.blackfish")
DEFAULT_DEBUG = 1  # True
DEFAULT_DEV_MODE = 1  # True


class ContainerProvider(StrEnum):
    Docker = auto()
    Apptainer = auto()


def get_container_provider() -> Optional[ContainerProvider]:
    """Determine which container platform to use: Docker (preferred) or Apptainer.

    Raises an exception if neither container platform is available.
    """
    try:
        _ = subprocess.run(["which", "docker"], check=True, capture_output=True)
        return ContainerProvider.Docker
    except subprocess.CalledProcessError:
        try:
            _ = subprocess.run(["which", "apptainer"], check=True, capture_output=True)
            return ContainerProvider.Apptainer
        except subprocess.CalledProcessError:
            print(
                "No supported container platforms available. Please install one of:"
                " docker, apptainer."
            )
            return None


class BlackfishConfig:
    """Blackfish app configuration.

    Most values are pulled from the local environment or a default if no environment variable is set.

    These values are passed to the Blackfish application on start up and used by the Blackfish CLI.
    Therefore, it's possible for the CLI config and app config to be out of sync.
    """

    def __init__(self) -> None:
        self.HOST = os.getenv("BLACKFISH_HOST", DEFAULT_HOST)
        self.PORT = int(os.getenv("BLACKFISH_PORT", DEFAULT_PORT))
        self.STATIC_DIR = Path(os.getenv("BLACKFISH_STATIC_DIR", DEFAULT_STATIC_DIR))
        self.HOME_DIR = os.getenv("BLACKFISH_HOME_DIR", DEFAULT_HOME_DIR)
        self.DEBUG = bool(int(os.getenv("BLACKFISH_DEBUG", DEFAULT_DEBUG)))
        self.DEV_MODE = bool(int(os.getenv("BLACKFISH_DEV_MODE", DEFAULT_DEBUG)))
        self.CONTAINER_PROVIDER = os.getenv(
            "BLACKFISH_CONTAINER_PROVIER", get_container_provider()
        )

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        inner = ", ".join([f"{k}: {v}" for k, v in self.__dict__.items()])
        return f"BlackfishConfig({inner})"

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.__dict__)


config = BlackfishConfig()
