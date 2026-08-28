"""Service container image pinnings.

Single source of truth for the images Blackfish renders into job scripts.
Defaults defined here can be overridden at deploy time via env vars
(`BLACKFISH_TEXT_GENERATION_IMAGE`, etc.) — see `BlackfishConfig`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImageSpec:
    """A pinned container image: its repository and tag."""

    repo: str
    tag: str

    @property
    def docker_ref(self) -> str:
        """Reference passed to `docker run` / `docker pull`."""
        return f"{self.repo}:{self.tag}"

    @property
    def sif(self) -> str:
        """Apptainer SIF filename, by Blackfish convention.

        Drops the registry prefix from the repo, then joins name and tag
        with `_`: `vllm/vllm-openai` + `v0.10.2` -> `vllm-openai_v0.10.2.sif`.
        """
        name = self.repo.rsplit("/", 1)[-1]
        return f"{name}_{self.tag}.sif"

    @classmethod
    def parse(cls, ref: str) -> "ImageSpec":
        """Parse a `repo:tag` reference. Raises ValueError if malformed."""
        if ":" not in ref:
            raise ValueError(f"Image reference must be 'repo:tag', got {ref!r}")
        repo, tag = ref.rsplit(":", 1)
        if not repo or not tag:
            raise ValueError(f"Image reference must be 'repo:tag', got {ref!r}")
        return cls(repo=repo, tag=tag)


def resolve_image(image_ref: str | None, default: ImageSpec) -> ImageSpec:
    """The pinned image if one was recorded, else the configured default.

    Services and batch jobs persist the image they launched with (``image_ref``)
    so that restarts reuse it rather than picking up whatever the config
    currently points at.

    Args:
        image_ref: A persisted ``repo:tag`` reference, or None to use the default.
        default: The configured image for this service/task.

    Raises:
        ValueError: If ``image_ref`` is set but malformed.
    """
    return ImageSpec.parse(image_ref) if image_ref else default


DEFAULT_IMAGES: dict[str, ImageSpec] = {
    "text_generation": ImageSpec(repo="vllm/vllm-openai", tag="v0.26.0"),
    "speech_recognition": ImageSpec(
        repo="ghcr.io/princeton-ddss/speech-recognition-inference",
        tag="0.2.1",
    ),
    # Note: the GHCR image tag is "0.2.0" (no leading "v"), unlike the
    # "v0.2.0" GitHub release tag.
    "tigerflow_ml": ImageSpec(
        repo="ghcr.io/princeton-ddss/tigerflow-ml",
        tag="0.2.0",
    ),
}
