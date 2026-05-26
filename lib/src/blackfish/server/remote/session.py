"""Pooled SSH + SFTP sessions for fabric-based remote operations.

A single :class:`RemoteSession` is held per ``(host, user)`` and owns one
:mod:`fabric` ``Connection`` and one :mod:`paramiko` ``SFTPClient``. Acquires
take the session's lock for the duration of one operation, then release —
so concurrent consumers (the WebSocket file browser, HTTP file-API handlers,
model-listing helpers) share a single open connection per ``(host, user)``
without paying the SSH+SFTP handshake on every call.

Typical use::

    from blackfish.server import remote

    with remote.acquire(profile.host, profile.user) as sess:
        sess.read_bytes(path)

The pool is process-scoped. Sessions are opened lazily on first acquire,
reconnected lazily if idle past ``_IDLE_TIMEOUT_SECONDS``, and closed en
masse on server shutdown via :func:`close_all`.

Errors here use Python's filesystem conventions (``FileNotFoundError``,
``PermissionError``, ``OSError``, ``ValueError``) rather than the subprocess
path's :class:`~blackfish.server.remote.exec.RemoteError` hierarchy —
callers of SFTP primitives are typically doing file I/O and want
file-I/O-shaped exceptions.

The :class:`RemoteSession` exposes only the low-level SFTP primitives
shared by all consumers (``stat``, ``read_bytes``, ``write_bytes``, etc.).
Higher-level wrappers — HTTP exception translation, response models,
domain-specific listing logic — live in caller modules (``sftp.py``,
``utils.py``, ``browser.py``) and use these primitives plus the raw
:attr:`~RemoteSession.sftp` client as needed.

Out of scope here: ``stream_file``'s long-lived generator (it holds its
own non-pooled ``Connection`` — pooling would block the host for the
duration of the read). Fabric's ``run``/``put``/``get`` aren't exposed
yet; no caller needs them today.
"""

from __future__ import annotations

import errno
import stat as stat_mod
import threading
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

from fabric.connection import Connection

from blackfish.server.logger import logger

if TYPE_CHECKING:
    from paramiko.sftp_attr import SFTPAttributes
    from paramiko.sftp_client import SFTPClient

# Pooled sessions unused for this long are closed and reopened on the next
# acquire — partly to free resources, partly to preempt connections the SSH
# server has silently dropped on its end after a long idle period.
_IDLE_TIMEOUT_SECONDS = 300.0


