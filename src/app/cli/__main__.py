import click
import requests
import os
from yaspin import yaspin
from log_symbols.symbols import LogSymbols

from app.cli.services.text_generation import run_text_generate
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
    default=config.BLACKFISH_HOME_DIR,
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
    """Create or modify a profile."""
    ctx.obj = {"home_dir": config.BLACKFISH_HOME_DIR}


profile.add_command(create_profile, "create")
profile.add_command(show_profile, "show")
profile.add_command(list_profiles, "list")
profile.add_command(update_profile, "update")
profile.add_command(delete_profile, "delete")


@main.command()
@click.option(
    "--reload",
    "-r",
    is_flag=True,
    default=False,
    help="Automatically reload changes to the application",
)
@click.option(
    "--profile",
    type=str,
    default=None,
)
def start(reload: bool, profile: str) -> None:  # pragma: no cover
    "Start the blackfish app."

    import uvicorn
    from advanced_alchemy.extensions.litestar.alembic import AlembicCommands
    from sqlalchemy.exc import OperationalError

    from app import __file__
    from app.asgi import app

    if not os.path.isdir(config.BLACKFISH_HOME_DIR):
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
        # app,
        host=config.BLACKFISH_HOST,
        port=config.BLACKFISH_PORT,
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
    "--profile", type=str, default="default", help="The Blackfish profile to use."
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
    """Run an inference service"""
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


run.add_command(run_text_generate, "text-generate")
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
            f"http://{config.BLACKFISH_HOST}:{config.BLACKFISH_PORT}/services/{service_id}/stop",
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
            f"http://{config.BLACKFISH_HOST}:{config.BLACKFISH_PORT}/services/{service_id}"
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

    from app.services.base import Service

    res = requests.get(
        f"http://{config.BLACKFISH_HOST}:{config.BLACKFISH_PORT}/services/{service_id}"
    )  # fresh data 🥬

    service = Service(**res.json())

    if service is not None:
        job = service.get_job()
        data = {
            "image": service.image,
            "model": service.model,
            "profile": service.profile,
            "created_at": service.created_at,  # .isoformat(),
            "name": service.name,
            "status": {
                "value": service.status,
                "updated_at": service.updated_at,  # .isoformat(),
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
                "host": job.host,  # or service["host"]
                "user": job.user,  # or service["user"]
                "node": job.node,
                "port": job.port,
                "name": job.name,
                "state": job.state,
            }
        else:
            raise NotImplementedError
        click.echo(data)
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
            "PORTS",
            "NAME",
            "PROFILE",
            "MOUNTS",
        ]
    )
    tab.set_style(PLAIN_COLUMNS)
    tab.align = "l"
    tab.right_padding_width = 3

    if filters is not None:
        filters = "/?" + filters.replace(",", "&")
    else:
        filters = ""

    with yaspin(text="Fetching services...") as spinner:
        res = requests.get(
            f"http://{config.BLACKFISH_HOST}:{config.BLACKFISH_PORT}/services{filters}"
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


# blackfish fetch
@main.group(name="fetch")
def fetch():  # pragma: no cover
    """Fetch results from a service"""
    pass


# fetch.add_command(fetch_text_generate, "fetch_text_generate")
# fetch.add_command(fetch_speech_recognition, "fetch_speech_recognition")


# blackfish image
@main.group()
def image():  # pragma: no cover
    """View information about available images"""
    pass


# blackfish image ls [OPTIONS]
@image.command(name="ls")
@click.option("--filter", type=str)
def image_ls(filter):  # pragma: no cover
    """List images"""
    pass


# blackfish image details IMAGE
@image.command(name="details")
@click.argument("image", type=str, required=True)
def image_details(image):  # pragma: no cover
    """Show detailed image information"""
    pass


@main.group()
def models():  # pragma: no cover
    """View information about available models."""
    pass


# blackfish models ls [OPTIONS]
@models.command(name="ls")
@click.option(
    "-p",
    "--profile",
    type=str,
    required=False,
    default=None,
    help="List models available for the given profile.",
)
@click.option(
    "-r",
    "--refresh",
    is_flag=True,
    default=False,
    help="Refresh the list of available models.",
)
def models_ls(profile, refresh):  # pragma: no cover
    """Show available (downloaded) models for a given image and (optional) profile."""

    from prettytable import PrettyTable, PLAIN_COLUMNS

    params = f"refresh={refresh}"
    if profile is not None:
        params += f"&profile={profile}"

    with yaspin(text="Fetching models") as spinner:
        res = requests.get(
            f"http://{config.BLACKFISH_HOST}:{config.BLACKFISH_PORT}/models?{params}"
        )
        spinner.text = ""
        if not res.ok:
            spinner.fail(f"{LogSymbols.ERROR.value} Error: {res.status_code}")
            return

    tab = PrettyTable(
        field_names=[
            "REPO",
            "REVISION",
            "PROFILE",
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
            ]
        )
    click.echo(tab)


if __name__ == "__main__":
    main()
