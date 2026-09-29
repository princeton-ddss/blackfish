"""Tests for the Blackfish programmatic interface."""

import pytest
import logging
from pathlib import Path
from collections.abc import AsyncGenerator
from blackfish import Blackfish, set_logging_level
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from advanced_alchemy.base import UUIDAuditBase


pytestmark = pytest.mark.anyio


def _create_blackfish_client(engine: AsyncEngine, home_dir: str) -> Blackfish:
    """Helper to create a Blackfish client with test database."""
    from blackfish.server.config import BlackfishConfig, ContainerProvider

    config = BlackfishConfig(
        home_dir=home_dir,
        debug=True,
        container_provider=ContainerProvider.Docker,
    )

    bf = Blackfish(home_dir=home_dir, config=config)
    bf._engine = engine
    bf._sessionmaker = async_sessionmaker(bind=engine, expire_on_commit=False)
    return bf


@pytest.fixture
async def blackfish_client(engine: AsyncEngine) -> AsyncGenerator[Blackfish, None]:
    """Create a Blackfish client using the test database."""
    home_dir = str(Path(__file__).parent.parent / "tests")

    # Initialize database tables (drop and recreate to ensure clean state)
    async with engine.begin() as conn:
        await conn.run_sync(UUIDAuditBase.metadata.drop_all)
        await conn.run_sync(UUIDAuditBase.metadata.create_all)

    bf = _create_blackfish_client(engine, home_dir)

    yield bf

    # Cleanup
    await bf._async_close()


class TestBlackfishClient:
    """Test the Blackfish programmatic interface."""

    async def test_client_initialization(self, blackfish_client: Blackfish):
        """Test that the client initializes correctly."""
        assert blackfish_client is not None
        assert blackfish_client.home_dir is not None
        assert blackfish_client.config is not None

    async def test_list_services_empty(self, blackfish_client: Blackfish):
        """Test listing services when none exist."""
        services = await blackfish_client.async_list_services()
        assert services == []

    async def test_get_nonexistent_service(self, blackfish_client: Blackfish):
        """Test getting a service that doesn't exist."""
        service = await blackfish_client.async_get_service(
            "550e8400-e29b-41d4-a716-446655440000"
        )
        assert service is None

    async def test_delete_nonexistent_service(self, blackfish_client: Blackfish):
        """Test deleting a service that doesn't exist."""
        deleted = await blackfish_client.async_delete_service(
            "550e8400-e29b-41d4-a716-446655440000"
        )
        assert deleted is False

    async def test_context_manager(self, engine: AsyncEngine):
        """Test that context manager properly manages resources."""
        home_dir = str(Path(__file__).parent.parent / "tests")

        # Initialize database tables
        async with engine.begin() as conn:
            await conn.run_sync(UUIDAuditBase.metadata.drop_all)
            await conn.run_sync(UUIDAuditBase.metadata.create_all)

        bf = _create_blackfish_client(engine, home_dir)

        async with bf:
            # Should be able to use the client
            services = await bf.async_list_services()
            assert services == []

        # After context exit, engine should be closed
        assert bf._engine is None

    async def test_wait_for_service_not_found(self, blackfish_client: Blackfish):
        """Test waiting for a service that doesn't exist."""
        # Should return None immediately for non-existent service
        service = await blackfish_client.async_wait_for_service(
            "550e8400-e29b-41d4-a716-446655440000",
            timeout=5,
            poll_interval=1,
        )
        assert service is None

    async def test_flexible_initialization(self):
        """Test flexible initialization with different parameter combinations."""
        from blackfish.server.config import BlackfishConfig, ContainerProvider

        # Test 1: Initialize with individual parameters
        bf1 = Blackfish(home_dir="/tmp/test", debug=False, port=9000)
        assert bf1.config.HOME_DIR == "/tmp/test"
        assert bf1.config.DEBUG is False
        assert bf1.config.PORT == 9000
        assert bf1.home_dir == "/tmp/test"  # Property should work

        # Test 2: Initialize with full config
        config = BlackfishConfig(
            home_dir="/tmp/test2",
            port=8080,
            debug=True,
            container_provider=ContainerProvider.Docker,
        )
        bf2 = Blackfish(config=config)
        assert bf2.config.HOME_DIR == "/tmp/test2"
        assert bf2.config.PORT == 8080
        assert bf2.config.DEBUG is True

        # Test 3: Initialize with config + overrides
        bf3 = Blackfish(config=config, port=9999, debug=False)
        assert bf3.config.HOME_DIR == "/tmp/test2"  # From config
        assert bf3.config.PORT == 9999  # Overridden
        assert bf3.config.DEBUG is False  # Overridden

        # Test 4: Default initialization
        bf4 = Blackfish()
        assert bf4.config.HOME_DIR == str(Path.home() / ".blackfish")
        assert bf4.config.DEBUG is False


