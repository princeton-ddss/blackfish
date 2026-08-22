"""Tests for staged container image discovery."""

from unittest.mock import AsyncMock, patch

import pytest
from blackfish.server.image_probe import (
    extract_tag,
    list_staged_tags,
    sort_tags,
)
from blackfish.server.images import ImageSpec
from blackfish.server.models.profile import LocalProfile

pytestmark = pytest.mark.anyio

VLLM = ImageSpec(repo="vllm/vllm-openai", tag="v0.20.0")
TIGERFLOW = ImageSpec(repo="ghcr.io/princeton-ddss/tigerflow-ml", tag="0.1.1")

# The filenames actually staged on the cluster, plus the orphan.
STAGED = [
    "speech-recognition-inference_0.1.2.sif",
    "speech-recognition-inference_0.2.1.sif",
    "text-generation-inference_2.3.0.sif",
    "tigerflow-ml_0.1.1.sif",
    "vllm-openai_v0.8.4.sif",
    "vllm-openai_v0.8.5.sif",
    "vllm-openai_v0.10.2.sif",
    "vllm-openai_v0.20.0.sif",
]


class TestExtractTag:
    def test_extracts_the_tag_for_a_matching_image(self) -> None:
        assert extract_tag("vllm-openai_v0.20.0.sif", VLLM) == "v0.20.0"

    def test_ignores_a_different_image(self) -> None:
        """The orphan on the cluster: a real .sif with no configured service."""
        assert extract_tag("text-generation-inference_2.3.0.sif", VLLM) is None

    def test_ignores_non_sif_files(self) -> None:
        assert extract_tag("vllm-openai_v0.20.0.txt", VLLM) is None

    def test_strips_the_registry_prefix_from_the_repo(self) -> None:
        """ImageSpec.sif drops the registry, so matching uses the bare name."""
        assert extract_tag("tigerflow-ml_0.1.1.sif", TIGERFLOW) == "0.1.1"

    def test_keeps_underscores_inside_a_tag(self) -> None:
        """Strip the known prefix rather than rsplit("_", 1), which would
        return "3" here and silently corrupt the tag."""
        assert extract_tag("vllm-openai_v1_2_3.sif", VLLM) == "v1_2_3"

    def test_rejects_an_empty_tag(self) -> None:
        assert extract_tag("vllm-openai_.sif", VLLM) is None

    def test_does_not_match_a_name_that_merely_shares_a_prefix(self) -> None:
        """A shorter image name must not swallow a longer one's files."""
        short = ImageSpec(repo="ghcr.io/x/vllm", tag="1.0")
        assert extract_tag("vllm-openai_v0.20.0.sif", short) is None


class TestSortTags:
    def test_orders_by_version_not_string(self) -> None:
        """The trap this exists for: as strings, v0.10.2 sorts before v0.8.4,
        which would present v0.8.4 as the newest available version."""
        assert sort_tags(["v0.10.2", "v0.20.0", "v0.8.4", "v0.8.5"]) == [
            "v0.8.4",
            "v0.8.5",
            "v0.10.2",
            "v0.20.0",
        ]

    def test_tolerates_a_leading_v(self) -> None:
        """vLLM publishes v0.20.0; the DDSS images publish a bare 0.1.2."""
        assert sort_tags(["v0.2.0", "0.10.0", "v0.3.0"]) == [
            "v0.2.0",
            "v0.3.0",
            "0.10.0",
        ]

    def test_handles_an_uppercase_v_prefix(self) -> None:
        """Version accepts v/V per PEP 440, so no hand-stripping is needed."""
        assert sort_tags(["V2.0.0", "v1.0.0"]) == ["v1.0.0", "V2.0.0"]

    def test_a_doubled_v_prefix_is_not_a_version(self) -> None:
        """Guards the reason for not hand-stripping: lstrip("v") removes every
        leading v, so "vv1.0.0" would parse as 1.0.0 and sort *between* the
        real versions instead of last with the other unparsable tags."""
        assert sort_tags(["vv1.0.0", "0.1.0", "V2.0.0"]) == [
            "0.1.0",
            "V2.0.0",
            "vv1.0.0",
        ]

    def test_unparsable_tags_sort_last_without_raising(self) -> None:
        """`latest` is runnable, so it is kept — but it says nothing about
        which image it names, so it must never sort first."""
        assert sort_tags(["latest", "0.2.0", "nightly", "0.1.0"]) == [
            "0.1.0",
            "0.2.0",
            "latest",
            "nightly",
        ]

    def test_empty(self) -> None:
        assert sort_tags([]) == []


def _profile() -> LocalProfile:
    return LocalProfile(
        name="test", home_dir="/home/test/.blackfish", cache_dir="/cache"
    )


def _mock_runner(stdout: bytes, returncode: int = 0):
    runner = AsyncMock()
    runner.run = AsyncMock(return_value=(returncode, stdout, b""))
    return runner


class TestListStagedTags:
    async def test_groups_tags_by_service_in_version_order(self) -> None:
        images = {"text_generation": VLLM, "tigerflow_ml": TIGERFLOW}
        runner = _mock_runner("\n".join(STAGED).encode())

        with patch("blackfish.server.image_probe._runner_for", return_value=runner):
            staged = await list_staged_tags(_profile(), images)

        assert staged["text_generation"] == ["v0.8.4", "v0.8.5", "v0.10.2", "v0.20.0"]
        assert staged["tigerflow_ml"] == ["0.1.1"]

    async def test_every_configured_service_appears(self) -> None:
        """A service with nothing staged still gets an entry, so callers never
        have to distinguish "absent" from "empty"."""
        images = {"text_generation": VLLM, "tigerflow_ml": TIGERFLOW}
        runner = _mock_runner(b"vllm-openai_v0.20.0.sif\n")

        with patch("blackfish.server.image_probe._runner_for", return_value=runner):
            staged = await list_staged_tags(_profile(), images)

        assert set(staged) == set(images)
        assert staged["tigerflow_ml"] == []

    async def test_orphan_files_are_ignored(self) -> None:
        """A .sif matching no configured service has no repo to attach to."""
        runner = _mock_runner(b"text-generation-inference_2.3.0.sif\n")

        with patch("blackfish.server.image_probe._runner_for", return_value=runner):
            staged = await list_staged_tags(_profile(), {"text_generation": VLLM})

        assert staged["text_generation"] == []

    async def test_missing_images_directory_yields_empty_not_an_error(self) -> None:
        """A fresh profile has no images dir. The probe's `|| true` turns that
        into empty output, so it must not read as a failure."""
        runner = _mock_runner(b"")

        with patch("blackfish.server.image_probe._runner_for", return_value=runner):
            staged = await list_staged_tags(_profile(), {"text_generation": VLLM})

        assert staged["text_generation"] == []

    async def test_probe_swallows_ls_errors_in_the_shell(self) -> None:
        """The command ends in `|| true`, so a missing directory cannot make
        the whole probe look like a transport failure."""
        runner = _mock_runner(b"")

        with patch("blackfish.server.image_probe._runner_for", return_value=runner):
            await list_staged_tags(_profile(), {"text_generation": VLLM})

        command = runner.run.call_args.args[0]
        assert command.endswith("|| true")
        assert "/cache/images" in command
