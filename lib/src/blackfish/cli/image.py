"""CLI utilities for inspecting service container images.

`blackfish image ls` shows pinned registry images, optionally with per-profile
availability. Pass `--strict` to exit non-zero when any pinned image is missing
from both shared (cache) and home dirs — useful in scripts and health checks.
"""

from __future__ import annotations

import asyncio
import os
import shlex
from typing import Iterable

import rich_click as click
from log_symbols.symbols import LogSymbols
from prettytable import PrettyTable, TableStyle
from yaspin import yaspin

from blackfish.server.config import config
from blackfish.server.images import ImageSpec
from blackfish.server.jobs.client import LocalRunner, SSHRunner, TigerFlowError
from blackfish.server.models.profile import (
    BlackfishProfile,
    SlurmProfile,
    deserialize_profile,
    deserialize_profiles,
)


class _ImageCliError(Exception):
    """Raised by helpers; commands convert into LogSymbols.ERROR + ctx.exit(1)."""


def _load_profile(home_dir: str, name: str) -> BlackfishProfile:
    profile = deserialize_profile(home_dir, name)
    if profile is None:
        raise _ImageCliError(f"Profile {name!r} not found.")
    return profile


def _sif_paths(profile: BlackfishProfile, spec: ImageSpec) -> tuple[str, str]:
    """Return (shared_path, home_path) for a SIF on this profile."""
    return (
        os.path.join(profile.cache_dir, "images", spec.sif),
        os.path.join(profile.home_dir, "images", spec.sif),
    )


def _runner_for(profile: BlackfishProfile) -> SSHRunner | LocalRunner:
    if isinstance(profile, SlurmProfile) and not profile.is_local():
        return SSHRunner(profile.user, profile.host)
    return LocalRunner()


async def _check_paths(
    runner: SSHRunner | LocalRunner, paths: Iterable[str]
) -> dict[str, bool]:
    """Probe `paths` via `runner`. Returns path -> exists."""
    paths = list(paths)
    if not paths:
        return {}

    # One round trip: print "1" if exists else "0", line per path.
    script = " ; ".join(
        f"if [ -e {shlex.quote(p)} ]; then echo 1; else echo 0; fi" for p in paths
    )
    rc, stdout, stderr = await runner.run(script)
    if rc != 0:
        raise _ImageCliError(
            f"Failed to probe images on {runner.host}: {stderr.decode().strip()}"
        )
    lines = stdout.decode().strip().splitlines()
    if len(lines) != len(paths):
        raise _ImageCliError(
            f"Unexpected probe output on {runner.host}: "
            f"got {len(lines)} lines for {len(paths)} paths."
        )
    return {p: line.strip() == "1" for p, line in zip(paths, lines)}


def _availability(
    profile: BlackfishProfile, images: dict[str, ImageSpec]
) -> dict[str, tuple[bool, bool]]:
    """For each service, return (shared_exists, home_exists) on the profile.

    Wraps the probe in a spinner so users get feedback during slow SSH calls.
    """
    paths: list[str] = []
    for spec in images.values():
        shared, home = _sif_paths(profile, spec)
        paths.extend([shared, home])

    runner = _runner_for(profile)
    with yaspin(text=f"Checking images for profile {profile.name!r}...") as spinner:
        try:
            present = asyncio.run(_check_paths(runner, paths))
        except TigerFlowError as exc:
            # SSHRunner raises TigerFlowError on transport failure (timeout, exit 255).
            spinner.fail(f"{LogSymbols.ERROR.value}")
            raise _ImageCliError(
                f"Could not reach profile {profile.name!r}: {exc}"
            ) from exc
        except _ImageCliError:
            spinner.fail(f"{LogSymbols.ERROR.value}")
            raise

    out: dict[str, tuple[bool, bool]] = {}
    for service, spec in images.items():
        shared, home = _sif_paths(profile, spec)
        out[service] = (present[shared], present[home])
    return out


def _render_registry_table() -> PrettyTable:
    tab = PrettyTable(field_names=["SERVICE", "DOCKER REF", "SIF"])
    tab.set_style(TableStyle.PLAIN_COLUMNS)
    for field in tab.field_names:
        tab.align[field] = "l"
    tab.right_padding_width = 3
    for service, spec in config.IMAGES.items():
        tab.add_row([service, spec.docker_ref, spec.sif])
    return tab


def _render_availability_table(
    profiles: list[BlackfishProfile],
    availability: dict[str, dict[str, tuple[bool, bool]]],
) -> PrettyTable:
    headers = ["PROFILE", "SERVICE", "DOCKER REF", "SIF", "SHARED", "HOME"]
    tab = PrettyTable(field_names=headers)
    tab.set_style(TableStyle.PLAIN_COLUMNS)
    for field in headers:
        tab.align[field] = "l"
    tab.right_padding_width = 3
    for profile in profiles:
        for service, spec in config.IMAGES.items():
            shared, home = availability[profile.name][service]
            tab.add_row(
                [
                    profile.name,
                    service,
                    spec.docker_ref,
                    spec.sif,
                    "yes" if shared else "no",
                    "yes" if home else "no",
                ]
            )
    return tab


def _resolve_profiles(
    profile_name: str | None, all_profiles: bool
) -> list[BlackfishProfile]:
    if profile_name and all_profiles:
        raise _ImageCliError("Pass either --profile or --all, not both.")
    if all_profiles:
        try:
            profiles = deserialize_profiles(config.HOME_DIR)
        except FileNotFoundError:
            raise _ImageCliError("No profiles configured.")
        if not profiles:
            raise _ImageCliError("No profiles configured.")
        return profiles
    if profile_name:
        return [_load_profile(config.HOME_DIR, profile_name)]
    return []


def _fail(ctx: click.Context, message: str) -> None:
    print(f"{LogSymbols.ERROR.value} {message}")
    ctx.exit(1)


@click.command(name="ls")
@click.option(
    "--profile", "profile_name", type=str, default=None, help="Profile to inspect."
)
@click.option(
    "--all",
    "all_profiles",
    is_flag=True,
    default=False,
    help="Inspect every profile.",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit 1 if any pinned image is missing from the inspected profile(s).",
)
@click.pass_context
def list_images(
    ctx: click.Context,
    profile_name: str | None,
    all_profiles: bool,
    strict: bool,
) -> None:
    """List pinned service images.

    Without --profile or --all, shows the registry (service, docker ref, SIF).
    With either flag, also reports availability in shared (cache) and home dirs.
    Pass --strict to exit 1 when any pinned image is missing from both locations.
    """
    try:
        profiles = _resolve_profiles(profile_name, all_profiles)
    except _ImageCliError as exc:
        _fail(ctx, str(exc))
        return

    if not profiles:
        if strict:
            _fail(ctx, "--strict requires --profile or --all.")
            return
        print(_render_registry_table())
        return

    try:
        availability = {p.name: _availability(p, config.IMAGES) for p in profiles}
    except _ImageCliError as exc:
        _fail(ctx, str(exc))
        return

    print(_render_availability_table(profiles, availability))

    if strict:
        missing = [
            (p.name, service)
            for p in profiles
            for service, (shared, home) in availability[p.name].items()
            if not shared and not home
        ]
        if missing:
            details = ", ".join(f"{p}:{s}" for p, s in missing)
            _fail(ctx, f"Missing images: {details}")
