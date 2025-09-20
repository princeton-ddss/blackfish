from __future__ import annotations

from dataclasses import dataclass
from typing import Union, Optional
from configparser import ConfigParser
import os


@dataclass
class SlurmProfile:
    name: str
    host: str
    user: str
    home_dir: str
    cache_dir: str
    schema: str = "slurm"

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
    schema: str = "local"

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
    def __init__(self, schema: str) -> None:
        super().__init__(f"Profile type {schema} is not supported.")


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
        schema = profile.get("schema") or profile.get("type")
        if schema == "slurm":
            profiles.append(
                SlurmProfile(
                    name=section,
                    host=profile["host"],
                    user=profile["user"],
                    home_dir=profile["home_dir"],
                    cache_dir=profile["cache_dir"],
                )
            )
        elif schema == "local":
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
            schema = profile.get("schema") or profile.get("type")
            if schema == "slurm":
                return SlurmProfile(
                    name=section,
                    host=profile["host"],
                    user=profile["user"],
                    home_dir=profile["home_dir"],
                    cache_dir=profile["cache_dir"],
                )
            elif schema == "local":
                return LocalProfile(
                    name=section,
                    home_dir=profile["home_dir"],
                    cache_dir=profile["cache_dir"],
                )
            else:
                schema_value = profile.get("schema") or profile.get("type", "unknown")
                raise ProfileTypeException(schema_value)

    return None
