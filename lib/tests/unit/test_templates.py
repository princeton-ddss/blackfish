"""Smoke tests for the service Jinja templates."""

import shlex
from types import SimpleNamespace

import pytest

from jinja2 import Environment, PackageLoader

from blackfish.server.images import DEFAULT_IMAGES


def _render(template_name: str, **ctx) -> str:
    env = Environment(loader=PackageLoader("blackfish.server", "templates"))
    # Mirrors `Service.render_job_script`, which registers the same filter.
    env.filters["shquote"] = shlex.quote
    return env.get_template(template_name).render(**ctx)


def _ctx(provider: str, image_key: str) -> dict:
    """Minimal render context shared across the four templates."""
    return {
        "uuid": "deadbeef",
        "name": "svc",
        "model": "openai/whisper-large-v3",
        "provider": provider,
        "profile": SimpleNamespace(
            cache_dir="/cache",
            home_dir="/home",
            host="localhost",
            user="alice",
        ),
        "container_config": SimpleNamespace(
            port=8000,
            model_dir="/models",
            revision="main",
            launch_kwargs="",
            api_key=None,
        ),
        "job_config": SimpleNamespace(
            gres=1, ntasks=1, partition="gpu", time="01:00:00"
        ),
        "mount": "/mnt/audio",
        "image": DEFAULT_IMAGES[image_key],
    }


@pytest.mark.parametrize(
    "template,image_key,provider,expected",
    [
        ("text_generation_local.sh", "text_generation", "docker", "docker_ref"),
        ("text_generation_local.sh", "text_generation", "apptainer", "sif"),
        ("text_generation_slurm.sh", "text_generation", "apptainer", "sif"),
        ("speech_recognition_local.sh", "speech_recognition", "docker", "docker_ref"),
        ("speech_recognition_local.sh", "speech_recognition", "apptainer", "sif"),
        ("speech_recognition_slurm.sh", "speech_recognition", "apptainer", "sif"),
    ],
)
def test_template_renders_resolved_image(template, image_key, provider, expected):
    rendered = _render(template, **_ctx(provider, image_key))
    spec = DEFAULT_IMAGES[image_key]

    expected_value = spec.docker_ref if expected == "docker_ref" else spec.sif
    assert expected_value in rendered


# ---------------------------------------------------------------------------
# Batch job templates (tigerflow-ml container)
# ---------------------------------------------------------------------------

CACHE_DIR = "/cache"
INPUT_DIR = "/data/input"
OUTPUT_DIR = "/data/output"
PIPELINE_PATH = "/home/jobs/deadbeef/pipeline.yaml"
IDLE_TIMEOUT = 15


def _batch_ctx(provider: str) -> dict:
    """Render context for the batch_{slurm,local}.sh templates."""
    return {
        "uuid": "deadbeef",
        "name": "batch-job",
        "image": DEFAULT_IMAGES["tigerflow_ml"],
        "provider": provider,
        "profile": SimpleNamespace(
            cache_dir=CACHE_DIR,
            home_dir="/home",
            host="localhost",
            user="alice",
        ),
        "job_config": SimpleNamespace(
            nodes=1,
            ntasks_per_node=4,
            mem=32,
            time="01:00:00",
            gres=1,
            constraint=None,
            partition="gpu",
            account=None,
        ),
        "pipeline_yaml": "tasks:\n- name: transcribe\n",
        "pipeline_path": PIPELINE_PATH,
        "input_dir": INPUT_DIR,
        "output_dir": OUTPUT_DIR,
        "cache_dir": CACHE_DIR,
        "idle_timeout": IDLE_TIMEOUT,
    }


