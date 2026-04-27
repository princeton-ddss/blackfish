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


DEFAULT_IMAGES: dict[str, ImageSpec] = {
    "text_generation": ImageSpec(repo="vllm/vllm-openai", tag="v0.10.2"),
    "speech_recognition": ImageSpec(
        repo="ghcr.io/princeton-ddss/speech-recognition-inference",
        tag="0.1.2",
    ),
}
