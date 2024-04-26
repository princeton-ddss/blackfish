import click
import requests

from app.models.nlp.text_generation import (
    TextGeneration,
    TextGenerationModels,
    TextGenerationConfig,
)
from app.config import default_config as app_config


# blackfish run [OPTIONS] text-generation [OPTIONS]
@click.option("--model", default="bloom-560m", help="Model to serve.")
@click.option(
    "--name",
    type=str,
    required=False,
)
@click.option(
    "--revision",
    "-r",
    default=None,
    type=int,
    required=False,
    help="Use a specific model revision (commit id or branch)",
)
@click.option(
    "--quantize",
    "-q",
    default=None,
    type=str,
    required=False,
    help=(
        "Quantize the model. Supported values: awq (4bit), gptq (4-bit), bitsandbytes"
        " (8-bit)."
    ),
)
@click.option(
    "--disable-custom-kernels",
    "-d",
    is_flag=True,
    default=None,
    type=str,
    required=False,
    help="Disable custom CUDA kernels.",
)
@click.option(
    "--max-input-length",
    default=1024,
    type=int,
    required=False,
    help="The maximum allowed input length (in tokens).",
)
@click.option(
    "--max-total-tokens",
    default=2048,
    type=int,
    required=False,
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
    max_input_length,
    max_total_tokens,
    dry_run,
):
    """Start service MODEL."""

    if model not in TextGenerationModels:
        print(
            f"❌ {model} is not a supported model. Supported models:"
            f" {[x for x in TextGenerationModels.keys()]}."
        )
        return

    quantizations = TextGenerationModels[model]["quantizations"]
    if quantize is not None and quantize not in quantizations:
        print(
            f"❌ {quantize} is not supported for model {model}. Supported quantizations:"
            f" {quantizations}."
        )
        return

    user = ctx.obj.get("user", app_config.BLACKFISH_USER)
    host = ctx.obj.get("host", app_config.BLACKFISH_HOST)
    port = ctx.obj.get("port", app_config.BLACKFISH_PORT)

    if (
        ctx.obj["gres"] is not None
        and ctx.obj.get("gres") > 0
        and host == "della.princeton.edu"
    ):
        print(
            "⭐️ della.princeton.edu does not support GPUs. Switching host to"
            " della-gpu.princeton.edu."
        )
        host = "della-gpu.princeton.edu"


    container_kwargs = {"model": model}
    if revision is not None:
        container_kwargs["revision"] = revision
    if disable_custom_kernels is not None:
        container_kwargs["disable_custom_kernels"] = disable_custom_kernels
    if quantize is not None:
        container_kwargs["quantize"] = quantize
    if max_input_length is not None:
        container_kwargs["max_input_length"] = max_input_length
    if max_total_tokens is not None:
        container_kwargs["max_total_tokens"] = max_total_tokens
    container_config = TextGenerationConfig(**container_kwargs)

    job_config = {k: v for k, v in ctx.obj.items() if v is not None}

    if dry_run:
        service = TextGeneration(
            name=name,
            image=container_config.image,
            model=container_config.model,
            host=host,
            port=port,
        )
        click.echo(service.launch_script(container_config, job_config))
    else:
        res = requests.post(
            f"{app_config.BLACKFISH_HOST}:{app_config.BLACKFISH_PORT}/services",
            data={
                "name": name,
                "host": host,
                "port": port,
                "container_config": container_config.as_dict(),
                "job_config": job_config.as_dict(),
            }
        )
        print(res)


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
    #     print(f"Service {service} not found")
