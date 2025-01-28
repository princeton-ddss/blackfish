import os
import rich_click as click
import requests
from random import randint
from yaspin import yaspin
from log_symbols.symbols import LogSymbols
from dataclasses import asdict

from app.services.speech_recognition import SpeechRecognition, SpeechRecognitionConfig
from app.models.profile import BlackfishProfile, SlurmProfile
from app.utils import (
    get_models,
    get_revisions,
    get_latest_commit,
    get_model_dir,
)
from app.config import BlackfishConfig
from app.job import JobScheduler, SlurmJobConfig, LocalJobConfig
from app.cli.classes import ServiceOptions


# blackfish run [OPTIONS] speech-recognition [OPTIONS]
@click.command()
@click.argument(
    "repo_id",
    required=True,
    type=str,
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
    name,
    revision,
    dry_run,
):  # pragma: no cover
    """Start a speech recognition service hosting MODEL. MODEL is specified as a repo ID, e.g., openai/whisper-tiny. The model has access to files via a mounted directory, which defaults to the profile's
    Blackfish home directory (e.g., $HOME/.blackfish). To use a custom directory, users should provide a
    value for the `blackfish run` `MOUNT` option.

    See https://github.com/princeton-ddss/speech-recognition-inference for additional option details.
    """

    config: BlackfishConfig = ctx.obj.get("config")
    profile: BlackfishProfile = ctx.obj.get("profile")
    options: ServiceOptions = ctx.obj.get("options")

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
        name = f"blackfish-{randint(10_000, 99_999)}"

    if options.mount is None:
        options.mount = profile.home_dir

    container_config = SpeechRecognitionConfig(
        model_id=repo_id,
        model_dir=os.path.dirname(model_dir),
        input_dir=options.mount,
        revision=revision,
    )

    if isinstance(profile, SlurmProfile):
        job_config = SlurmJobConfig(
            name=name,
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
                mount=options.mount,
                grace_period=options.grace_period,
            )
            click.echo("\n🚧 Rendering job script for service:\n")
            click.echo(f"> name: {name}")
            click.echo(f"> model: {repo_id}")
            click.echo(f"> profile: {profile.name}")
            click.echo(f"> host: {profile.host}")
            click.echo(f"> user: {profile.user}")
            click.echo(f"> home_dir: {profile.home_dir}")
            click.echo(f"> cache_dir: {profile.cache_dir}")
            click.echo(f"> scheduler: {service.scheduler}")
            click.echo(f"> mount: {options.mount}")
            click.echo(f"> grace_period: {options.grace_period}")
            click.echo("\n👇 Here's the job script 👇\n")
            click.echo(service.render_job_script(container_config, job_config))
        else:
            with yaspin(text="Starting service...") as spinner:
                res = requests.post(
                    f"http://{config.HOST}:{config.PORT}/api/services/slurm/speech-recognition",
                    json={
                        "name": name,
                        "repo_id": repo_id,
                        "profile": asdict(profile),
                        "container_config": asdict(container_config),
                        "job_config": asdict(job_config),
                        "mount": options.mount,
                        "grace_period": options.grace_period,
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
        job_config = LocalJobConfig(
            name=name,
            gres=ctx.obj.get("resources").get("gres"),
        )

        if dry_run:
            service = SpeechRecognition(
                name=name,
                model=repo_id,
                profile=profile.name,
                host="localhost",
                home_dir=profile.home_dir,
                cache_dir=profile.cache_dir,
                provider=config.CONTAINER_PROVIDER,
                mount=options.mount,
                grace_period=options.grace_period,
            )
            click.echo("\n🚧 Rendering job script for service:\n")
            click.echo(f"> name: {name}")
            click.echo(f"> task: {service.image}")
            click.echo(f"> model: {repo_id}")
            click.echo(f"> profile: {profile.name}")
            click.echo(f"> home_dir: {profile.home_dir}")
            click.echo(f"> cache_dir: {profile.cache_dir}")
            click.echo(f"> provider: {config.CONTAINER_PROVIDER}")
            click.echo(f"> mount: {options.mount}")
            click.echo(f"> grace_period: {options.grace_period}")
            click.echo("\n👇 Here's the job script 👇\n")
            click.echo(service.render_job_script(container_config, job_config))
        else:
            with yaspin(text="Starting service...") as spinner:
                res = requests.post(
                    f"http://{config.HOST}:{config.PORT}/api/services/local/speech-recognition",
                    json={
                        "name": name,
                        "repo_id": repo_id,
                        "profile": asdict(profile),
                        "container_config": asdict(container_config),
                        "job_config": asdict(job_config),
                        "provider": config.CONTAINER_PROVIDER,
                        "mount": options.mount,
                        "grace_period": options.grace_period,
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
