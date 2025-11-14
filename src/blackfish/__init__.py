from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import (
    Optional,
    Any,
    Self,
    Callable,
    AsyncGenerator,
    TypeVar,
    ParamSpec,
    cast,
)
from functools import wraps
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from litestar.datastructures import State

from app.config import BlackfishConfig
from app.services.base import Service, ServiceStatus
from app.services.text_generation import TextGenerationConfig
from app.services.speech_recognition import SpeechRecognitionConfig
from app.job import JobScheduler, JobConfig
from app.utils import find_port
from yaspin import yaspin
from log_symbols.symbols import LogSymbols

# Import all service subclasses to register polymorphic identities with SQLAlchemy
from app.services.text_generation import TextGeneration  # noqa: F401
from app.services.speech_recognition import SpeechRecognition  # noqa: F401


def set_logging_level(level: str = "WARNING") -> None:
    """Set the global Blackfish logging level.

    This function controls the logging level for all Blackfish operations.
    By default, the programmatic interface uses WARNING level to reduce
    verbose output. Use this function to change the logging level globally.

    Args:
        level: Logging level string. Must be one of: "DEBUG", "INFO", "WARNING",
               "ERROR", or "CRITICAL". Case-insensitive.

    Examples:
        >>> import blackfish
        >>> blackfish.set_logging_level("INFO")  # Show info logs
        >>> blackfish.set_logging_level("DEBUG")  # Show all logs including debug
        >>> blackfish.set_logging_level("WARNING")  # Only warnings and errors (default)
    """
    import logging
    from app.logger import logger

    numeric_level = getattr(logging, level.upper(), None)
    if numeric_level is None:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        raise ValueError(
            f"Invalid logging level: {level}. Must be one of: {', '.join(valid_levels)}"
        )

    for handler in logger.handlers:
        handler.setLevel(numeric_level)


class ManagedService:
    """Wrapper around Service that provides convenient access to service methods.

    This class wraps a Service object and provides easy-to-use methods that don't
    require passing session and state objects. All operations are delegated to the
    parent Blackfish client.
    """

    def __init__(self, service: Service, client: "Blackfish"):
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

        Example:
            >>> service = await bf.async_create_service(...)
            >>> service = await service.async_wait()
            >>> if service and service.status == ServiceStatus.HEALTHY:
            ...     print(f"Service ready on port {service.port}")
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


P = ParamSpec("P")
T = TypeVar("T")