class TestSyncAPI:
    """Test the synchronous API wrappers.

    Note: Sync wrappers cannot be tested from within async context.
    These tests verify that the sync API exists and has the correct signature.
    The underlying async functionality is tested in TestBlackfishClient.
    """

    async def test_sync_methods_exist(self, blackfish_client: Blackfish):
        """Test that sync methods exist with correct signatures."""
        # Verify methods exist
        assert hasattr(blackfish_client, "launch_service")
        assert hasattr(blackfish_client, "get_service")
        assert hasattr(blackfish_client, "list_services")
        assert hasattr(blackfish_client, "stop_service")
        assert hasattr(blackfish_client, "delete_service")
        assert hasattr(blackfish_client, "wait_for_service")
        assert hasattr(blackfish_client, "close")

        # Verify they are callable
        assert callable(blackfish_client.launch_service)
        assert callable(blackfish_client.get_service)
        assert callable(blackfish_client.list_services)
        assert callable(blackfish_client.stop_service)
        assert callable(blackfish_client.delete_service)
        assert callable(blackfish_client.wait_for_service)
        assert callable(blackfish_client.close)

    async def test_context_managers_exist(self, blackfish_client: Blackfish):
        """Test that context manager methods exist."""
        assert hasattr(blackfish_client, "__enter__")
        assert hasattr(blackfish_client, "__exit__")
        assert hasattr(blackfish_client, "__aenter__")
        assert hasattr(blackfish_client, "__aexit__")


class TestManagedService:
    """Test the ManagedService wrapper."""

    async def test_managed_service_attributes(self, blackfish_client: Blackfish):
        """Test that ManagedService properly exposes Service attributes."""
        from blackfish import ManagedService
        from blackfish.server.services.text_generation import TextGeneration

        # Create a dummy service
        service = TextGeneration(
            name="test-service",
            model="test-model",
            profile="default",
            home_dir="/tmp",
            cache_dir="/tmp/cache",
            host="localhost",
            provider="docker",
        )

        # Wrap it
        managed = ManagedService(service, blackfish_client)

        # Test attribute access
        assert managed.name == "test-service"
        assert managed.model == "test-model"
        assert managed.id == service.id
        # Status is None until the service is started
        assert managed.status is None

    async def test_managed_service_methods_exist(self, blackfish_client: Blackfish):
        """Test that ManagedService has expected methods."""
        from blackfish import ManagedService
        from blackfish.server.services.text_generation import TextGeneration

        # Create a dummy service
        service = TextGeneration(
            name="test-service",
            model="test-model",
            profile="default",
            home_dir="/tmp",
            cache_dir="/tmp/cache",
            host="localhost",
            provider="docker",
        )

        # Wrap it
        managed = ManagedService(service, blackfish_client)

        # Check that methods exist
        assert hasattr(managed, "async_refresh")
        assert hasattr(managed, "refresh")
        assert hasattr(managed, "async_stop")
        assert hasattr(managed, "stop")
        assert hasattr(managed, "async_delete")
        assert hasattr(managed, "delete")
        assert hasattr(managed, "async_wait")
        assert hasattr(managed, "wait")

        # Verify they're callable
        assert callable(managed.async_refresh)
        assert callable(managed.refresh)
        assert callable(managed.async_stop)
        assert callable(managed.stop)
        assert callable(managed.async_delete)
        assert callable(managed.delete)
        assert callable(managed.async_wait)
        assert callable(managed.wait)


