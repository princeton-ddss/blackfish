import rich_click as click
import requests
from random import randint

from app.services.text_generation import TextGeneration
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


# blackfish run [OPTIONS] text-generation [OPTIONS]
@click.command()
@click.argument(
    "model",
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
# @click.option(
#     "--quantize",
#     "-q",
#     type=str,
#     required=False,
#     default=None,
#     help=(
#         "Quantize the model. Supported values: awq (4bit), gptq (4-bit), bitsandbytes"
#         " (8-bit)."
#     ),
# )
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
    model,
    name,
    revision,
    # quantize,
    disable_custom_kernels,
    sharded,
    max_input_length,
    max_total_tokens,
    dry_run,
):  # pragma: no cover
    """Start a text generation service hosting MODEL, where MODEL is specified as a repo ID, e.g., openai/whisper-tiny.

    See https://huggingface.co/docs/text-generation-inference/en/basic_tutorials/launcher for additional option details.
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

    container_options = {"model_dir": model_dir}
    if revision is not None:
        container_options["revision"] = revision
    if disable_custom_kernels is not None:
        container_options["disable_custom_kernels"] = disable_custom_kernels
    if sharded is not None:
        container_options["sharded"] = sharded
    # if quantize is not None:
    #     container_options["quantize"] = quantize
    if max_input_length is not None:
        container_options["max_input_length"] = max_input_length
    if max_total_tokens is not None:
        container_options["max_total_tokens"] = max_total_tokens

    job_options = {k: v for k, v in ctx.obj.items() if v is not None}
    del job_options["profile"]
    del job_options["config"]

    if isinstance(profile, SlurmProfile) and not profile.is_local():
        job_options["user"] = profile.user
        job_options["home_dir"] = profile.home_dir
        job_options["cache_dir"] = profile.cache_dir

        if dry_run:
            service = TextGeneration(
                name=name,
                model=model,
                profile=profile.name,
                job_type="slurm",
                host=profile.host,
                user=profile.user,
            )
            click.echo("-" * 80)
            click.echo(f"Name: {name}")
            click.echo("Service: text-generate")
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
                        "image": "text_generation",
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
            service = TextGeneration(
                name=name,
                model=model,
                profile=profile.name,
                job_type="local" if isinstance(profile, LocalProfile) else "slurm",
                host="localhost",
            )
            click.echo("-" * 80)
            click.echo(f"Name: {name}")
            click.echo("Service: text-generate")
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
                        "image": "text_generation",
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
