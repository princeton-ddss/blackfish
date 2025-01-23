import os
import rich_click as click
import requests
from random import randint
from yaspin import yaspin
from log_symbols.symbols import LogSymbols
from dataclasses import asdict

from app.services.speech_recognition import SpeechRecognition, SpeechRecognitionConfig
from app.models.profile import serialize_profiles, SlurmProfile
from app.utils import (
    find_port,
    get_models,
    get_revisions,
    get_latest_commit,
    get_model_dir,
)
from app.config import BlackfishConfig
from app.job import JobScheduler, SlurmJobConfig, LocalJobConfig


# blackfish run [OPTIONS] speech-recognition [OPTIONS]
@click.command()
@click.argument(
    "repo_id",
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
    repo_id,
    input_dir,
    name,
    revision,
    dry_run,
):  # pragma: no cover
    """Start a speech recognition service hosting MODEL with access to INPUT_DIR on the service host. MODEL is specified as a repo ID, e.g., openai/whisper-tiny.

    See https://github.com/princeton-ddss/speech-recognition-inference for additional option details.
    """

    config: BlackfishConfig = ctx.obj.get("config")
    profiles = serialize_profiles(config.HOME_DIR)
    profile = next(p for p in profiles if p.name == ctx.obj.get("profile", "default"))

    if repo_id in get_models(profile):
        if revision is None:
            revision = get_latest_commit(repo_id, get_revisions(repo_id, profile))
            model_dir = get_model_dir(repo_id, revision, profile)
            click.echo(
                f"{LogSymbols.WARNING.value} No revision provided. Using latest"
                f" available commit {revision}."
            )
        else:
            model_dir = get_model_dir(repo_id, revision, profile)
            if model_dir is None:
                return

    else:
        click.echo(
            f"{LogSymbols.ERROR.value} Unable to find {repo_id} for profile"
            f" '{profile.name}'."
        )
        return

    if name is None:
        name = f"blackfish-{randint(10_000, 20_000)}"

    if isinstance(profile, SlurmProfile):
        container_config = SpeechRecognitionConfig(
            provider=None,
            port=None,
            model_id=repo_id,
            model_dir=os.path.dirname(model_dir),
            input_dir=input_dir,
            revision=revision,
        )

        job_config = SlurmJobConfig(
            name=name,
            host=profile.host,
            user=profile.user,
            home_dir=profile.home_dir,
            cache_dir=profile.cache_dir,
            **{k: v for k, v in ctx.obj.get("resources").items() if k is not None},
        )

        if dry_run:
            service = SpeechRecognition(
                name=name,
                model=repo_id,
                profile=profile.name,
                host=profile.host,
                user=profile.user,
                home_dir=profile.home_dir,
                cache_dir=profile.cache_dir,
                scheduler=JobScheduler.Slurm,
                mount=container_config.input_dir,
            )
            click.echo("-" * 80)
            click.echo(f"Name: {name}")
            click.echo("Service: speech-recognition")
            click.echo(f"Model: {repo_id}")
            click.echo(f"Profile: {profile.name}")
            click.echo(f"Scheduler: {service.scheduler}")
            click.echo(f"Host: {profile.host}")
            click.echo(f"User: {profile.user}")
            click.echo("-" * 80)
            click.echo(service.render_job_script(container_config, job_config))
        else:
            with yaspin(text="Starting service...") as spinner:
                res = requests.post(
                    f"http://{config.HOST}:{config.PORT}/api/services",
                    json={
                        "name": name,
                        "image": "speech_recognition",
                        "model": repo_id,
                        "profile": profile.name,
                        "host": profile.host,
                        "user": profile.user,
                        "container_options": asdict(container_config),
                        "job_options": asdict(job_config),
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
        container_config = SpeechRecognitionConfig(
            provider=config.CONTAINER_PROVIDER,
            port=find_port(use_stdout=True),
            model_id=repo_id,
            model_dir=os.path.dirname(model_dir),
            input_dir=input_dir,
            revision=revision,
        )

        job_config = LocalJobConfig(
            home_dir=profile.home_dir,
            cache_dir=profile.cache_dir,
            gres=ctx.obj.get("resources").get("gres"),
        )

        if dry_run:
            service = SpeechRecognition(
                name=name,
                model=repo_id,
                profile=profile.name,
                host="localhost",
                mount=container_config.input_dir,
            )
            click.echo("-" * 80)
            click.echo(f"Name: {name}")
            click.echo("Service: speech-recognition")
            click.echo(f"Model: {repo_id}")
            click.echo(f"Profile: {profile.name}")
            click.echo(f"Host: {service.host}")
            click.echo(f"Provider: {container_config.provider}")
            click.echo("-" * 80)
            click.echo(service.render_job_script(container_config, job_config))
        else:
            with yaspin(text="Starting service...") as spinner:
                data = {
                    "name": name,
                    "repo_id": repo_id,
                    "profile": asdict(profile),
                    "container_config": asdict(container_config),
                    "job_config": asdict(job_config),
                    "provider": container_config.provider,
                }
                res = requests.post(
                    # f"http://{config.HOST}:{config.PORT}/api/services",
                    f"http://{config.HOST}:{config.PORT}/api/services/local/speech-recognition",
                    json=data,
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