class TestLoggingControl:
    """Test the global logging level control."""

    def test_set_logging_level_valid(self):
        """Test setting valid logging levels."""
        from blackfish.server.logger import logger

        # Test each valid level
        for level_name in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            set_logging_level(level_name)
            expected_level = getattr(logging, level_name)
            # Check that all handlers are set to the correct level
            for handler in logger.handlers:
                assert handler.level == expected_level

        # Test case insensitivity
        set_logging_level("debug")
        for handler in logger.handlers:
            assert handler.level == logging.DEBUG

    def test_set_logging_level_invalid(self):
        """Test that invalid logging levels raise ValueError."""
        with pytest.raises(ValueError, match="Invalid logging level"):
            set_logging_level("INVALID")

        with pytest.raises(ValueError, match="Invalid logging level"):
            set_logging_level("trace")

    def test_blackfish_sets_warning_by_default(self):
        """Test that creating a Blackfish client sets logging to WARNING."""
        from blackfish.server.logger import logger

        # Reset to INFO first
        set_logging_level("INFO")
        for handler in logger.handlers:
            assert handler.level == logging.INFO

        # Create a new client (don't need database for this test)
        _ = Blackfish(home_dir=str(Path(__file__).parent.parent / "tests"))

        # Should now be at WARNING
        for handler in logger.handlers:
            assert handler.level == logging.WARNING