def test_batch_slurm_renders_apptainer_run():
    rendered = _render("batch_slurm.sh", **_batch_ctx("apptainer"))
    sif = DEFAULT_IMAGES["tigerflow_ml"].sif

    # Container invocation
    assert "apptainer run" in rendered
    assert "--env PYTHONNOUSERSITE=1" in rendered
    # Disable vLLM's flashinfer sampler, whose runtime kernel JIT needs a C
    # compiler the tigerflow-ml image doesn't ship (breaks vLLM tasks on GPU).
    assert "--env VLLM_USE_FLASHINFER_SAMPLER=0" in rendered
    assert f"--bind {CACHE_DIR}:/cache" in rendered
    assert f"/images/{sif}" in rendered
    # tigerflow pipeline run and resume behavior
    assert f"run {PIPELINE_PATH} {INPUT_DIR} {OUTPUT_DIR}" in rendered
    assert f"--idle-timeout {IDLE_TIMEOUT}" in rendered
    # sbatch directives from base template; job-name is quoted so names with
    # spaces (e.g. a task display name) don't break sbatch parsing.
    assert '#SBATCH --job-name="batch-job"' in rendered
    assert "#SBATCH --gres=gpu:1" in rendered
    # pipeline YAML written into the script
    assert "tasks:" in rendered


def test_batch_local_renders_docker_run():
    rendered = _render("batch_local.sh", **_batch_ctx("docker"))
    docker_ref = DEFAULT_IMAGES["tigerflow_ml"].docker_ref

    assert "docker run --rm" in rendered
    assert "-e VLLM_USE_FLASHINFER_SAMPLER=0" in rendered
    assert f"-v {CACHE_DIR}:/cache" in rendered
    assert docker_ref in rendered
    assert f"run {PIPELINE_PATH} {INPUT_DIR} {OUTPUT_DIR}" in rendered
    assert f"--idle-timeout {IDLE_TIMEOUT}" in rendered


def test_batch_local_renders_apptainer_run():
    rendered = _render("batch_local.sh", **_batch_ctx("apptainer"))
    sif = DEFAULT_IMAGES["tigerflow_ml"].sif

    assert "apptainer run" in rendered
    assert "--env PYTHONNOUSERSITE=1" in rendered
    assert "--env VLLM_USE_FLASHINFER_SAMPLER=0" in rendered
    assert f"/images/{sif}" in rendered
    assert "docker run" not in rendered


# (template, image_key, provider, flag) — the two images disagree on the flag
# name: vLLM takes --api-key, speech-recognition-inference --auth-token.
API_KEY_TEMPLATES = [
    ("text_generation_slurm.sh", "text_generation", "apptainer", "--api-key"),
    ("text_generation_local.sh", "text_generation", "docker", "--api-key"),
    ("speech_recognition_slurm.sh", "speech_recognition", "apptainer", "--auth-token"),
    ("speech_recognition_local.sh", "speech_recognition", "docker", "--auth-token"),
    ("speech_recognition_local.sh", "speech_recognition", "apptainer", "--auth-token"),
]


@pytest.mark.parametrize("template,image_key,provider,flag", API_KEY_TEMPLATES)
def test_no_auth_flag_when_no_api_key(template, image_key, provider, flag):
    """An unset key emits nothing — not an empty flag."""
    ctx = _ctx(provider, image_key)
    ctx["container_config"].api_key = None

    rendered = _render(template, **ctx)

    assert flag not in rendered


@pytest.mark.parametrize("template,image_key,provider,flag", API_KEY_TEMPLATES)
def test_auth_flag_rendered_when_api_key_set(template, image_key, provider, flag):
    ctx = _ctx(provider, image_key)
    ctx["container_config"].api_key = "sk-secret"

    rendered = _render(template, **ctx)

    assert f"{flag} sk-secret" in rendered


@pytest.mark.parametrize("template,image_key,provider,flag", API_KEY_TEMPLATES)
def test_api_key_is_shell_quoted(template, image_key, provider, flag):
    """The key is interpolated into a script that runs as the user.

    Without quoting, a key containing `;` or a space would execute as shell
    rather than being passed as one argument.
    """
    nasty = "a b;touch /tmp/pwned"
    ctx = _ctx(provider, image_key)
    ctx["container_config"].api_key = nasty

    rendered = _render(template, **ctx)

    assert f"{flag} {shlex.quote(nasty)}" in rendered
    assert f"{flag} {nasty}" not in rendered
