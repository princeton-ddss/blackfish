import rich_click as click
from rich_click import Context
import requests
import os
from yaspin import yaspin
from log_symbols.symbols import LogSymbols
from typing import Optional, cast

from app.cli.services.text_generation import run_text_generation
from app.cli.services.speech_recognition import run_speech_recognition

from app.cli.profile import (
    create_profile,
    show_profile,
    list_profiles,
    update_profile,
    delete_profile,
)
from app.config import config
from app.logger import logger
from app.cli.classes import ServiceOptions


# blackfish
@click.group()
def main() -> None:  # pragma: no cover
    "A CLI to manage ML models."
    pass


@main.command()
@click.option(
    "--home_dir",
    type=str,
    default=config.HOME_DIR,
    help="The location to store Blackfish application data.",
)
def init(home_dir: str) -> None:  # pragma: no cover
    """Setup Blackfish.

    Creates all files and directories to run Blackfish.
    """

    from app.setup import create_local_home_dir
    from app.cli.profile import _create_profile_
    import configparser

    create_local_home_dir(home_dir)

    profiles = configparser.ConfigParser()
    profiles.read(f"{home_dir}/profiles.cfg")
    if "default" not in profiles:
        print("Let's set up a profile:")
        success = _create_profile_(home_dir)
        if success:
            print("🎉 All done—let's fish!")
    else:
        print(f"{LogSymbols.SUCCESS.value} Default profile exists.")
        print("🎉 Looks good—let's fish!")


@main.group()
@click.pass_context
def profile(ctx: Context) -> None:  # pragma: no cover
    """Manage profiles.

        Profiles determine how services are deployed and what assets (i.e., models) are available.
    There are currently two profile types: "slurm" and "local". Slurm profiles look for model files
    and deploy services on a HPC cluster running a Slurm scheduler; local profiles look for
    model files on the same host where the Blackfish API is running and deploy services using without a scheduler.
    """
    ctx.obj = {"home_dir": config.HOME_DIR}


profile.add_command(list_profiles, "ls")
profile.add_command(show_profile, "show")
profile.add_command(create_profile, "add")
profile.add_command(delete_profile, "rm")
profile.add_command(update_profile, "update")


@main.command()
@click.option(
    "--reload",
    "-r",
    is_flag=True,
    default=False,
    help="Automatically reload changes to the application",
)
def start(reload: bool) -> None:  # pragma: no cover
    """Start the blackfish app.

    Application configuration is based on the following local environment variables:

    - BLACKFISH_HOST: the host to run the API on. Default: "localhost".

    - BLACKFISH_PORT: the port to run the API on. Default: 8000.

    - BLACKFISH_HOME_DIR: the location of Blackfish application file. Default: $HOME/.blackfish.

    - BLACKFISH_DEBUG: the debug logger. Default: 1 (true).

    - BLACKFISH_DEV_MODE: run the API without token authentication. Default: 1 (true).

    - BLACKFISH_CONTAINER_PROVIDER: the container management system to use for local
        service deployment. Defaults to Docker, if available, then Apptainer.
    """

    import uvicorn
    from advanced_alchemy.extensions.litestar import (
        AlembicCommands as _AlembicCommands,
        SQLAlchemyInitPlugin,
    )
    from sqlalchemy.exc import OperationalError
    from litestar import Litestar

    from app import __file__
    from app.asgi import app

    if not os.path.isdir(config.HOME_DIR):
        click.echo("Home directory not found. Have you run `blackfish init`?")
        return

    class AlembicCommands(_AlembicCommands):
        def __init__(self, app: Litestar) -> None:
            self._app = app
            self.sqlalchemy_config = self._app.plugins.get(SQLAlchemyInitPlugin)._config  # type: ignore # noqa: SLF001
            self.config = self._get_alembic_command_config()

    alembic_commands = AlembicCommands(app=app)

    try:
        logger.info("Upgrading database...")
        alembic_commands.upgrade()
    except OperationalError as e:
        if e.args == ("(sqlite3.OperationalError) table service already exists",):
            logger.info("Database is already up-to-date. Skipping.")
        else:
            logger.error(f"Failed to upgrade database: {e}")

    uvicorn.run(
        "app.asgi:app",
        host=config.HOST,
        port=config.PORT,
        log_level="info",
        app_dir=os.path.abspath(os.path.join(__file__, "..", "..")),
        reload_dirs=os.path.abspath(os.path.join(__file__, "..")),
        reload=reload,
    )