class TestWaitResult:
    """Tests for ManagedService.wait's return contract (#470).

    `wait` reports what happened without prescribing a response: HEALTHY and
    FAILED describe the service, while the TIMEOUT_* outcomes describe the
    caller giving up, tagged by the phase the service was in.
    """

    def _managed(self, status):
        """A ManagedService whose refreshes are driven by the test."""
        from unittest.mock import MagicMock

        from blackfish import ManagedService

        service = MagicMock()
        service.status = status
        return ManagedService(service, MagicMock())

    def _clock(self, step=10.0):
        """A monotonic clock that advances `step` seconds per reading.

        Keeps timeout tests deterministic instead of racing real wall-clock.
        """
        from itertools import count

        ticks = count(0.0, step)
        return lambda: next(ticks)

    async def test_cached_healthy_returns_immediately(self):
        from blackfish import ServiceStatus, WaitOutcome

        svc = self._managed(ServiceStatus.HEALTHY)
        result = await svc.async_wait(timeout=0)

        assert result.outcome is WaitOutcome.HEALTHY
        assert result.status == ServiceStatus.HEALTHY
        assert result  # WaitResult is truthy only when healthy

    async def test_cached_terminal_returns_failed(self):
        from blackfish import ServiceStatus, WaitOutcome

        svc = self._managed(ServiceStatus.FAILED)
        result = await svc.async_wait(timeout=0)

        assert result.outcome is WaitOutcome.FAILED
        assert not result

    async def test_refreshes_before_sleeping(self):
        """A service that just became healthy is not missed for a full interval.

        The cached status is stale, so the first fresh read must happen before
        any sleep — otherwise a service healthy moments ago costs poll_interval.
        """
        from unittest.mock import AsyncMock, patch

        from blackfish import ServiceStatus, WaitOutcome

        svc = self._managed(ServiceStatus.SUBMITTED)
        refresh = AsyncMock(return_value=ServiceStatus.HEALTHY)
        with (
            patch.object(type(svc), "_refresh_status", refresh),
            patch("blackfish.service.asyncio.sleep", AsyncMock()) as sleep,
        ):
            result = await svc.async_wait(timeout=300, poll_interval=10)

        assert result.outcome is WaitOutcome.HEALTHY
        refresh.assert_awaited_once()
        sleep.assert_not_awaited()

    async def test_timeout_while_queued_is_tagged_pending(self):
        from unittest.mock import AsyncMock, patch

        from blackfish import ServiceStatus, WaitOutcome

        svc = self._managed(ServiceStatus.SUBMITTED)
        refresh = AsyncMock(return_value=ServiceStatus.PENDING)
        with (
            patch.object(type(svc), "_refresh_status", refresh),
            patch("blackfish.service.asyncio.sleep", AsyncMock()),
            patch("blackfish.service.time.monotonic", self._clock()),
        ):
            result = await svc.async_wait(timeout=30, poll_interval=10)

        assert result.outcome is WaitOutcome.TIMEOUT_PENDING
        assert result.status == ServiceStatus.PENDING
        assert not result

    async def test_timeout_while_starting_is_tagged_starting(self):
        from unittest.mock import AsyncMock, patch

        from blackfish import ServiceStatus, WaitOutcome

        svc = self._managed(ServiceStatus.SUBMITTED)
        refresh = AsyncMock(return_value=ServiceStatus.STARTING)
        with (
            patch.object(type(svc), "_refresh_status", refresh),
            patch("blackfish.service.asyncio.sleep", AsyncMock()),
            patch("blackfish.service.time.monotonic", self._clock()),
        ):
            result = await svc.async_wait(timeout=30, poll_interval=10)

        assert result.outcome is WaitOutcome.TIMEOUT_STARTING
        assert result.status == ServiceStatus.STARTING

    async def test_polls_until_healthy(self):
        from unittest.mock import AsyncMock, patch

        from blackfish import ServiceStatus, WaitOutcome

        svc = self._managed(ServiceStatus.SUBMITTED)
        refresh = AsyncMock(
            side_effect=[
                ServiceStatus.PENDING,
                ServiceStatus.STARTING,
                ServiceStatus.HEALTHY,
            ]
        )
        with (
            patch.object(type(svc), "_refresh_status", refresh),
            patch("blackfish.service.asyncio.sleep", AsyncMock()),
        ):
            result = await svc.async_wait(timeout=300, poll_interval=0)

        assert result.outcome is WaitOutcome.HEALTHY
        assert refresh.await_count == 3

    async def test_terminal_state_during_polling_returns_failed(self):
        from unittest.mock import AsyncMock, patch

        from blackfish import ServiceStatus, WaitOutcome

        svc = self._managed(ServiceStatus.SUBMITTED)
        refresh = AsyncMock(side_effect=[ServiceStatus.STARTING, ServiceStatus.TIMEOUT])
        with (
            patch.object(type(svc), "_refresh_status", refresh),
            patch("blackfish.service.asyncio.sleep", AsyncMock()),
        ):
            result = await svc.async_wait(timeout=300, poll_interval=0)

        assert result.outcome is WaitOutcome.FAILED
        assert result.status == ServiceStatus.TIMEOUT

    async def test_unbounded_wait_never_times_out(self):
        """With timeout=None only HEALTHY and FAILED are reachable."""
        from unittest.mock import AsyncMock, patch

        from blackfish import ServiceStatus, WaitOutcome

        svc = self._managed(ServiceStatus.SUBMITTED)
        refresh = AsyncMock(
            side_effect=[ServiceStatus.PENDING] * 5 + [ServiceStatus.HEALTHY]
        )
        with (
            patch.object(type(svc), "_refresh_status", refresh),
            patch("blackfish.service.asyncio.sleep", AsyncMock()),
        ):
            result = await svc.async_wait(timeout=None, poll_interval=0)

        assert result.outcome is WaitOutcome.HEALTHY
        assert refresh.await_count == 6

    async def test_elapsed_is_recorded(self):
        from blackfish import ServiceStatus

        svc = self._managed(ServiceStatus.HEALTHY)
        result = await svc.async_wait(timeout=0)

        assert result.elapsed >= 0

    def test_sync_wrapper_returns_the_result(self):
        """The sync wait() forwards the WaitResult from async_wait.

        Not an async test: `_async_to_sync` refuses to run from inside a
        running event loop, so this must call it from sync context.
        """
        from blackfish import ServiceStatus, WaitOutcome

        svc = self._managed(ServiceStatus.HEALTHY)
        result = svc.wait(timeout=0)

        assert result.outcome is WaitOutcome.HEALTHY
        assert result

    async def test_sleep_is_clamped_to_the_remaining_time(self):
        """The final sleep must not overshoot the caller's deadline."""
        from unittest.mock import AsyncMock, patch

        from blackfish import ServiceStatus

        svc = self._managed(ServiceStatus.SUBMITTED)
        refresh = AsyncMock(return_value=ServiceStatus.PENDING)
        sleep = AsyncMock()
        # A clock that has already consumed 7s of a 10s budget by the time the
        # loop reaches its sleep, leaving 3s: an unclamped 10s sleep would
        # overshoot the deadline by 7s.
        with (
            patch.object(type(svc), "_refresh_status", refresh),
            patch("blackfish.service.asyncio.sleep", sleep),
            patch("blackfish.service.time.monotonic", self._clock(step=7.0)),
        ):
            await svc.async_wait(timeout=10, poll_interval=10)

        assert sleep.await_args_list, "expected at least one sleep"
        first = sleep.await_args_list[0].args[0]
        assert first < 10, f"sleep was not clamped to the remaining budget: {first}"

    async def test_refresh_errors_propagate(self):
        """A failing refresh is not swallowed by the spinner context."""
        from unittest.mock import AsyncMock, patch

        import pytest as _pytest

        from blackfish import ServiceStatus

        svc = self._managed(ServiceStatus.SUBMITTED)
        refresh = AsyncMock(side_effect=RuntimeError("boom"))
        with (
            patch.object(type(svc), "_refresh_status", refresh),
            patch("blackfish.service.asyncio.sleep", AsyncMock()),
        ):
            with _pytest.raises(RuntimeError, match="boom"):
                await svc.async_wait(timeout=30, poll_interval=0)


