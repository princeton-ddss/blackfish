import rich_click as click
import requests
import os
from yaspin import yaspin
from log_symbols.symbols import LogSymbols

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
def init(home_dir: str | None) -> None:  # pragma: no cover
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
def profile(ctx):  # pragma: no cover
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
    from advanced_alchemy.extensions.litestar import AlembicCommands
    from sqlalchemy.exc import OperationalError

    from app import __file__
    from app.asgi import app

    if not os.path.isdir(config.HOME_DIR):
        click.echo("Home directory not found. Have you run `blackfish init`?")
        return

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
    default=None,
    help="The duration to run the service for, e.g., 1:00 (one hour).",
)
@click.option(
    "--ntasks_per_node",
    type=int,
    default=None,
    help="The number of tasks per compute node.",
)
@click.option(
    "--mem",
    type=int,
    default=None,
    help="The memory required per compute node in GB, e.g., 16 (G).",
)
@click.option(
    "--gres",
    type=int,
    default=None,
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
@click.pass_context
def run(
    ctx,
    time,
    ntasks_per_node,
    mem,
    gres,
    partition,
    constraint,
    profile,
):  # pragma: no cover
    """Run an inference service.

    The format of options approximately follows that of Slurm's `sbatch` command.
    """
    ctx.obj = {
        "config": config,
        "profile": profile,
        "time": time,
        "ntasks_per_node": ntasks_per_node,
        "mem": mem,
        "gres": gres,
        "partition": partition,
        "constraint": constraint,
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
def stop(service_id, delay) -> None:  # pragma: no cover
    """Stop one or more services"""

    with yaspin(text="Stopping service...") as spinner:
        res = requests.put(
            f"http://{config.HOST}:{config.PORT}/api/services/{service_id}/stop",
            json={
                "delay": delay,
            },
        )
        spinner.text = ""
        if not res.ok is not None:
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
def rm(service_id, force) -> None:  # pragma: no cover
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
def details(service_id):  # pragma: no cover
    """Show detailed service information"""

    from datetime import datetime
    import json
    from app.services.base import Service

    res = requests.get(
        f"http://{config.HOST}:{config.PORT}/api/services/{service_id}"
    )  # fresh data 🥬

    body = res.json()
    body["created_at"] = datetime.fromisoformat(body["created_at"])
    body["updated_at"] = datetime.fromisoformat(body["updated_at"])
    service = Service(**body)

    if service is not None:
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
                # "remote_port": service.remote_port,
            },
        }
        if service.job_type == "slurm":
            data["job"] = {
                "job_id": job.job_id,
                "host": job.host,
                "user": job.user,
                "node": job.node,
                "port": job.port,
                "name": job.name,
                "state": job.state,
            }
        if service.job_type == "local":
            data["job"] = {
                "job_id": job.job_id,
                "name": job.name,
                "state": job.state,
            }
        else:
            raise NotImplementedError
        click.echo(json.dumps(data))
    else:
        click.echo(f"Service {service} not found.")


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
def ls(filters):  # pragma: no cover
    """List services"""

    from prettytable import PrettyTable, PLAIN_COLUMNS

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
            "MOUNTS",
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
                service["id"],
                service["image"],
                service["model"],
                service["created_at"],  # TODO: format (e.g., 5 min ago)
                service["updated_at"],  # TODO: format (e.g., 5 min ago)
                service["status"],
                service["port"],
                service["name"],
                service["profile"],
                service["mounts"],
            ]
        )
    click.echo(tab)


# # blackfish fetch
# @main.group(name="fetch")
# def fetch():  # pragma: no cover
#     """Fetch results from a service"""
#     pass


# fetch.add_command(fetch_text_generate, "fetch_text_generate")
# fetch.add_command(fetch_speech_recognition, "fetch_speech_recognition")


# blackfish image
# @main.group()
# def image():  # pragma: no cover
#     """View information about available images"""
#     pass


# blackfish image ls [OPTIONS]
# @image.command(name="ls")
# @click.option("--filter", type=str)
# def image_ls(filter):  # pragma: no cover
#     """List images"""
#     pass


# blackfish image details IMAGE
# @image.command(name="details")
# @click.argument("image", type=str, required=True)
# def image_details(image):  # pragma: no cover
#     """Show detailed image information"""
#     pass


@main.group()
def model():  # pragma: no cover
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
def models_ls(profile: str, image: str, refresh: bool):  # pragma: no cover
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
    repo_id: str, profile: str, revision: str | None, use_cache: bool
) -> None:
    """Download a model to make it available.

    Models can only downloaded for local profiles.
    """

    from app.models.model import add_model
    from app.models.profile import serialize_profile, SlurmProfile

    profile = serialize_profile(config.HOME_DIR, profile)
    if isinstance(profile, SlurmProfile):
        if not profile.host == "localhost":
            print(
                f"{LogSymbols.ERROR.value} Sorry—Blackfish can only manage models for"
                " local profiles 😔."
            )
            return

    try:
        model, path = add_model(
            repo_id, profile=profile, revision=revision, use_cache=use_cache
        )
        print(
            f"{LogSymbols.SUCCESS.value} Successfully downloaded model {repo_id} to"
            f" {path}."
        )
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
            },
        )
        spinner.text = ""
        if not res.ok is not None:
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
    repo_id: str, profile: str, revision: str | None, use_cache: bool
) -> None:
    """Remove model files."""

    from app.models.model import remove_model
    from app.models.profile import serialize_profile, SlurmProfile

    profile = serialize_profile(config.HOME_DIR, profile)
    if isinstance(profile, SlurmProfile):
        if not profile.host == "localhost":
            print(
                f"{LogSymbols.ERROR.value} Sorry—Blackfish can only manage models for"
                " local profiles 😔."
            )
            return

    with yaspin(text="Removing model...") as spinner:
        try:
            remove_model(
                repo_id, profile=profile, revision=revision, use_cache=use_cache
            )
            spinner.text = ""
            spinner.ok(f"{LogSymbols.SUCCESS.value} Removed model {repo_id}")
        except Exception as e:
            spinner.text = ""
            spinner.fail(f"{LogSymbols.ERROR.value} Failed to remove model: {e}")


if __name__ == "__main__":
    main()