# blackfish run [OPTIONS] COMMAND
@main.group()
@click.option(
    "--time",
    type=str,
    default="00:30:00",
    help="The duration to run the service for, e.g., 1:00 (one hour).",
)
@click.option(
    "--ntasks_per_node",
    type=int,
    default=8,
    help="The number of tasks per compute node.",
)
@click.option(
    "--mem",
    type=int,
    default=16,
    help="The memory required per compute node in GB, e.g., 16 (G).",
)
@click.option(
    "--gres",
    type=int,
    default=0,
    help="The number of GPU devices required per compute node, e.g., 1.",
)
@click.option(
    "--partition",
    type=str,
    default=None,
    help="The HPC partition to run the service on.",
)
@click.option(
    "--constraint",
    type=str,
    default=None,
    help="Required compute node features, e.g., 'gpu80'.",
)
@click.option(
    "--profile", "-p", type=str, default="default", help="The Blackfish profile to use."
)
@click.option(
    "--mount", "-m", type=str, default=None, help="An optional directory to mount."
)
@click.option(
    "--grace_period",
    "-g",
    type=int,
    default=180,
    help="Time (s) to wait before setting service health to 'unhealthy'.",
)
@click.pass_context
def run(
    ctx: Context,
    time: str,
    ntasks_per_node: int,
    mem: int,
    gres: int,
    partition: Optional[str],
    constraint: Optional[str],
    profile: str,
    mount: Optional[str],
    grace_period: int,
) -> None:  # pragma: no cover
    """Run an inference service.

    The format of options approximately follows that of Slurm's `sbatch` command.
    """

    from app.models.profile import serialize_profile

    ctx.obj = {
        "config": config,
        "profile": serialize_profile(config.HOME_DIR, profile),
        "resources": {
            "time": time,
            "ntasks_per_node": ntasks_per_node,
            "mem": mem,
            "gres": gres,
            "partition": partition,
            "constraint": constraint,
        },
        "options": ServiceOptions(
            mount=mount,
            grace_period=grace_period,
        ),
    }


run.add_command(run_text_generation, "text-generation")
run.add_command(run_speech_recognition, "speech-recognition")


# blackfish stop [OPTIONS] SERVICE [SERVICE...]
@main.command()
@click.option(
    "--delay", type=int, default=0, help="Seconds to wait before stopping the service"
)
@click.argument(
    "service_id",
    type=str,
    required=True,
)
def stop(service_id: str, delay: int) -> None:  # pragma: no cover
    """Stop one or more services"""

    with yaspin(text="Stopping service...") as spinner:
        res = requests.put(
            f"http://{config.HOST}:{config.PORT}/api/services/{service_id}/stop",
            json={
                "delay": delay,
            },
        )
        spinner.text = ""
        if not res.ok:
            spinner.fail(
                f"{LogSymbols.ERROR.value} Failed to stop service {service_id}."
            )
        else:
            spinner.ok(f"{LogSymbols.SUCCESS.value} Stopped service {service_id}")


# blackfish rm [OPTIONS] SERVICE [SERVICE...]
@main.command()
@click.argument(
    "service_id",
    required=True,
    type=str,
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Force the removal of a running service",
)
def rm(service_id: str, force: bool) -> None:  # pragma: no cover
    """Remove one or more services"""

    with yaspin(text="Deleting service...") as spinner:
        res = requests.delete(
            f"http://{config.HOST}:{config.PORT}/api/services/{service_id}"
        )
        spinner.text = ""
        if not res.ok:
            spinner.fail(
                f"{LogSymbols.ERROR.value} Failed to stop service {service_id}."
            )
        else:
            spinner.ok(f"{LogSymbols.SUCCESS.value} Removed service {service_id}")


