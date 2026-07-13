from typing import Optional
import asyncio
import sys
import rich_click as click
from rich_click import Context
import configparser
import os
from enum import StrEnum
from log_symbols.symbols import LogSymbols
from yaspin import yaspin
import requests

from blackfish.cli import api
from blackfish.server.config import config
from blackfish.server.setup import ProfileManager, ProfileSetupError
from blackfish.server.models.profile import (
    SlurmProfile,
    LocalProfile,
    get_default_profile_name,
    has_any_default,
    section_is_default,
    set_exclusive_default,
    validate_profile_name,
)
from blackfish.server.config import ContainerProvider, config as blackfish_config
from blackfish.server.images import ImageSpec
from blackfish.server.jobs.client import (
    TigerFlowClient,
    TigerFlowError,
    SSHRunner,
    LocalRunner,
    CommandRunner,
)


def _setup_profile(
    runner: CommandRunner,
    home_dir: str,
    cache_dir: str,
) -> None:
    """Set up profile directories.

    Shows spinner progress, resolving to a checkmark on completion. No package
    installation is performed — batch jobs run from the tigerflow-ml container
    image, which is staged separately (see ``blackfish image ls``).

    Args:
        runner: CommandRunner (SSHRunner or LocalRunner)
        home_dir: Profile home directory
        cache_dir: Profile cache directory

    Raises:
        ProfileSetupError: If directory setup fails
    """

    async def setup_directories() -> None:
        profile_mgr = ProfileManager(
            runner=runner,
            home_dir=home_dir,
            cache_dir=cache_dir,
            on_progress=lambda msg: setattr(spinner, "text", msg),
        )
        await profile_mgr.create_directories()
        await profile_mgr.check_cache()

    with yaspin(text=f"Setting up directories on {runner.host}...") as spinner:
        asyncio.run(setup_directories())
        spinner.text = "Directories ready."
        spinner.ok(f"{LogSymbols.SUCCESS.value}")


def _repair_profile(
    runner: CommandRunner,
    home_dir: str,
    cache_dir: str,
    image: ImageSpec,
    provider: ContainerProvider,
    force: bool = False,
) -> bool:
    """Repair a Slurm profile with step-by-step progress.

    Recreates directories and verifies the tigerflow-ml image is staged. No
    package installation is performed.

    Args:
        runner: CommandRunner (SSHRunner or LocalRunner)
        home_dir: Profile home directory
        cache_dir: Profile cache directory
        image: tigerflow-ml image spec
        provider: container provider (Apptainer/Docker)
        force: Recreate directories even if the image already looks staged

    Returns:
        True if repair was performed, False if the profile was already healthy.

    Raises:
        ProfileSetupError: If directory setup fails
    """

    async def setup_directories() -> None:
        profile_mgr = ProfileManager(
            runner=runner,
            home_dir=home_dir,
            cache_dir=cache_dir,
            on_progress=lambda msg: setattr(spinner, "text", msg),
        )
        await profile_mgr.create_directories()
        await profile_mgr.check_cache()

    with yaspin(text=f"Checking directories on {runner.host}...") as spinner:
        asyncio.run(setup_directories())
        spinner.text = "Directories ready."
        spinner.ok(f"{LogSymbols.SUCCESS.value}")

    # Verify the tigerflow-ml image is staged.
    async def check_image() -> tuple[bool, str]:
        client = TigerFlowClient(
            runner=runner,
            home_dir=home_dir,
            image=image,
            provider=provider,
            cache_dir=cache_dir,
            on_progress=lambda msg: setattr(spinner, "text", msg),
        )
        try:
            versions = await client.check_health()
            return (
                True,
                f"tigerflow-ml image available "
                f"(tigerflow {versions.tigerflow}, tigerflow-ml {versions.tigerflow_ml}).",
            )
        except TigerFlowError as e:
            return (False, e.user_message())

    with yaspin(text="Checking tigerflow-ml image...") as spinner:
        is_healthy, message = asyncio.run(check_image())
        spinner.text = message
        spinner.ok(
            f"{LogSymbols.SUCCESS.value}"
            if is_healthy
            else f"{LogSymbols.WARNING.value}"
        )

    if is_healthy and not force:
        print(f"{LogSymbols.SUCCESS.value} Profile healthy.")
        return False

    return True


