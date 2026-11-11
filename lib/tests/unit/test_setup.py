import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call, patch


from blackfish.server.config import ContainerProvider
from blackfish.server.jobs.client import TigerFlowError, TigerFlowVersions
from blackfish.server.setup import (
    ProfileManager,
    ProfileSetupError,
    check_local_cache_exists,
    repair_slurm_profile,
)
from blackfish.server.bootstrap import ensure_app_dir
from blackfish.cli.profile import _auto_profile_


def test_check_local_cache_exists_existing_dir(tmp_path):
    check_local_cache_exists(tmp_path)


def test_check_local_cache_exists_missing_dir(tmp_path):
    with pytest.raises(Exception):
        check_local_cache_exists(tmp_path / "missing")


def test_local_auto_setup(tmp_path):
    p = tmp_path / ".blackfish"
    ensure_app_dir(p)
    _auto_profile_(p, "default", "local", None, None, home_dir=p, cache_dir=p)


def test_slurm_auto_setup(tmp_path):
    p = tmp_path / ".blackfish"
    ensure_app_dir(p)
    _auto_profile_(p, "default", "slurm", "localhost", "test", home_dir=p, cache_dir=p)


HOME_DIR = "/cluster/blackfish"
CACHE_DIR = "/scratch/cache"
DIRECTORY_COMMANDS = [
    call(f"mkdir -p {HOME_DIR}"),
    call(f"mkdir -p {HOME_DIR}/models {HOME_DIR}/images"),
]
CACHE_COMMAND = call(f'test -d {CACHE_DIR} && echo "exists"')
SUCCESS = (0, b"", b"")
CACHE_EXISTS = (0, b"exists\n", b"")


@pytest.fixture
def manager():
    runner = SimpleNamespace(host="cluster.example", run=AsyncMock())
    progress = Mock()
    return ProfileManager(runner, HOME_DIR, CACHE_DIR, on_progress=progress)


@pytest.mark.anyio
class TestProfileManagerCommands:
    async def test_creates_home_and_model_image_directories(self, manager):
        manager.runner.run.side_effect = [SUCCESS, SUCCESS]

        await manager.create_directories()

        assert manager.runner.run.await_args_list == DIRECTORY_COMMANDS
        manager._on_progress.assert_called_once_with(
            "Setting up directories on cluster.example..."
        )

    @pytest.mark.parametrize(
        ("failed_step", "message"),
        [
            (0, "Failed to create home directory"),
            (1, "Failed to create subdirectories"),
        ],
    )
    @pytest.mark.parametrize("stderr", [b"permission denied\n", b""])
    async def test_directory_failure_preserves_details_and_stops(
        self, manager, failed_step, message, stderr
    ):
        manager.runner.run.side_effect = [SUCCESS] * failed_step + [(1, b"", stderr)]

        with pytest.raises(ProfileSetupError) as exc:
            await manager.create_directories()

        assert exc.value.message == message
        assert exc.value.details == ("permission denied" if stderr else None)
        assert str(exc.value) == (
            f"{message} (permission denied)" if stderr else message
        )
        assert (
            manager.runner.run.await_args_list == DIRECTORY_COMMANDS[: failed_step + 1]
        )

    @pytest.mark.parametrize("failed_step", [0, 1])
    async def test_directory_transport_failure_becomes_setup_error(
        self, manager, failed_step
    ):
        manager.runner.run.side_effect = [SUCCESS] * failed_step + [OSError("SSH lost")]

        with pytest.raises(ProfileSetupError) as exc:
            await manager.create_directories()

        assert exc.value.message == "Failed to create directories"
        assert exc.value.details == "SSH lost"
        assert str(exc.value) == "Failed to create directories (SSH lost)"
        assert (
            manager.runner.run.await_args_list == DIRECTORY_COMMANDS[: failed_step + 1]
        )

    async def test_existing_cache_succeeds(self, manager):
        manager.runner.run.return_value = CACHE_EXISTS

        await manager.check_cache()

        manager.runner.run.assert_awaited_once_with(*CACHE_COMMAND.args)
        manager._on_progress.assert_called_once_with(
            "Checking cache directory on cluster.example..."
        )

    @pytest.mark.parametrize(
        "response", [(1, b"", b""), (1, b"exists\n", b""), (0, b"", b"")]
    )
    async def test_cache_requires_success_and_confirmation(self, manager, response):
        manager.runner.run.return_value = response

        with pytest.raises(ProfileSetupError) as exc:
            await manager.check_cache()

        assert exc.value.message == f"Cache directory does not exist: {CACHE_DIR}"
        assert exc.value.details is None
        manager.runner.run.assert_awaited_once_with(*CACHE_COMMAND.args)

    async def test_cache_transport_failure_becomes_setup_error(self, manager):
        manager.runner.run.side_effect = OSError("SSH lost")

        with pytest.raises(ProfileSetupError) as exc:
            await manager.check_cache()

        assert exc.value.message == "Failed to check cache directory"
        assert exc.value.details == "SSH lost"