# blackfish details [OPTIONS] SERVICE
@main.command()
@click.argument("service_id", required=True, type=str)
def details(service_id: str) -> None:  # pragma: no cover
    """Show detailed service information"""

    from datetime import datetime
    import json
    from app.services.base import Service
    from app.job import SlurmJob, LocalJob

    with yaspin(text="Fetching service...") as spinner:
        res = requests.get(
            f"http://{config.HOST}:{config.PORT}/api/services/{service_id}"
        )  # fresh data 🥬
        spinner.text = ""
        if not res.ok:
            spinner.fail(
                f"{LogSymbols.ERROR.value} Failed to fetch service {service_id} (status={res.status_code})."
            )
            return
        else:
            spinner.ok(f"{LogSymbols.SUCCESS.value} Found service {service_id}")

    body = res.json()
    body["created_at"] = datetime.fromisoformat(body["created_at"])
    body["updated_at"] = datetime.fromisoformat(body["updated_at"])
    service = Service(**body)
    job = service.get_job()
    data = {
        "image": service.image,
        "model": service.model,
        "profile": service.profile,
        "created_at": service.created_at.isoformat().replace("+00:00", "Z"),
        "name": service.name,
        "status": {
            "value": service.status,
            "updated_at": service.updated_at.isoformat().replace("+00:00", "Z"),
        },
        "connection": {
            "host": service.host,
            "port": service.port,
        },
    }

    if isinstance(job, SlurmJob):
        data["job"] = {
            "job_id": job.job_id,
            "host": job.host,
            "user": job.user,
            "node": job.node,
            "port": job.port,
            "name": job.name,
            "state": job.state,
        }
    elif isinstance(job, LocalJob):
        data["job"] = {
            "job_id": job.job_id,
            "name": job.name,
            "state": job.state,
        }
    else:
        raise NotImplementedError
    click.echo(json.dumps(data, indent=4))


# blackfish ls [OPTIONS]
@main.command()
@click.option(
    "--filters",
    type=str,
    help=(
        "A list of comma-separated filtering criteria, e.g.,"
        " image=text_generation,status=SUBMITTED"
    ),
)
def ls(filters: Optional[str]) -> None:  # pragma: no cover
    """List services"""

    from prettytable import PrettyTable, PLAIN_COLUMNS
    from datetime import datetime
    from app.utils import format_datetime

    tab = PrettyTable(
        field_names=[
            "SERVICE ID",
            "IMAGE",
            "MODEL",
            "CREATED",
            "UPDATED",
            "STATUS",
            "PORT",
            "NAME",
            "PROFILE",
        ]
    )
    tab.set_style(PLAIN_COLUMNS)
    tab.align = "l"
    tab.right_padding_width = 3

    if filters is not None:
        try:
            params = {k: v for k, v in map(lambda x: x.split("="), filters.split(","))}
        except Exception as e:
            click.echo(f"Unable to parse filter: {e}")
            return
    else:
        params = None

    with yaspin(text="Fetching services...") as spinner:
        res = requests.get(
            f"http://{config.HOST}:{config.PORT}/api/services", params=params
        )  # fresh data 🥬
        spinner.text = ""
        if not res.ok:
            spinner.fail(
                f"{LogSymbols.ERROR.value} Failed to fetch services. Status code:"
                f" {res.status_code}."
            )
            return

    services = res.json()
    for service in services:
        tab.add_row(
            [
                service["id"][:13],
                service["image"],
                service["model"],
                format_datetime(datetime.fromisoformat(service["created_at"])),
                format_datetime(datetime.fromisoformat(service["updated_at"])),
                service["status"].upper() if service["status"] is not None else None,
                service["port"],
                service["name"],
                service["profile"],
            ]
        )
    click.echo(tab)


@main.group()
def model() -> None:  # pragma: no cover
    """View and manage available models."""
    pass


# blackfish models ls [OPTIONS]
@model.command(name="ls")
@click.option(
    "-p",
    "--profile",
    type=str,
    required=False,
    default=None,
    help="List models available for the given profile.",
)
@click.option(
    "-t",
    "--image",
    type=str,
    required=False,
    default=None,
    help="List models available for the given task/image.",
)
@click.option(
    "-r",
    "--refresh",
    is_flag=True,
    default=False,
    help="Refresh the list of available models.",
)
def models_ls(
    profile: Optional[str], image: Optional[str], refresh: bool
) -> None:  # pragma: no cover
    """Show available (downloaded) models."""

    from prettytable import PrettyTable, PLAIN_COLUMNS

    params = f"refresh={refresh}"
    if profile is not None:
        params += f"&profile={profile}"
    if image is not None:
        params += f"&image={image}"

    with yaspin(text="Fetching models") as spinner:
        res = requests.get(f"http://{config.HOST}:{config.PORT}/api/models?{params}")
        spinner.text = ""
        if not res.ok:
            spinner.fail(f"{LogSymbols.ERROR.value} Error: {res.status_code}")
            return

    tab = PrettyTable(
        field_names=[
            "REPO",
            "REVISION",
            "PROFILE",
            "IMAGE",
        ]
    )
    tab.set_style(PLAIN_COLUMNS)
    tab.align = "l"
    tab.right_padding_width = 3
    for model in res.json():
        tab.add_row(
            [
                model["repo"],
                model["revision"],
                model["profile"],
                model["image"],
            ]
        )
    click.echo(tab)