class ProfileType(StrEnum):
    Slurm = "slurm"
    Local = "local"


def resolve_profile_or_exit(home_dir: str, profile: Optional[str]) -> str:
    """Return ``profile`` if provided, else the resolved default profile name.

    Exits the process with code 1 if no profile is given and none is configured.
    Intended for CLI commands whose ``--profile`` option falls back to the default.
    """
    if profile is not None:
        return profile
    resolved = get_default_profile_name(home_dir)
    if resolved is None:
        click.echo(
            f"{LogSymbols.ERROR.value} No profiles configured. Run"
            " `blackfish profile add` to register one."
        )
        sys.exit(1)
    return resolved


def _create_profile_(app_dir: str, default_name: str = "default") -> bool:
    profiles = configparser.ConfigParser()
    profiles.read(f"{app_dir}/profiles.cfg")

    name = input(f"> name [{default_name}]: ")
    name = default_name if name == "" else name

    try:
        validate_profile_name(name)
    except ValueError as e:
        print(f"{LogSymbols.ERROR.value} {e}")
        return False

    if name in profiles:
        print(
            f"{LogSymbols.ERROR.value} Profile named {name} already exists. Try"
            " deleting or modifying this profile instead."
        )
        return False

    while True:
        try:
            schema = ProfileType[input("> schema [slurm or local]: ").capitalize()]
            break
        except Exception:
            print(f"Profile schema should be one of: {list(ProfileType.__members__)}.")

    if schema == ProfileType.Slurm:
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

        # Set up directories
        runner: SSHRunner | LocalRunner
        if host == "localhost":
            runner = LocalRunner()
        else:
            runner = SSHRunner(user=user, host=host)

        try:
            _setup_profile(
                runner=runner,
                home_dir=home_dir,
                cache_dir=cache_dir,
            )
        except ProfileSetupError as e:
            print(f"{LogSymbols.ERROR.value} {e.user_message()}")
            return False

        profiles[name] = {
            "schema": "slurm",
            "user": user,
            "host": host,
            "home_dir": home_dir,
            "cache_dir": cache_dir,
        }

    elif schema == ProfileType.Local:
        home_dir = input(f"> home [{app_dir}]: ")
        home_dir = app_dir if home_dir == "" else home_dir
        cache_dir = input("> cache: ")
        while cache_dir == "":
            print("Cache directory is required.")
            cache_dir = input("> cache: ")

        # Set up directories
        runner = LocalRunner()
        try:
            _setup_profile(
                runner=runner,
                home_dir=home_dir,
                cache_dir=cache_dir,
            )
        except ProfileSetupError as e:
            print(f"{LogSymbols.ERROR.value} {e.user_message()}")
            return False

        profiles[name] = {
            "schema": "local",
            "home_dir": home_dir,
            "cache_dir": cache_dir,
        }

    if not has_any_default(profiles):
        profiles[name]["default"] = "true"
    else:
        profiles[name]["default"] = "false"

    with open(os.path.join(app_dir, "profiles.cfg"), "w") as f:
        profiles.write(f)
        print(f"{LogSymbols.SUCCESS.value} Created profile '{name}'.")
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

    if name is not None:
        try:
            validate_profile_name(name)
        except ValueError as e:
            print(f"{LogSymbols.ERROR.value} {e}")
            return False

    if name in profiles:
        print(
            f"{LogSymbols.ERROR.value} Profile '{name}' already exists. Try"
            " deleting or modifying this profile instead."
        )
        return False

    if schema.capitalize() not in list(ProfileType.__members__):
        print(
            f"{LogSymbols.ERROR.value} Profile schema should be one of: {list(ProfileType.__members__)}."
        )
        return False
    else:
        schema_enum = ProfileType[schema.capitalize()]

    profile: LocalProfile | SlurmProfile
    if schema_enum == ProfileType.Slurm:
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

        # Set up directories
        runner: SSHRunner | LocalRunner
        if profile.host == "localhost":
            runner = LocalRunner()
        else:
            runner = SSHRunner(user=profile.user, host=profile.host)

        try:
            _setup_profile(
                runner=runner,
                home_dir=profile.home_dir,
                cache_dir=profile.cache_dir,
            )
        except ProfileSetupError as e:
            print(f"{LogSymbols.ERROR.value} {e.user_message()}")
            return False

        profiles[profile.name] = {
            "schema": "slurm",
            "user": profile.user,
            "host": profile.host,
            "home_dir": profile.home_dir,
            "cache_dir": profile.cache_dir,
        }

    elif schema_enum == ProfileType.Local:
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

        # Set up directories
        runner = LocalRunner()
        try:
            _setup_profile(
                runner=runner,
                home_dir=profile.home_dir,
                cache_dir=profile.cache_dir,
            )
        except ProfileSetupError as e:
            print(f"{LogSymbols.ERROR.value} {e.user_message()}")
            return False

        profiles[name] = {
            "schema": "local",
            "home_dir": profile.home_dir,
            "cache_dir": profile.cache_dir,
        }

    if not has_any_default(profiles):
        profiles[profile.name]["default"] = "true"
    else:
        profiles[profile.name]["default"] = "false"

    with open(os.path.join(app_dir, "profiles.cfg"), "w") as f:
        profiles.write(f)
        print(f"{LogSymbols.SUCCESS.value} Created profile '{profile.name}'.")
        return True


