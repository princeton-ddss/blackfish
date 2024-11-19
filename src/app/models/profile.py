from dataclasses import dataclass
from configparser import ConfigParser
import os

from app.logger import logger


class BlackfishProfile:
    ...


@dataclass
class SlurmRemote(BlackfishProfile):
    name: str
    host: str
    user: str
    home_dir: str
    cache_dir: str


@dataclass
class LocalProfile(BlackfishProfile):
    name: str
    home_dir: str
    cache_dir: str


class ProfileNotFoundException(Exception):
    def __init__(self, name):
        super().__init__(f"Profile {name} not found.")


class ProfileTypeException(Exception):
    def __init__(self, type):
        super().__init__(f"Profile type {type} is not supported.")


def init_profile(home_dir: str, profile: BlackfishProfile) -> None:
    """Create resources required by profile."""
    # create home_dir
    # create cache_dir
    # raise exception if any of this fails


def write_profile(
    home_dir: str, profile: BlackfishProfile, modify: bool = False
) -> BlackfishProfile:
    """Add a profile to profiles.cfg."""

    profiles = import_profiles(home_dir)

    if modify:
        if profile.name not in profiles:
            raise Exception(f"Profile {profile.name} not found.")
    else:
        if profile.name in profiles:
            raise Exception(
                f"Profile {profile.name} already exists. Set `modify=True` to modify an"
                " existing profile."
            )

    if profile.type == "slurm":
        profiles[profile.name] = {
            "type": "slurm",
            "user": profile.user,
            "host": profile.host,
            "home_dir": profile.home_dir,
            "cache_dir": profile.cache_dir,
        }
    elif profile.type == "local":
        profiles[profile.name] = {
            "type": "local",
            "home_dir": profile.home_dir,
            "cache_dir": profile.cache_dir,
        }
    else:
        raise NotImplementedError("Profile type should be one of: slurm, local.")

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
        profile = {k: v for k, v in parser[section].items()}
        if profile["type"] == "slurm":
            profiles.append(
                SlurmRemote(
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


def serialize_profile(home_dir: str, name: str) -> BlackfishProfile:
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
                return SlurmRemote(
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

    raise ProfileNotFoundException(name)


def import_profiles(home_dir: str) -> list[dict]:
    """Parse profiles from profile.cfg."""

    profiles_path = os.path.join(home_dir, "profiles.cfg")
    if not os.path.isfile(profiles_path):
        raise FileNotFoundError()

    parser = ConfigParser()
    parser.read(profiles_path)

    profiles = []
    for section in parser.sections():
        profile = {k: v for k, v in parser[section].items()}
        if profile["type"] == "slurm":
            profiles.append(
                dict(
                    name=section,
                    type="slurm",
                    host=profile["host"],
                    user=profile["user"],
                    home_dir=profile["home_dir"],
                    cache_dir=profile["cache_dir"],
                )
            )
        elif profile["type"] == "local":
            profiles.append(
                dict(
                    name=section,
                    type="local",
                    home_dir=profile["home_dir"],
                    cache_dir=profile["cache_dir"],
                )
            )
        else:
            pass
    return profiles


def import_profile(home_dir: str, name: str) -> dict:
    """Parse profile from profile.ini."""

    profiles_path = os.path.join(home_dir, "profiles.cfg")
    if not os.path.isfile(profiles_path):
        raise FileNotFoundError()

    parser = ConfigParser()
    parser.read(profiles_path)

    for section in parser.sections():
        if section == name:
            profile = {k: v for k, v in parser[section].items()}
            if profile["type"] == "slurm":
                return dict(
                    name=section,
                    type="slurm",
                    host=profile["host"],
                    user=profile["user"],
                    home_dir=profile["home_dir"],
                    cache_dir=profile["cache_dir"],
                )
            elif profile["type"] == "local":
                return dict(
                    name=section,
                    type="local",
                    home_dir=profile["home_dir"],
                    cache_dir=profile["cache_dir"],
                )
            else:
                pass

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
