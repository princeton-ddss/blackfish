from __future__ import annotations

import threading
import time
from typing import Dict, Optional, Generator, Any
from contextlib import contextmanager
from dataclasses import dataclass
from fabric.connection import Connection
from app.logger import logger


@dataclass
class ConnectionInfo:
    """Information about an SSH connection."""

    host: str
    user: str

    def key(self) -> str:
        """Return a unique key for this connection."""
        return f"{self.user}@{self.host}"


@dataclass
class ManagedConnection:
    """A managed SSH connection with metadata."""

    connection: Connection
    info: ConnectionInfo
    last_used: float
    is_connected: bool = True

    def is_alive(self) -> bool:
        """Check if the connection is still alive."""
        try:
            result = self.connection.run("true", hide=True, warn=True)
            self.is_connected = result.ok
            return self.is_connected
        except Exception as e:
            logger.debug(f"Connection check failed for {self.info.key()}: {e}")
            self.is_connected = False
            return False

    def touch(self) -> None:
        """Update the last used timestamp."""
        self.last_used = time.time()


class SSHConnectionManager:
    """Manages persistent SSH connections with automatic recovery."""

    def __init__(self, max_idle_time: int = 300, cleanup_interval: int = 60):
        """
        Initialize the SSH connection manager.

        Args:
            max_idle_time: Maximum time (seconds) a connection can be idle before cleanup
            cleanup_interval: Interval (seconds) between cleanup cycles
        """
        self._connections: Dict[str, ManagedConnection] = {}
        self._lock = threading.RLock()
        self._max_idle_time = max_idle_time
        self._cleanup_interval = cleanup_interval
        self._cleanup_thread: Optional[threading.Thread] = None
        self._shutdown = False
        self._start_cleanup_thread()

    def _start_cleanup_thread(self) -> None:
        """Start the background cleanup thread."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_loop, daemon=True, name="ssh-connection-cleanup"
            )
            self._cleanup_thread.start()
            logger.debug("Started SSH connection cleanup thread")

    def _cleanup_loop(self) -> None:
        """Background loop to clean up idle connections."""
        while not self._shutdown:
            try:
                self._cleanup_idle_connections()
                time.sleep(self._cleanup_interval)
            except Exception as e:
                logger.error(f"Error in SSH connection cleanup: {e}")
                time.sleep(self._cleanup_interval)

    def _cleanup_idle_connections(self) -> None:
        """Remove idle and dead connections."""
        current_time = time.time()
        to_remove = []

        with self._lock:
            for key, managed_conn in self._connections.items():
                # Check if connection is idle
                if current_time - managed_conn.last_used > self._max_idle_time:
                    logger.debug(f"Connection {key} is idle, marking for removal")
                    to_remove.append(key)
                # Check if connection is still alive
                elif not managed_conn.is_alive():
                    logger.debug(f"Connection {key} is dead, marking for removal")
                    to_remove.append(key)

            # Remove idle/dead connections
            for key in to_remove:
                managed_conn = self._connections.pop(key)
                if managed_conn:
                    try:
                        managed_conn.connection.close()
                        logger.debug(f"Closed idle/dead connection: {key}")
                    except Exception as e:
                        logger.debug(f"Error closing connection {key}: {e}")

    def _create_connection(self, info: ConnectionInfo) -> Connection:
        """Create a new SSH connection."""
        logger.debug(f"Creating new SSH connection to {info.key()}")
        return Connection(host=info.host, user=info.user)

    def get_connection(self, host: str, user: str) -> Connection:
        """
        Get a persistent SSH connection, creating one if needed.

        Args:
            host: Remote host to connect to
            user: Username for SSH connection

        Returns:
            An active SSH connection
        """
        info = ConnectionInfo(host=host, user=user)
        key = info.key()

        with self._lock:
            managed_conn = self._connections.get(key)

            # Check if we have a valid existing connection
            if managed_conn and managed_conn.is_alive():
                managed_conn.touch()
                logger.debug(f"Reusing existing connection: {key}")
                return managed_conn.connection

            # Remove dead connection if it exists
            if managed_conn:
                try:
                    managed_conn.connection.close()
                except Exception:
                    pass
                del self._connections[key]

            # Create new connection
            connection = self._create_connection(info)
            managed_conn = ManagedConnection(
                connection=connection, info=info, last_used=time.time()
            )

            # Test the connection
            try:
                managed_conn.is_alive()  # This will set is_connected appropriately
                if not managed_conn.is_connected:
                    raise Exception("Connection test failed")

                self._connections[key] = managed_conn
                logger.debug(f"Created and cached new connection: {key}")
                return connection

            except Exception as e:
                logger.error(f"Failed to create connection to {key}: {e}")
                try:
                    connection.close()
                except Exception:
                    pass
                raise

    @contextmanager
    def connection(self, host: str, user: str) -> Generator[Connection, None, None]:
        """
        Context manager for getting SSH connections.

        Args:
            host: Remote host to connect to
            user: Username for SSH connection

        Yields:
            An active SSH connection
        """
        conn = self.get_connection(host, user)
        try:
            yield conn
        finally:
            # Connection stays open and managed by the pool
            pass

    def close_connection(self, host: str, user: str) -> None:
        """
        Explicitly close a connection.

        Args:
            host: Remote host
            user: Username
        """
        info = ConnectionInfo(host=host, user=user)
        key = info.key()

        with self._lock:
            managed_conn = self._connections.pop(key, None)
            if managed_conn:
                try:
                    managed_conn.connection.close()
                    logger.debug(f"Explicitly closed connection: {key}")
                except Exception as e:
                    logger.debug(f"Error closing connection {key}: {e}")

    def close_all(self) -> None:
        """Close all managed connections."""
        with self._lock:
            for key, managed_conn in self._connections.items():
                try:
                    managed_conn.connection.close()
                    logger.debug(f"Closed connection: {key}")
                except Exception as e:
                    logger.debug(f"Error closing connection {key}: {e}")
            self._connections.clear()

    def shutdown(self) -> None:
        """Shutdown the connection manager."""
        logger.debug("Shutting down SSH connection manager")
        self._shutdown = True

        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5.0)

        self.close_all()

    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information about managed connections."""
        with self._lock:
            return {
                key: {
                    "host": conn.info.host,
                    "user": conn.info.user,
                    "last_used": conn.last_used,
                    "is_connected": conn.is_connected,
                    "idle_time": time.time() - conn.last_used,
                }
                for key, conn in self._connections.items()
            }
