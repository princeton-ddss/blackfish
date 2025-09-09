from __future__ import annotations

import os
from typing import Optional
import rich_click as click
from rich_click import Context
import requests
from random import randint
from yaspin import yaspin
from log_symbols.symbols import LogSymbols
from dataclasses import asdict

from app.jobs.speech_recognition import (
    SpeechRecognitionBatch,
    SpeechRecognitionBatchConfig,
)
from app.models.profile import BlackfishProfile, SlurmProfile
from app.utils import (
    get_models,
    get_revisions,
    get_latest_commit,
    get_model_dir,
)
from app.config import BlackfishConfig
from app.job import JobScheduler, JobConfig, SlurmJobConfig, LocalJobConfig
from app.cli.classes import ServiceOptions


# blackfish batch [OPTIONS] speech-recognition [OPTIONS]
@click.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
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
    help="Assign a name to the batch job. A random name is assigned by default.",
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
    ctx: Context,
    name: Optional[str],
    repo_id: str,
    revision: Optional[str],
    dry_run: bool,
) -> None:  # pragma: no cover
    """Start a speech recognition batch job running REPO_ID. The format of REPO_ID is "<org>/<model>", e.g., openai/whisper-tiny. The job has access to files via a mounted directory that defaults to the profile's Blackfish home directory (e.g., $HOME/.blackfish). To use a custom directory, users should provide a value for the `blackfish run` `MOUNT` option.

    See https://github.com/princeton-ddss/speech-recognition-inference for additional option details.
    """

    from uuid import uuid4

    config: BlackfishConfig = ctx.obj.get("config")
    profile: BlackfishProfile | None = ctx.obj.get("profile")
    options: ServiceOptions = ctx.obj.get("options")

    if profile is None:
        click.echo(
            f"{LogSymbols.ERROR.value} Profile not found 😔. To view a list of available profiles, use `blackfish profile ls`."
        )
        return

    if repo_id in get_models(profile):
        if revision is None:
            revision = get_latest_commit(repo_id, get_revisions(repo_id, profile))
            click.echo(
                f"{LogSymbols.WARNING.value} No revision provided. Using latest"
                f" available commit: {revision}."
            )
            model_dir = get_model_dir(repo_id, revision, profile)
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
        print(f"{LogSymbols.ERROR.value} Mount option is required for batch inference.")
        return

    container_config = SpeechRecognitionBatchConfig(
        model_dir=os.path.dirname(model_dir),  # type: ignore
        revision=revision,
        kwargs=ctx.args,
    )

    job_config: JobConfig

    if isinstance(profile, SlurmProfile):
        job_config = SlurmJobConfig(
            name=name,
            **{k: v for k, v in ctx.obj.get("resources").items() if k is not None},
        )

        if dry_run:
            job = SpeechRecognitionBatch(
                id=uuid4(),
                name=name,
                repo_id=repo_id,
                profile=profile.name,
                scheduler=JobScheduler.Slurm,
                mount=options.mount,
            )
            click.echo("\n🚧 Rendering job script for job:\n")
            click.echo(f"> name: {name}")
            click.echo(f"> repo_id: {repo_id}")
            click.echo(f"> profile: {profile.name}")
            click.echo(f"> scheduler: {job.scheduler}")
            click.echo(f"> mount: {options.mount}")
            click.echo("\n👇 Here's the job script 👇\n")
            click.echo(job.render_job_script(config, job_config, container_config))
        else:
            with yaspin(text="Starting batch job...") as spinner:
                res = requests.post(
                    f"http://{config.HOST}:{config.PORT}/api/jobs",
                    json={
                        "name": name,
                        "pipeline": "speech_recognition",
                        "repo_id": repo_id,
                        "profile": asdict(profile),
                        "container_config": asdict(container_config),
                        "job_config": asdict(job_config),
                        "mount": options.mount,
                    },
                )
                if res.ok:
                    spinner.text = f"Started batch job: {res.json()['id']}"
                    spinner.ok(f"{LogSymbols.SUCCESS.value}")
                else:
                    spinner.text = (
                        f"Failed to start batch job: {res.status_code} - {res.reason}"
                    )
                    spinner.fail(f"{LogSymbols.ERROR.value}")
    else:
        job_config = LocalJobConfig(
            gres=ctx.obj.get("resources").get("gres"),
        )

        if dry_run:
            job = SpeechRecognitionBatch(
                id=uuid4(),
                name=name,
                repo_id=repo_id,
                profile=profile.name,
                provider=config.CONTAINER_PROVIDER,
                mount=options.mount,
            )
            click.echo("\n🚧 Rendering job script for batch job:\n")
            click.echo(f"> name: {name}")
            click.echo(f"> pipeline: {job.pipeline}")
            click.echo(f"> repo_id: {repo_id}")
            click.echo(f"> profile: {profile.name}")
            click.echo(f"> provider: {config.CONTAINER_PROVIDER}")
            click.echo(f"> mount: {options.mount}")
            click.echo("\n👇 Here's the job script 👇\n")
            click.echo(job.render_job_script(config, job_config, container_config))
        else:
            with yaspin(text="Starting batch job...") as spinner:
                res = requests.post(
                    f"http://{config.HOST}:{config.PORT}/api/jobs",
                    json={
                        "name": name,
                        "pipeline": "speech_recognition",
                        "repo_id": repo_id,
                        "profile": asdict(profile),
                        "job_config": asdict(job_config),
                        "container_config": asdict(container_config),
                        "mount": options.mount,
                    },
                )
                if res.ok:
                    spinner.text = f"Started batch job: {res.json()['id']}"
                    spinner.ok(f"{LogSymbols.SUCCESS.value}")
                else:
                    spinner.text = (
                        f"Failed to start batch job: {res.status_code} - {res.reason}"
                    )
                    spinner.fail(f"{LogSymbols.ERROR.value}")
