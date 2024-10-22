import click
import requests
from random import randint

from app.services.text_generation import TextGeneration
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


# blackfish run [OPTIONS] text-generation [OPTIONS]
@click.command()
@click.option("--model", default="bigscience/bloom-560m", help="Model to serve.")
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
@click.option(
    "--quantize",
    "-q",
    type=str,
    required=False,
    default=None,
    help=(
        "Quantize the model. Supported values: awq (4bit), gptq (4-bit), bitsandbytes"
        " (8-bit)."
    ),
)
@click.option(
    "--disable-custom-kernels",
    is_flag=True,
    required=False,
    default=True,
    help="Disable custom CUDA kernels.",
)
@click.option(
    "--sharded",
    type=str,
    required=False,
    default="true",
    # TODO: help
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
@click.option("--dry-run", is_flag=True, default=False, help="Print Slurm script only.")
@click.pass_context
def run_text_generate(
    ctx,
    model,
    name,
    revision,
    quantize,
    disable_custom_kernels,
    sharded,
    max_input_length,
    max_total_tokens,
    dry_run,
):  # pragma: no cover
    """Start service MODEL."""

    profile = config.BLACKFISH_PROFILES[ctx.obj.get("profile", "default")]

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

    # if model not in TextGenerationModels:
    #     click.echo(
    #         f"{LogSymbols.ERROR.value} {model} is not a supported model. Supported models:"
    #         f" {[x for x in TextGenerationModels.keys()]}."
    #     )
    #     return

    # quantizations = TextGenerationModels[model]["quantizations"]
    # if quantize is not None and quantize not in quantizations:
    #     click.echo(
    #         f"❌ {quantize} is not supported for model {model}. Supported quantizations:"
    #         f" {quantizations}."
    #     )
    #     return

    if name is None:
        name = f"blackfish-{randint(10_000, 20_000)}"

    container_options = {}
    if revision is not None:
        container_options["revision"] = revision
    if disable_custom_kernels is not None:
        container_options["disable_custom_kernels"] = disable_custom_kernels
    if sharded is not None:
        container_options["sharded"] = sharded
    if quantize is not None:
        container_options["quantize"] = quantize
    if max_input_length is not None:
        container_options["max_input_length"] = max_input_length
    if max_total_tokens is not None:
        container_options["max_total_tokens"] = max_total_tokens

    job_options = {k: v for k, v in ctx.obj.items() if v is not None}
    del job_options["profile"]

    if isinstance(profile, SlurmRemote):
        job_options["user"] = profile.user
        job_options["home_dir"] = profile.home_dir
        job_options["cache_dir"] = profile.cache_dir
        job_options["model_dir"] = model_dir

        if dry_run:
            service = TextGeneration(
                name=name,
                model=model,
                job_type="slurm",
                host=profile.host,
                user=profile.user,
            )
            click.echo("-" * 80)
            click.echo("Service: text-generate")
            click.echo(f"Model: {model}")
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
                        "image": "text_generation",
                        "model": model,
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
        container_options["port"] = find_port(use_stdout=True)
        container_options["provider"] = config.BLACKFISH_CONTAINER_PROVIDER
        job_options["home_dir"] = profile.home_dir
        job_options["cache_dir"] = profile.cache_dir
        job_options["model_dir"] = model_dir

        if dry_run:
            service = TextGeneration(
                name=name,
                model=model,
                job_type="local",
                host="localhost",
            )
            click.echo("-" * 80)
            click.echo("Service: text-generate")
            click.echo(f"Model: {model}")
            click.echo(f"Name: {name}")
            click.echo("Type: local")
            click.echo("Host: localhost")
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
                        "image": "text_generation",
                        "model": model,
                        "job_type": "local",
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
    else:
        raise NotImplementedError


# blackfish fetch text-generation [OPTIONS] SERVICE INPUT
# TODO: add help messages
@click.argument("service_id", type=str, required=True)
@click.argument("input", type=str, required=True)
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
    # NEW
    # first, refresh the service data GET /services/:service_id
    # next, directly call the service
    # res = service.call(...)
    # -or-
    # call the service via the API (slow, but the API if definitely connected to the service—the CLI might not be)
    # res = GET /fetch/:service_id
    pass

    # OLD
    # service = fetch_service(session, service_id)
    # if service is not None:
    #     resp = service.call(input, max_new_tokens=max_new_tokens)
    #     click.echo(resp.json())
    # else:
    #     click.echo(f"Service {service} not found")
