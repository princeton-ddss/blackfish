from typing import Optional
import rich_click as click
from rich_click import Context
import configparser
import os
from enum import StrEnum
from log_symbols.symbols import LogSymbols

from app.setup import (
    create_remote_home_dir,
    check_remote_cache_exists,
    create_local_home_dir,
    check_local_cache_exists,
)
from app.models.profile import SlurmProfile, LocalProfile


class ProfileType(StrEnum):
    Slurm = "slurm"
    Local = "local"


def _create_profile_(app_dir: str, default_name: str = "default") -> bool:
    profiles = configparser.ConfigParser()
    profiles.read(f"{app_dir}/profiles.cfg")

    name = input(f"> name [{default_name}]: ")
    name = default_name if name == "" else name

    if name in profiles:
        print(
            f"{LogSymbols.ERROR.value} Profile named {name} already exists. Try"
            " deleting or modifying this profile instead."
        )
        return False

    while True:
        try:
            profile_type = ProfileType[input("> type [slurm or local]: ").capitalize()]
            break
        except Exception:
            print(f"Profile type should be one of: {list(ProfileType.__members__)}.")

    if profile_type == ProfileType.Slurm:
        host = input("> host [localhost]: ")
        host = "localhost" if host == "" else host
        user = input("> user: ")
        while user == "":
            print("User is required.")
            user = input("> user: ")
        home_dir = input(f"> home [/home/{user}/.blackfish]: ")
        home_dir = f"/home/{user}/.blackfish" if home_dir == "" else home_dir
        cache_dir = input("> cache: ")
        while cache_dir == "":
            print("Cache directory is required.")
            cache_dir = input("> cache: ")
        if host == "localhost":
            try:
                create_local_home_dir(home_dir)
                check_local_cache_exists(cache_dir)
            except Exception:
                print(f"{LogSymbols.ERROR.value} Failed to set up local profile.")
                return False
        else:
            try:
                create_remote_home_dir(host=host, user=user, home_dir=home_dir)
                check_remote_cache_exists(host=host, user=user, cache_dir=cache_dir)
            except Exception:
                print(f"{LogSymbols.ERROR.value} Failed to set up remote profile.")
                return False

        profiles[name] = {
            "type": "slurm",
            "user": user,
            "host": host,
            "home_dir": home_dir,
            "cache_dir": cache_dir,
        }

    elif profile_type == ProfileType.Local:
        home_dir = input(f"> home [{app_dir}]: ")
        home_dir = app_dir if home_dir == "" else home_dir
        cache_dir = input("> cache: ")
        while cache_dir == "":
            print("Cache directory is required.")
            cache_dir = input("> cache: ")
        try:
            create_local_home_dir(home_dir)
            check_local_cache_exists(cache_dir)
        except Exception:
            print(f"{LogSymbols.ERROR.value} Failed to set up local profile.")
            return False

        profiles[name] = {
            "type": "local",
            "home_dir": home_dir,
            "cache_dir": cache_dir,
        }

    with open(os.path.join(app_dir, "profiles.cfg"), "w") as f:
        profiles.write(f)
        print(f"{LogSymbols.SUCCESS.value} Created profile {name}.")
        return True


