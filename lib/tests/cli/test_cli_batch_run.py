"""Tests for `blackfish batch run` option plumbing."""

from unittest.mock import Mock, patch

from blackfish.cli.__main__ import main
from blackfish.server.models.profile import SlurmProfile


def _profile() -> SlurmProfile:
    return SlurmProfile(
        name="default",
        host="hpc.example.com",
        user="test",
        home_dir="/home/test/.blackfish",
        cache_dir="/home/test/.blackfish/cache",
    )


def _invoke(cli_runner, extra_args):
    """Run `batch run` with the model-resolution collaborators stubbed."""
    cmd = [
        "batch",
        "run",
        "--name",
        "test-job",
        "--task",
        "chat",
        "--model",
        "google/gemma-3-4b-it",
        "--input-dir",
        "/data/in",
        "--output-dir",
        "/data/out",
        *extra_args,
    ]

    with (
        patch("blackfish.cli.batch.resolve_profile_or_exit") as mock_resolve,
        patch("blackfish.cli.batch.deserialize_profile") as mock_deserialize,
        patch("blackfish.cli.batch.get_models") as mock_get_models,
        patch("blackfish.cli.batch.get_model_dir") as mock_get_model_dir,
        patch("blackfish.cli.batch.get_latest_commit") as mock_get_latest,
        patch("blackfish.cli.batch.get_revisions") as mock_get_revisions,
        patch("blackfish.cli.batch.api.post") as mock_post,
    ):
        mock_resolve.return_value = "default"
        mock_deserialize.return_value = _profile()
        mock_get_models.return_value = ["google/gemma-3-4b-it"]
        mock_get_model_dir.return_value = "/models/gemma"
        mock_get_latest.return_value = "abc123"
        mock_get_revisions.return_value = ["abc123"]

        response = Mock()
        response.ok = True
        response.json.return_value = {"id": "job-uuid-123"}
        mock_post.return_value = response

        result = cli_runner.invoke(main, cmd)

    return result, mock_post


class TestBatchRunImageRef:
    def test_image_ref_is_forwarded_to_the_api(self, cli_runner, mock_config):
        """--image-ref reaches the request body as image_ref."""
        pin = "ghcr.io/princeton-ddss/tigerflow-ml:9.9.9"
        _, mock_post = _invoke(cli_runner, ["--image-ref", pin])

        assert mock_post.call_args[1]["json"]["image_ref"] == pin

    def test_image_ref_defaults_to_none(self, cli_runner, mock_config):
        """Omitting it sends null, so the server resolves its configured
        default and records it on the job."""
        _, mock_post = _invoke(cli_runner, [])

        assert mock_post.call_args[1]["json"]["image_ref"] is None

    def test_dry_run_reports_the_pinned_image(self, cli_runner, mock_config):
        """The image is rendered into the job script rather than the pipeline
        config, so a dry run must report it separately or the pin is
        invisible."""
        pin = "ghcr.io/princeton-ddss/tigerflow-ml:9.9.9"
        result, _ = _invoke(cli_runner, ["--image-ref", pin, "--dry-run"])

        assert pin in result.output