def _update_profile_(
    default_home: str, default_name: str = "default", name: Optional[str] = None
) -> bool:
    profiles = configparser.ConfigParser()
    profiles.read(f"{default_home}/profiles.cfg")

    if name is None:
        name = input(f"> name [{default_name}]: ")
        name = default_name if name == "" else name

    was_default = name in profiles and section_is_default(profiles, name)

    if name not in profiles:
        print(
            f"{LogSymbols.ERROR.value} Profile {name} not found. To view your existing"
            " profiles, type `blackfish profile list`."
        )
        return False
    else:
        profile = profiles[name]
        schema = profile.get("schema") or profile.get("type")
        if schema == "slurm":
            host = input(f"> host [{profile['host']}]: ")
            host = profile["host"] if host == "" else host
            user = input(f"> user [{profile['user']}]: ")
            user = profile["user"] if user == "" else user
            home_dir = input(f"> home [{profile['home_dir']}]: ")
            home_dir = profile["home_dir"] if home_dir == "" else home_dir
            cache_dir = input(f"> cache [{profile['cache_dir']}]: ")
            cache_dir = profile["cache_dir"] if cache_dir == "" else cache_dir

            # Set up directories
            runner: SSHRunner | LocalRunner
            if host == "localhost":
                runner = LocalRunner()
            else:
                runner = SSHRunner(user=user, host=host)

            try:
                _setup_profile(
                    runner=runner,
                    home_dir=home_dir,
                    cache_dir=cache_dir,
                )
            except ProfileSetupError as e:
                print(f"{LogSymbols.ERROR.value} {e.user_message()}")
                return False
        elif schema == "local":
            home_dir = input(f"> home [{profile['home_dir']}]: ")
            home_dir = profile["home_dir"] if home_dir == "" else home_dir
            cache_dir = input(f"> cache [{profile['cache_dir']}]: ")
            cache_dir = profile["cache_dir"] if cache_dir == "" else cache_dir

            # Set up directories
            runner = LocalRunner()
            try:
                _setup_profile(
                    runner=runner,
                    home_dir=home_dir,
                    cache_dir=cache_dir,
                )
            except ProfileSetupError as e:
                print(f"{LogSymbols.ERROR.value} {e.user_message()}")
                return False
        else:
            raise NotImplementedError

    if schema == "slurm":
        profiles[name] = {
            "schema": "slurm",
            "user": user,
            "host": host,
            "home_dir": home_dir,
            "cache_dir": cache_dir,
        }
    elif schema == "local":
        profiles[name] = {
            "schema": "local",
            "home_dir": home_dir,
            "cache_dir": cache_dir,
        }
    else:
        raise NotImplementedError

    profiles[name]["default"] = "true" if was_default else "false"

    with open(os.path.join(default_home, "profiles.cfg"), "w") as f:
        profiles.write(f)
        print(f"{LogSymbols.SUCCESS.value} Updated profile {name}.")
        return True