class TestServiceURL:
    """Tests for ManagedService.url (#458)."""

    def _managed(self, *, port, status=None, service_id="svc-1"):
        from unittest.mock import MagicMock

        from blackfish import ManagedService

        service = MagicMock()
        service.port = port
        service.status = status
        service.id = service_id
        return ManagedService(service, MagicMock())

    def test_url_is_localhost_not_the_login_node(self):
        """Slurm services are reached through a tunnel, never via `host`."""
        from blackfish import ServiceStatus

        svc = self._managed(port=8080, status=ServiceStatus.HEALTHY)
        svc._service.host = "della.princeton.edu"

        assert svc.url == "http://localhost:8080"
        assert "della" not in svc.url

    def test_url_composes_with_a_client_base_url(self):
        from blackfish import ServiceStatus

        svc = self._managed(port=9001, status=ServiceStatus.HEALTHY)

        assert f"{svc.url}/v1" == "http://localhost:9001/v1"

    def test_url_raises_when_there_is_no_port(self):
        import pytest as _pytest

        from blackfish import ServiceNotReachableError, ServiceStatus

        svc = self._managed(port=None, status=ServiceStatus.PENDING)

        with _pytest.raises(ServiceNotReachableError) as exc:
            _ = svc.url

        # The message should name the service and say what to do about it.
        assert "svc-1" in str(exc.value)
        assert "pending" in str(exc.value)
        assert "wait" in str(exc.value).lower()

    def test_error_carries_the_service_id_and_status(self):
        import pytest as _pytest

        from blackfish import ServiceNotReachableError, ServiceStatus

        svc = self._managed(port=None, status=ServiceStatus.STOPPED)

        with _pytest.raises(ServiceNotReachableError) as exc:
            _ = svc.url

        assert exc.value.service_id == "svc-1"
        assert exc.value.status == ServiceStatus.STOPPED

    def test_error_is_a_runtime_error(self):
        """Subclasses RuntimeError so existing handlers still catch it."""
        from blackfish import ServiceNotReachableError

        assert issubclass(ServiceNotReachableError, RuntimeError)

    def test_url_on_a_deleted_service_raises(self):
        import pytest as _pytest

        from blackfish import ManagedService

        svc = ManagedService(None, None)  # type: ignore[arg-type]

        with _pytest.raises(RuntimeError, match="deleted"):
            _ = svc.url