@model.command(name="add")
@click.argument("repo_id", type=str, required=True)
@click.option(
    "-p",
    "--profile",
    type=str,
    required=False,
    default="default",
    help="Add model to the given profile (default: 'default').",
)
@click.option(
    "-r",
    "--revision",
    type=str,
    required=False,
    default=None,
    help=(
        "Add the specified model commit. Use the latest commit if no revision is"
        " provided."
    ),
)
@click.option(
    "-c",
    "--use_cache",
    type=bool,
    is_flag=True,
    default=False,
    help=(
        "Add the model to the profile's cache directory. By default, the model is added"
        " to the profile's home directory."
    ),
)
def models_add(
    repo_id: str, profile: str, revision: Optional[str], use_cache: bool
) -> None:
    """Download a model to make it available.

    Models can only downloaded for local profiles.
    """

    from app.models.model import add_model
    from app.models.profile import serialize_profile, SlurmProfile

    profile_obj = serialize_profile(config.HOME_DIR, profile)
    if profile_obj is None:
        print(f"{LogSymbols.ERROR.value} Failed to load profile 😔.")
        return

    if isinstance(profile_obj, SlurmProfile):
        if not profile_obj.is_local():
            print(
                f"{LogSymbols.ERROR.value} Sorry—Blackfish can only manage models for"
                " local profiles 😔."
            )
            return

    try:
        model_data = add_model(
            repo_id, profile=profile_obj, revision=revision, use_cache=use_cache
        )
        if model_data is not None:
            model, path = model_data
            print(
                f"{LogSymbols.SUCCESS.value} Successfully downloaded model {repo_id} to"
                f" {path}."
            )
        else:
            return None
    except Exception as e:
        print(f"{LogSymbols.ERROR.value} Failed to download model {repo_id}: {e}.")
        return

    with yaspin(text="Inserting model to database...") as spinner:
        res = requests.post(
            f"http://{config.HOST}:{config.PORT}/api/models",
            json={
                "repo": model.repo,
                "profile": model.profile,
                "revision": model.revision,
                "image": model.image,
                "model_dir": path,
            },
        )
        spinner.text = ""
        if not res.ok:
            spinner.fail(
                f"{LogSymbols.ERROR.value} Failed to insert model"
                f" {repo_id} ({res.status_code}: {res.reason})"
            )
        else:
            spinner.ok(f"{LogSymbols.SUCCESS.value} Added model {repo_id}")


@model.command(name="rm")
@click.argument("repo_id", type=str, required=True)
@click.option(
    "-p",
    "--profile",
    type=str,
    required=False,
    default="default",
    help="Remove model from the given profile (default: 'default').",
)
@click.option(
    "-r",
    "--revision",
    type=str,
    required=False,
    default=None,
    help=(
        "Remove the specified model commit. Remove *all* commits if no revision is"
        " provided."
    ),
)
@click.option(
    "-c",
    "--use_cache",
    type=bool,
    is_flag=True,
    default=False,
    help=(
        "Remove the model from the profile's cache directory. By default, the model is"
        " removed from the profile's home directory."
    ),
)
def models_remove(
    repo_id: str, profile: str, revision: Optional[str], use_cache: bool
) -> None:
    """Remove model files."""

    from app.models.model import remove_model
    from app.models.profile import serialize_profile, SlurmProfile

    profile_obj = serialize_profile(config.HOME_DIR, profile)
    if profile_obj is None:
        print(f"{LogSymbols.ERROR.value} Failed to serialize profile 😔.")
        return

    if isinstance(profile_obj, SlurmProfile):
        if not profile_obj.is_local():
            print(
                f"{LogSymbols.ERROR.value} Sorry—Blackfish can only manage models for"
                " local profiles 😔."
            )
            return

    with yaspin(text="Removing model...") as spinner:
        try:
            remove_model(
                repo_id, profile=profile_obj, revision=revision, use_cache=use_cache
            )
            spinner.text = ""
            spinner.ok(f"{LogSymbols.SUCCESS.value} Removed model {repo_id}")
        except Exception as e:
            spinner.text = ""
            spinner.fail(f"{LogSymbols.ERROR.value} Failed to remove model: {e}")


