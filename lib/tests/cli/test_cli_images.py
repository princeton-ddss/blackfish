"""Tests for `blackfish image ls`."""

import os
import tempfile
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from log_symbols.symbols import LogSymbols

from blackfish.cli.__main__ import main

YES = LogSymbols.SUCCESS.value
NO = LogSymbols.ERROR.value


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def home_dir():
    """A temp home dir with a profiles.cfg referencing further temp paths."""
    with tempfile.TemporaryDirectory() as home:
        with tempfile.TemporaryDirectory() as profile_home:
            with tempfile.TemporaryDirectory() as profile_cache:
                cfg = os.path.join(home, "profiles.cfg")
                with open(cfg, "w") as f:
                    f.write(
                        "[default]\n"
                        "schema = local\n"
                        f"home_dir = {profile_home}\n"
                        f"cache_dir = {profile_cache}\n"
                    )
                os.makedirs(os.path.join(profile_home, "images"))
                os.makedirs(os.path.join(profile_cache, "images"))
                yield home, profile_home, profile_cache


@pytest.fixture
def home_dir_two_profiles():
    """A temp home dir with two local profiles (`default` and `secondary`)."""
    with tempfile.TemporaryDirectory() as home:
        with tempfile.TemporaryDirectory() as default_home:
            with tempfile.TemporaryDirectory() as default_cache:
                with tempfile.TemporaryDirectory() as secondary_home:
                    with tempfile.TemporaryDirectory() as secondary_cache:
                        cfg = os.path.join(home, "profiles.cfg")
                        with open(cfg, "w") as f:
                            f.write(
                                "[default]\n"
                                "schema = local\n"
                                f"home_dir = {default_home}\n"
                                f"cache_dir = {default_cache}\n"
                                "[secondary]\n"
                                "schema = local\n"
                                f"home_dir = {secondary_home}\n"
                                f"cache_dir = {secondary_cache}\n"
                            )
                        for d in (
                            default_home,
                            default_cache,
                            secondary_home,
                            secondary_cache,
                        ):
                            os.makedirs(os.path.join(d, "images"))
                        yield (
                            home,
                            {
                                "default": (default_home, default_cache),
                                "secondary": (secondary_home, secondary_cache),
                            },
                        )


def _patch_home(home: str):
    return patch("blackfish.cli.image.config.HOME_DIR", home)


class TestImageLs:
    def test_no_profile_shows_registry(self, cli_runner):
        result = cli_runner.invoke(main, ["image", "ls"])
        assert result.exit_code == 0
        assert "SERVICE" in result.output
        assert "text_generation" in result.output
        assert "speech_recognition" in result.output

    def test_profile_reports_missing(self, cli_runner, home_dir):
        home, _, _ = home_dir
        with _patch_home(home):
            result = cli_runner.invoke(main, ["image", "ls", "--profile", "default"])
        assert result.exit_code == 0, result.output
        assert "default" in result.output
        # No SIFs placed -> nothing is reported as available.
        assert YES not in result.output

    def test_profile_reports_present_in_home(self, cli_runner, home_dir):
        home, profile_home, _ = home_dir
        from blackfish.server.images import DEFAULT_IMAGES

        sif = DEFAULT_IMAGES["text_generation"].sif
        open(os.path.join(profile_home, "images", sif), "w").close()
        with _patch_home(home):
            result = cli_runner.invoke(main, ["image", "ls", "--profile", "default"])
        assert result.exit_code == 0, result.output
        assert YES in result.output

    def test_unknown_profile(self, cli_runner, home_dir):
        home, _, _ = home_dir
        with _patch_home(home):
            result = cli_runner.invoke(main, ["image", "ls", "--profile", "nope"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_all_reports_per_profile_availability(
        self, cli_runner, home_dir_two_profiles
    ):
        home, profiles = home_dir_two_profiles
        from blackfish.server.config import config

        # Place every pinned SIF in `default`'s home; leave `secondary` empty.
        default_home, _ = profiles["default"]
        for spec in config.IMAGES.values():
            open(os.path.join(default_home, "images", spec.sif), "w").close()

        with _patch_home(home):
            result = cli_runner.invoke(main, ["image", "ls", "--all"])
        assert result.exit_code == 0, result.output

        # Each profile gets one row per service.
        services = list(config.IMAGES.keys())
        lines = result.output.splitlines()
        default_rows = [
            line
            for line in lines
            if line.startswith("default") and any(s in line for s in services)
        ]
        secondary_rows = [
            line
            for line in lines
            if line.startswith("secondary") and any(s in line for s in services)
        ]
        assert len(default_rows) == len(services)
        assert len(secondary_rows) == len(services)

        # `default` reports HOME present for every service; `secondary` does not.
        for row in default_rows:
            assert YES in row, row
        for row in secondary_rows:
            assert YES not in row, row

    def test_profile_and_all_conflict(self, cli_runner, home_dir):
        home, _, _ = home_dir
        with _patch_home(home):
            result = cli_runner.invoke(
                main, ["image", "ls", "--profile", "default", "--all"]
            )
        assert result.exit_code != 0


class TestImageLsStrict:
    def test_strict_missing_exits_nonzero(self, cli_runner, home_dir):
        home, _, _ = home_dir
        with _patch_home(home):
            result = cli_runner.invoke(
                main, ["image", "ls", "--profile", "default", "--strict"]
            )
        assert result.exit_code == 1
        assert "Missing images" in result.output

    def test_strict_all_present_exits_zero(self, cli_runner, home_dir):
        home, profile_home, _ = home_dir
        from blackfish.server.config import config

        for spec in config.IMAGES.values():
            open(os.path.join(profile_home, "images", spec.sif), "w").close()
        with _patch_home(home):
            result = cli_runner.invoke(
                main, ["image", "ls", "--profile", "default", "--strict"]
            )
        assert result.exit_code == 0, result.output

    def test_strict_without_profile_errors(self, cli_runner, home_dir):
        home, _, _ = home_dir
        with _patch_home(home):
            result = cli_runner.invoke(main, ["image", "ls", "--strict"])
        assert result.exit_code != 0
        assert "--strict" in result.output
