import os
import rich_click as click
import requests
from random import randint

from app.services.speech_recognition import SpeechRecognition
from app.models.profile import serialize_profiles, SlurmProfile, LocalProfile
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
@click.argument(
    "model",
    required=True,
    type=str,
)
@click.argument(
    "input_dir",
    type=str,
    required=True,
)
@click.option(
    "--name",
    "-n",
    type=str,
    required=False,
    help="Assign a name to the service. A random name is assigned by default.",
)
@click.option(
    "--revision",
    "-r",
    type=str,
    required=False,
    default=None,
    help=(
        "Use a specific model revision. The most recent locally available (i.e.,"
        " downloaded) revision is used by default."
    ),
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the job script but do not run it.",
)
@click.pass_context
def run_speech_recognition(
    ctx,
    model,
    input_dir,
    name,
    revision,
    dry_run,
):  # pragma: no cover
    """Start a speech recognition service hosting MODEL with access to INPUT_DIR on the service host. MODEL is specified as a repo ID, e.g., openai/whisper-tiny.

    See https://github.com/princeton-ddss/speech-recognition-inference for additional option details.
    """

    config = ctx.obj.get("config")
    profiles = serialize_profiles(config.HOME_DIR)
    profile = next(p for p in profiles if p.name == ctx.obj.get("profile", "default"))

    if model in get_models(profile):
        if revision is None:
            revision = get_latest_commit(model, get_revisions(model, profile))
            model_dir = get_model_dir(model, revision, profile)
            click.echo(
                f"{LogSymbols.WARNING.value} No revision provided. Using latest"
                f" available commit {revision}."
            )
        else:
            model_dir = get_model_dir(model, revision, profile)
            if model_dir is None:
                return

    else:
        click.echo(
            f"{LogSymbols.ERROR.value} Unable to find {model} for profile"
            f" '{profile.name}'."
        )
        return

    if name is None:
        name = f"blackfish-{randint(10_000, 20_000)}"

    # Put input_dir and revision in container_options
    container_options = {"model_dir": os.path.dirname(model_dir)}
    if input_dir is None:
        raise Exception("Input directory is required.")
    else:
        container_options["input_dir"] = input_dir
    if revision is not None:
        container_options["revision"] = revision

    job_options = {k: v for k, v in ctx.obj.items() if v is not None}
    del job_options["profile"]
    del job_options["config"]

    if isinstance(profile, SlurmProfile):
        job_options["user"] = profile.user
        job_options["home_dir"] = profile.home_dir
        job_options["cache_dir"] = profile.cache_dir

        if dry_run:
            service = SpeechRecognition(
                name=name,
                model=model,
                profile=profile.name,
                job_type="slurm",
                host=profile.host,
                user=profile.user,
                mounts=container_options["input_dir"],
            )
            click.echo("-" * 80)
            click.echo(f"Name: {name}")
            click.echo("Service: speech-recognition")
            click.echo(f"Model: {model}")
            click.echo(f"Profile: {profile.name}")
            click.echo("Type: slurm")
            click.echo(f"Host: {profile.host}")
            click.echo(f"User: {profile.user}")
            click.echo("-" * 80)
            click.echo(service.launch_script(container_options, job_options))
        else:
            with yaspin(text="Starting service...") as spinner:
                res = requests.post(
                    f"http://{config.HOST}:{config.PORT}/api/services",
                    json={
                        "name": name,
                        "image": "speech_recognition",
                        "model": model,
                        "profile": profile.name,
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
    else:
        container_options["port"] = find_port(use_stdout=True)
        job_options["home_dir"] = profile.home_dir
        job_options["cache_dir"] = profile.cache_dir

        if dry_run:
            service = SpeechRecognition(
                name=name,
                model=model,
                profile=profile.name,
                job_type="local" if isinstance(profile, LocalProfile) else "slurm",
                host="localhost",
                mounts=container_options["input_dir"],
            )
            click.echo("-" * 80)
            click.echo(f"Name: {name}")
            click.echo("Service: speech-recognition")
            click.echo(f"Model: {model}")
            click.echo(f"Profile: {profile.name}")
            click.echo(f"Type: {service.job_type}")
            click.echo("Host: localhost")
            click.echo(f"Provider: {container_options['provider']}")
            click.echo("-" * 80)
            click.echo(
                service.launch_script(container_options, job_options, job_id="test")
            )
        else:
            with yaspin(text="Starting service...") as spinner:
                res = requests.post(
                    f"http://{config.HOST}:{config.PORT}/api/services",
                    json={
                        "name": name,
                        "image": "speech_recognition",
                        "model": model,
                        "profile": profile.name,
                        "job_type": (
                            "local" if isinstance(profile, LocalProfile) else "slurm"
                        ),
                        "host": "localhost",
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
