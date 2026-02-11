"""Contract tests for TigerFlow CLI interface.

These tests validate that the actual tigerflow CLI output matches
the expected schemas used by blackfish.

Setup:
    uv sync --group contract

Run:
    TIGERFLOW_CONTRACT_TESTS=1 uv run pytest tests/contract/ -v

By default, these tests are skipped unless TIGERFLOW_CONTRACT_TESTS=1
is set in the environment.
"""

import json
import os
import subprocess

import pytest
from packaging.version import Version

# Skip all tests in this module unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.environ.get("TIGERFLOW_CONTRACT_TESTS") != "1",
    reason="Contract tests disabled. Set TIGERFLOW_CONTRACT_TESTS=1 to run.",
)

# Minimum versions expected
MIN_TIGERFLOW_VERSION = "0.1.0"
MIN_TIGERFLOW_ML_VERSION = "0.1.0"

# Tasks we expect to be available in tigerflow-ml
EXPECTED_TASKS = [
    "transcribe",
    "translate",
]


def get_tigerflow_bin() -> str:
    """Get path to tigerflow binary.

    Uses TIGERFLOW_BIN env var if set, otherwise assumes 'tigerflow' is in PATH.
    """
    return os.environ.get("TIGERFLOW_BIN", "tigerflow")


def run_tigerflow(*args: str) -> tuple[int, str, str]:
    """Run tigerflow command and return (returncode, stdout, stderr)."""
    cmd = [get_tigerflow_bin(), *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


class TestTigerflowVersion:
    """Contract tests for tigerflow version requirements."""

    def test_tigerflow_version_available(self) -> None:
        """tigerflow --version should return version info."""
        returncode, stdout, stderr = run_tigerflow("--version")

        assert returncode == 0, f"--version failed: {stderr}"
        assert stdout.strip(), "Expected version output"

    def test_tigerflow_meets_minimum_version(self) -> None:
        """tigerflow version should meet minimum requirements."""
        returncode, stdout, _ = run_tigerflow("--version")
        assert returncode == 0

        # Parse version from output (format may vary)
        version_str = stdout.strip().split()[-1]
        try:
            version = Version(version_str)
            assert version >= Version(MIN_TIGERFLOW_VERSION), (
                f"tigerflow {version} < {MIN_TIGERFLOW_VERSION}"
            )
        except Exception:
            pytest.skip(f"Could not parse version from: {stdout}")


class TestTigerflowTasksList:
    """Contract tests for tigerflow tasks list command."""

    def test_returns_valid_json(self) -> None:
        """tigerflow tasks list --json should return valid JSON array."""
        returncode, stdout, stderr = run_tigerflow("tasks", "list", "--json")

        assert returncode == 0, f"Command failed: {stderr}"

        tasks = json.loads(stdout)
        assert isinstance(tasks, list), "Expected JSON array"

    def test_task_has_required_fields(self) -> None:
        """Each task should have name, description, and version."""
        returncode, stdout, _ = run_tigerflow("tasks", "list", "--json")
        assert returncode == 0

        tasks = json.loads(stdout)
        assert len(tasks) > 0, "Expected at least one task"

        for task in tasks:
            assert "name" in task, "Task missing 'name' field"
            assert "description" in task, "Task missing 'description' field"
            assert "version" in task, "Task missing 'version' field"

            assert isinstance(task["name"], str)
            assert isinstance(task["description"], str)
            assert isinstance(task["version"], str)

    def test_expected_tasks_available(self) -> None:
        """Expected tasks should be available."""
        returncode, stdout, _ = run_tigerflow("tasks", "list", "--json")
        assert returncode == 0

        tasks = json.loads(stdout)
        available_tasks = {t["name"] for t in tasks}

        missing = set(EXPECTED_TASKS) - available_tasks
        assert not missing, f"Expected tasks not available: {missing}"


class TestTigerflowTasksInfo:
    """Contract tests for tigerflow tasks info command."""

    @pytest.fixture
    def task_name(self) -> str:
        """Get a valid task name from tasks list."""
        returncode, stdout, _ = run_tigerflow("tasks", "list", "--json")
        if returncode != 0:
            pytest.skip("Could not get tasks list")

        tasks = json.loads(stdout)
        if not tasks:
            pytest.skip("No tasks available")

        return tasks[0]["name"]

    def test_returns_valid_json(self, task_name: str) -> None:
        """tigerflow tasks info <task> --json should return valid JSON object."""
        returncode, stdout, stderr = run_tigerflow(
            "tasks", "info", task_name, "--json"
        )

        assert returncode == 0, f"Command failed: {stderr}"

        task_info = json.loads(stdout)
        assert isinstance(task_info, dict), "Expected JSON object"

    def test_has_required_fields(self, task_name: str) -> None:
        """Task info should have required fields."""
        returncode, stdout, _ = run_tigerflow("tasks", "info", task_name, "--json")
        assert returncode == 0

        info = json.loads(stdout)

        assert info["name"] == task_name
        assert "description" in info, "Task info missing 'description'"
        assert "version" in info, "Task info missing 'version'"
        assert "params" in info, "Task info missing 'params'"

        assert isinstance(info["version"], str)
        assert isinstance(info["params"], dict)

    def test_unknown_task_fails(self) -> None:
        """tigerflow tasks info with unknown task should fail."""
        returncode, _, _ = run_tigerflow(
            "tasks", "info", "nonexistent_task_xyz_123", "--json"
        )

        assert returncode != 0, "Expected non-zero exit for unknown task"
