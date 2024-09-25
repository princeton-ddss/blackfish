import os
import click
import requests
from random import randint

from app.services.speech_recognition import SpeechRecognition
from app.config import config, SlurmRemote, LocalProfile
from app.utils import (
    find_port,
    get_models,
    get_revisions,
    get_latest_commit,
    get_model_dir,
)
from yaspin import yaspin
from log_symbols.symbols import LogSymbols


# blackfish run [OPTIONS] speech-recognition [OPTIONS]
@click.command()
@click.option(
    "--model_id", required=False, default="openai/whisper-large-v3",
    help="Model to serve."
)
@click.option(
    "--input_dir",
    type=str,
    required=True,
)
@click.option(
    "--name",
    type=str,
    required=False,
)
@click.option(
    "--revision",
    "-r",
    type=str,
    required=False,
    default=None,
    help="Use a specific model revision (commit id or branch)",
)
@click.option("--dry-run", is_flag=True, default=False, help="Print Slurm script only.")
@click.pass_context
def run_speech_recognition(
    ctx,
    model_id,
    input_dir,
    name,
    revision,
    dry_run,
):  # pragma: no cover
    """Start service MODEL."""

    profile = config.BLACKFISH_PROFILES[ctx.obj.get("profile", "default")]

    if model_id in get_models(profile):
        if revision is None:
            revision = get_latest_commit(model_id, get_revisions(model_id,
                                                                profile))
            model_dir = get_model_dir(model_id, revision, profile)
            click.echo(
                f"{LogSymbols.WARNING.value} No revision provided. Using latest"
                f" available commit {revision}."
            )
        else:
            model_dir = get_model_dir(model_id, revision, profile)
            if model_dir is None:
                return

    else:
        click.echo(
            f"{LogSymbols.ERROR.value} Unable to find {model_id} for profile"
            f" '{profile.name}'."
        )
        return

    if name is None:
        name = f"blackfish-{randint(10_000, 20_000)}"

    # Put input_dir and revision in container_options
    container_options = {}

    if input_dir is None:
        raise Exception("Input Directory is Missing")
    else:
        container_options["input_dir"] = input_dir

    if revision is not None:
        container_options["revision"] = revision

    container_options["model_dir"] = os.path.dirname(model_dir)

    container_options["model_id"] = model_id

    job_options = {k: v for k, v in ctx.obj.items() if v is not None}
    del job_options["profile"]

    if isinstance(profile, SlurmRemote):
        job_options["user"] = profile.user
        job_options["home_dir"] = profile.home_dir
        job_options["cache_dir"] = profile.cache_dir
        job_options["model_dir"] = model_dir

        if dry_run:
            service = SpeechRecognition(
                name=name,
                model=model_id,
                job_type="slurm",
                host=profile.host,
                user=profile.user,
            )
            click.echo("-" * 80)
            click.echo("Service: speech-recognition")
            click.echo(f"Model: {model_id}")
            click.echo(f"Name: {name}")
            click.echo("Type: slurm")
            click.echo(f"Host: {profile.host}")
            click.echo(f"User: {profile.user}")
            click.echo("-" * 80)
            click.echo(service.launch_script(container_options, job_options))
        else:
            with yaspin(text="Starting service...") as spinner:
                res = requests.post(
                    f"http://{config.BLACKFISH_HOST}:{config.BLACKFISH_PORT}/services",
                    json={
                        "name": name,
                        "image": "speech_recognition",
                        "model": model_id,
                        "job_type": "slurm",
                        "host": profile.host,
                        "user": profile.user,
                        "container_options": container_options,
                        "job_options": job_options,
                    },
                )
                spinner.text = ""
                if res.ok:
                    spinner.ok(
                        f"{LogSymbols.SUCCESS.value} Started service:"
                        f" {res.json()['id']}"
                    )
                else:
                    spinner.fail(
                        f"{LogSymbols.ERROR.value} Failed to start service:"
                        f" {res.status_code} - {res.reason}"
                    )
    elif isinstance(profile, LocalProfile):
        container_options["port"] = find_port()
        container_options["provider"] = config.BLACKFISH_CONTAINER_PROVIDER
        job_options["user"] = profile.user
        job_options["home_dir"] = profile.home_dir
        job_options["cache_dir"] = profile.cache_dir
        job_options["model_dir"] = model_dir

        if dry_run:
            service = SpeechRecognition(
                name=name,
                model=model_id,
                job_type="local",
                host="localhost",
                user=profile.user,
            )
            click.echo("-" * 80)
            click.echo("Service: speech-recognition")
            click.echo(f"Model: {model_id}")
            click.echo(f"Name: {name}")
            click.echo("Type: local")
            click.echo("Host: localhost")
            click.echo(f"User: {profile.user}")
            click.echo(f"Provider: {container_options['provider']}")
            click.echo("-" * 80)
            click.echo(
                service.launch_script(container_options, job_options, job_id="test")
            )
        else:
            with yaspin(text="Starting service...") as spinner:
                res = requests.post(
                    f"http://{config.BLACKFISH_HOST}:{config.BLACKFISH_PORT}/services",
                    json={
                        "name": name,
                        "image": "speech_recognition",
                        "model": model_id,
                        "job_type": "local",
                        "host": "localhost",
                        "user": profile.user,
                        "container_options": container_options,
                        "job_options": job_options,
                    },
                )
                spinner.text = ""
                if res.ok:
                    spinner.ok(
                        f"{LogSymbols.SUCCESS.value} Started service:"
                        f" {res.json()['id']}"
                    )
                else:
                    spinner.fail(
                        f"{LogSymbols.ERROR.value} Failed to start service:"
                        f" {res.status_code} - {res.reason}"
                    )
    else:
        raise NotImplementedError