def _auto_profile_(
    app_dir: str,
    name: str | None,
    schema: str,
    host: str | None,
    user: str | None,
    home_dir: str | None,
    cache_dir: str | None,
) -> bool:
    profiles = configparser.ConfigParser()
    profiles.read(f"{home_dir}/profiles.cfg")

    if name in profiles:
        print(
            f"{LogSymbols.ERROR.value} Profile '{name}' already exists. Try"
            " deleting or modifying this profile instead."
        )
        return False

    if schema.capitalize() not in list(ProfileType.__members__):
        print(
            f"{LogSymbols.ERROR.value} Profile type should be one of: {list(ProfileType.__members__)}."
        )
        return False
    else:
        profile_type = ProfileType[schema.capitalize()]

    profile: LocalProfile | SlurmProfile
    if profile_type == ProfileType.Slurm:
        if name is None:
            raise ValueError("'name' is required.")
        if host is None:
            raise ValueError("'host' is required.")
        if user is None:
            raise ValueError("'user' is required.")
        if home_dir is None:
            raise ValueError("'home_dir' is required.")
        if cache_dir is None:
            raise ValueError("'cache_dir' is required.")
        try:
            profile = SlurmProfile(
                name=name, host=host, user=user, home_dir=home_dir, cache_dir=cache_dir
            )
        except Exception as e:
            print(f"{LogSymbols.ERROR.value} Failed to construct profile: {e}")
            return False

        if host == "localhost":
            try:
                create_local_home_dir(profile.home_dir)
                check_local_cache_exists(profile.cache_dir)
            except Exception as e:
                print(
                    f"{LogSymbols.ERROR.value} Failed to set up local Slurm profile: {e}"
                )
                return False
        else:
            try:
                create_remote_home_dir(
                    host=profile.host, user=profile.user, home_dir=profile.home_dir
                )
                check_remote_cache_exists(
                    host=profile.host, user=profile.user, cache_dir=profile.cache_dir
                )
            except Exception as e:
                print(
                    f"{LogSymbols.ERROR.value} Failed to set up remote Slurm profile: {e}"
                )
                return False

        profiles[profile.name] = {
            "type": "slurm",
            "user": profile.user,
            "host": profile.host,
            "home_dir": profile.home_dir,
            "cache_dir": profile.cache_dir,
        }

    elif profile_type == ProfileType.Local:
        if name is None:
            raise ValueError("'name' is required.")
        if home_dir is None:
            raise ValueError("'home_dir' is required.")
        if cache_dir is None:
            raise ValueError("'cache_dir' is required.")
        try:
            profile = LocalProfile(name=name, home_dir=home_dir, cache_dir=cache_dir)
        except Exception as e:
            print(f"{LogSymbols.ERROR.value} Failed to construct profile: {e}")
            return False

        try:
            create_local_home_dir(profile.home_dir)
            check_local_cache_exists(profile.cache_dir)
        except Exception as e:
            print(f"{LogSymbols.ERROR.value} Failed to set up local profile: {e}")
            return False

        profiles[name] = {
            "type": "local",
            "home_dir": profile.home_dir,
            "cache_dir": profile.cache_dir,
        }

    with open(os.path.join(app_dir, "profiles.cfg"), "w") as f:
        profiles.write(f)
        print(f"{LogSymbols.SUCCESS.value} Created profile {profile.name}.")
        return True


def _update_profile_(
    default_home: str, default_name: str = "default", name: Optional[str] = None
) -> None:
    profiles = configparser.ConfigParser()
    profiles.read(f"{default_home}/profiles.cfg")

    if name is None:
        name = input(f"> name [{default_name}]: ")
        name = default_name if name == "" else name

    if name not in profiles:
        print(
            f"{LogSymbols.ERROR.value} Profile {name} not found. To view your existing"
            " profiles, type `blackfish profile list`."
        )
        return
    else:
        profile = profiles[name]
        profile_type = profile["type"]
        if profile_type == "slurm":
            host = input(f"> host [{profile['host']}]: ")
            host = profile["host"] if host == "" else host
            user = input(f"> user [{profile['user']}]: ")
            user = profile["user"] if user == "" else user
            home_dir = input(f"> home [{profile['home_dir']}]: ")
            home_dir = profile["home_dir"] if home_dir == "" else home_dir
            cache_dir = input(f"> cache [{profile['cache_dir']}]: ")
            cache_dir = profile["cache_dir"] if cache_dir == "" else cache_dir
            try:
                create_remote_home_dir(host=host, user=user, home_dir=home_dir)
                check_remote_cache_exists(host=host, user=user, cache_dir=cache_dir)
            except Exception:
                print(f"{LogSymbols.ERROR.value} Failed to set up remote profile.")
                return
        elif profile_type == "local":
            home_dir = input(f"> home [{profile['home_dir']}]: ")
            home_dir = profile["home_dir"] if home_dir == "" else home_dir
            cache_dir = input(f"> cache [{profile['cache_dir']}]: ")
            cache_dir = profile["cache_dir"] if cache_dir == "" else cache_dir
            try:
                create_local_home_dir(home_dir)
                check_local_cache_exists(cache_dir)
            except Exception:
                print(f"{LogSymbols.ERROR.value} Failed to set up local profile.")
                return
        else:
            raise NotImplementedError

    if profile_type == "slurm":
        profiles[name] = {
            "type": "slurm",
            "user": user,
            "host": host,
            "home_dir": home_dir,
            "cache_dir": cache_dir,
        }
    elif profile_type == "local":
        profiles[name] = {
            "type": "local",
            "home_dir": home_dir,
            "cache_dir": cache_dir,
        }
    else:
        raise NotImplementedError

    with open(os.path.join(default_home, "profiles.cfg"), "w") as f:
        profiles.write(f)
        print(f"{LogSymbols.SUCCESS.value} Updated profile {name}.")