def _async_to_sync(async_func: Callable[P, Any]) -> Callable[P, T]:
    """Decorator to convert async methods to sync by running them in event loop."""

    @wraps(async_func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            # Try to get the running loop
            _ = asyncio.get_running_loop()
            # If we're already in an async context, just call the async function
            raise RuntimeError(
                f"Cannot call sync version of {async_func.__name__} from async context. "
                "Use the async version instead (prefix with 'a')."
            )
        except RuntimeError:
            # No running loop, we can create one
            return cast(T, asyncio.run(async_func(*args, **kwargs)))

    return wrapper


class Blackfish:
    """Programmatic interface for managing Blackfish ML inference services.

    This client provides both synchronous and asynchronous APIs for creating,
    managing, and monitoring ML inference services. All async methods are prefixed
    with 'async_' (e.g., async_create_service, async_list_services).

    Examples:
        Synchronous usage:
        >>> bf = Blackfish()
        >>> service = bf.create_service(
        ...     name="my-llm",
        ...     image="text_generation",
        ...     model="meta-llama/Llama-3.3-70B-Instruct",
        ...     profile_name="default"
        ... )
        >>> print(service.status)

        Asynchronous usage:
        >>> async def main():
        ...     bf = Blackfish()
        ...     service = await bf.async_create_service(
        ...         name="my-llm",
        ...         image="text_generation",
        ...         model="meta-llama/Llama-3.3-70B-Instruct",
        ...         profile_name="default"
        ...     )
        ...     print(service.status)
        >>> asyncio.run(main())
    """

    def __init__(
        self,
        home_dir: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        debug: Optional[bool] = None,
        auth_token: Optional[str] = None,
        config: Optional[BlackfishConfig] = None,
    ):
        """Initialize the Blackfish client.

        You can either pass a complete BlackfishConfig object, or pass individual
        configuration parameters. Individual parameters will override values from
        a provided config object.

        Args:
            home_dir: Path to Blackfish home directory (default: ~/.blackfish)
            host: API host (default: localhost)
            port: API port (default: 8000)
            debug: Debug mode (default: True)
            auth_token: Authentication token (optional)
            config: Optional BlackfishConfig instance for advanced configuration.
                   Individual parameters will override config values if provided.

        Examples:
            Simple usage:
            >>> bf = Blackfish(home_dir="~/.blackfish", debug=True)

            Advanced usage with full config:
            >>> config = BlackfishConfig(home_dir="~/.blackfish", port=9000)
            >>> bf = Blackfish(config=config)

            Mixed usage (config + overrides):
            >>> config = BlackfishConfig(...)
            >>> bf = Blackfish(config=config, port=9000)  # Override just the port
        """
        # Start with provided config or create default
        if config is None:
            self.config = BlackfishConfig(
                home_dir=home_dir or os.path.expanduser("~/.blackfish"),
                host=host or "localhost",
                port=port or 8000,
                debug=debug if debug is not None else True,
                auth_token=auth_token,
            )
        else:
            # Apply parameter overrides to existing config
            if any(
                param is not None for param in [home_dir, host, port, debug, auth_token]
            ):
                self.config = BlackfishConfig(
                    home_dir=home_dir or config.HOME_DIR,
                    host=host or config.HOST,
                    port=port or config.PORT,
                    static_dir=config.STATIC_DIR,
                    debug=debug if debug is not None else config.DEBUG,
                    auth_token=auth_token or config.AUTH_TOKEN,
                    container_provider=config.CONTAINER_PROVIDER,
                )
            else:
                self.config = config

        # Database setup
        db_path = Path(self.config.HOME_DIR) / "app.sqlite"
        connection_string = f"sqlite+aiosqlite:///{db_path}"

        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None
        self._connection_string = connection_string

        # Convert config to Litestar State for compatibility with base.py methods
        self._state = State(self.config.as_dict())

        # Set logging level to WARNING by default for cleaner programmatic interface
        set_logging_level("WARNING")

    @property
    def home_dir(self) -> str:
        """Get the Blackfish home directory."""
        return self.config.HOME_DIR

    def _ensure_engine(self) -> AsyncEngine:
        """Lazily initialize the database engine."""
        if self._engine is None:
            self._engine = create_async_engine(
                self._connection_string,
                echo=False,
            )
        return self._engine

    def _ensure_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        """Lazily initialize the session maker."""
        if self._sessionmaker is None:
            engine = self._ensure_engine()
            self._sessionmaker = async_sessionmaker(
                bind=engine,
                expire_on_commit=False,
            )
        return self._sessionmaker

    @asynccontextmanager
    async def _session(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager for database sessions."""
        sessionmaker = self._ensure_sessionmaker()
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _async_close(self) -> None:
        """Close the database engine."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None

    def close(self) -> None:
        """Close the database connection (sync wrapper)."""
        _async_to_sync(self._async_close)()

    # Service Management Methods

    async def async_create_service(
        self,
        name: str,
        image: str,
        model: str,
        profile_name: str = "default",
        container_config: Optional[dict[str, Any]] = None,
        job_config: Optional[dict[str, Any]] = None,
        mount: Optional[str] = None,
        grace_period: int = 180,
        **kwargs: dict[str, Any],  # BlackfishConfig
    ) -> ManagedService:
        """Create and start a new service (async).

        Args:
            name: Service name
            image: Service image type (e.g., "text_generation", "speech_recognition")
            model: Model repository ID (e.g., "meta-llama/Llama-3.3-70B-Instruct")
            profile_name: Name of the profile to use
            container_config: Container configuration options. If 'model_dir' and 'revision'
                are not provided, they will be automatically determined by searching for
                the model in the profile's cache directories and selecting the latest revision.
            job_config: Job configuration options (Slurm settings, etc.)
            mount: Optional directory to mount
            grace_period: Time in seconds to wait before marking unhealthy
            **kwargs: Additional service-specific parameters

        Returns:
            ManagedService: The created service instance wrapped for easy access

        Raises:
            ValueError: If the profile is not found, the model is not available,
                or model files cannot be located.
        """
        from app.models.profile import deserialize_profile

        # Load profile
        profile = deserialize_profile(self.home_dir, profile_name)
        if profile is None:
            raise ValueError(f"Profile '{profile_name}' not found")

        # Build service class mapping
        service_classes = {
            "text_generation": TextGeneration,
            "speech_recognition": SpeechRecognition,
        }

        ServiceClass = service_classes.get(image)
        if ServiceClass is None:
            raise ValueError(f"Unknown service image: {image}")

        # Prepare service parameters
        service_params = {
            "name": name,
            "model": model,
            "profile": profile.name,
            "home_dir": profile.home_dir,
            "cache_dir": profile.cache_dir,
            "mount": mount,
            "grace_period": grace_period,
            **kwargs,
        }

        # Add profile-specific parameters
        from app.models.profile import LocalProfile, SlurmProfile

        if isinstance(profile, LocalProfile):
            service_params["host"] = "localhost"
            service_params["provider"] = self.config.CONTAINER_PROVIDER
        elif isinstance(profile, SlurmProfile):
            service_params["host"] = profile.host
            service_params["user"] = profile.user
            service_params["scheduler"] = JobScheduler.Slurm

        # Create service instance
        service = ServiceClass(**service_params)

        # Prepare configs
        if container_config is None:
            container_config = {}
        if job_config is None:
            job_config = {}

        # Auto-assign port if not provided
        if "port" not in container_config or container_config.get("port") is None:
            container_config["port"] = find_port()

        # Auto-populate model_dir and revision if not provided
        needs_model_info = (
            "model_dir" not in container_config
            or container_config.get("model_dir") in (None, "")
            or "revision" not in container_config
            or container_config.get("revision") in (None, "")
        )

        if needs_model_info:
            from app.utils import (
                get_models,
                get_revisions,
                get_latest_commit,
                get_model_dir,
            )

            # Check if model is available
            available_models = get_models(profile)
            if model not in available_models:
                error_msg = (
                    f"{LogSymbols.ERROR.value} Model {model} is unavailable for profile "
                    f"'{profile_name}'. You can try adding it using `blackfish model add`."
                )
                print(error_msg)
                raise ValueError(
                    f"Model '{model}' is not available for profile '{profile_name}'. "
                    f"Available models: {', '.join(available_models) if available_models else 'none'}. "
                    "You can add models using the `blackfish model add` command."
                )

            # Get or select revision
            if container_config.get("revision") in (None, ""):
                available_revisions = get_revisions(model, profile)
                if not available_revisions:
                    error_msg = (
                        f"{LogSymbols.ERROR.value} No revisions found for model '{model}' "
                        f"in profile '{profile_name}'."
                    )
                    print(error_msg)
                    raise ValueError(
                        f"No revisions found for model '{model}' in profile '{profile_name}'."
                    )
                revision = get_latest_commit(model, available_revisions)
                container_config["revision"] = revision
                print(
                    f"{LogSymbols.WARNING.value} No revision provided. Using latest "
                    f"available commit: {revision}."
                )
            else:
                revision = container_config["revision"]

            # Get model directory
            if container_config.get("model_dir") in (None, ""):
                model_dir = get_model_dir(model, revision, profile)
                if model_dir is None:
                    error_msg = (
                        f"{LogSymbols.ERROR.value} The model directory for repo {model}[{revision}] "
                        f"could not be found for profile '{profile_name}'. These files may have been "
                        "moved or there may be an issue with permissions. You can try adding the model "
                        "using `blackfish model add`."
                    )
                    print(error_msg)
                    raise ValueError(
                        f"Could not find model directory for '{model}' [{revision}] in profile '{profile_name}'. "
                        "The model files may have been moved or there may be a permissions issue."
                    )
                container_config["model_dir"] = model_dir

        # Create appropriate config objects based on service type
        from app.job import SlurmJobConfig, LocalJobConfig

        # Map image type to config class
        container_cfg: TextGenerationConfig | SpeechRecognitionConfig
        if image == "text_generation":
            container_cfg = TextGenerationConfig(**container_config)
        elif image == "speech_recognition":
            container_cfg = SpeechRecognitionConfig(**container_config)
        else:
            raise ValueError(f"Unknown image type: {image}")

        job_cfg: JobConfig
        if isinstance(profile, SlurmProfile):
            job_cfg = SlurmJobConfig(**job_config)
        else:
            job_cfg = LocalJobConfig(**job_config)

        # Start the service
        with yaspin(text="Starting service...") as spinner:
            async with self._session() as session:
                await service.start(session, self._state, container_cfg, job_cfg)
            spinner.text = f"Started service: {service.id}"
            spinner.ok(f"{LogSymbols.SUCCESS.value}")

        return ManagedService(service, self)

    @_async_to_sync
    async def create_service(
        self,
        name: str,
        image: str,
        model: str,
        profile_name: str = "default",
        container_config: Optional[dict[str, Any]] = None,
        job_config: Optional[dict[str, Any]] = None,
        mount: Optional[str] = None,
        grace_period: int = 180,
        **kwargs: dict[str, Any],  # BlackfishConfig
    ) -> ManagedService:
        """Create and start a new service (sync wrapper).

        See async_create_service for details.
        """
        return await self.async_create_service(
            name,
            image,
            model,
            profile_name,
            container_config,
            job_config,
            mount,
            grace_period,
            **kwargs,
        )

    async def async_get_service(self, service_id: str) -> Optional[ManagedService]:
        """Get a service by ID (async).

        Args:
            service_id: UUID of the service

        Returns:
            ManagedService instance or None if not found
        """
        import sqlalchemy as sa
        from uuid import UUID

        async with self._session() as session:
            query = sa.select(Service).where(Service.id == UUID(service_id))
            result = await session.execute(query)
            service = result.scalar_one_or_none()

            if service is not None:
                await service.refresh(session, self._state)
                return ManagedService(service, self)

            return None

    @_async_to_sync
    async def get_service(self, service_id: str) -> Optional[ManagedService]:
        """Get a service by ID (sync wrapper).

        See async_get_service for details.
        """
        return await self.async_get_service(service_id)

    async def async_list_services(
        self,
        image: Optional[str] = None,
        model: Optional[str] = None,
        status: Optional[ServiceStatus] = None,
        name: Optional[str] = None,
        profile: Optional[str] = None,
    ) -> list[ManagedService]:
        """List services with optional filters (async).

        Args:
            image: Filter by image type
            model: Filter by model
            status: Filter by status
            name: Filter by name
            profile: Filter by profile

        Returns:
            List of matching managed services
        """
        import sqlalchemy as sa

        # Build query filters
        filters = {}
        if image is not None:
            filters["image"] = image
        if model is not None:
            filters["model"] = model
        if status is not None:
            filters["status"] = status
        if name is not None:
            filters["name"] = name
        if profile is not None:
            filters["profile"] = profile

        async with self._session() as session:
            query = sa.select(Service).filter_by(**filters)
            result = await session.execute(query)
            services = list(result.scalars().all())

            # Refresh all services and wrap them
            managed_services = []
            for service in services:
                await service.refresh(session, self._state)
                managed_services.append(ManagedService(service, self))

            return managed_services

    @_async_to_sync
    async def list_services(
        self,
        image: Optional[str] = None,
        model: Optional[str] = None,
        status: Optional[ServiceStatus] = None,
        name: Optional[str] = None,
        profile: Optional[str] = None,
    ) -> list[ManagedService]:
        """List services with optional filters (sync wrapper).

        See async_list_services for details.
        """
        return await self.async_list_services(image, model, status, name, profile)

    async def async_stop_service(
        self,
        service_id: str,
        timeout: bool = False,
        failed: bool = False,
    ) -> Optional[ManagedService]:
        """Stop a service (async).

        Args:
            service_id: UUID of the service
            timeout: Mark as timed out
            failed: Mark as failed

        Returns:
            Updated managed service instance or None if not found
        """
        managed_service = await self.async_get_service(service_id)
        if managed_service is None:
            return None

        async with self._session() as session:
            managed_service._service = await session.merge(managed_service._service)
            if managed_service._service is not None:
                await managed_service._service.stop(
                    session, timeout=timeout, failed=failed
                )
            else:
                raise RuntimeError("ManagedService._service is None")

        return managed_service

    @_async_to_sync
    async def stop_service(
        self,
        service_id: str,
        timeout: bool = False,
        failed: bool = False,
    ) -> Optional[ManagedService]:
        """Stop a service (sync wrapper).

        See async_stop_service for details.
        """
        return await self.async_stop_service(service_id, timeout, failed)

    async def async_delete_service(self, service_id: str) -> bool:
        """Delete a service from the database (async).

        Note: This only deletes the database record. The service should be
        stopped first using stop_service().

        Args:
            service_id: UUID of the service

        Returns:
            True if deleted, False if not found
        """
        import sqlalchemy as sa
        from uuid import UUID

        async with self._session() as session:
            query = sa.delete(Service).where(Service.id == UUID(service_id))
            result = await session.execute(query)
            return result.rowcount > 0

    @_async_to_sync
    async def delete_service(self, service_id: str) -> bool:
        """Delete a service from the database (sync wrapper).

        See async_delete_service for details.
        """
        return await self.async_delete_service(service_id)

    async def async_wait_for_service(
        self,
        service_id: str,
        target_status: ServiceStatus = ServiceStatus.HEALTHY,
        timeout: float = 300,
        poll_interval: float = 5,
    ) -> Optional[ManagedService]:
        """Wait for a service to reach a target status (async).

        Args:
            service_id: UUID of the service
            target_status: Status to wait for (default: HEALTHY)
            timeout: Maximum time to wait in seconds (default: 300)
            poll_interval: Time between status checks in seconds (default: 5)

        Returns:
            ManagedService instance if target status reached, None if timeout or service failed

        Example:
            >>> service = bf.create_service(...)
            >>> service = await bf.async_wait_for_service(str(service.id))
            >>> if service and service.status == ServiceStatus.HEALTHY:
            ...     print(f"Service ready on port {service.port}")
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            service = await self.async_get_service(service_id)

            if service is None:
                return None

            # Check if we've reached the target status
            if service.status == target_status:
                return service

            # Check for terminal failure states
            if service.status in [
                ServiceStatus.FAILED,
                ServiceStatus.TIMEOUT,
                ServiceStatus.STOPPED,
            ]:
                return service

            # Wait before next check
            await asyncio.sleep(poll_interval)

        # Timeout reached
        return await self.async_get_service(service_id)

    @_async_to_sync
    async def wait_for_service(
        self,
        service_id: str,
        target_status: ServiceStatus = ServiceStatus.HEALTHY,
        timeout: float = 300,
        poll_interval: float = 5,
    ) -> Optional[ManagedService]:
        """Wait for a service to reach a target status (sync wrapper).

        See async_wait_for_service for details.
        """
        return await self.async_wait_for_service(
            service_id, target_status, timeout, poll_interval
        )

    # Context manager support for resource cleanup

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self._async_close()

    def __enter__(self) -> Self:
        """Sync context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Sync context manager exit."""
        self.close()


__all__ = [
    "Blackfish",
    "ManagedService",
    "Service",
    "ServiceStatus",
    "set_logging_level",
]
