"""ManagedService wrapper class for the Blackfish programmatic interface."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, Optional, Self

from yaspin import yaspin
from log_symbols.symbols import LogSymbols

from blackfish.server.services.base import ServiceStatus
from blackfish.utils import _async_to_sync

if TYPE_CHECKING:
    from blackfish.server.services.base import Service
    from blackfish.client import Blackfish


class WaitOutcome(StrEnum):
    """Why `ManagedService.wait` stopped waiting.

    HEALTHY and FAILED describe the service. The TIMEOUT_* outcomes describe
    the *caller* giving up, tagged by the phase the service was in, and are
    only reachable when `wait` is given a maximum waiting time.
    """

    HEALTHY = auto()
    """The service became healthy."""

    FAILED = auto()
    """The service reached a terminal state (FAILED, TIMEOUT or STOPPED)."""

    TIMEOUT_PENDING = auto()
    """Gave up while the job was still queued; the scheduler had not run it."""

    TIMEOUT_STARTING = auto()
    """Gave up after the job started but before the service answered a ping."""


@dataclass(frozen=True)
class WaitResult:
    """The outcome of a `ManagedService.wait` call.

    `wait` reports what happened and leaves the response to the caller. In
    particular a timeout does not imply that a restart is warranted: the
    service may be healthy and merely slow to schedule.
    """

    outcome: WaitOutcome
    status: Optional[ServiceStatus]
    """The service's status when waiting stopped."""

    elapsed: float
    """Seconds spent waiting."""

    def __bool__(self) -> bool:
        """True only when the service became healthy."""
        return self.outcome is WaitOutcome.HEALTHY


