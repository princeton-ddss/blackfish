from __future__ import annotations

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
    type: str = "slurm"

    def is_local(self) -> bool:
        return self.host == "localhost"

    def __post_init__(self) -> None:
        if self.name is None:
            raise ValueError("Field 'name' is required.")
        if self.host is None:
            raise ValueError("Field 'host' is required.")
        if self.user is None:
            raise ValueError("Field 'user' is required.")
        if self.home_dir is None:
            raise ValueError("Field 'home_dir' is required.")
        if self.cache_dir is None:
            raise ValueError("Field 'cache_dir' is required.")


@dataclass
class LocalProfile:
    name: str
    home_dir: str
    cache_dir: str
    type: str = "local"

    def is_local(self) -> bool:
        return True

    def __post_init__(self) -> None:
        if self.name is None:
            raise ValueError("Field 'name' is required.")
        if self.home_dir is None:
            raise ValueError("Field 'home_dir' is required.")
        if self.cache_dir is None:
            raise ValueError("Field 'cache_dir' is required.")


BlackfishProfile = Union[SlurmProfile, LocalProfile]


class ProfileTypeException(Exception):
    def __init__(self, type: str) -> None:
        super().__init__(f"Profile type {type} is not supported.")


def deserialize_profiles(home_dir: str) -> list[BlackfishProfile]:
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


def deserialize_profile(home_dir: str, name: str) -> BlackfishProfile | None:
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
