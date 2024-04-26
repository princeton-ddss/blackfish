import os
import configparser


class BlackfishConfig:
    """Blackfish app configuration.

    # Arguments
    - profile: str. Set `profile="base"` to generate init config variables and
        `profile=None` to populate all other args. Provide any other value to pull
        args from a config file.
    """

    def __init__(self, profile="default", user=None, host=None, cache=None):
        if profile == "base":
            self.BLACKFISH_HOME = os.getenv(
                "BLACKFISH_HOME", os.path.expanduser("~/.blackfish")
            )
            self.BLACKFISH_ENV = os.getenv(
                "BLACKFISH_ENV", "local"
            )  # "local", "head" or "compute"
            self.BLACKFISH_DEBUG = os.getenv("BLACKFISH_DEBUG", True)
        elif profile is None:
            self.BLACKFISH_HOME = os.getenv(
                "BLACKFISH_HOME", os.path.expanduser("~/.blackfish")
            )
            self.BLACKFISH_USER = user
            self.BLACKFISH_HOST = host
            self.BLACKFISH_CACHE = cache
            self.BLACKFISH_REMOTE = os.getenv(
                "BLACKFISH_REMOTE", f"/home/{self.BLACKFISH_USER}/.blackfish"
            )
            self.BLACKFISH_ENV = os.getenv(
                "BLACKFISH_ENV", "local"
            )  # "local", "head" or "compute"
            self.BLACKFISH_DEBUG = os.getenv("BLACKFISH_DEBUG", True)
            self.APPTAINER_CACHE = f"/scratch/gpfs/{self.BLACKFISH_USER}"
            self.APPTAINER_TMPDIR = "/tmp"
        else:
            self.BLACKFISH_HOME = os.getenv(
                "BLACKFISH_HOME", os.path.expanduser("~/.blackfish")
            )

            config = configparser.ConfigParser()
            config.read(f"{self.BLACKFISH_HOME}/config")

            self.BLACKFISH_DEBUG = os.getenv("BLACKFISH_DEBUG", True)
            self.BLACKFISH_ENV = os.getenv(
                "BLACKFISH_ENV", "local"
            )  # "local", "head" or "compute"
            self.APPTAINER_TMPDIR = "/tmp"
            if profile in config:
                self.BLACKFISH_USER = os.getenv(
                    "BLACKFISH_USER", config[profile]["user"]
                )
                self.BLACKFISH_HOST = os.getenv(
                    "BLACKFISH_HOST", config[profile]["host"]
                )
                self.BLACKFISH_CACHE = os.getenv(
                    "BLACKFISH_CACHE", config[profile]["cache"]
                )  # TODO - Make default /scratch/gpfs/BLACKFISH.
                self.BLACKFISH_REMOTE = os.getenv(
                    "BLACKFISH_REMOTE", f"/home/{self.BLACKFISH_USER}/.blackfish"
                )
                self.APPTAINER_CACHE = f"/scratch/gpfs/{self.BLACKFISH_USER}"
            else:
                self.BLACKFISH_USER = None
                self.BLACKFISH_HOST = None
                self.BLACKFISH_CACHE = None
                self.BLACKFISH_REMOTE = None
                self.APPTAINER_CACHE = None

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        inner = ", ".join([f"{k}: {v}" for k, v in self.__dict__.items()])
        return f"BlackfishConfig({inner})"


base_config = BlackfishConfig(profile="base")
default_config = BlackfishConfig(profile="default")
