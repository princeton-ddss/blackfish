from dataclasses import dataclass
from typing import Literal, Optional
from configparser import ConfigParser
import os

from app.logger import logger


@dataclass
class BlackfishProfile:
    """
    A Blackfish profile indicates how to launch services.

    Not all combinations for fields represent valid profile settings. The logic
    to validate profile fields must be provided by the user. For example, a
    profile that uses a remote host *should* specify a `host` and `user`, even
    though these are optional fields.
    """

    name: str
    provider: Literal["docker", "apptainer"]
    scheduler: Literal["slurm", None]
    host: Optional[str]
    user: Optional[str]
    home_dir: str
    cache_dir: str


class ProfileNotFoundException(Exception):
    def __init__(self, name):
        super().__init__(f"Profile {name} not found.")


class ProfileTypeException(Exception):
    def __init__(self, type):
        super().__init__(f"Profile type {type} is not supported.")


def write_profile(
    home_dir: str, profile: BlackfishProfile, modify: bool = False
) -> BlackfishProfile:
    """Add a profile to profiles.cfg."""

    profiles = import_profiles(home_dir)

    if modify:
        if profile.name not in profiles:
            raise Exception(f"Profile {profile.name} not found.")
    elif profile.name in profiles:
        raise Exception(
            f"Profile {profile.name} already exists. Set `modify=True` to modify an"
            " existing profile."
        )

    profiles[profile.name] = {
        "provider": profile.provider,
        "scheduler": profile.scheduler,
        "host": profile.host,
        "user": profile.user,
        "home_dir": profile.home_dir,
        "cache_dir": profile.cache_dir,
    }

    with open(os.path.join(home_dir, "profiles.cfg"), "w") as f:
        profiles.write(f)
        return profile


def serialize_profiles(home_dir: str) -> list[BlackfishProfile]:
    """Parse profiles from profile.cfg."""

    profiles_path = os.path.join(home_dir, "profiles.cfg")
    if not os.path.isfile(profiles_path):
        raise FileNotFoundError()

    parser = ConfigParser()
    parser.read(profiles_path)

    profiles = []
    for section in parser.sections():
        profile = BlackfishProfile(**{k: v for k, v in parser[section].items()})
        profiles.append(profile)

    return profiles


def serialize_profile(home_dir: str, name: str) -> BlackfishProfile:
    """Parse a profile from profile.cfg."""

    profiles_path = os.path.join(home_dir, "profiles.cfg")
    if not os.path.isfile(profiles_path):
        raise FileNotFoundError()

    parser = ConfigParser()
    parser.read(profiles_path)

    for section in parser.sections():
        if section == name:
            return BlackfishProfile(**{k: v for k, v in parser[section].items()})

    raise ProfileNotFoundException(name)


def import_profiles(home_dir: str) -> list[dict]:
    """Parse profiles from profile.cfg and return as dict."""

    profiles_path = os.path.join(home_dir, "profiles.cfg")
    if not os.path.isfile(profiles_path):
        raise FileNotFoundError()

    parser = ConfigParser()
    parser.read(profiles_path)

    profiles = []
    for section in parser.sections():
        profile = {k: v for k, v in parser[section].items()}
        profiles.append(profile)

    return profiles


def import_profile(home_dir: str, name: str) -> dict:
    """Parse profile from profile.cfg and return as dict."""

    profiles_path = os.path.join(home_dir, "profiles.cfg")
    if not os.path.isfile(profiles_path):
        raise FileNotFoundError()

    parser = ConfigParser()
    parser.read(profiles_path)

    for section in parser.sections():
        if section == name:
            return {k: v for k, v in parser[section].items()}

    return None


def modify_profile(home_dir: str, profile: BlackfishProfile) -> BlackfishProfile:
    """Update a profile in profiles.cfg. The provided profile's name should match an existing profile."""

    profiles = import_profiles(home_dir)

    if profile.name not in profiles:
        raise Exception(f"Profile {profile.name} not found.")

    write_profile(home_dir, profile)


def remove_profile(home_dir: str, name: str) -> None:
    """Delete a profile from profiles.cfg by name."""

    logger.info(f"Deleting profile {name}")

    profiles = import_profiles(home_dir)

    if name not in profiles:
        raise ProfileNotFoundException(name)

    del profiles[name]

    with open(os.path.join(home_dir, "profiles.cfg"), "w") as f:
        profiles.write(f)