@click.command()
@click.pass_context
def create_profile(ctx: Context) -> None:  # pragma: no cover
    """Create a new profile. Fails if the profile name already exists."""

    success = _create_profile_(ctx.obj.get("home_dir"))
    if not success:
        ctx.exit(1)


@click.command()
@click.option(
    "--name",
    type=str,
    default=None,
    help="The name of the profile to display (defaults to the default profile).",
)
@click.pass_context
def show_profile(ctx: Context, name: str | None) -> None:  # pragma: no cover
    """Display a profile."""

    default_home = ctx.obj.get("home_dir")

    profiles = configparser.ConfigParser()
    profiles.read(f"{default_home}/profiles.cfg")

    if name is None:
        name = get_default_profile_name(default_home)
        if name is None:
            print(f"{LogSymbols.ERROR.value} No profiles configured.")
            ctx.exit(1)
            return

    if name in profiles:
        profile = profiles[name]
        schema = profile.get("schema") or profile.get("type")
        if schema == "slurm":
            print(f"[{name}]")
            print("schema: slurm")
            print(f"host: {profile['host']}")
            print(f"user: {profile['user']}")
            print(f"home: {profile['home_dir']}")
            print(f"cache: {profile['cache_dir']}")
        elif schema == "local":
            print(f"[{name}]")
            print("schema: local")
            print(f"home: {profile['home_dir']}")
            print(f"cache: {profile['cache_dir']}")
        else:
            raise NotImplementedError
    else:
        print(f"{LogSymbols.ERROR.value} Profile {name} not found.")
        ctx.exit(1)


