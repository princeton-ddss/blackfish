import click
import requests
from random import randint

from app.models.nlp.text_generation import (
    TextGeneration,
    TextGenerationModels,
)
from app.config import config as app_config
from app.config import profiles


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
    is_flag=True,
    required=False,
    default=False,
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
):
    """Start service MODEL."""

    if model not in TextGenerationModels:
        click.echo(
            f"❌ {model} is not a supported model. Supported models:"
            f" {[x for x in TextGenerationModels.keys()]}."
        )
        return

    quantizations = TextGenerationModels[model]["quantizations"]
    if quantize is not None and quantize not in quantizations:
        click.echo(
            f"❌ {quantize} is not supported for model {model}. Supported quantizations:"
            f" {quantizations}."
        )
        return

    profile = profiles[ctx.obj.get("profile", "default")]

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

    if profile["type"] == "slurm":
        if (
            ctx.obj.get("gres") is not None
            and ctx.obj.get("gres") > 0
            and profile["host"] == "della.princeton.edu"
        ):
            click.echo(
                "⭐️ della.princeton.edu does not support GPUs. Switching host to"
                " della-gpu.princeton.edu."
            )
            profile["host"] = "della-gpu.princeton.edu"

        job_options["user"] = profile["user"]
        job_options["home_dir"] = profile["home_dir"]
        job_options["cache_dir"] = profile["cache_dir"]

        if dry_run:
            service = TextGeneration(
                name=name,
                model=model,
                job_type=profile["type"],
                host=profile["host"],
                user=profile["user"],
            )
            click.echo("-" * 80)
            click.echo("Service: text-generate")
            click.echo(f"Model: {model}")
            click.echo(f"Name: {name}")
            click.echo(f"Type: {profile['type']}")
            click.echo(f"Host: {profile['host']}")
            click.echo(f"User: {profile['user']}")
            click.echo("-" * 80)
            click.echo(service.launch_script(container_options, job_options))
        else:
            data = (
                {
                    "name": name,
                    "image": "text_generation",
                    "model": model,
                    "job_type": profile["type"],
                    "host": profile["host"],
                    "user": profile["user"],
                    "container_config": container_options,
                    "job_config": job_options,
                },
            )
            click.echo(data)
            res = requests.post(
                f"http://{app_config.BLACKFISH_HOST}:{app_config.BLACKFISH_PORT}/services",
                json={
                    "name": name,
                    "image": "text_generation",
                    "model": model,
                    "job_type": profile["type"],
                    "host": profile["host"],
                    "user": profile["user"],
                    "container_options": container_options,
                    "job_options": job_options,
                },
            )
            if res.ok:
                click.echo(f"Started service: {res.json()['id']}")
            else:
                click.echo(f"Failed to start service: {res.status_code} - {res.reason}")
    elif profile["type"] == "test":
        if dry_run:
            service = TextGeneration(
                name=name,
                model=model,
                job_type="test",
            )
            click.echo("-" * 80)
            click.echo(f"Service type: {profile['type']}")
            click.echo(f"Name: {name}")
            click.echo(f"Container options: {container_options}")
            click.echo(f"Job options: {job_options}")
            click.echo("-" * 80)
            click.echo(service.launch_script(container_options, job_options))
        else:
            res = requests.post(
                f"http://{app_config.BLACKFISH_HOST}:{app_config.BLACKFISH_PORT}/services",
                json={
                    "name": name,
                    "image": "text_generation",
                    "model": model,
                    "job_type": profile["type"],
                    "container_options": container_options,
                    "job_options": job_options,
                },
            )
            click.echo(f"Started service: {res.json()['id']}")
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
):
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
