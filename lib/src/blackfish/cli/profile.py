from typing import Optional
from collections.abc import Callable
import asyncio
import rich_click as click
from rich_click import Context
import configparser
import os
from enum import StrEnum
from log_symbols.symbols import LogSymbols
from yaspin import yaspin

from blackfish.server.setup import ProfileManager, ProfileSetupError
from blackfish.server.models.profile import SlurmProfile, LocalProfile
from blackfish.server.jobs.client import (
    TigerFlowClient,
    TigerFlowError,
    SSHRunner,
    LocalRunner,
    CommandRunner,
)


async def _setup_profile_async(
    runner: CommandRunner,
    home_dir: str,
    cache_dir: str,
    setup_tigerflow: bool = False,
    python_path: str = "python3",
    on_progress: Callable[[str], None] | None = None,
) -> None:
    """Set up profile directories and optionally TigerFlow.

    This is the shared async implementation used by both API and CLI.

    Args:
        runner: CommandRunner (SSHRunner or LocalRunner)
        home_dir: Profile home directory
        cache_dir: Profile cache directory
        setup_tigerflow: Whether to install TigerFlow (Slurm profiles only)
        python_path: Python interpreter path for TigerFlow venv
        on_progress: Optional callback for progress updates
    """
    # Set up directories
    profile_mgr = ProfileManager(
        runner=runner,
        home_dir=home_dir,
        cache_dir=cache_dir,
        on_progress=on_progress,
    )
    await profile_mgr.create_directories()
    await profile_mgr.check_cache()

    # Set up TigerFlow if requested
    if setup_tigerflow:
        tigerflow = TigerFlowClient(
            runner=runner,
            home_dir=home_dir,
            python_path=python_path,
            on_progress=on_progress,
        )
        await tigerflow.setup()


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
        python_path = input("> python_path [python3]: ")
        python_path = "python3" if python_path == "" else python_path

        # Set up directories and TigerFlow
        runner: SSHRunner | LocalRunner
        if host == "localhost":
            runner = LocalRunner()
        else:
            runner = SSHRunner(user=user, host=host)

        with yaspin(text=f"Setting up profile on {host}...") as spinner:
            try:
                asyncio.run(
                    _setup_profile_async(
                        runner=runner,
                        home_dir=home_dir,
                        cache_dir=cache_dir,
                        setup_tigerflow=True,
                        python_path=python_path,
                        on_progress=lambda msg: setattr(spinner, "text", msg),
                    )
                )
                spinner.ok(f"{LogSymbols.SUCCESS.value}")
            except ProfileSetupError as e:
                spinner.fail(f"{LogSymbols.ERROR.value}")
                print(f"  {e.user_message()}")
                return False
            except TigerFlowError as e:
                spinner.fail(f"{LogSymbols.ERROR.value}")
                print(f"  {e.user_message()}")
                return False

        profiles[name] = {
            "schema": "slurm",
            "user": user,
            "host": host,
            "home_dir": home_dir,
            "cache_dir": cache_dir,
        }
        if python_path != "python3":
            profiles[name]["python_path"] = python_path

    elif schema == ProfileType.Local:
        home_dir = input(f"> home [{app_dir}]: ")
        home_dir = app_dir if home_dir == "" else home_dir
        cache_dir = input("> cache: ")
        while cache_dir == "":
            print("Cache directory is required.")
            cache_dir = input("> cache: ")

        # Set up directories (no TigerFlow for local profiles)
        runner = LocalRunner()
        with yaspin(text="Setting up local profile...") as spinner:
            try:
                asyncio.run(
                    _setup_profile_async(
                        runner=runner,
                        home_dir=home_dir,
                        cache_dir=cache_dir,
                        setup_tigerflow=False,
                        on_progress=lambda msg: setattr(spinner, "text", msg),
                    )
                )
                spinner.ok(f"{LogSymbols.SUCCESS.value}")
            except ProfileSetupError as e:
                spinner.fail(f"{LogSymbols.ERROR.value}")
                print(f"  {e.user_message()}")
                return False

        profiles[name] = {
            "schema": "local",
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

        # Set up directories and TigerFlow
        try:
            print(f"Setting up profile on {profile.host}...")
            runner: SSHRunner | LocalRunner
            if profile.host == "localhost":
                runner = LocalRunner()
            else:
                runner = SSHRunner(user=profile.user, host=profile.host)
            asyncio.run(
                _setup_profile_async(
                    runner=runner,
                    home_dir=profile.home_dir,
                    cache_dir=profile.cache_dir,
                    setup_tigerflow=True,
                )
            )
            print(f"{LogSymbols.SUCCESS.value} Profile setup complete.")
        except ProfileSetupError as e:
            print(f"{LogSymbols.ERROR.value} {e.user_message()}")
            return False
        except TigerFlowError as e:
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

        # Set up directories (no TigerFlow for local profiles)
        try:
            print("Setting up local profile...")
            runner = LocalRunner()
            asyncio.run(
                _setup_profile_async(
                    runner=runner,
                    home_dir=profile.home_dir,
                    cache_dir=profile.cache_dir,
                    setup_tigerflow=False,
                )
            )
            print(f"{LogSymbols.SUCCESS.value} Profile setup complete.")
        except ProfileSetupError as e:
            print(f"{LogSymbols.ERROR.value} {e.user_message()}")
            return False

        profiles[name] = {
            "schema": "local",
            "home_dir": profile.home_dir,
            "cache_dir": profile.cache_dir,
        }

    with open(os.path.join(app_dir, "profiles.cfg"), "w") as f:
        profiles.write(f)
        print(f"{LogSymbols.SUCCESS.value} Created profile {profile.name}.")
        return True


def _update_profile_(
    default_home: str, default_name: str = "default", name: Optional[str] = None
) -> bool:
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
            existing_python_path = profile.get("python_path", "python3")
            python_path = input(f"> python_path [{existing_python_path}]: ")
            python_path = existing_python_path if python_path == "" else python_path

            # Set up directories and install TigerFlow if missing
            async def setup_slurm_profile(
                on_progress: Callable[[str], None] | None = None,
            ) -> None:
                runner: SSHRunner | LocalRunner
                if host == "localhost":
                    runner = LocalRunner()
                else:
                    runner = SSHRunner(user=user, host=host)

                # Set up directories
                profile_mgr = ProfileManager(
                    runner=runner,
                    home_dir=home_dir,
                    cache_dir=cache_dir,
                    on_progress=on_progress,
                )
                await profile_mgr.create_directories()
                await profile_mgr.check_cache()

                # Install TigerFlow if not present
                tigerflow = TigerFlowClient(
                    runner=runner,
                    home_dir=home_dir,
                    python_path=python_path,
                    on_progress=on_progress,
                )
                _, current_version = await tigerflow.check_version()
                if current_version is None:
                    await tigerflow.setup()

            with yaspin(text=f"Setting up profile on {host}...") as spinner:
                try:
                    asyncio.run(
                        setup_slurm_profile(
                            on_progress=lambda msg: setattr(spinner, "text", msg),
                        )
                    )
                    spinner.ok(f"{LogSymbols.SUCCESS.value}")
                except ProfileSetupError as e:
                    spinner.fail(f"{LogSymbols.ERROR.value}")
                    print(f"  {e.user_message()}")
                    return False
                except TigerFlowError as e:
                    spinner.fail(f"{LogSymbols.ERROR.value}")
                    print(f"  {e.user_message()}")
                    return False
        elif schema == "local":
            home_dir = input(f"> home [{profile['home_dir']}]: ")
            home_dir = profile["home_dir"] if home_dir == "" else home_dir
            cache_dir = input(f"> cache [{profile['cache_dir']}]: ")
            cache_dir = profile["cache_dir"] if cache_dir == "" else cache_dir

            # Set up directories
            runner = LocalRunner()
            with yaspin(text="Setting up local profile...") as spinner:
                try:
                    asyncio.run(
                        _setup_profile_async(
                            runner=runner,
                            home_dir=home_dir,
                            cache_dir=cache_dir,
                            setup_tigerflow=False,
                            on_progress=lambda msg: setattr(spinner, "text", msg),
                        )
                    )
                    spinner.ok(f"{LogSymbols.SUCCESS.value}")
                except ProfileSetupError as e:
                    spinner.fail(f"{LogSymbols.ERROR.value}")
                    print(f"  {e.user_message()}")
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
        if python_path != "python3":
            profiles[name]["python_path"] = python_path
    elif schema == "local":
        profiles[name] = {
            "schema": "local",
            "home_dir": home_dir,
            "cache_dir": cache_dir,
        }
    else:
        raise NotImplementedError

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
        schema = profile.get("schema") or profile.get("type")
        if schema == "slurm":
            print(f"[{name}]")
            print("schema: slurm")
            print(f"host: {profile['host']}")
            print(f"user: {profile['user']}")
            print(f"home: {profile['home_dir']}")
            print(f"cache: {profile['cache_dir']}")
            python_path = profile.get("python_path", "python3")
            print(f"python_path: {python_path}")
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

    for name in profiles:
        profile = profiles[name]
        if profile.name == "DEFAULT":
            continue
        schema = profile.get("schema") or profile.get("type")
        if schema == "slurm":
            print(f"[{name}]")
            print("schema: slurm")
            print(f"host: {profile['host']}")
            print(f"user: {profile['user']}")
            print(f"home: {profile['home_dir']}")
            print(f"cache: {profile['cache_dir']}")
            python_path = profile.get("python_path", "python3")
            print(f"python_path: {python_path}")
        elif schema == "local":
            print(f"[{name}]")
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

    This command does not permit changes to a profile's name or type. If you wish
    to rename a profile, you must delete the profile and then re-create
    it using a new name.
    """

    success = _update_profile_(ctx.obj.get("home_dir"), "default", name)
    if not success:
        ctx.exit(1)


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
        # Note: User canceling deletion is not an error, so no exit(1)
    else:
        print(f"{LogSymbols.ERROR.value} Profile {name} not found.")
        ctx.exit(1)


@click.command()
@click.option(
    "--name", type=str, default="default", help="The name of the profile to upgrade."
)
@click.option(
    "--tigerflow-spec",
    type=str,
    default="tigerflow",
    help="Package spec for tigerflow (e.g., 'tigerflow' or 'git+https://github.com/org/tigerflow@branch').",
)
@click.option(
    "--tigerflow-ml-spec",
    type=str,
    default="tigerflow-ml",
    help="Package spec for tigerflow-ml (e.g., 'tigerflow-ml' or 'git+https://github.com/org/tigerflow-ml@branch').",
)
@click.pass_context
def upgrade_tigerflow(
    ctx: Context,
    name: str,
    tigerflow_spec: str,
    tigerflow_ml_spec: str,
) -> None:  # pragma: no cover
    """Upgrade TigerFlow on a profile.

    This command upgrades tigerflow and tigerflow-ml packages on the
    remote cluster. Use custom package specs to install from git branches
    for testing unreleased features.

    Examples:

        # Upgrade to latest release
        blackfish profile upgrade --name default

        # Install from git branches
        blackfish profile upgrade --name default \\
            --tigerflow-spec "git+https://github.com/princeton-ddss/tigerflow@feature-branch" \\
            --tigerflow-ml-spec "git+https://github.com/princeton-ddss/tigerflow-ml@feature-branch"
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
        print(
            f"{LogSymbols.ERROR.value} TigerFlow is only supported on Slurm profiles."
        )
        ctx.exit(1)

    host = profile["host"]
    user = profile["user"]
    profile_home_dir = profile["home_dir"]
    python_path = profile.get("python_path", "python3")

    runner: SSHRunner | LocalRunner
    if host == "localhost":
        runner = LocalRunner()
    else:
        runner = SSHRunner(user=user, host=host)

    with yaspin(text=f"Upgrading TigerFlow on {host}...") as spinner:
        try:
            tigerflow = TigerFlowClient(
                runner=runner,
                home_dir=profile_home_dir,
                python_path=python_path,
                on_progress=lambda msg: setattr(spinner, "text", msg),
            )
            asyncio.run(
                tigerflow.upgrade(
                    tigerflow_spec=tigerflow_spec,
                    tigerflow_ml_spec=tigerflow_ml_spec,
                )
            )
            spinner.ok(f"{LogSymbols.SUCCESS.value}")
        except TigerFlowError as e:
            spinner.fail(f"{LogSymbols.ERROR.value}")
            print(f"  {e.user_message()}")
            ctx.exit(1)


@click.command()
@click.option(
    "--name", type=str, default="default", help="The name of the profile to repair."
)
@click.option(
    "--tigerflow-spec",
    type=str,
    default="tigerflow",
    help="Package spec for tigerflow (e.g., 'tigerflow' or 'git+https://github.com/org/tigerflow@branch').",
)
@click.option(
    "--tigerflow-ml-spec",
    type=str,
    default="tigerflow-ml",
    help="Package spec for tigerflow-ml (e.g., 'tigerflow-ml' or 'git+https://github.com/org/tigerflow-ml@branch').",
)
@click.pass_context
def repair_profile(
    ctx: Context,
    name: str,
    tigerflow_spec: str,
    tigerflow_ml_spec: str,
) -> None:  # pragma: no cover
    """Repair a Slurm profile.

    Re-runs profile setup to ensure directories exist and TigerFlow is installed.
    Use this when a profile is in a broken state.

    Examples:

        blackfish profile repair --name default

        # Repair with specific TigerFlow version
        blackfish profile repair --name default \\
            --tigerflow-spec "git+https://github.com/princeton-ddss/tigerflow@branch"
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
    python_path = profile.get("python_path", "python3")

    async def do_repair(on_progress: Callable[[str], None] | None = None) -> None:
        runner: SSHRunner | LocalRunner
        if host == "localhost":
            runner = LocalRunner()
        else:
            runner = SSHRunner(user=user, host=host)

        # Set up directories
        profile_mgr = ProfileManager(
            runner=runner,
            home_dir=profile_home_dir,
            cache_dir=cache_dir,
            on_progress=on_progress,
        )
        await profile_mgr.create_directories()
        await profile_mgr.check_cache()

        # Set up TigerFlow
        tigerflow = TigerFlowClient(
            runner=runner,
            home_dir=profile_home_dir,
            python_path=python_path,
            on_progress=on_progress,
        )
        await tigerflow.setup(
            tigerflow_spec=tigerflow_spec,
            tigerflow_ml_spec=tigerflow_ml_spec,
        )

    with yaspin(text=f"Repairing profile on {host}...") as spinner:
        try:
            asyncio.run(do_repair(on_progress=lambda msg: setattr(spinner, "text", msg)))
            spinner.ok(f"{LogSymbols.SUCCESS.value}")
        except ProfileSetupError as e:
            spinner.fail(f"{LogSymbols.ERROR.value}")
            print(f"  {e.user_message()}")
            ctx.exit(1)
        except TigerFlowError as e:
            spinner.fail(f"{LogSymbols.ERROR.value}")
            print(f"  {e.user_message()}")
            ctx.exit(1)
