"""Task registry for supported TigerFlow tasks."""

from typing import Any


# Maps task name to the tigerflow-ml module used in the pipeline `module` field.
#
# We use the ``local`` task variants, run in-process inside a single
# containerized Slurm allocation, rather than tigerflow's ``slurm`` variant.
# The ``slurm`` variant's orchestrator/worker tiers shell out to ``sbatch`` from
# whatever process runs them; running that inside the tigerflow-ml container
# requires binding host Slurm libraries/plugins/config (``libslurmfull.so``,
# ``/usr/lib64/slurm``, ``/etc/slurm``, munge), which is site-specific and
# Slurm-version-fragile. The ``local`` variant never sub-submits Slurm jobs, so
# it avoids that entirely; walltime is handled by Blackfish resubmitting the
# allocation until the input directory is fully processed.
SUPPORTED_TASKS: dict[str, str] = {
    "detect": "tigerflow_ml.image.detect.local",
    "ocr": "tigerflow_ml.text.ocr.local",
    "transcribe": "tigerflow_ml.audio.transcribe.local",
    "translate": "tigerflow_ml.text.translate.local",
    "chat": "tigerflow_ml.text.chat.local",
}

# Default input file extensions for each task
DEFAULT_INPUT_EXT: dict[str, str] = {
    "detect": ".jpg",
    "ocr": ".jpg",
    "transcribe": ".wav",
    "translate": ".txt",
    "chat": ".txt",
}

# Default output file extensions for each task
# Tasks not listed here have user-configurable output formats
DEFAULT_OUTPUT_EXT: dict[str, str] = {
    "detect": ".json",  # Object detection always outputs JSON
    "translate": ".txt",  # Translation outputs text files
}


def is_supported_task(task: str) -> bool:
    """Check if a task is supported."""
    return task in SUPPORTED_TASKS


def get_task_library(task: str) -> str:
    """Get the library module for a task.

    Raises:
        ValueError: If task is not supported
    """
    if task not in SUPPORTED_TASKS:
        raise ValueError(
            f"Unsupported task: {task}. Supported tasks: {list(SUPPORTED_TASKS.keys())}"
        )
    return SUPPORTED_TASKS[task]


def get_default_input_ext(task: str) -> str:
    """Get the default input file extension for a task.

    Raises:
        ValueError: If task is not supported
    """
    if task not in DEFAULT_INPUT_EXT:
        raise ValueError(
            f"Unsupported task: {task}. Supported tasks: {list(SUPPORTED_TASKS.keys())}"
        )
    return DEFAULT_INPUT_EXT[task]


def get_default_output_ext(task: str) -> str | None:
    """Get the default output file extension for a task.

    Returns None if the task doesn't have a fixed output format.
    """
    return DEFAULT_OUTPUT_EXT.get(task)


def build_pipeline_config(
    task: str,
    input_ext: str,
    params: dict[str, Any] | None = None,
    output_ext: str | None = None,
) -> dict[str, Any]:
    """Build a TigerFlow pipeline configuration for containerized local execution.

    The pipeline runs the task's ``local`` variant in-process inside the
    tigerflow-ml container. Slurm resources (gpus/cpus/memory/time) are set on
    the enclosing sbatch allocation (the rendered job script), not here.

    The Hugging Face cache is exposed inside the container at ``/cache`` (the
    image sets ``HF_HOME=/cache``), so the model cache is bound there by the job
    script rather than exported in per-task setup commands.

    Args:
        task: Task name (e.g., "transcribe")
        input_ext: Input file extension (e.g., ".wav")
        params: Task-specific parameters (e.g., model, language)
        output_ext: Output file extension (e.g., ".json")

    Returns:
        Pipeline configuration dict ready to be written as YAML
    """
    module = get_task_library(task)

    task_config: dict[str, Any] = {
        "name": task,
        "kind": "local",
        "module": module,
        "input_ext": input_ext,
    }

    if output_ext:
        task_config["output_ext"] = output_ext

    if params:
        task_config["params"] = params

    return {"tasks": [task_config]}
