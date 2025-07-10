import os
from pathlib import Path
from enum import StrEnum, auto
from typing import Optional, Any
import subprocess
from base64 import b64encode
from copy import deepcopy


DEFAULT_BASE_PATH = ""
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000
DEFAULT_STATIC_DIR = Path(__file__).parent.parent
DEFAULT_HOME_DIR = os.path.expanduser("~/.blackfish")
DEFAULT_DEBUG = True


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

    def __init__(
        self,
        base_path: str = DEFAULT_BASE_PATH,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        static_dir: Path = DEFAULT_STATIC_DIR,
        home_dir: str = DEFAULT_HOME_DIR,
        debug: bool = DEFAULT_DEBUG,
        auth_token: Optional[str] = None,
        container_provider: Optional[ContainerProvider] = None,
    ) -> None:
        self.BASE_PATH = os.getenv("BLACKFISH_BASE_PATH", base_path)
        self.HOST = os.getenv("BLACKFISH_HOST", host)
        self.PORT = int(os.getenv("BLACKFISH_PORT", port))
        self.STATIC_DIR = Path(os.getenv("BLACKFISH_STATIC_DIR", static_dir))
        self.HOME_DIR = os.getenv("BLACKFISH_HOME_DIR", home_dir)
        self.DEBUG = bool(int(os.getenv("BLACKFISH_DEBUG", debug)))
        if self.DEBUG:
            self.AUTH_TOKEN = None
        elif auth_token is None:
            self.AUTH_TOKEN = os.getenv(
                "BLACKFISH_AUTH_TOKEN", b64encode(os.urandom(32)).decode("utf-8")
            )
        else:
            self.AUTH_TOKEN = auth_token
        if container_provider is None:
            self.CONTAINER_PROVIDER = os.getenv(
                "BLACKFISH_CONTAINER_PROVIDER", get_container_provider()
            )
        else:
            self.CONTAINER_PROVIDER = container_provider

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        inner = ", ".join([f"{k}: {v}" for k, v in self.__dict__.items()])
        return f"BlackfishConfig({inner})"

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.__dict__)


config = BlackfishConfig()
