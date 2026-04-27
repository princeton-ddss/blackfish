"""Smoke tests for the service Jinja templates."""

from types import SimpleNamespace

import pytest

from jinja2 import Environment, PackageLoader

from blackfish.server.images import DEFAULT_IMAGES


def _render(template_name: str, **ctx) -> str:
    env = Environment(loader=PackageLoader("blackfish.server", "templates"))
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
