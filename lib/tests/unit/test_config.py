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


class TestDebugDefault:
    """Authentication is on unless explicitly disabled (issue #533)."""

    def test_debug_is_off_by_default(self, monkeypatch):
        monkeypatch.delenv("BLACKFISH_DEBUG", raising=False)
        assert _fresh_config().DEBUG is False

    def test_auth_token_generated_when_not_debug(self, monkeypatch):
        monkeypatch.delenv("BLACKFISH_DEBUG", raising=False)
        monkeypatch.delenv("BLACKFISH_AUTH_TOKEN", raising=False)
        assert _fresh_config().AUTH_TOKEN is not None

    @pytest.mark.parametrize("value", ["1", "true", "True", "TRUE", "yes", "on"])
    def test_truthy_spellings_enable_debug(self, monkeypatch, value):
        """`int()` used to raise ValueError on anything but 0/1 — and the docs
        advertised `true` as the default value."""
        monkeypatch.setenv("BLACKFISH_DEBUG", value)
        assert _fresh_config().DEBUG is True

    @pytest.mark.parametrize("value", ["0", "false", "False", "no", "off", ""])
    def test_falsy_spellings_keep_debug_off(self, monkeypatch, value):
        monkeypatch.setenv("BLACKFISH_DEBUG", value)
        assert _fresh_config().DEBUG is False

    def test_debug_mode_has_no_auth_token(self, monkeypatch):
        monkeypatch.setenv("BLACKFISH_DEBUG", "1")
        assert _fresh_config().AUTH_TOKEN is None
