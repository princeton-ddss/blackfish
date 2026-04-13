"""CLI commands for batch jobs."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from typing import Any, Optional

import requests
import rich_click as click
from log_symbols.symbols import LogSymbols
from prettytable import PrettyTable, TableStyle
from yaspin import yaspin

import yaml

from blackfish.server.config import config
from blackfish.server.jobs.base import BatchJobStatus
from blackfish.server.jobs.client import VENV_PATH
from blackfish.server.jobs.tasks import (
    SUPPORTED_TASKS,
    build_pipeline_config,
    get_default_input_ext,
    is_supported_task,
)
from blackfish.server.models.profile import deserialize_profile
from blackfish.server.utils import (
    format_datetime,
    get_latest_commit,
    get_model_dir,
    get_models,
    get_revisions,
)


DISPLAY_ID_LENGTH = 13


def _resolve_job_id(partial_id: str) -> str | None:
    """Resolve an abbreviated job ID to a full UUID.

    Args:
        partial_id: The abbreviated ID (or full UUID)

    Returns:
        The full UUID if found, or None if not found/ambiguous
    """
    from uuid import UUID

    # If it's already a full UUID, return it
    try:
        UUID(partial_id)
        return partial_id
    except ValueError:
        pass

    # Query API to find matching jobs
    with yaspin(text="Looking up job...") as spinner:
        try:
            res = requests.get(f"http://{config.HOST}:{config.PORT}/api/jobs")
        except requests.exceptions.ConnectionError:
            spinner.text = f"Failed to connect to Blackfish API on port {config.PORT}."
            spinner.fail(f"{LogSymbols.ERROR.value}")
            return None

        if not res.ok:
            spinner.text = f"Failed to fetch jobs (status={res.status_code})."
            spinner.fail(f"{LogSymbols.ERROR.value}")
            return None

        jobs = res.json()
        matching = [job for job in jobs if job["id"].startswith(partial_id)]

        if len(matching) == 0:
            spinner.text = f"No job found matching '{partial_id}'."
            spinner.fail(f"{LogSymbols.ERROR.value}")
            return None
        elif len(matching) > 1:
            ids = ", ".join([job["id"][:DISPLAY_ID_LENGTH] for job in matching])
            spinner.text = (
                f"Multiple jobs match '{partial_id}': {ids}. "
                "Provide a more specific ID."
            )
            spinner.fail(f"{LogSymbols.ERROR.value}")
            return None
        else:
            full_id: str = str(matching[0]["id"])
            spinner.text = f"Found job {full_id[:DISPLAY_ID_LENGTH]}."
            spinner.ok(f"{LogSymbols.SUCCESS.value}")
            return full_id


@click.command(name="ls")
@click.option(
    "--task",
    "-t",
    type=str,
    default=None,
    help="Filter by task type (e.g., transcribe, translate).",
)
@click.option(
    "--status",
    "-s",
    type=str,
    default=None,
    help="Filter by status (e.g., running, stopped).",
)
@click.option(
    "--profile",
    "-p",
    type=str,
    default=None,
    help="Filter by profile name.",
)
@click.option(
    "--all",
    "-a",
    is_flag=True,
    default=False,
    help="Include all jobs, including stopped ones.",
)
def list_batch_jobs(
    task: Optional[str],
    status: Optional[str],
    profile: Optional[str],
    all: bool = False,
) -> None:  # pragma: no cover
    """List batch jobs."""

    tab = PrettyTable(
        field_names=[
            "JOB ID",
            "TASK",
            "MODEL",
            "CREATED",
            "UPDATED",
            "STATUS",
            "PROGRESS",
            "NAME",
            "PROFILE",
        ]
    )
    tab.set_style(TableStyle.PLAIN_COLUMNS)
    for field in tab.field_names:
        tab.align[field] = "l"
    tab.right_padding_width = 3

    # Build query params
    params: dict[str, str] = {}
    if task:
        params["task"] = task
    if status:
        params["status"] = status
    if profile:
        params["profile"] = profile

    with yaspin(text="Fetching batch jobs...") as spinner:
        try:
            res = requests.get(
                f"http://{config.HOST}:{config.PORT}/api/jobs",
                params=params if params else None,
            )
        except requests.exceptions.ConnectionError:
            spinner.text = (
                f"Failed to connect to Blackfish API on port {config.PORT}. "
                "Is the server running?"
            )
            spinner.fail(f"{LogSymbols.ERROR.value}")
            return

        if not res.ok:
            spinner.text = f"Failed to fetch jobs (status={res.status_code})."
            spinner.fail(f"{LogSymbols.ERROR.value}")
            try:
                detail = res.json().get("detail", res.reason)
                click.echo(f"Error: {detail}")
            except Exception:
                pass
            return

        spinner.ok(f"{LogSymbols.SUCCESS.value}")

    def is_active(job: Any) -> bool:
        job_status = job.get("status")
        return bool(job_status == BatchJobStatus.RUNNING or job_status == "running")

    jobs = res.json()
    for job in jobs:
        if is_active(job) or all:
            staged = job.get("staged") or 0
            finished = job.get("finished") or 0
            errored = job.get("errored") or 0
            total = staged + finished + errored
            progress = f"{finished}/{total}" if total else "N/A"

            job_status = job.get("status")
            tab.add_row(
                [
                    job["id"][:DISPLAY_ID_LENGTH],
                    job.get("task", ""),
                    job.get("repo_id", ""),
                    format_datetime(datetime.fromisoformat(job["created_at"])),
                    format_datetime(datetime.fromisoformat(job["updated_at"])),
                    job_status.upper() if job_status else "NONE",
                    progress,
                    job.get("name", ""),
                    job.get("profile", ""),
                ]
            )

    if len(tab.rows) == 0:
        click.echo("No batch jobs running.")
    else:
        click.echo(tab)


@click.command(name="stop")
@click.argument(
    "job_id",
    type=str,
    required=True,
)
def stop_batch_job(job_id: str) -> None:  # pragma: no cover
    """Stop a batch job.

    JOB_ID can be a full UUID or an abbreviated prefix.
    """

    # Resolve abbreviated ID if needed
    full_job_id = _resolve_job_id(job_id)
    if full_job_id is None:
        return

    with yaspin(text="Stopping batch job...") as spinner:
        try:
            res = requests.put(
                f"http://{config.HOST}:{config.PORT}/api/jobs/{full_job_id}/stop",
                json={},
            )
        except requests.exceptions.ConnectionError:
            spinner.text = (
                f"Failed to connect to Blackfish API on port {config.PORT}. "
                "Is the server running?"
            )
            spinner.fail(f"{LogSymbols.ERROR.value}")
            return

        if not res.ok:
            spinner.text = (
                f"Failed to stop batch job {full_job_id[:DISPLAY_ID_LENGTH]} "
                f"(status={res.status_code})."
            )
            spinner.fail(f"{LogSymbols.ERROR.value}")
            try:
                detail = res.json().get("detail", res.reason)
                click.echo(f"Error: {detail}")
            except Exception:
                pass
        else:
            job_data = res.json()
            status = job_data.get("status", "").lower()
            if status == "broken":
                spinner.text = f"Job {full_job_id[:DISPLAY_ID_LENGTH]} marked as broken due to missing metadata."
                spinner.ok(f"{LogSymbols.WARNING.value}")
            else:
                spinner.text = f"Stopped batch job {full_job_id[:DISPLAY_ID_LENGTH]}."
                spinner.ok(f"{LogSymbols.SUCCESS.value}")


@click.command(name="rm")
@click.argument(
    "job_id",
    type=str,
    required=False,
    default=None,
)
@click.option(
    "--task",
    "-t",
    type=str,
    default=None,
    help="Filter by task type.",
)
@click.option(
    "--status",
    "-s",
    type=str,
    default=None,
    help="Filter by status.",
)
@click.option(
    "--profile",
    "-p",
    type=str,
    default=None,
    help="Filter by profile name.",
)
def remove_batch_job(
    job_id: Optional[str],
    task: Optional[str],
    status: Optional[str],
    profile: Optional[str],
) -> None:
    """Remove batch jobs.

    Provide a JOB_ID to remove a specific job, or use filter options
    to remove multiple jobs matching the criteria.
    """

    # Build query params
    params: dict[str, str] = {}
    if job_id:
        # Resolve abbreviated ID
        full_job_id = _resolve_job_id(job_id)
        if full_job_id is None:
            return
        params["id"] = full_job_id
    if task:
        params["task"] = task
    if status:
        params["status"] = status
    if profile:
        params["profile"] = profile

    if not params:
        click.echo(
            f"{LogSymbols.ERROR.value} Please provide a job ID or filter options."
        )
        sys.exit(1)

    with yaspin(text="Deleting batch jobs...") as spinner:
        try:
            res = requests.delete(
                f"http://{config.HOST}:{config.PORT}/api/jobs",
                params=params,
            )
        except requests.exceptions.ConnectionError:
            spinner.text = (
                f"Failed to connect to Blackfish API on port {config.PORT}. "
                "Is the server running?"
            )
            spinner.fail(f"{LogSymbols.ERROR.value}")
            return

        if not res.ok:
            spinner.text = f"Failed to remove batch jobs (status={res.status_code})."
            spinner.fail(f"{LogSymbols.ERROR.value}")
            try:
                detail = res.json().get("detail", res.reason)
                click.echo(f"Error: {detail}")
            except Exception:
                pass
            return

        data = res.json()
        if len(data) == 0:
            spinner.text = "No batch jobs matched the query."
            spinner.ok(f"{LogSymbols.WARNING.value}")
            return

        oks = [x for x in data if x.get("status") == "ok"]
        errors = [x for x in data if x.get("status") == "error"]

        spinner.text = (
            f"Removed {len(oks)} {'batch job' if len(oks) == 1 else 'batch jobs'}."
        )
        spinner.ok(f"{LogSymbols.SUCCESS.value}")

        if len(errors) > 0:
            click.echo(
                f"{LogSymbols.ERROR.value} Failed to delete "
                f"{len(errors)} {'batch job' if len(errors) == 1 else 'batch jobs'}:"
            )
            for error in errors:
                # API returns 'job_id', not 'id'
                error_id = error.get("job_id", "unknown")[:DISPLAY_ID_LENGTH]
                error_msg = error.get("message", "Unknown error")
                click.echo(f"  - {error_id}: {error_msg}")


@click.command(name="run")
@click.option(
    "--name",
    "-n",
    type=str,
    required=True,
    help="Name for the batch job.",
)
@click.option(
    "--task",
    "-t",
    type=click.Choice(list(SUPPORTED_TASKS.keys())),
    required=True,
    help="ML task to run (e.g., transcribe, translate, detect, ocr).",
)
@click.option(
    "--model",
    "-m",
    type=str,
    required=True,
    help="Model repo ID (e.g., openai/whisper-large-v3).",
)
@click.option(
    "--profile",
    "-p",
    type=str,
    default="default",
    help="Blackfish profile to use.",
)
@click.option(
    "--input-dir",
    "-i",
    type=str,
    required=True,
    help="Input directory containing files to process.",
)
@click.option(
    "--output-dir",
    "-o",
    type=str,
    required=True,
    help="Output directory for results.",
)
@click.option(
    "--revision",
    type=str,
    default=None,
    help="Model revision (commit hash). Uses latest available if not specified.",
)
@click.option(
    "--params",
    type=str,
    default=None,
    help='Task parameters as JSON string (e.g., \'{"language": "en"}\').',
)
@click.option(
    "--resources",
    type=str,
    default=None,
    help='Slurm resource configuration as JSON string (e.g., \'{"gpus": 1, "cpus": 4}\').',
)
@click.option(
    "--max-workers",
    type=int,
    default=1,
    help="Maximum number of concurrent Slurm workers.",
)
@click.option(
    "--input-ext",
    type=str,
    default=None,
    help="Input file extension (e.g., '.wav', '.mp4'). Uses task default if not specified.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the pipeline config without submitting the job.",
)
def run_batch_job(
    name: str,
    task: str,
    model: str,
    profile: str,
    input_dir: str,
    output_dir: str,
    revision: Optional[str],
    params: Optional[str],
    resources: Optional[str],
    max_workers: int,
    input_ext: Optional[str],
    dry_run: bool,
) -> None:
    """Start a batch inference job.

    Batch jobs process files in INPUT_DIR using the specified MODEL and TASK,
    writing results to OUTPUT_DIR. Jobs are managed by TigerFlow on the cluster.
    """

    # 1. Validate profile exists
    matched_profile = deserialize_profile(config.HOME_DIR, profile)
    if matched_profile is None:
        click.echo(
            f"{LogSymbols.ERROR.value} Profile '{profile}' not found. "
            "Use `blackfish profile ls` to view available profiles."
        )
        return

    # 2. Validate model exists for profile
    if model not in get_models(matched_profile):
        click.echo(
            f"{LogSymbols.ERROR.value} Model '{model}' is unavailable for profile "
            f"'{profile}'. Use `blackfish model add` to download it first."
        )
        return

    # 3. Resolve revision (use latest if not provided)
    if revision is None:
        revisions = get_revisions(model, matched_profile)
        if not revisions:
            click.echo(
                f"{LogSymbols.ERROR.value} No revisions found for model '{model}'."
            )
            return
        revision = get_latest_commit(model, revisions)
        click.echo(
            f"{LogSymbols.WARNING.value} No revision provided. "
            f"Using latest available: {revision}"
        )

    # 4. Get model directory and derive cache_dir
    model_dir = get_model_dir(model, revision, matched_profile)
    if model_dir is None:
        click.echo(
            f"{LogSymbols.ERROR.value} Model directory not found. "
            f"The requested revision ({revision}) is missing."
        )
        return
    # cache_dir is the parent of model_dir (e.g., /scratch/.../models)
    cache_dir = os.path.dirname(model_dir)

    # 5. Validate task is supported
    if not is_supported_task(task):
        supported = ", ".join(SUPPORTED_TASKS.keys())
        click.echo(
            f"{LogSymbols.ERROR.value} Unsupported task: '{task}'. "
            f"Supported tasks: {supported}"
        )
        return

    # 6. Parse JSON parameters
    params_dict: dict[str, Any] | None = None
    if params is not None:
        try:
            params_dict = json.loads(params)
        except json.JSONDecodeError as e:
            click.echo(f"{LogSymbols.ERROR.value} Invalid JSON for --params: {e}")
            return

    resources_dict: dict[str, Any] | None = None
    if resources is not None:
        try:
            resources_dict = json.loads(resources)
        except json.JSONDecodeError as e:
            click.echo(f"{LogSymbols.ERROR.value} Invalid JSON for --resources: {e}")
            return

    # Resolve input extension
    resolved_input_ext = input_ext or get_default_input_ext(task)

    # Handle dry-run: print config and exit
    if dry_run:
        # Build the same config that would be sent to TigerFlow
        task_params: dict[str, Any] = {"model": model, "cache_dir": cache_dir}
        if revision:
            task_params["revision"] = revision
        if params_dict:
            task_params.update(params_dict)

        venv_path = f"{matched_profile.home_dir}/{VENV_PATH}"

        pipeline_config = build_pipeline_config(
            task=task,
            input_ext=resolved_input_ext,
            venv_path=venv_path,
            params=task_params,
            resources=resources_dict,
            max_workers=max_workers,
            cache_dir=cache_dir,
        )

        click.echo("Pipeline config (dry run):\n")
        click.echo(
            yaml.dump(pipeline_config, default_flow_style=False, sort_keys=False)
        )
        return

    # Build and submit the job
    with yaspin(text="Starting batch job...") as spinner:
        try:
            res = requests.post(
                f"http://{config.HOST}:{config.PORT}/api/jobs",
                json={
                    "name": name,
                    "task": task,
                    "repo_id": model,
                    "revision": revision,
                    "profile": asdict(matched_profile),
                    "input_dir": input_dir,
                    "output_dir": output_dir,
                    "input_ext": resolved_input_ext,
                    "cache_dir": cache_dir,
                    "params": params_dict,
                    "resources": resources_dict,
                    "max_workers": max_workers,
                },
            )
            if res.ok:
                job_id = res.json().get("id", "unknown")
                spinner.text = f"Started batch job: {job_id[:DISPLAY_ID_LENGTH]}"
                spinner.ok(f"{LogSymbols.SUCCESS.value}")
            else:
                spinner.text = f"Failed to start batch job (status={res.status_code})."
                spinner.fail(f"{LogSymbols.ERROR.value}")
                try:
                    detail = res.json().get("detail", res.reason)
                    click.echo(f"Error: {detail}")
                except Exception:
                    pass
        except requests.exceptions.ConnectionError:
            spinner.text = (
                f"Failed to connect to Blackfish API on port {config.PORT}. "
                "Is the server running?"
            )
            spinner.fail(f"{LogSymbols.ERROR.value}")
