"""Tests for the service image registry."""

import pytest

from blackfish.server.images import DEFAULT_IMAGES, ImageSpec


def test_image_spec_docker_ref():
    spec = ImageSpec(repo="vllm/vllm-openai", tag="v0.10.2")
    assert spec.docker_ref == "vllm/vllm-openai:v0.10.2"


def test_image_spec_sif_drops_registry_prefix():
    spec = ImageSpec(
        repo="ghcr.io/princeton-ddss/speech-recognition-inference",
        tag="0.1.2",
    )
    assert spec.sif == "speech-recognition-inference_0.1.2.sif"


def test_image_spec_sif_no_prefix():
    spec = ImageSpec(repo="vllm-openai", tag="v0.10.2")
    assert spec.sif == "vllm-openai_v0.10.2.sif"


def test_image_spec_parse_round_trip():
    spec = ImageSpec.parse("vllm/vllm-openai:v0.10.2")
    assert spec == ImageSpec(repo="vllm/vllm-openai", tag="v0.10.2")


def test_image_spec_parse_with_registry():
    spec = ImageSpec.parse("ghcr.io/princeton-ddss/speech-recognition-inference:0.1.2")
    assert spec.repo == "ghcr.io/princeton-ddss/speech-recognition-inference"
    assert spec.tag == "0.1.2"


@pytest.mark.parametrize("bad", ["no-tag", ":onlytag", "norepo:", ""])
def test_image_spec_parse_rejects_malformed(bad):
    with pytest.raises(ValueError):
        ImageSpec.parse(bad)


def test_default_tigerflow_ml_image():
    """The tigerflow-ml batch-job image is pinned in DEFAULT_IMAGES."""
    spec = DEFAULT_IMAGES["tigerflow_ml"]
    assert spec.repo == "ghcr.io/princeton-ddss/tigerflow-ml"
    assert spec.tag == "0.1.1"
    assert spec.sif == "tigerflow-ml_0.1.1.sif"
    assert spec.docker_ref == "ghcr.io/princeton-ddss/tigerflow-ml:0.1.1"


def test_default_images_covers_all_concrete_services():
    """If a Service subclass exists with a polymorphic identity, it must
    have a pinning. Catches: 'I added a service, forgot the image.'

    ``tigerflow_ml`` is a batch-job image (not a Service), so it is excluded
    from the service-identity comparison.
    """
    from blackfish.server.services.base import Service

    identities = {
        sub.__mapper_args__["polymorphic_identity"]
        for sub in Service.__subclasses__()
        if "polymorphic_identity" in getattr(sub, "__mapper_args__", {})
    }
    service_image_keys = set(DEFAULT_IMAGES.keys()) - {"tigerflow_ml"}
    assert identities == service_image_keys, (
        f"Service identities {identities} do not match "
        f"DEFAULT_IMAGES service keys {service_image_keys}"
    )
