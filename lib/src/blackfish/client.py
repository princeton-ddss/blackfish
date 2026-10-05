"""Blackfish client for the programmatic interface."""

from __future__ import annotations

# Registers SQLite PRAGMA listener on SQLAlchemy's Engine class.
# Must be imported before any engine opens a connection.
import blackfish.server.db  # noqa: F401

import sys
import asyncio
import atexit
import os
import time
from uuid import UUID
from pathlib import Path
from dataclasses import asdict
from typing import Literal, Optional, Any, Self, AsyncGenerator
from contextlib import asynccontextmanager

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from litestar.datastructures import State
from log_symbols.symbols import LogSymbols

from blackfish.server.config import DEFAULT_DEBUG, BlackfishConfig, config
from blackfish.server.http_client import create_http_client
from blackfish.server.models.profile import (
    deserialize_profile,
    get_default_profile_name,
    LocalProfile,
    SlurmProfile,
)
from blackfish.server.services.base import Service, ServiceStatus
from blackfish.server.services.text_generation import (
    TextGeneration,
    TextGenerationConfig,
)
from blackfish.server.services.speech_recognition import (
    SpeechRecognition,
    SpeechRecognitionConfig,
)
from blackfish.server.job import JobScheduler, JobConfig, SlurmJobConfig, LocalJobConfig
from blackfish.server.utils import (
    find_port,
    get_models,
    get_revisions,
    get_latest_commit,
    get_model_dir,
)

from blackfish.service import ManagedService
from blackfish.server.logger import logger
from blackfish.utils import _async_to_sync, _spinner


ServiceImage = Literal["text_generation", "speech_recognition"]
"""The service images `launch_service` accepts."""

ContainerConfigLike = TextGenerationConfig | SpeechRecognitionConfig | dict[str, Any]
JobConfigLike = SlurmJobConfig | LocalJobConfig | dict[str, Any]


def _as_uuid(service_id: str | UUID) -> UUID:
    """Accept either spelling of a service id.

    `Service.id` is a UUID, so `bf.stop_service(service.id)` is the natural
    thing to write; it used to fail inside `UUID()`.
    """
    return service_id if isinstance(service_id, UUID) else UUID(service_id)


