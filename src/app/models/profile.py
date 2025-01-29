from dataclasses import dataclass
from typing import Union
from configparser import ConfigParser
import os


@dataclass
class SlurmProfile:
    name: str
    host: str
    user: str
    home_dir: str
    cache_dir: str

    def is_local(self) -> bool:
        return self.host == "localhost"


@dataclass
class LocalProfile:
    name: str
    home_dir: str
    cache_dir: str

    def is_local(self) -> bool:
        return True


BlackfishProfile = Union[SlurmProfile, LocalProfile]


class ProfileTypeException(Exception):
    def __init__(self, type: str) -> None:
        super().__init__(f"Profile type {type} is not supported.")


def serialize_profiles(home_dir: str) -> list[BlackfishProfile]:
    """Parse profiles from profile.cfg."""

    profiles_path = os.path.join(home_dir, "profiles.cfg")
    if not os.path.isfile(profiles_path):
        raise FileNotFoundError()

    parser = ConfigParser()
    parser.read(profiles_path)

    profiles: list[BlackfishProfile] = []
    for section in parser.sections():
        profile = {k: v for k, v in parser[section].items()}
        if profile["type"] == "slurm":
            profiles.append(
                SlurmProfile(
                    name=section,
                    host=profile["host"],
                    user=profile["user"],
                    home_dir=profile["home_dir"],
                    cache_dir=profile["cache_dir"],
                )
            )
        elif profile["type"] == "local":
            profiles.append(
                LocalProfile(
                    name=section,
                    home_dir=profile["home_dir"],
                    cache_dir=profile["cache_dir"],
                )
            )
        else:
            pass

    return profiles


def serialize_profile(home_dir: str, name: str) -> BlackfishProfile | None:
    """Parse a profile from profile.cfg."""

    profiles_path = os.path.join(home_dir, "profiles.cfg")
    if not os.path.isfile(profiles_path):
        raise FileNotFoundError()

    parser = ConfigParser()
    parser.read(profiles_path)

    for section in parser.sections():
        if section == name:
            profile = {k: v for k, v in parser[section].items()}
            if profile["type"] == "slurm":
                return SlurmProfile(
                    name=section,
                    host=profile["host"],
                    user=profile["user"],
                    home_dir=profile["home_dir"],
                    cache_dir=profile["cache_dir"],
                )
            elif profile["type"] == "local":
                return LocalProfile(
                    name=section,
                    home_dir=profile["home_dir"],
                    cache_dir=profile["cache_dir"],
                )
            else:
                raise ProfileTypeException(profile["type"])

    return None
