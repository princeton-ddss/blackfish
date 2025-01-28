from typing import Optional, Tuple
import rich_click as click
import requests
from random import randint
from yaspin import yaspin
from log_symbols.symbols import LogSymbols
from dataclasses import asdict

from app.services.text_generation import TextGeneration, TextGenerationConfig
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


def try_get_model_info(
    profile: BlackfishProfile, repo_id: str, revision: Optional[str] = None
) -> Optional[Tuple[str, str]]:
    if repo_id in get_models(profile):
        if revision is None:
            revision = get_latest_commit(repo_id, get_revisions(repo_id, profile))
            click.echo(
                f"{LogSymbols.WARNING.value} No revision provided. Using latest"
                f" available commit {revision}."
            )

        model_dir = get_model_dir(repo_id, revision, profile)
        if model_dir is None:
            click.echo(
                f"{LogSymbols.ERROR.value} The model directory for repo  {repo_id}[{revision}] could not be found for profile"
                f" '{profile.name}'. These files may have been moved or there may be a issue with permissions. You can try adding the model using `blackfish model add`."
            )
            return
    else:
        click.echo(
            f"{LogSymbols.ERROR.value} Model {repo_id} is unavailable for profile"
            f" '{profile.name}'. You can try adding it using `blackfish model add`."
        )
        return

    return model_dir, revision


def build_service(
    name: str,
    repo_id: str,
    profile: BlackfishProfile,
    container_config: TextGenerationConfig,
    job_config: JobConfig,
) -> TextGeneration:
    service = TextGeneration(
        name=name,
        model=repo_id,
        profile=profile.name,
        host="localhost",
    )

    click.echo("-" * 80)
    click.echo(f"Name: {name}")
    click.echo("Service: text-generation")
    click.echo(f"Model: {repo_id}")
    click.echo(f"Profile: {profile.name}")
    click.echo("Host: localhost")
    click.echo(f"Provider: {container_config.provider}")
    click.echo("-" * 80)
    click.echo(service.render_job_script(container_config, job_config))

    return service


# blackfish run [OPTIONS] text-generation [OPTIONS]
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
    "--disable-custom-kernels",
    is_flag=True,
    required=False,
    default=True,
    help=(
        "Disable custom CUDA kernels. Custom CUDA kernels are not guaranteed to run on"
        " all devices, but will run faster if they do."
    ),
)
@click.option(
    "--sharded",
    type=str,
    required=False,
    default=None,
    help=(
        "Shard the model across multiple GPUs. The API uses all available GPUs by"
        " default. Setting to 'true' with a single GPU results in an error."
    ),
)
@click.option(
    "--max-input-length",
    type=int,
    required=False,
    default=None,  # 1024,
    help="The maximum allowed input length (in tokens).",
)
@click.option(
    "--max-total-tokens",
    type=int,
    required=False,
    default=None,  # 2048,
    help="The maximum allowed total length of input and output (in tokens).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the job script but do not run it.",
)
@click.pass_context
def run_text_generation(
    ctx,
    repo_id,
    name,
    revision,
    disable_custom_kernels,
    sharded,
    max_input_length,
    max_total_tokens,
    dry_run,
):  # pragma: no cover
    """Start a text generation service hosting a model provided by REPO_ID, e.g., openai/whisper-tiny.

    See https://huggingface.co/docs/text-generation-inference/en/basic_tutorials/launcher for additional option details.
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

    container_config = TextGenerationConfig(
        model_dir=model_dir,
        revision=revision,
        sharded=sharded,
        max_input_length=max_input_length,
        max_total_tokens=max_total_tokens,
        disable_custom_kernels=disable_custom_kernels,
    )

    if isinstance(profile, SlurmProfile):
        job_config = SlurmJobConfig(
            name=name,
            **{k: v for k, v in ctx.obj.get("resources").items() if k is not None},
        )

        if dry_run:
            service = TextGeneration(
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
                    f"http://{config.HOST}:{config.PORT}/api/services/slurm/text-generation",
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
            service = TextGeneration(
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
                    f"http://{config.HOST}:{config.PORT}/api/services/local/text-generation",
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


# blackfish fetch text-generation [OPTIONS] SERVICE INPUT
@click.argument("service_id", type=str, required=True)
@click.argument("inputs", type=str, required=True)
@click.option("--best_of", type=int, default=None)
@click.option("--decoder_input_details", type=bool, default=True)
@click.option("--details", type=bool, default=True)
@click.option("--do_sample", type=bool, default=False)
@click.option("--max_new_tokens", type=int, default=None)
@click.option("--repetition_penalty", type=float, default=1.03)
@click.option("--return_full_text", type=bool, default=False)
@click.option("--seed", type=int, default=None)
@click.option("--stop", type=list, default=[])
@click.option("--temperature", type=float, default=None)
@click.option("--top_k", type=int, default=None)
@click.option("--top_n_tokens", type=int, default=None)
@click.option("--top_p", type=float, default=None)
@click.option("--truncate", type=int, default=None)
@click.option("--typical_p", type=float, default=None)
@click.option("--watermark", type=bool, default=False)
def fetch_text_generate(
    service_id,
    input,
    best_of,
    decoder_input_details,
    details,
    do_sample,
    max_new_tokens,
    repetition_penalty,
    return_full_text,
    seed,
    stop,
    temperature,
    top_k,
    top_n_tokens,
    top_p,
    truncate,
    typical_p,
    watermark,
):  # pragma: no cover
    """Fetch results from a text-generation service"""
    raise NotImplementedError