class ManagedService:
    """Wrapper around Service that provides convenient access to service methods.

    This class wraps a Service object and provides easy-to-use methods that don't
    require passing session and state objects. All operations are delegated to the
    parent Blackfish client.
    """

    TERMINAL_STATUSES = (
        ServiceStatus.FAILED,
        ServiceStatus.TIMEOUT,
        ServiceStatus.STOPPED,
    )

    PENDING_STATUSES = (
        ServiceStatus.SUBMITTED,
        ServiceStatus.PENDING,
    )

    def __init__(self, service: Service, client: Blackfish):
        """Initialize a managed service.

        Args:
            service: The underlying Service object
            client: The Blackfish client managing this service
        """
        self._service: Service | None = service
        self._client = client

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the underlying service."""
        if self._service is None:
            raise RuntimeError(
                "This service has been deleted and can no longer be accessed."
            )
        return getattr(self._service, name)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ManagedService({self._service!r})"

    async def async_refresh(self) -> Self:
        """Refresh the service status (async).

        Returns:
            Self for method chaining
        """
        with yaspin(text="Refreshing service status...") as spinner:
            async with self._client._session() as session:
                # Merge the detached service into this session
                self._service = await session.merge(self._service)
                if self._service is not None:
                    await self._service.refresh(
                        session, self._client._ensure_http_client()
                    )
                else:
                    raise RuntimeError("self._service is None")
                # Don't call session.refresh() - refresh() modifies status and we want to keep that change
                # The commit will happen when the session context exits
            spinner.text = f"Service status: {self._service.status.value if self._service.status else 'unknown'}"
            spinner.ok(f"{LogSymbols.SUCCESS.value}")
        return self

    def refresh(self) -> Self:
        """Refresh the service status (sync).

        Returns:
            Self for method chaining
        """
        return _async_to_sync(self.async_refresh)()

    async def async_stop(self, timeout: bool = False, failed: bool = False) -> Self:
        """Stop the service (async).

        Args:
            timeout: Mark as timed out
            failed: Mark as failed

        Returns:
            Self for method chaining
        """
        with yaspin(text="Stopping service...") as spinner:
            async with self._client._session() as session:
                self._service = await session.merge(self._service)
                if self._service is not None:
                    await self._service.stop(session, timeout=timeout, failed=failed)
                else:
                    raise RuntimeError("self._service is None")
            spinner.text = f"Service stopped: {self._service.id}"
            spinner.ok(f"{LogSymbols.SUCCESS.value}")
        return self

    def stop(self, timeout: bool = False, failed: bool = False) -> Self:
        """Stop the service (sync).

        Args:
            timeout: Mark as timed out
            failed: Mark as failed

        Returns:
            Self for method chaining
        """
        return _async_to_sync(self.async_stop)(timeout=timeout, failed=failed)

    async def async_close_tunnel(self) -> Self:
        """Close the SSH tunnel for this service (async).

        This is useful when a service didn't properly release its port.
        Finds and kills SSH processes associated with the service's port.

        Returns:
            Self for method chaining
        """
        with yaspin(text="Closing SSH tunnel...") as spinner:
            async with self._client._session() as session:
                self._service = await session.merge(self._service)
                if self._service is not None:
                    await self._service.close_tunnel(session)
                else:
                    raise RuntimeError("self._service is None")
            spinner.text = f"Closed tunnel for service: {self._service.id}"
            spinner.ok(f"{LogSymbols.SUCCESS.value}")
        return self

    def close_tunnel(self) -> Self:
        """Close the SSH tunnel for this service (sync).

        This is useful when a service didn't properly release its port.
        Finds and kills SSH processes associated with the service's port.

        Returns:
            Self for method chaining
        """
        return _async_to_sync(self.async_close_tunnel)()

    async def async_delete(self) -> bool:
        """Delete the service from the database (async).

        Returns:
            True if deleted successfully
        """
        if self._service is None:
            raise RuntimeError("self._service is None")

        with yaspin(text="Deleting service...") as spinner:
            result = await self._client.async_delete_service(str(self._service.id))
            if result:
                spinner.text = f"Service deleted: {self._service.id}"
                spinner.ok(f"{LogSymbols.SUCCESS.value}")
                # Mark service as deleted to prevent further operations
                self._service = None
            else:
                spinner.text = "Service not found"
                spinner.fail(f"{LogSymbols.ERROR.value}")
        return result

    def delete(self) -> bool:
        """Delete the service from the database (sync).

        Returns:
            True if deleted successfully
        """
        return _async_to_sync(self.async_delete)()

    async def _refresh_status(self) -> Optional[ServiceStatus]:
        """Refresh the underlying service and return its current status."""
        async with self._client._session() as session:
            self._service = await session.merge(self._service)
            if self._service is None:
                raise RuntimeError("self._service is None")
            await self._service.refresh(session, self._client._ensure_http_client())
            # Access the attribute before the session closes.
            return self._service.status

    async def async_wait(
        self,
        timeout: Optional[float] = 300,
        poll_interval: float = 10,
    ) -> WaitResult:
        """Wait for the service to become healthy.

        Args:
            timeout: Maximum time to wait in seconds, or None to wait
                indefinitely (default: 300)
            poll_interval: Time between status checks in seconds (default: 10)

        Returns:
            WaitResult: what happened, the service's final status, and how long
            waiting took. The result is falsy unless the service became
            healthy, so it can be tested directly.

        Note:
            A TIMEOUT_* outcome means the caller ran out of patience, not that
            the service is broken; a queued job may simply not have been
            scheduled yet. Deciding what to do about it is the caller's.

        Examples:
            ```pycon
            >>> service = await bf.async_launch_service(...)
            >>> result = await service.async_wait()
            >>> if result:
            ...     print(f"Service ready on port {service.port}")
            ... elif result.outcome is WaitOutcome.TIMEOUT_PENDING:
            ...     print("Still queued; waiting longer")
            ```
        """

        if self._service is None:
            raise RuntimeError("self._service is None")

        # monotonic() cannot jump backwards if the system clock is adjusted,
        # which would otherwise corrupt the deadline and the elapsed time.
        start_time = time.monotonic()

        def _result(
            outcome: WaitOutcome, status: Optional[ServiceStatus]
        ) -> WaitResult:
            return WaitResult(
                outcome=outcome, status=status, elapsed=time.monotonic() - start_time
            )

        def _timed_out(status: Optional[ServiceStatus]) -> WaitResult:
            """Tag a timeout by the phase the service was in when we gave up.

            An unknown status (None, which `Service.status` permits) is
            reported as TIMEOUT_STARTING: the job was neither queued nor
            conclusively finished, so startup is the closest description.
            """
            outcome = (
                WaitOutcome.TIMEOUT_PENDING
                if status in self.PENDING_STATUSES
                else WaitOutcome.TIMEOUT_STARTING
            )
            return _result(outcome, status)

        with yaspin(text="Waiting for service to be healthy...") as spinner:
            # The cached status is only a snapshot of the last observation, so
            # it is trusted only when already conclusive. Anything else is
            # re-checked against the service before sleeping, so a service that
            # became healthy moments ago is not missed for a whole interval.
            status = self._service.status
            if status not in (ServiceStatus.HEALTHY, *self.TERMINAL_STATUSES):
                status = await self._refresh_status()

            while True:
                if status == ServiceStatus.HEALTHY:
                    spinner.text = "Service is ready!"
                    spinner.ok(f"{LogSymbols.SUCCESS.value}")
                    return _result(WaitOutcome.HEALTHY, status)

                if status in self.TERMINAL_STATUSES:
                    spinner.text = (
                        "Service failed with terminal state:"
                        f" {status.value if status else 'unknown'}"
                    )
                    spinner.fail(f"{LogSymbols.ERROR.value}")
                    return _result(WaitOutcome.FAILED, status)

                remaining = (
                    None
                    if timeout is None
                    else timeout - (time.monotonic() - start_time)
                )
                if remaining is not None and remaining <= 0:
                    spinner.text = (
                        "Timeout reached. Current status:"
                        f" {status.value if status else 'unknown'}"
                    )
                    spinner.fail(f"{LogSymbols.WARNING.value}")
                    return _timed_out(status)

                # Clamp the sleep to what is left so the call does not overshoot
                # the caller's deadline by up to a full interval.
                await asyncio.sleep(
                    poll_interval
                    if remaining is None
                    else min(poll_interval, remaining)
                )
                status = await self._refresh_status()

    def wait(
        self,
        timeout: Optional[float] = 300,
        poll_interval: float = 10,
    ) -> WaitResult:
        """Wait for the service to become healthy (sync).

        See async_wait for details.
        """

        return _async_to_sync(self.async_wait)(
            timeout=timeout, poll_interval=poll_interval
        )