@pytest.fixture
def repair_dependencies():
    # Mock only the execution boundaries: repair uses the real ProfileManager.
    with (
        patch("blackfish.server.jobs.client.LocalRunner", autospec=True) as local,
        patch("blackfish.server.jobs.client.SSHRunner", autospec=True) as ssh,
        patch("blackfish.server.jobs.client.TigerFlowClient", autospec=True) as client,
    ):
        local.return_value.host = "localhost"
        ssh.return_value.host = "cluster.example"
        for factory in (local, ssh):
            factory.return_value.run.side_effect = [SUCCESS, SUCCESS, CACHE_EXISTS]
        client.return_value.check_health.return_value = TigerFlowVersions(
            tigerflow="1.2.3", tigerflow_ml="4.5.6"
        )
        yield SimpleNamespace(local=local, ssh=ssh, client=client, progress=Mock())


async def repair(dependencies, host="cluster.example", force=False):
    return await repair_slurm_profile(
        host=host,
        user="testuser",
        home_dir=HOME_DIR,
        cache_dir=CACHE_DIR,
        force=force,
        on_progress=dependencies.progress,
    )


@pytest.mark.anyio
class TestRepairSlurmProfile:
    @pytest.mark.parametrize("host", ["localhost", "cluster.example"])
    async def test_healthy_image_skips_setup_and_uses_apptainer(
        self, repair_dependencies, host
    ):
        deps = repair_dependencies

        result = await repair(deps, host=host)

        assert result.repaired is False
        assert "tigerflow 1.2.3" in result.message
        assert "tigerflow-ml 4.5.6" in result.message
        assert "--force" in result.message
        deps.client.return_value.check_health.assert_awaited_once_with()
        deps.local.return_value.run.assert_not_called()
        deps.ssh.return_value.run.assert_not_called()
        if host == "localhost":
            deps.local.assert_called_once_with()
            deps.ssh.assert_not_called()
            runner = deps.local.return_value
        else:
            deps.ssh.assert_called_once_with(user="testuser", host=host)
            deps.local.assert_not_called()
            runner = deps.ssh.return_value
        # The Blackfish host uses Docker in the test configuration, but Slurm
        # execution must use Apptainer on both remote clusters and localhost.
        from blackfish.server.config import config

        assert config.CONTAINER_PROVIDER == ContainerProvider.Docker
        deps.client.assert_called_once_with(
            runner=runner,
            home_dir=HOME_DIR,
            image=config.IMAGES["tigerflow_ml"],
            provider=ContainerProvider.Apptainer,
            cache_dir=CACHE_DIR,
            on_progress=deps.progress,
        )

    @pytest.mark.parametrize("host", ["localhost", "cluster.example"])
    async def test_force_skips_health_and_runs_setup(self, repair_dependencies, host):
        deps = repair_dependencies

        result = await repair(deps, host=host, force=True)

        assert result.repaired is True
        assert result.message == f"Profile repaired on {host}."
        deps.client.return_value.check_health.assert_not_called()
        runner = (
            deps.local.return_value if host == "localhost" else deps.ssh.return_value
        )
        unused = (
            deps.ssh.return_value if host == "localhost" else deps.local.return_value
        )
        assert runner.run.await_args_list == [*DIRECTORY_COMMANDS, CACHE_COMMAND]
        unused.run.assert_not_called()

    @pytest.mark.parametrize("error_type", ["missing", "timeout"])
    async def test_failed_health_check_reports_reason_and_runs_setup(
        self, repair_dependencies, error_type
    ):
        deps = repair_dependencies
        error = TigerFlowError(error_type, "cluster.example", "image unavailable")
        deps.client.return_value.check_health.side_effect = error

        result = await repair(deps)

        assert result.repaired is True
        deps.client.return_value.check_health.assert_awaited_once_with()
        assert deps.ssh.return_value.run.await_args_list == [
            *DIRECTORY_COMMANDS,
            CACHE_COMMAND,
        ]
        deps.progress.assert_any_call(f"Image check failed: {error.user_message()}")

    @pytest.mark.parametrize(
        ("responses", "message", "commands"),
        [
            (
                [(1, b"", b"denied")],
                "Failed to create home directory",
                DIRECTORY_COMMANDS[:1],
            ),
            (
                [SUCCESS, (1, b"", b"denied")],
                "Failed to create subdirectories",
                DIRECTORY_COMMANDS,
            ),
            (
                [SUCCESS, SUCCESS, (1, b"", b"")],
                f"Cache directory does not exist: {CACHE_DIR}",
                [*DIRECTORY_COMMANDS, CACHE_COMMAND],
            ),
        ],
    )
    async def test_setup_failure_is_not_reported_as_success(
        self, repair_dependencies, responses, message, commands
    ):
        deps = repair_dependencies
        deps.ssh.return_value.run.side_effect = responses

        with pytest.raises(ProfileSetupError) as exc:
            await repair(deps, force=True)

        assert exc.value.message == message
        assert deps.ssh.return_value.run.await_args_list == commands

    async def test_unexpected_health_failure_propagates_without_setup(
        self, repair_dependencies
    ):
        deps = repair_dependencies
        error = RuntimeError("invalid health response")
        deps.client.return_value.check_health.side_effect = error

        with pytest.raises(RuntimeError) as exc:
            await repair(deps)

        assert exc.value is error
        deps.ssh.return_value.run.assert_not_called()
        deps.local.return_value.run.assert_not_called()
