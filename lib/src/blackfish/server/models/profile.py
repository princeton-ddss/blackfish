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
    python_path: str = "python3"
    schema: str = "slurm"
    default: bool = False

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
    default: bool = False

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


_TRUTHY = {"1", "true", "yes", "on"}


def _as_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in _TRUTHY


def section_is_default(parser: ConfigParser, name: str) -> bool:
    """Return whether the named section is flagged as the default profile."""
    return _as_bool(parser[name].get("default"))


def has_any_default(parser: ConfigParser) -> bool:
    """Return whether any section in the parser has ``default = true`` set."""
    return any(section_is_default(parser, s) for s in parser.sections())


def set_exclusive_default(parser: ConfigParser, name: str) -> None:
    """Mark ``name`` as default and explicitly clear the flag on all other sections."""
    for section in parser.sections():
        parser[section]["default"] = "true" if section == name else "false"


def _build_profile(name: str, raw: dict[str, str]) -> BlackfishProfile | None:
    schema = raw.get("schema") or raw.get("type")
    is_default = _as_bool(raw.get("default"))
    if schema == "slurm":
        return SlurmProfile(
            name=name,
            host=raw["host"],
            user=raw["user"],
            home_dir=raw["home_dir"],
            cache_dir=raw["cache_dir"],
            python_path=raw.get("python_path", "python3"),
            default=is_default,
        )
    if schema == "local":
        return LocalProfile(
            name=name,
            home_dir=raw["home_dir"],
            cache_dir=raw["cache_dir"],
            default=is_default,
        )
    return None


def deserialize_profiles(home_dir: str) -> list[BlackfishProfile]:
    """Parse profiles from profile.cfg."""

    profiles_path = os.path.join(home_dir, "profiles.cfg")
    if not os.path.isfile(profiles_path):
        raise FileNotFoundError()

    parser = ConfigParser()
    parser.read(profiles_path)

    profiles: list[BlackfishProfile] = []
    for section in parser.sections():
        raw = {k: v for k, v in parser[section].items()}
        profile = _build_profile(section, raw)
        if profile is not None:
            profiles.append(profile)

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
            raw = {k: v for k, v in parser[section].items()}
            profile = _build_profile(section, raw)
            if profile is None:
                schema_value = raw.get("schema") or raw.get("type", "unknown")
                raise ProfileTypeException(schema_value)
            return profile

    return None


def get_default_profile_name(home_dir: str) -> str | None:
    """Resolve the name of the default profile.

    Resolution order:
      1. The (first) profile with ``default = true``.
      2. A profile literally named ``default`` (legacy convention).
      3. The first declared profile section.
      4. ``None`` if no profiles exist.
    """

    profiles_path = os.path.join(home_dir, "profiles.cfg")
    if not os.path.isfile(profiles_path):
        return None

    parser = ConfigParser()
    parser.read(profiles_path)

    sections: list[str] = parser.sections()
    for section in sections:
        if _as_bool(parser[section].get("default")):
            return section

    if "default" in sections:
        return "default"

    return sections[0] if sections else None