@main.group()
def database() -> None:  # pragma: no cover
    """View and manage available models."""
    pass


@database.command(
    name="make-migrations",
    help="Create a new migration revision.",
)
@click.option("-m", "--message", default=None, help="Revision message")
@click.option(
    "--autogenerate/--no-autogenerate",
    default=True,
    help="Automatically populate revision with detected changes",
)
@click.option(
    "--sql",
    is_flag=True,
    default=False,
    help="Export to `.sql` instead of writing to the database.",
)
@click.option(
    "--head",
    default="head",
    help="Specify head revision to use as base for new revision.",
)
@click.option(
    "--splice",
    is_flag=True,
    default=False,
    help='Allow a non-head revision as the "head" to splice onto',
)
@click.option(
    "--branch-label",
    default=None,
    help="Specify a branch label to apply to the new revision",
)
@click.option(
    "--version-path",
    default=None,
    help="Specify specific path from config for version file",
)
@click.option("--rev-id", default=None, help="Specify a ID to use for revision.")
@click.option(
    "--no-prompt",
    help="Do not prompt for confirmation before executing the command.",
    type=bool,
    default=False,
    required=False,
    show_default=True,
    is_flag=True,
)
def create_revision(
    message: str | None,
    autogenerate: bool,
    sql: bool,
    head: str,
    splice: bool,
    branch_label: str | None,
    version_path: str | None,
    rev_id: str | None,
    no_prompt: bool,
) -> None:
    """Create a new database revision. Copied from advanced_alchemy CLI."""
    from rich.prompt import Prompt
    from rich import get_console

    from advanced_alchemy.extensions.litestar import (
        AlembicCommands as _AlembicCommands,
        SQLAlchemyInitPlugin,
    )
    from alembic.migration import MigrationContext
    from alembic.operations.ops import MigrationScript, UpgradeOps
    from litestar import Litestar

    from app.asgi import app

    class AlembicCommands(_AlembicCommands):
        def __init__(self, app: Litestar) -> None:
            self._app = app
            self.sqlalchemy_config = self._app.plugins.get(SQLAlchemyInitPlugin)._config  # type: ignore # noqa: SLF001
            self.config = self._get_alembic_command_config()

    alembic_commands = AlembicCommands(app=app)

    console = get_console()

    def process_revision_directives(
        context: MigrationContext,  # noqa: ARG001
        revision: tuple[str],  # noqa: ARG001
        directives: list[MigrationScript],
    ) -> None:
        """Handle revision directives."""
        if autogenerate and cast("UpgradeOps", directives[0].upgrade_ops).is_empty():
            console.rule(
                "[magenta]The generation of a migration file is being skipped because it would result in an empty file.",
                style="magenta",
                align="left",
            )
            console.rule(
                "[magenta]More information can be found here. https://alembic.sqlalchemy.org/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect",
                style="magenta",
                align="left",
            )
            console.rule(
                "[magenta]If you intend to create an empty migration file, use the --no-autogenerate option.",
                style="magenta",
                align="left",
            )
            directives.clear()

    console.rule("[yellow]Starting database upgrade process[/]", align="left")
    if message is None:
        message = (
            "autogenerated"
            if no_prompt
            else Prompt.ask("Please enter a message describing this revision")
        )

    alembic_commands.revision(
        message=message,
        autogenerate=autogenerate,
        sql=sql,
        head=head,
        splice=splice,
        branch_label=branch_label,
        version_path=version_path,
        rev_id=rev_id,
        process_revision_directives=process_revision_directives,  # type: ignore[arg-type]
    )


if __name__ == "__main__":
    main()
