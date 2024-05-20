import click
import requests
import os
from prettytable import PrettyTable, PLAIN_COLUMNS
import uvicorn

import app
from app.services.base import Service
from app.cli.services.text_generation import run_text_generate, fetch_text_generate
from app.config import config as app_config
from app.config import config, SlurmRemote
from app.setup import make_local_dir, create_or_modify_config


"""
The CLI serves as a client to access the API from as well as performing
administrative tasks, such as adjusting application settings.
"""


# blackfish
@click.group()
def main() -> None:
    "A CLI to manage ML models."
    pass


@main.command()
@click.option("--home_dir", type=str, default=None)
def init(home_dir: str) -> None:
    "Initialize the blackfish service."
    home_dir = home_dir if home_dir is not None else app_config.BLACKFISH_HOME_DIR
    make_local_dir(home_dir)
    create_or_modify_config(home_dir)


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
def start(reload: bool, profile: str) -> None:
    "Start the blackfish app."

    if not os.path.isdir(app_config.BLACKFISH_HOME_DIR):
        click.echo("Home directory not found. Have you run `blackfish init`?")
        return
    if not os.path.isdir(app_config.BLACKFISH_CACHE_DIR):
        click.echo("Cache directory not found. Have you run `blackfish init`?")
        return

    if profile is None:
        # TODO: migrate_db()
        # TODO: update models table
        uvicorn.run(
            "app:app",
            host=app_config.BLACKFISH_HOST,
            port=app_config.BLACKFISH_PORT,
            log_level="info",
            app_dir=os.path.abspath(os.path.join(app.__file__, "..", "..")),
            reload_dirs=os.path.abspath(os.path.join(app.__file__, "..")),
            reload=reload,
        )
        # _ = subprocess.check_output(
        #     [
        #         sys.executable,
        #         "-m",
        #         "uvicorn",
        #         "--host",
        #         app_config.BLACKFISH_HOST,
        #         "--port",
        #         str(app_config.BLACKFISH_PORT),
        #         "--log-level",
        #         "info",
        #         "--reload",
        #         "--app-dir",
        #         os.path.abspath(os.path.join(app.__file__, "..", "..")),
        #         "app:app",
        #     ]
        # )
        # _ = subprocess.check_output(
        #     [
        #         "litestar",
        #         "--app-dir",
        #         os.path.abspath(os.path.join(app.__file__, "..", "..")),
        #         "run",
        #         "--reload"
        #     ]
        # )
    else:
        # TODO: running Blackfish remotely
        profile = config.BLACKFISH_PROFILES[profile]
        if isinstance(profile, SlurmRemote):
            raise NotImplementedError
            # _ = subprocess.check_output(
            #     [
            #         "ssh",
            #         f"{profile['user']}@{profile['host']}",
            #         "uvicorn",
            #         "--port",
            #         profile['port'],
            #         "--log-level",
            #         "info",
            #         "--reload",
            #         reload,
            #     ]
            # )
        else:
            raise NotImplementedError
        raise NotImplementedError


# blackfish run [OPTIONS] COMMAND
@main.group()
@click.option("--time", type=str, default="00:30:00")
@click.option("--ntasks_per_node", type=int, default=None)
@click.option("--mem", type=int, default=None)
@click.option("--gres", type=int, default=None)
@click.option("--partition", type=str, default=None)
@click.option("--constraint", type=str, default=None)
@click.option("--profile", type=str, default="default")
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
):
    """Run an inference service"""
    ctx.obj = {
        "profile": profile,
        "time": time,
        "ntasks_per_node": ntasks_per_node,
        "mem": mem,
        "gres": gres,
        "partition": partition,
        "constraint": constraint,
    }


run.add_command(run_text_generate, "text-generate")


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
def stop(service_id, delay) -> None:
    """Stop one or more services"""

    res = requests.put(
        f"http://{app_config.BLACKFISH_HOST}:{app_config.BLACKFISH_PORT}/services/{service_id}/stop",
        json={
            "delay": delay,
        },
    )

    if not res.ok is not None:
        click.echo(f"Failed to stop service {service_id}.")


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
def rm(service_id, force) -> None:
    """Remove one or more services"""

    res = requests.delete(
        f"http://{app_config.BLACKFISH_HOST}:{app_config.BLACKFISH_PORT}/services/{service_id}"
    )

    if not res.ok is not None:
        click.echo(f"Failed to stop service {service_id}.")
    else:
        click.echo(f"Removed service {service_id}")


# blackfish details [OPTIONS] SERVICE
@main.command()
@click.argument("service_id", required=True, type=str)
def details(service_id):
    """Show detailed service information"""

    res = requests.get(
        f"http://{app_config.BLACKFISH_HOST}:{app_config.BLACKFISH_PORT}/services/{service_id}"
    )  # fresh data 🥬

    service = Service(**res.json())

    if service is not None:
        job = service.get_job()
        data = {
            "image": service.image,
            "model": service.model,
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
        elif service.job_type == "test":
            data["job"] = {}
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
    help="A list of comma-separated filtering criteria, e.g., image=text_generation,status=SUBMITTED",
)
def ls(filters):
    """List services"""

    if filters is not None:
        filters = "/?" + filters.replace(",", "&")
    else:
        filters = ""

    res = requests.get(
        f"http://{app_config.BLACKFISH_HOST}:{app_config.BLACKFISH_PORT}/services{filters}"
    )  # fresh data 🥬

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
        ]
    )
    tab.set_style(PLAIN_COLUMNS)
    tab.align = "l"
    tab.right_padding_width = 3
    for service in res.json():
        ports = (
            f"""localhost:{service["port"]}->{service["host"]}:{service["remote_port"]}"""
            if (
                service.get("port") is not None
                and service.get("remote_port") is not None
                and service.get("host") is not None
            )
            else "None"
        )
        tab.add_row(
            [
                service["id"],
                service["image"],
                service["model"],
                service["created_at"],  # TODO: format (e.g., 5 min ago)
                service["updated_at"],  # TODO: format (e.g., 5 min ago)
                service["status"],
                ports,
                service["name"],
            ]
        )
    click.echo(tab)


# blackfish fetch
@main.group(name="fetch")
def fetch():
    """Fetch results from a service"""
    pass


fetch.add_command(fetch_text_generate, "fetch_text_generate")


# blackfish image
@main.group()
def image():
    """View information about available images"""
    pass


# blackfish image ls [OPTIONS]
@image.command(name="ls")
@click.option("--filter", type=str)
def image_ls(filter):
    """List images"""
    pass


# blackfish image details IMAGE
@image.command(name="details")
@click.argument("image", type=str, required=True)
def image_details(image):
    """Show detailed image information"""
    pass


@main.group()
def models():
    """View information about available models."""
    pass


# blackfish models ls [OPTIONS]
@models.command(name="ls")
@click.option(
    "-p",
    "--profile",
    type=str,
    required=False,
    default="default",
    help="List models available for the given profile.",
)
@click.option(
    "-r",
    "--refresh",
    is_flag=True,
    default=False,
    help="Refresh the list of available models.",
)
def models_ls(profile, refresh):
    """Show available (downloaded) models for a given image and (optional) profile."""
    res = requests.get(
        f"http://{app_config.BLACKFISH_HOST}:{app_config.BLACKFISH_PORT}/models?refresh={refresh}&profile={profile}"
    )
    tab = PrettyTable(
        field_names=[
            "ID",
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
                model["id"],
                model["repo"],
                model["revision"],
                model["profile"],
            ]
        )
    click.echo(tab)


if __name__ == "__main__":
    main()
