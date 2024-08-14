import click
import configparser
import os
from log_symbols.symbols import LogSymbols

from app.setup import (
    create_remote_home_dir,
    check_remote_cache_exists,
    create_local_home_dir,
    check_local_cache_exists,
)


@click.command()
@click.pass_context
def create_profile(ctx):
    """Create a new profile.

    Fails if the profile name already exists.
    """

    default_home = ctx.obj.get("home_dir")

    profiles = configparser.ConfigParser()
    profiles.read(f"{default_home}/profiles")

    name = input("> name [default]: ")
    name = "default" if name == "" else name

    if name in profiles:
        print(
            f"{LogSymbols.ERROR.value} Profile named {name} already exists. Try"
            " deleting or modifying this profile instead."
        )
        return
    else:
        profile_type = input("> type [slurm]: ")
        profile_type = "slurm" if profile_type == "" else profile_type
        if profile_type == "slurm":
            host = input("> host: ")
            while host == "":
                print("Host is required.")
                host = input("> host: ")
            user = input("> user: ")
            while user == "":
                print("User is required.")
                user = input("> user: ")
            remote_dir = input(f"> home [/home/{user}/.blackfish]: ")
            remote_dir = f"/home/{user}/.blackfish" if remote_dir == "" else remote_dir
            cache_dir = input("> cache: ")
            while cache_dir == "":
                print("Cache directory is required.")
                cache_dir = input("> cache: ")
            try:
                create_remote_home_dir(
                    "slurm", host=host, user=user, home_dir=remote_dir
                )
                check_remote_cache_exists(
                    "slurm", host=host, user=user, cache_dir=cache_dir
                )
            except Exception:
                print(f"{LogSymbols.ERROR.value} Failed to setup remote profile.")
                return
        elif profile_type == "local":
            home_dir = input(f"> home [{default_home}]: ")
            home_dir = default_home if home_dir == "" else home_dir
            cache_dir = input("> cache: ")
            while cache_dir == "":
                print("Cache directory is required.")
                cache_dir = input("> cache: ")
            try:
                create_local_home_dir(home_dir)
                check_local_cache_exists(cache_dir)
            except Exception:
                print(f"{LogSymbols.ERROR.value} Failed to setup local profile.")
                return
        else:
            raise NotImplementedError

    if profile_type == "slurm":
        profiles[name] = {
            "type": "slurm",
            "user": user,
            "host": host,
            "home_dir": remote_dir,
            "cache_dir": cache_dir,
        }
    elif profile_type == "local":
        profiles[name] = {
            "type": "local",
            "user": user,
            "home_dir": home_dir,
            "cache_dir": cache_dir,
        }
    else:
        raise NotImplementedError

    with open(os.path.join(default_home, "profiles"), "w") as f:
        profiles.write(f)
        print(f"{LogSymbols.SUCCESS.value} Created profile {name}.")


@click.command()
@click.option(
    "--name", type=str, default="default", help="The name of the profile to display."
)
@click.pass_context
def show_profile(ctx, name):
    """Display a profile."""

    default_home = ctx.obj.get("home_dir")

    profiles = configparser.ConfigParser()
    profiles.read(f"{default_home}/profiles")

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
def list_profiles(ctx):
    """Display all available profiles."""

    default_home = ctx.obj.get("home_dir")

    profiles = configparser.ConfigParser()
    profiles.read(f"{default_home}/profiles")

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
def update_profile(ctx, name):
    """Update a profile."""

    default_home = ctx.obj.get("home_dir")

    profiles = configparser.ConfigParser()
    profiles.read(f"{default_home}/profiles")

    name = input("> name [default]: ")
    name = "default" if name == "" else name

    if name not in profiles:
        print(
            f"{LogSymbols.ERROR.value} Profile {name} not found. To view your existing"
            " profiles, type `blackfish profile list`."
        )
        return
    else:
        profile = profiles[name]
        profile_type = input(f"> type [{profile['type']}]: ")
        profile_type = profile["type"] if profile_type == "" else profile_type
        if profile_type == "slurm":
            host = input(f"> host [{profile['host']}]: ")
            host = profile["host"] if host == "" else host
            user = input(f"> user [{profile['user']}]: ")
            user = profile["user"] if user == "" else user
            home_dir = input(f"> home_dir [{profile['home_dir']}]: ")
            home_dir = profile["home_dir"] if home_dir == "" else home_dir
            cache_dir = input(f"> cache_dir [{profile['cache_dir']}]: ")
            cache_dir = profile["cache_dir"] if cache_dir == "" else cache_dir
            try:
                create_remote_home_dir("slurm", host=host, user=user, home_dir=home_dir)
                check_remote_cache_exists(
                    "slurm", host=host, user=user, cache_dir=cache_dir
                )
            except Exception:
                print(f"{LogSymbols.ERROR.value} Failed to setup remote profile.")
                return
        elif profile_type == "local":
            home_dir = input(f"> type [{profile['home_dir']}]: ")
            home_dir = profile["type"] if home_dir == "" else home_dir
            cache_dir = input(f"> type [{profile['cache_dir']}]: ")
            cache_dir = profile["type"] if cache_dir == "" else cache_dir
            try:
                create_local_home_dir(home_dir)
                check_local_cache_exists(cache_dir)
            except Exception:
                print(f"{LogSymbols.ERROR.value} Failed to setup local profile.")
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
            "user": user,
            "home_dir": home_dir,
            "cache_dir": cache_dir,
        }
    else:
        raise NotImplementedError

    with open(os.path.join(default_home, "profiles"), "w") as f:
        profiles.write(f)
        print(f"{LogSymbols.SUCCESS.value} Updated profile {name}.")


@click.command()
@click.option(
    "--name", type=str, default="default", help="The name of the profile to delete."
)
@click.pass_context
def delete_profile(ctx, name: str):
    """Delete a profile.

    Does not clean up the profile's remote or local resources.
    """

    home_dir = ctx.obj.get("home_dir")
    profiles = configparser.ConfigParser()
    profiles.read(f"{home_dir}/profiles")

    if name in profiles:
        confirm = input(f"  Delete profile {name}? (y/n)")
        if confirm.lower() == "y":
            del profiles[name]
            with open(os.path.join(home_dir, "profiles"), "w") as f:
                profiles.write(f)
            print(f"{LogSymbols.SUCCESS.value} Profile {name} deleted.")
    else:
        print(f"{LogSymbols.ERROR.value} Profile {name} not found.")