@click.command()
@click.pass_context
def list_profiles(ctx: Context) -> None:  # pragma: no cover
    """Display all available profiles."""

    default_home = ctx.obj.get("home_dir")

    profiles = configparser.ConfigParser()
    profiles.read(f"{default_home}/profiles.cfg")

    default_name = get_default_profile_name(default_home)

    for name in profiles:
        profile = profiles[name]
        if profile.name == "DEFAULT":
            continue
        schema = profile.get("schema") or profile.get("type")
        marker = " (default)" if name == default_name else ""
        if schema == "slurm":
            print(f"[{name}]{marker}")
            print("schema: slurm")
            print(f"host: {profile['host']}")
            print(f"user: {profile['user']}")
            print(f"home: {profile['home_dir']}")
            print(f"cache: {profile['cache_dir']}")
        elif schema == "local":
            print(f"[{name}]{marker}")
            print("schema: local")
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

    This command does not permit changes to a profile's type. To rename a
    profile, use `blackfish profile rename` instead.
    """

    success = _update_profile_(ctx.obj.get("home_dir"), "default", name)
    if not success:
        ctx.exit(1)


@click.command()
@click.option(
    "--name", type=str, required=True, help="The name of the profile to delete."
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Allow deleting the default profile; another must be set as default first.",
)
@click.pass_context
def delete_profile(ctx: Context, name: str, force: bool) -> None:  # pragma: no cover
    """Delete a profile.

    This command does not clean up the profile's remote or local resources because
    these might be required for another profile or user.
    """

    home_dir = ctx.obj.get("home_dir")
    profiles = configparser.ConfigParser()
    profiles.read(f"{home_dir}/profiles.cfg")

    if name not in profiles:
        print(f"{LogSymbols.ERROR.value} Profile {name} not found.")
        ctx.exit(1)
        return

    was_default = name == get_default_profile_name(home_dir)
    if was_default and not force:
        print(
            f"{LogSymbols.ERROR.value} '{name}' is the default profile. Set another"
            " profile as default with `blackfish profile default <name>` first, or"
            " pass --force."
        )
        ctx.exit(1)
        return

    confirm = input(f"  Delete profile {name}? (y/n) ")
    if confirm.lower() == "y":
        del profiles[name]
        with open(os.path.join(home_dir, "profiles.cfg"), "w") as f:
            profiles.write(f)
        print(f"{LogSymbols.SUCCESS.value} Profile {name} deleted.")
        if was_default and not has_any_default(profiles):
            print(
                f"{LogSymbols.WARNING.value} No default profile is set. Run"
                " `blackfish profile default <name>` to assign one."
            )
    # Note: User canceling deletion is not an error, so no exit(1)


@click.command(name="default")
@click.argument("name", type=str, required=True)
@click.pass_context
def set_default_profile(ctx: Context, name: str) -> None:  # pragma: no cover
    """Set the default profile.

    Exactly one profile is marked default at a time; this command sets the flag on
    NAME and clears it from every other profile.
    """

    home_dir = ctx.obj.get("home_dir")
    profiles = configparser.ConfigParser()
    profiles.read(f"{home_dir}/profiles.cfg")

    if name not in profiles:
        print(f"{LogSymbols.ERROR.value} Profile {name} not found.")
        ctx.exit(1)
        return

    set_exclusive_default(profiles, name)
    with open(os.path.join(home_dir, "profiles.cfg"), "w") as f:
        profiles.write(f)
    print(f"{LogSymbols.SUCCESS.value} '{name}' is now the default profile.")


@click.command(name="rename")
@click.argument("old_name", type=str, required=True)
@click.argument("new_name", type=str, required=True)
def rename_profile(old_name: str, new_name: str) -> None:  # pragma: no cover
    """Rename a profile from OLD_NAME to NEW_NAME.

    Renames the profile and updates the stored profile name on every
    associated model, download, service and job. This requires the Blackfish
    server to be running.
    """

    try:
        res = api.put(
            f"/api/profiles/{old_name}/rename",
            json={"new_name": new_name},
        )
    except requests.exceptions.ConnectionError:
        print(
            f"{LogSymbols.ERROR.value} Failed to connect to the Blackfish API. Is"
            f" Blackfish running on port {config.PORT}?"
        )
        raise SystemExit(1)

    if res.ok:
        print(
            f"{LogSymbols.SUCCESS.value} Renamed profile '{old_name}' to '{new_name}'."
        )
        return

    detail = f"Failed to rename profile ({res.status_code})."
    try:
        body = res.json()
        if isinstance(body, dict) and body.get("detail"):
            detail = body["detail"]
    except ValueError:
        pass
    print(f"{LogSymbols.ERROR.value} {detail}")
    raise SystemExit(1)


@click.command()
@click.option(
    "--name", type=str, default="default", help="The name of the profile to repair."
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force repair even if profile is healthy.",
)
@click.pass_context
def repair_profile(
    ctx: Context,
    name: str,
    force: bool,
) -> None:  # pragma: no cover
    """Repair a Slurm profile.

    Checks profile health first and skips repair if everything is working.
    Use --force to repair anyway.

    Examples:

        blackfish profile repair --name default

        # Force repair even if healthy
        blackfish profile repair --name default --force
    """
    home_dir = ctx.obj.get("home_dir")
    profiles = configparser.ConfigParser()
    profiles.read(f"{home_dir}/profiles.cfg")

    if name not in profiles:
        print(f"{LogSymbols.ERROR.value} Profile {name} not found.")
        ctx.exit(1)

    profile = profiles[name]
    schema = profile.get("schema") or profile.get("type")

    if schema != "slurm":
        print(f"{LogSymbols.ERROR.value} Repair is only supported on Slurm profiles.")
        ctx.exit(1)

    host = profile["host"]
    user = profile["user"]
    profile_home_dir = profile["home_dir"]
    cache_dir = profile["cache_dir"]

    runner: SSHRunner | LocalRunner
    if host == "localhost":
        runner = LocalRunner()
    else:
        runner = SSHRunner(user=user, host=host)

    try:
        _repair_profile(
            runner=runner,
            home_dir=profile_home_dir,
            cache_dir=cache_dir,
            image=blackfish_config.IMAGES["tigerflow_ml"],
            provider=blackfish_config.CONTAINER_PROVIDER or ContainerProvider.Apptainer,
            force=force,
        )
    except ProfileSetupError as e:
        print(f"{LogSymbols.ERROR.value} {e.user_message()}")
        ctx.exit(1)
    except TigerFlowError as e:
        print(f"{LogSymbols.ERROR.value} {e.user_message()}")
        ctx.exit(1)
