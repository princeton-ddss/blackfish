"""Task registry for supported TigerFlow tasks."""

from typing import Any


# Maps task name to tigerflow-ml library module:class
SUPPORTED_TASKS: dict[str, str] = {
    "detect": "tigerflow_ml.image.detect.slurm:Detect",
    "ocr": "tigerflow_ml.text.ocr.slurm:OCR",
    "transcribe": "tigerflow_ml.audio.slurm:Transcribe",
    "translate": "tigerflow_ml.text.slurm:Translate",
}

# Default input file extensions for each task
DEFAULT_INPUT_EXT: dict[str, str] = {
    "detect": ".jpg",
    "ocr": ".jpg",
    "transcribe": ".wav",
    "translate": ".txt",
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


def build_pipeline_config(
    task: str,
    input_ext: str,
    venv_path: str,
    params: dict[str, Any] | None = None,
    resources: dict[str, Any] | None = None,
    max_workers: int = 1,
) -> dict[str, Any]:
    """Build a TigerFlow pipeline configuration.

    Args:
        task: Task name (e.g., "transcribe")
        input_ext: Input file extension (e.g., ".wav")
        venv_path: Path to venv on cluster (for setup_commands)
        params: Task-specific parameters (e.g., model, language)
        resources: Slurm worker resources (e.g., cpus, memory, gpus)
        max_workers: Maximum number of concurrent Slurm workers

    Returns:
        Pipeline configuration dict ready to be written as YAML
    """
    module = get_task_library(task)

    # Default worker resources if not provided
    worker_resources = resources or {
        "cpus": 4,
        "memory": "32GB",
        "gpus": 1,
        "time": "01:00:00",
    }

    task_config: dict[str, Any] = {
        "name": task,
        "kind": "slurm",
        "module": module,
        "input_ext": input_ext,
        "max_workers": max_workers,
        "worker_resources": worker_resources,
        "setup_commands": [
            f"source {venv_path}/bin/activate",
        ],
    }

    if params:
        task_config["params"] = params

    return {"tasks": [task_config]}
