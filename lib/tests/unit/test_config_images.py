"""Tests for env-var image overrides on BlackfishConfig."""

import pytest


def _fresh_config():
    """Build a BlackfishConfig instance with the current environment."""
    from blackfish.server.config import BlackfishConfig

    return BlackfishConfig()


def test_images_default_when_no_env(monkeypatch):
    monkeypatch.delenv("BLACKFISH_TEXT_GENERATION_IMAGE", raising=False)
    monkeypatch.delenv("BLACKFISH_SPEECH_RECOGNITION_IMAGE", raising=False)

    from blackfish.server.images import DEFAULT_IMAGES

    cfg = _fresh_config()
    assert cfg.IMAGES == DEFAULT_IMAGES


def test_images_env_override_text_generation(monkeypatch):
    monkeypatch.setenv("BLACKFISH_TEXT_GENERATION_IMAGE", "vllm/vllm-openai:v0.9.0")
    monkeypatch.delenv("BLACKFISH_SPEECH_RECOGNITION_IMAGE", raising=False)

    from blackfish.server.images import DEFAULT_IMAGES, ImageSpec

    cfg = _fresh_config()
    assert cfg.IMAGES["text_generation"] == ImageSpec(
        repo="vllm/vllm-openai", tag="v0.9.0"
    )
    assert cfg.IMAGES["speech_recognition"] == DEFAULT_IMAGES["speech_recognition"]


def test_images_env_override_malformed_raises(monkeypatch):
    monkeypatch.setenv("BLACKFISH_TEXT_GENERATION_IMAGE", "no-colon-here")
    with pytest.raises(ValueError):
        _fresh_config()
