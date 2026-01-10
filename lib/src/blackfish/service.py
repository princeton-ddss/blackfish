"""ManagedService wrapper class for the Blackfish programmatic interface."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, Self

from yaspin import yaspin
from log_symbols.symbols import LogSymbols

from blackfish.server.services.base import ServiceStatus
from blackfish.utils import _async_to_sync

if TYPE_CHECKING:
    from blackfish.server.services.base import Service
    from blackfish.client import Blackfish


class ManagedService:
    """Wrapper around Service that provides convenient access to service methods.

    This class wraps a Service object and provides easy-to-use methods that don't
    require passing session and state objects. All operations are delegated to the
    parent Blackfish client.
    """

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
                    await self._service.refresh(session, self._client._state)
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

    async def async_wait(
        self,
        timeout: float = 300,
        poll_interval: float = 10,
    ) -> Self:
        """Wait for the service to be healthy.

        Args:
            timeout: Maximum time to wait in seconds (default: 300)
            poll_interval: Time between status checks in seconds (default: 10)

        Returns:
            Self (for method chaining), or None if service not found

        Examples:
            ```pycon
            >>> service = await bf.async_launch_service(...)
            >>> service = await service.async_wait()
            >>> if service and service.status == ServiceStatus.HEALTHY:
            ...     print(f"Service ready on port {service.port}")
            ```
        """

        target_status = ServiceStatus.HEALTHY

        if self._service is None:
            raise RuntimeError("self._service is None")

        with yaspin(text="Waiting for service to be healthy...") as spinner:
            # Check current status first without refreshing - might already be healthy or terminal
            current_status = self._service.status

            if current_status == target_status:
                spinner.text = "Service is ready!"
                spinner.ok(f"{LogSymbols.SUCCESS.value}")
                return self

            if current_status in [
                ServiceStatus.FAILED,
                ServiceStatus.TIMEOUT,
                ServiceStatus.STOPPED,
            ]:
                spinner.text = (
                    f"Service failed with terminal state: {current_status.value}"
                )
                spinner.fail(f"{LogSymbols.ERROR.value}")
                return self

            # Start polling
            start_time = time.time()
            while time.time() - start_time < timeout:
                await asyncio.sleep(poll_interval)

                # Refresh the underlying service
                async with self._client._session() as session:
                    self._service = await session.merge(self._service)
                    if self._service is not None:
                        await self._service.refresh(session, self._client._state)
                        # Access attributes to ensure they're loaded before session closes
                        current_status = self._service.status
                    else:
                        raise RuntimeError("self._service is None")

                if current_status == target_status:
                    spinner.text = "Service is ready!"
                    spinner.ok(f"{LogSymbols.SUCCESS.value}")
                    return self

                if current_status in [
                    ServiceStatus.FAILED,
                    ServiceStatus.TIMEOUT,
                    ServiceStatus.STOPPED,
                ]:
                    spinner.text = (
                        f"Service failed with terminal state: {current_status.value}"
                    )
                    spinner.fail(f"{LogSymbols.ERROR.value}")
                    return self

            # Timeout - do final check
            async with self._client._session() as session:
                self._service = await session.merge(self._service)
                if self._service is not None:
                    await self._service.refresh(session, self._client._state)
                else:
                    raise RuntimeError("self._service is None")
                final_status = self._service.status

            spinner.text = f"Timeout reached. Current status: {final_status.value if final_status else 'unknown'}"
            spinner.fail(f"{LogSymbols.WARNING.value}")
            return self

    def wait(
        self,
        timeout: float = 300,
        poll_interval: float = 10,
    ) -> Self:
        """Wait for the service to be healthy (sync).

        Args:
            timeout: Maximum time to wait in seconds (default: 300)
            poll_interval: Time between status checks in seconds (default: 10)

        Returns:
            Self (for method chaining), or None if service not found
        """

        return _async_to_sync(self.async_wait)(
            timeout=timeout, poll_interval=poll_interval
        )
