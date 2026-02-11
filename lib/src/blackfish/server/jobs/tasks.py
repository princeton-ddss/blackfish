"""Task registry for supported TigerFlow tasks."""

from typing import Any


# Maps task name to tigerflow-ml library module
SUPPORTED_TASKS: dict[str, str] = {
    "transcribe": "tigerflow_ml.transcribe",
    "translate": "tigerflow_ml.translate",
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


def build_pipeline_config(
    task: str,
    input_ext: str | None = None,
    output_ext: str | None = None,
    params: dict[str, Any] | None = None,
    resources: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a TigerFlow pipeline configuration.

    Args:
        task: Task name (e.g., "transcribe")
        input_ext: Input file extension (e.g., ".wav"), optional
        output_ext: Output file extension (e.g., ".json"), optional
        params: Task-specific parameters (e.g., model, language)
        resources: Slurm resources (e.g., cpus, memory, gpus)

    Returns:
        Pipeline configuration dict ready to be written as YAML
    """
    library = get_task_library(task)

    task_config: dict[str, Any] = {
        "name": task,
        "kind": "slurm",
        "library": library,
    }

    if input_ext:
        task_config["input_ext"] = input_ext

    if output_ext:
        task_config["output_ext"] = output_ext

    if params:
        task_config["params"] = params

    if resources:
        task_config["resources"] = resources

    return {"tasks": [task_config]}