def _as_config_dict(
    value: Optional[ContainerConfigLike | JobConfigLike],
) -> dict[str, Any]:
    """Normalize a config argument to a plain dict.

    Callers may pass a typed config object (whose field names are checked) or
    a dict (which is not). Both are accepted; the typed objects are simply
    unpacked here so the rest of the function has one shape to work with.
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    return asdict(value)


class Blackfish:
    """Programmatic interface for managing Blackfish ML inference services.

    This client provides both synchronous and asynchronous APIs for creating,
    managing, and monitoring ML inference services. All async methods are prefixed
    with 'async_' (e.g., async_launch_service, async_list_services).

    Examples:
        Synchronous usage:
        ```pycon
        >>> bf = Blackfish()
        >>> service = bf.launch_service(
        ...     name="my-llm",
        ...     image="text_generation",
        ...     model="meta-llama/Llama-3.3-70B-Instruct",
        ...     profile_name="default"
        ... )
        >>> print(service.status)
        ```

        Asynchronous usage:
        ```pycon
        >>> async def main():
        ...     bf = Blackfish()
        ...     service = await bf.async_launch_service(
        ...         name="my-llm",
        ...         image="text_generation",
        ...         model="meta-llama/Llama-3.3-70B-Instruct",
        ...         profile_name="default"
        ...     )
        ...     print(service.status)
        >>> asyncio.run(main())
        ```
    """

    def __init__(
        self,
        home_dir: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        debug: Optional[bool] = None,
        auth_token: Optional[str] = None,
        config: Optional[BlackfishConfig] = None,
        progress: bool = False,
    ):
        """Initialize the Blackfish client.

        You can either pass a complete BlackfishConfig object, or pass individual
        configuration parameters. Individual parameters will override values from
        a provided config object.

        Args:
            home_dir: Path to Blackfish home directory (default: ~/.blackfish)
            host: API host (default: localhost)
            port: API port (default: 8000)
            debug: Debug mode, which disables API authentication
                (default: False)
            auth_token: Authentication token (optional)
            config: Optional BlackfishConfig instance for advanced configuration.
                   Individual parameters will override config values if provided.
            progress: Print spinners and progress messages (default: False).
                Useful in a notebook or REPL; leave off for scripts, where the
                output is noise. Read at call time, so assigning to
                `bf.progress` later affects services already created.

        Examples:
            Simple usage:
            ```pycon
            >>> bf = Blackfish(home_dir="~/.blackfish", debug=True)
            ```

            Advanced usage with full config:
            ```pycon
            >>> config = BlackfishConfig(home_dir="~/.blackfish", port=9000)
            >>> bf = Blackfish(config=config)
            ```

            Mixed usage (config + overrides):
            ```pycon
            >>> config = BlackfishConfig(...)
            >>> bf = Blackfish(config=config, port=9000)  # Override just the port
            ```
        """
        # Start with provided config or create default
        if config is None:
            self.config = BlackfishConfig(
                home_dir=home_dir or os.path.expanduser("~/.blackfish"),
                host=host or "localhost",
                port=port or 8000,
                debug=debug if debug is not None else DEFAULT_DEBUG,
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
        self._http_client: Optional[httpx.AsyncClient] = None

        # Convert config to Litestar State for compatibility with base.py methods
        self._state = State(self.config.as_dict())

        # Auto-cleanup tracking
        self._managed_services: list[ManagedService] = []
        atexit.register(self._cleanup_services)

        self.progress = progress

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

    def _ensure_http_client(self) -> httpx.AsyncClient:
        """Lazily initialize the shared HTTP client."""
        if self._http_client is None:
            self._http_client = create_http_client()
        return self._http_client

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
        """Close the database engine and HTTP client."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def close(self) -> None:
        """Close the database connection (sync wrapper)."""
        _async_to_sync(self._async_close)()

    def _cleanup_services(self) -> None:
        """Stop and delete tracked services on interpreter exit.

        Registered with atexit. Services hold expensive external resources, so
        tying their lifetime to the script prevents forgotten GPU allocations.
        Use `auto_cleanup=False` at launch for a service that should outlive
        the script.
        """
        if not self._managed_services:
            return

        print(
            f"🧹 Blackfish cleaning up {len(self._managed_services)} service(s)...",
            file=sys.stderr,
        )

        try:
            # A new event loop, in case the default one is already closed.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                stopped, undeleted, failed = loop.run_until_complete(
                    self._async_cleanup_services()
                )
            finally:
                loop.close()
        except Exception as e:
            # Last resort: cleanup could not run at all, so nothing was stopped.
            print(
                f"{LogSymbols.ERROR.value} Blackfish cleanup failed: {e}",
                file=sys.stderr,
            )
            self._report_orphans(
                [(m, None) for m in self._managed_services],
                reason="may still be running",
                command="stop",
            )
            return

        if stopped:
            print(
                f"{LogSymbols.SUCCESS.value} Blackfish stopped {stopped} service(s).",
                file=sys.stderr,
            )
        if undeleted:
            # The job was cancelled, so no allocation is leaking; only the
            # database record remains.
            print(
                f"{LogSymbols.WARNING.value} Blackfish stopped"
                f" {len(undeleted)} service(s) but could not remove their records.",
                file=sys.stderr,
            )
            self._report_orphans(
                undeleted, reason="stopped; record remains", command="rm"
            )
        if failed:
            print(
                f"{LogSymbols.ERROR.value} Blackfish could not stop"
                f" {len(failed)} service(s).",
                file=sys.stderr,
            )
            self._report_orphans(failed, reason="may still be running", command="stop")

    @staticmethod
    def _report_orphans(
        services: list[tuple[ManagedService, Optional[BaseException]]],
        reason: str,
        command: str,
    ) -> None:
        """Name services the caller has to deal with, and how."""
        for managed, error in services:
            service = managed._service
            if service is None:
                continue
            detail = f" [{type(error).__name__}: {error}]" if error is not None else ""
            print(
                f"  - {service.id} ({reason}):"
                f" blackfish {command} {service.id}{detail}",
                file=sys.stderr,
            )

    async def _async_cleanup_services(
        self,
    ) -> tuple[
        int,
        list[tuple[ManagedService, Optional[BaseException]]],
        list[tuple[ManagedService, Optional[BaseException]]],
    ]:
        """Stop and delete each tracked service.

        Each service is handled independently: stopping a Slurm service means
        SSH to the login node, which can fail during shutdown (a dropped
        network, an expired Kerberos ticket). One failure must not abandon the
        rest, or a `scancel` that never ran leaves an allocation burning
        GPU-hours until it hits its own time limit.

        Stopping and deleting are tracked separately because they fail
        differently: a failed stop may leave an allocation running, while a
        failed delete only leaves a database record behind.

        Returns:
            How many services were fully cleaned up; the ones stopped but not
            deleted; and the ones that could not be stopped, each paired with
            the error that stopped us.
        """
        stopped = 0
        undeleted: list[tuple[ManagedService, Optional[BaseException]]] = []
        failed: list[tuple[ManagedService, Optional[BaseException]]] = []

        for managed in self._managed_services:
            service = managed._service
            if service is None:
                continue

            try:
                await managed.async_stop()
            except Exception as e:
                logger.debug(f"Failed to stop service {service.id}: {e}")
                failed.append((managed, e))
                continue

            try:
                await managed.async_delete()
            except Exception as e:
                logger.debug(f"Failed to delete service {service.id}: {e}")
                undeleted.append((managed, e))
                continue

            stopped += 1

        return stopped, undeleted, failed

    async def async_launch_service(
        self,
        name: str,
        image: ServiceImage,
        model: str,
        profile_name: Optional[str] = None,
        container_config: Optional[ContainerConfigLike] = None,
        job_config: Optional[JobConfigLike] = None,
        mount: Optional[str] = None,
        grace_period: int = config.GRACE_PERIOD,
        image_ref: Optional[str] = None,
        auto_cleanup: bool = True,
        **kwargs: Any,
    ) -> ManagedService:
        """Create and start a new service (async).

        Args:
            name: Service name
            image: Service image type (e.g., "text_generation", "speech_recognition")
            model: Model repository ID (e.g., "meta-llama/Llama-3.3-70B-Instruct")
            profile_name: Name of the profile to use. If None, the configured
                default profile is used.
            container_config: Container configuration, either a typed config
                (TextGenerationConfig or SpeechRecognitionConfig, whose field
                names are checked) or a dict. If 'model_dir' and 'revision'
                are not provided, they will be automatically determined by searching for
                the model in the profile's cache directories and selecting the latest revision.
            job_config: Job configuration, either a typed config (SlurmJobConfig
                or LocalJobConfig) or a dict of Slurm settings.
            mount: Optional directory to mount
            grace_period: Time in seconds to wait before marking unhealthy
            image_ref: Pin the container image as "repo:tag" (e.g.
                "vllm/vllm-openai:v0.26.0"). None uses the configured image,
                which is then recorded on the service so restarts reuse it.
            auto_cleanup: If True, automatically stop and delete this service when the
                Python script exits (default: True)
            **kwargs: Additional values passed to the Service constructor,
                which raises TypeError for any name that is not a mapped
                attribute.

        Returns:
            ManagedService: The created service instance wrapped for easy access

        Raises:
            ValueError: If the profile is not found, the model is not available,
                or model files cannot be located.
        """

        # Load profile (falling back to the configured default)
        if profile_name is None:
            profile_name = get_default_profile_name(self.home_dir)
            if profile_name is None:
                raise ValueError("No profiles are configured.")

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
            "image_ref": image_ref,
            **kwargs,
        }

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
        # Accept typed config objects as well as dicts; normalize to one shape.
        container_options = _as_config_dict(container_config)
        job_options = _as_config_dict(job_config)

        # Auto-assign port if not provided
        if "port" not in container_options or container_options.get("port") is None:
            container_options["port"] = find_port()

        # Auto-populate model_dir and revision if not provided
        needs_model_info = (
            "model_dir" not in container_options
            or container_options.get("model_dir") in (None, "")
            or "revision" not in container_options
            or container_options.get("revision") in (None, "")
        )

        if needs_model_info:
            # Check if model is available
            available_models = get_models(profile)
            if model not in available_models:
                raise ValueError(
                    f"Model '{model}' is not available for profile '{profile_name}'. "
                    f"Available models: {', '.join(available_models) if available_models else 'none'}. "
                    "You can add models using the `blackfish model add` command."
                )

            # Get or select revision
            if container_options.get("revision") in (None, ""):
                available_revisions = get_revisions(model, profile)
                if not available_revisions:
                    raise ValueError(
                        f"No revisions found for model '{model}' in profile"
                        f" '{profile_name}'. You can try adding it using"
                        " `blackfish model add`."
                    )
                revision = get_latest_commit(model, available_revisions)
                container_options["revision"] = revision
                logger.warning(
                    f"No revision provided. Using latest available commit: {revision}."
                )
            else:
                revision = container_options["revision"]

            # Get model directory
            if container_options.get("model_dir") in (None, ""):
                model_dir = get_model_dir(model, revision, profile)
                if model_dir is None:
                    raise ValueError(
                        f"Could not find model directory for '{model}' [{revision}]"
                        f" in profile '{profile_name}'. The model files may have"
                        " been moved or there may be a permissions issue. You can"
                        " try re-adding the model using `blackfish model add`."
                    )
                container_options["model_dir"] = model_dir

        # Map image type to config class
        container_cfg: TextGenerationConfig | SpeechRecognitionConfig
        if image == "text_generation":
            container_cfg = TextGenerationConfig(**container_options)
        elif image == "speech_recognition":
            container_cfg = SpeechRecognitionConfig(**container_options)
        else:
            raise ValueError(f"Unknown image type: {image}")

        job_cfg: JobConfig
        if isinstance(profile, SlurmProfile):
            job_cfg = SlurmJobConfig(**job_options)
        else:
            job_cfg = LocalJobConfig(**job_options)

        # Start the service
        with _spinner(self.progress, "Starting service...") as spinner:
            async with self._session() as session:
                await service.start(session, self._state, container_cfg, job_cfg)
            spinner.text = f"Started service: {service.id}"
            spinner.ok(f"{LogSymbols.SUCCESS.value}")

        managed_service = ManagedService(service, self)

        # Track service for auto-cleanup if enabled
        if auto_cleanup:
            self._managed_services.append(managed_service)

        return managed_service

    @_async_to_sync
    async def launch_service(
        self,
        name: str,
        image: ServiceImage,
        model: str,
        profile_name: Optional[str] = None,
        container_config: Optional[ContainerConfigLike] = None,
        job_config: Optional[JobConfigLike] = None,
        mount: Optional[str] = None,
        grace_period: int = config.GRACE_PERIOD,
        image_ref: Optional[str] = None,
        auto_cleanup: bool = True,
        **kwargs: Any,
    ) -> ManagedService:
        """Create and start a new service (sync wrapper).

        See async_launch_service for details.
        """
        # Keyword arguments so adding a parameter to the async signature can't
        # silently shift these onto the wrong ones.
        return await self.async_launch_service(
            name,
            image,
            model,
            profile_name=profile_name,
            container_config=container_config,
            job_config=job_config,
            mount=mount,
            grace_period=grace_period,
            image_ref=image_ref,
            auto_cleanup=auto_cleanup,
            **kwargs,
        )

    async def async_get_service(
        self, service_id: str | UUID
    ) -> Optional[ManagedService]:
        """Get a service by ID (async).

        Args:
            service_id: UUID of the service

        Returns:
            ManagedService instance or None if not found
        """
        async with self._session() as session:
            query = sa.select(Service).where(Service.id == _as_uuid(service_id))
            result = await session.execute(query)
            service = result.scalar_one_or_none()

            if service is not None:
                await service.refresh(session, self._ensure_http_client())
                return ManagedService(service, self)

            return None

    @_async_to_sync
    async def get_service(self, service_id: str | UUID) -> Optional[ManagedService]:
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
                await service.refresh(session, self._ensure_http_client())
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
        service_id: str | UUID,
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
        service_id: str | UUID,
        timeout: bool = False,
        failed: bool = False,
    ) -> Optional[ManagedService]:
        """Stop a service (sync wrapper).

        See async_stop_service for details.
        """
        return await self.async_stop_service(service_id, timeout, failed)

    async def async_delete_service(self, service_id: str | UUID) -> bool:
        """Delete a service from the database (async).

        Note: This only deletes the database record. The service should be
        stopped first using stop_service().

        Args:
            service_id: UUID of the service

        Returns:
            True if deleted, False if not found
        """

        async with self._session() as session:
            query = sa.delete(Service).where(Service.id == _as_uuid(service_id))
            result = await session.execute(query)
            return bool(result.rowcount and result.rowcount > 0)  # type: ignore[attr-defined]

    @_async_to_sync
    async def delete_service(self, service_id: str | UUID) -> bool:
        """Delete a service from the database (sync wrapper).

        See async_delete_service for details.
        """
        return await self.async_delete_service(service_id)

    async def async_wait_for_service(
        self,
        service_id: str | UUID,
        target_status: ServiceStatus = ServiceStatus.HEALTHY,
        timeout: float = 300,
        poll_interval: float = 10,
    ) -> Optional[ManagedService]:
        """Wait for a service to reach a target status (async).

        Args:
            service_id: UUID of the service
            target_status: Status to wait for (default: HEALTHY)
            timeout: Maximum time to wait in seconds (default: 300)
            poll_interval: Time between status checks in seconds (default: 10)

        Returns:
            ManagedService instance if target status reached, None if timeout or service failed

        Examples:
            ```pycon
            >>> service = bf.launch_service(...)
            >>> service = await bf.async_wait_for_service(str(service.id))
            >>> if service and service.status == ServiceStatus.HEALTHY:
            ...     print(f"Service ready on port {service.port}")
            ```
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
        service_id: str | UUID,
        target_status: ServiceStatus = ServiceStatus.HEALTHY,
        timeout: float = 300,
        poll_interval: float = 10,
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
