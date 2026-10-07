"""ManagedService wrapper class for the Blackfish programmatic interface."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, Literal, Optional, Self
from uuid import UUID

from log_symbols.symbols import LogSymbols

from blackfish.server.logger import logger
from blackfish.server.services.base import ServiceStatus
from blackfish.utils import _async_to_sync, _spinner

if TYPE_CHECKING:
    from blackfish.server.services.base import Service
    from blackfish.client import Blackfish


class ServiceNotReachableError(RuntimeError):
    """Raised when a service has no address to send requests to.

    A service is reachable once its tunnel is open and its port recorded. That
    happens while the job starts, so a service that is still queued, or one
    that has stopped, has nothing to connect to.
    """

    def __init__(self, service_id: UUID, status: Optional[ServiceStatus] = None):
        self.service_id = service_id
        self.status = status
        detail = f" (status: {status.value})" if status is not None else ""
        super().__init__(
            f"Service {service_id} has no port and cannot be reached{detail}."
            " Wait for it to become healthy before requesting its url,"
            " e.g. `if service.wait(): ...`."
        )


ServiceImage = Literal["text_generation", "speech_recognition"]
"""The service images `launch_service` accepts."""


@dataclass(frozen=True)
class LaunchSpec:
    """The arguments a service was launched with, so it can be relaunched.

    `restart()` replays these rather than asking the caller to keep a launch
    dict in sync by hand.
    """

    name: str
    image: ServiceImage
    model: str
    profile_name: Optional[str] = None
    container_config: Optional[dict[str, Any]] = None
    job_config: Optional[dict[str, Any]] = None
    mount: Optional[str] = None
    grace_period: int = 0
    image_ref: Optional[str] = None


class RestartLimitExceeded(RuntimeError):
    """Raised when `ensure_healthy` has used up its restart budget.

    Distinguishes "gave up relaunching" from any other failure, so a caller can
    tell a broken model from a transient problem.
    """

    def __init__(self, service_id: Optional[UUID], max_restarts: int):
        self.service_id = service_id
        self.max_restarts = max_restarts
        super().__init__(
            f"Service {service_id} could not be brought back after"
            f" {max_restarts} restart(s). The model or its configuration is"
            " likely at fault; check the job logs."
        )


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

    def __init__(
        self,
        service: Service,
        client: Blackfish,
        launch_spec: Optional[LaunchSpec] = None,
    ):
        """Initialize a managed service.

        Args:
            service: The underlying Service object
            client: The Blackfish client managing this service
            launch_spec: The arguments this service was launched with. Set by
                `launch_service`; required for `restart()` and
                `ensure_healthy()`, which replay it.
        """
        self._service: Service | None = service
        self._client = client
        self._launch_spec = launch_spec

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

    @property
    def url(self) -> str:
        """The base URL to send requests to.

        Always a `localhost` address: for a Slurm service, requests travel
        through an SSH tunnel, so `service.host` is the cluster's login node
        and *not* where requests go.

        Services expose several endpoints, so this is a base URL to hand to a
        client library rather than a complete request path. Text generation
        runs vLLM's OpenAI-compatible server:

        ```pycon
        >>> from openai import OpenAI
        >>> client = OpenAI(base_url=f"{service.url}/v1", api_key="EMPTY")
        ```

        Note:
            A recorded port means a tunnel was opened, not that it is still
            up. `stop()` closes the tunnel and clears the port, but a job that
            dies on its own is only noticed on the next `refresh()`, so until
            then `url` can return an address that no longer connects. Treat it
            as the service's last known address.

        Raises:
            ServiceNotReachableError: if the service has no port, i.e. its
                tunnel has never been opened or has been closed.
        """
        if self._service is None:
            raise RuntimeError(
                "This service has been deleted and can no longer be accessed."
            )
        if self._service.port is None:
            raise ServiceNotReachableError(self._service.id, self._service.status)
        return f"http://localhost:{self._service.port}"

    async def async_refresh(self) -> Self:
        """Refresh the service status (async).

        Returns:
            Self for method chaining
        """
        with _spinner(self._client.progress, "Refreshing service status...") as spinner:
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
        with _spinner(self._client.progress, "Stopping service...") as spinner:
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
        with _spinner(self._client.progress, "Closing SSH tunnel...") as spinner:
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

        with _spinner(self._client.progress, "Deleting service...") as spinner:
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

        with _spinner(
            self._client.progress, "Waiting for service to be healthy..."
        ) as spinner:
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

    async def async_restart(self) -> Self:
        """Stop this service and launch a replacement (async).

        The replacement is launched from the spec this service was created
        with, so the caller does not have to keep those arguments around. This
        object is repointed at the new service.

        The old service is stopped first but its record is removed only once the
        replacement is running: if the launch fails, the failed job's record and
        logs are still there to inspect, and this object remains usable so the
        caller can retry.

        Raises:
            RuntimeError: if the service was not created by `launch_service`
                and so has no spec to replay.
        """
        spec = self._launch_spec
        if spec is None:
            raise RuntimeError(
                "This service has no launch spec and cannot be restarted."
                " Only services created by `launch_service` can be restarted."
            )

        previous = self._service
        if previous is not None:
            try:
                await self.async_stop()
            except Exception as e:
                # The old job may already be gone; that is not a reason to
                # refuse to launch its replacement.
                logger.debug(f"Ignoring error while stopping before restart: {e}")

        # `auto_cleanup=False` because this wrapper is already tracked (or
        # deliberately not) by the client. Letting the replacement register
        # itself would leave two tracked wrappers for one service, and the
        # stale one would be reported as an orphan at exit.
        replacement = await self._client.async_launch_service(
            name=spec.name,
            image=spec.image,
            model=spec.model,
            profile_name=spec.profile_name,
            container_config=dict(spec.container_config or {}),
            job_config=dict(spec.job_config or {}),
            mount=spec.mount,
            grace_period=spec.grace_period,
            image_ref=spec.image_ref,
            auto_cleanup=False,
        )

        # Adopt the replacement so the caller keeps using the same object.
        self._service = replacement._service

        # The replacement is up, so the old record is safe to remove.
        if previous is not None:
            try:
                await self._client.async_delete_service(previous.id)
            except Exception as e:
                logger.debug(f"Ignoring error while deleting the old service: {e}")

        return self

    def restart(self) -> Self:
        """Stop this service and launch a replacement (sync).

        See async_restart for details.
        """
        return _async_to_sync(self.async_restart)()

    async def async_ensure_healthy(
        self,
        max_restarts: int = 3,
        timeout: Optional[float] = 300,
        poll_interval: float = 10,
    ) -> Self:
        """Make sure the service is answering, relaunching it if it is not.

        This is the primitive a long-running script needs: the script outlives
        the scheduler allocation, so it must notice when the service goes away
        and bring it back.

        `refresh()` is the check. It pings first and only falls back to the
        scheduler on failure, so the healthy case is cheap, and it re-opens a
        dropped tunnel — which a bare ping cannot do.

        A queued service is waited on rather than restarted: cancelling and
        resubmitting would only return it to the back of the queue, so
        TIMEOUT_PENDING does not consume the restart budget. Note that this
        means a job which never leaves the queue is waited on indefinitely —
        `timeout` bounds each individual wait, not the call as a whole. Any
        other non-healthy outcome counts against `max_restarts`.

        Args:
            max_restarts: How many relaunches to attempt before giving up
                (default: 3). Bounds the damage from a model that never loads.
            timeout: Passed to `wait` after each relaunch.
            poll_interval: Passed to `wait` after each relaunch.

        Returns:
            Self, once the service is healthy.

        Raises:
            RestartLimitExceeded: if the budget is used up.

        Examples:
            ```pycon
            >>> for chunk in work:
            ...     await service.async_ensure_healthy()
            ...     requests.post(f"{service.url}/v1/completions", ...)
            ```
        """
        restarts = 0
        # Captured up front so the error names the service even if a later
        # restart leaves the wrapper without one.
        service_id = self._service.id if self._service is not None else None

        while True:
            await self.async_refresh()
            if self._service is not None and self._service.status == (
                ServiceStatus.HEALTHY
            ):
                return self

            result = await self.async_wait(timeout=timeout, poll_interval=poll_interval)
            if result.outcome is WaitOutcome.HEALTHY:
                return self

            if result.outcome is WaitOutcome.TIMEOUT_PENDING:
                # Still queued. Nothing is wrong, so keep waiting rather than
                # spending a restart and losing our place in the queue.
                logger.debug(
                    "Service is still queued after"
                    f" {result.elapsed:.0f}s; continuing to wait."
                )
                continue

            if restarts >= max_restarts:
                raise RestartLimitExceeded(service_id, max_restarts)

            restarts += 1
            logger.warning(
                f"Service is {result.outcome}; relaunching"
                f" (attempt {restarts} of {max_restarts})."
            )
            await self.async_restart()

    def ensure_healthy(
        self,
        max_restarts: int = 3,
        timeout: Optional[float] = 300,
        poll_interval: float = 10,
    ) -> Self:
        """Make sure the service is answering, relaunching it if not (sync).

        See async_ensure_healthy for details.
        """
        return _async_to_sync(self.async_ensure_healthy)(
            max_restarts=max_restarts, timeout=timeout, poll_interval=poll_interval
        )