@click.command()
@click.pass_context
def create_profile(ctx: Context) -> None:  # pragma: no cover
    """Create a new profile. Fails if the profile name already exists."""

    _create_profile_(ctx.obj.get("home_dir"))


@click.command()
@click.option(
    "--name", type=str, default="default", help="The name of the profile to display."
)
@click.pass_context
def show_profile(ctx: Context, name: str) -> None:  # pragma: no cover
    """Display a profile."""

    default_home = ctx.obj.get("home_dir")

    profiles = configparser.ConfigParser()
    profiles.read(f"{default_home}/profiles.cfg")

    if name in profiles:
        profile = profiles[name]
        profile_type = profile["type"]
        if profile_type == "slurm":
            print(f"[{name}]")
            print("type: slurm")
            print(f"host: {profile['host']}")
            print(f"user: {profile['user']}")
            print(f"home: {profile['home_dir']}")
            print(f"cache: {profile['cache_dir']}")
        elif profile_type == "local":
            print(f"[{name}]")
            print("type: local")
            print(f"home: {profile['home_dir']}")
            print(f"cache: {profile['cache_dir']}")
        else:
            raise NotImplementedError
    else:
        print(f"{LogSymbols.ERROR.value} Profile {name} not found.")


@click.command()
@click.pass_context
def list_profiles(ctx: Context) -> None:  # pragma: no cover
    """Display all available profiles."""

    default_home = ctx.obj.get("home_dir")

    profiles = configparser.ConfigParser()
    profiles.read(f"{default_home}/profiles.cfg")

    for name in profiles:
        profile = profiles[name]
        if profile.name == "DEFAULT":
            continue
        profile_type = profile["type"]
        if profile_type == "slurm":
            print(f"[{name}]")
            print("type: slurm")
            print(f"host: {profile['host']}")
            print(f"user: {profile['user']}")
            print(f"home: {profile['home_dir']}")
            print(f"cache: {profile['cache_dir']}")
        elif profile_type == "local":
            print(f"[{name}]")
            print("type: local")
            print(f"home: {profile['home_dir']}")
            print(f"cache: {profile['cache_dir']}")
        print("")


@click.command()
@click.option(
    "--name", type=str, default="default", help="The name of the profile to modify."
)
@click.pass_context
def update_profile(ctx: Context, name: str) -> None:  # pragma: no cover
    """Update a profile.

    This command does not permit changes to a profile's name or type. If you wish
    to rename a profile, you must delete the profile and then re-create
    it using a new name.
    """

    _update_profile_(ctx.obj.get("home_dir"), "default", name)


@click.command()
@click.option(
    "--name", type=str, default="default", help="The name of the profile to delete."
)
@click.pass_context
def delete_profile(ctx: Context, name: str) -> None:  # pragma: no cover
    """Delete a profile.

    This command does not clean up the profile's remote or local resources because
    these might be required for another profile or user.
    """

    home_dir = ctx.obj.get("home_dir")
    profiles = configparser.ConfigParser()
    profiles.read(f"{home_dir}/profiles.cfg")

    if name in profiles:
        confirm = input(f"  Delete profile {name}? (y/n) ")
        if confirm.lower() == "y":
            del profiles[name]
            with open(os.path.join(home_dir, "profiles.cfg"), "w") as f:
                profiles.write(f)
            print(f"{LogSymbols.SUCCESS.value} Profile {name} deleted.")
    else:
        print(f"{LogSymbols.ERROR.value} Profile {name} not found.")