class RemoteSession:
    """One pooled fabric ``Connection`` + SFTP client for a ``(host, user)``.

    Don't instantiate directly — use :func:`acquire`. The session's lock is
    held by the :func:`acquire` context manager for the duration of the
    ``with`` block; only one operation runs at a time per ``(host, user)``.
    """

    def __init__(self, host: str, user: str) -> None:
        self.host = host
        self.user = user
        self._connection: Connection | None = None
        self._sftp: "SFTPClient | None" = None
        self._lock = threading.Lock()
        self._last_used = time.monotonic()

    # --- lifecycle -----------------------------------------------------------

    def _open(self) -> None:
        conn = Connection(
            host=self.host,
            user=self.user,
            connect_kwargs={"timeout": 15, "banner_timeout": 10},
        )
        try:
            conn.open()
            self._sftp = conn.sftp()
        except Exception:
            try:
                conn.close()
            except Exception as cleanup_error:
                logger.warning(f"Error during connection cleanup: {cleanup_error}")
            raise
        self._connection = conn
        logger.info(f"Opened SFTP session to {self.user}@{self.host}")

    def _close(self) -> None:
        if self._sftp is not None:
            try:
                self._sftp.close()
            except Exception as e:
                logger.warning(f"Error closing SFTP session: {e}")
            self._sftp = None
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception as e:
                logger.warning(f"Error closing SSH connection: {e}")
            self._connection = None

    def _stale(self) -> bool:
        return time.monotonic() - self._last_used > _IDLE_TIMEOUT_SECONDS

    # --- raw access ----------------------------------------------------------

    @property
    def sftp(self) -> "SFTPClient":
        """Underlying paramiko SFTPClient. Only valid inside :func:`acquire`."""
        if self._sftp is None:
            raise RuntimeError("RemoteSession is not currently acquired")
        return self._sftp

    def home_dir(self) -> str:
        """Return the absolute path of the remote home directory.

        A method, not a property, because it issues an SFTP RPC.
        """
        return self.sftp.normalize(".")

    # --- SFTP primitives -----------------------------------------------------
    # Map paramiko's IOError-with-errno to standard Python exceptions so
    # callers can ``except FileNotFoundError`` / ``PermissionError`` /
    # ``OSError`` without reaching into paramiko internals.

    def stat(self, path: str) -> "SFTPAttributes":
        try:
            return self.sftp.stat(path)
        except (FileNotFoundError, PermissionError):
            raise
        except Exception as e:
            raise OSError(str(e)) from e

    def exists(self, path: str) -> bool:
        try:
            self.sftp.stat(path)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            raise OSError(str(e)) from e

    def mkdir(self, path: str) -> None:
        try:
            self.sftp.mkdir(path)
        except (FileNotFoundError, PermissionError):
            raise
        except IOError as e:
            if getattr(e, "errno", None) == errno.EEXIST:
                raise ValueError(f"Directory already exists: {path}") from e
            raise OSError(str(e)) from e

    def delete(self, path: str) -> None:
        """Remove a file or (empty) directory."""
        try:
            attr = self.sftp.stat(path)
            if attr.st_mode and stat_mod.S_ISDIR(attr.st_mode):
                self.sftp.rmdir(path)
            else:
                self.sftp.remove(path)
        except (FileNotFoundError, PermissionError):
            raise
        except IOError as e:
            if getattr(e, "errno", None) == errno.ENOTEMPTY:
                raise ValueError(f"Directory not empty: {path}") from e
            raise OSError(str(e)) from e

    def rename(self, old_path: str, new_path: str) -> None:
        try:
            self.sftp.rename(old_path, new_path)
        except (FileNotFoundError, PermissionError):
            raise
        except Exception as e:
            raise OSError(str(e)) from e

    def read_bytes(self, path: str) -> bytes:
        try:
            with self.sftp.open(path, "rb") as f:
                return f.read()
        except (FileNotFoundError, PermissionError):
            raise
        except Exception as e:
            raise OSError(str(e)) from e

    def write_bytes(self, path: str, content: bytes) -> None:
        try:
            with self.sftp.open(path, "wb") as f:
                f.write(content)
        except (FileNotFoundError, PermissionError):
            raise
        except Exception as e:
            raise OSError(str(e)) from e


class _SessionPool:
    """Process-scoped table of :class:`RemoteSession` keyed by ``(host, user)``."""

    def __init__(self) -> None:
        self._sessions: dict[tuple[str, str], RemoteSession] = {}
        self._lock = threading.Lock()

    def get(self, host: str, user: str) -> RemoteSession:
        key = (host, user)
        with self._lock:
            session = self._sessions.get(key)
            if session is None:
                session = RemoteSession(host=host, user=user)
                self._sessions[key] = session
            return session

    def close_all(self) -> None:
        with self._lock:
            for session in self._sessions.values():
                with session._lock:
                    session._close()
            self._sessions.clear()


_pool = _SessionPool()


@contextmanager
def acquire(host: str, user: str) -> Iterator[RemoteSession]:
    """Acquire the pooled :class:`RemoteSession` for ``(host, user)``.

    Holds the session's lock for the duration of the ``with`` block, so a
    single operation per ``(host, user)`` runs at a time. Opens the
    underlying connection lazily, and reopens it on the next acquire if
    the session has been idle past the idle timeout.
    """
    session = _pool.get(host, user)
    with session._lock:
        if session._sftp is not None and session._stale():
            logger.debug(f"Closing idle SFTP session to {session.user}@{session.host}")
            session._close()
        if session._sftp is None:
            session._open()
        try:
            yield session
        finally:
            session._last_used = time.monotonic()


def close_all() -> None:
    """Close every pooled session. Call on server shutdown."""
    _pool.close_all()
