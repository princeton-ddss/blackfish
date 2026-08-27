"""Discover which container images are actually staged on a profile.

Images are staged out of band by administrators (``apptainer pull`` into
``{cache_dir}/images/``). ``config.IMAGES`` records only the *pinned* spec per
service, so it cannot answer "which versions could this profile run?" — that is
what this module is for.

The repo always comes from configuration and only the tag from the filename:
``ImageSpec.sif`` drops the registry prefix (``<host>/<org>/<name>:<tag>`` ->
``<name>_<tag>.sif``), so a filename alone cannot identify a repo.
"""

from __future__ import annotations

import os
import shlex
from typing import TYPE_CHECKING

from packaging.version import InvalidVersion, Version

from blackfish.server.jobs.client import LocalRunner, SSHRunner

if TYPE_CHECKING:
    from blackfish.server.images import ImageSpec
    from blackfish.server.models.profile import BlackfishProfile

# Shorter than the runner's 120s default: this sits behind a UI dropdown, so a
# slow login node should fail fast rather than hang the request.
PROBE_TIMEOUT = 20.0


def _runner_for(profile: "BlackfishProfile") -> SSHRunner | LocalRunner:
    """Return a runner that executes on the profile's host."""
    from blackfish.server.models.profile import SlurmProfile

    if isinstance(profile, SlurmProfile) and not profile.is_local():
        return SSHRunner(profile.user, profile.host, timeout=PROBE_TIMEOUT)
    return LocalRunner()


def sort_tags(tags: list[str]) -> list[str]:
    """Order tags by version, ascending, with unparsable tags last.

    A plain string sort is wrong — ``"0.1.10" < "0.1.2"`` — and tag styles are
    inconsistent across images (vLLM publishes ``v0.20.0``, the DDSS images
    publish a bare ``0.1.2``). ``Version`` accepts either form per PEP 440, so
    no prefix stripping is needed; hand-stripping with ``lstrip("v")`` would
    also mangle a malformed ``vv1.0.0`` into a valid-looking version.

    Tags that are not versions at all (``latest``, ``nightly``) are still
    runnable, so they are kept and sorted last rather than hidden; callers must
    never auto-select them, since they say nothing about which image they name.
    """

    def key(tag: str) -> tuple[int, Version | str]:
        try:
            return (0, Version(tag))
        except InvalidVersion:
            return (1, tag)

    return sorted(tags, key=key)


def extract_tag(filename: str, spec: "ImageSpec") -> str | None:
    """Return the tag in ``filename`` for ``spec``, or None if it isn't a match.

    Strips the *known* image-name prefix rather than splitting on the last
    underscore, so a tag that itself contains underscores survives
    (``vllm-openai_v1_2_3.sif`` -> ``v1_2_3``).
    """
    if not filename.endswith(".sif"):
        return None
    prefix = f"{spec.repo.rsplit('/', 1)[-1]}_"
    stem = filename[: -len(".sif")]
    if not stem.startswith(prefix):
        return None
    tag = stem[len(prefix) :]
    return tag or None


async def _list_sif_files(profile: "BlackfishProfile") -> list[str]:
    """List the ``.sif`` filenames staged in the profile's images directory.

    A missing images directory is a valid state (a fresh profile), not an
    error: ``ls`` exits non-zero for it, so the failure is swallowed and an
    empty list returned. A genuine transport failure still surfaces, because
    the runner raises before any command exit code is inspected.
    """
    images_dir = os.path.join(profile.cache_dir, "images")
    command = f"ls -1 {shlex.quote(images_dir)} 2>/dev/null | grep '\\.sif$' || true"

    runner = _runner_for(profile)
    _, stdout, _ = await runner.run(command)
    return [
        line.strip() for line in stdout.decode("utf-8").splitlines() if line.strip()
    ]


async def list_staged_tags(
    profile: "BlackfishProfile", images: dict[str, "ImageSpec"]
) -> dict[str, list[str]]:
    """Map each configured service to the tags staged on ``profile``.

    Every service in ``images`` appears in the result, with an empty list when
    nothing is staged for it. Staged files matching no configured service (for
    example a deprecated image left on disk) are ignored — without a repo there
    is nothing launchable to attach them to.

    Raises:
        TigerFlowError: the profile could not be reached.
    """
    filenames = await _list_sif_files(profile)

    staged: dict[str, list[str]] = {}
    for service, spec in images.items():
        tags = [t for f in filenames if (t := extract_tag(f, spec)) is not None]
        staged[service] = sort_tags(tags)
    return staged
