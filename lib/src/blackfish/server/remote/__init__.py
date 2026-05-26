"""Outbound SSH-flavored operations: async subprocess + pooled SFTP sessions.

This package groups two related-but-distinct primitives:

- :mod:`.exec` — async subprocess ``ssh``/``scp``/``run`` with mandatory
  timeouts and a :class:`RemoteError` hierarchy. Built on
  :func:`asyncio.create_subprocess_exec`; for one-shot command execution.

- :mod:`.session` — sync :mod:`fabric`/:mod:`paramiko` pool. :func:`acquire`
  returns a :class:`RemoteSession` for a ``(host, user)`` pair, opened
  lazily and reused across calls so consumers share one connection instead
  of paying the SFTP handshake on every operation. For SFTP and other
  long-lived in-process SSH work.

The two halves don't share code; they're co-located because they cover the
same conceptual layer (outbound SSH). Reach for ``run``/``ssh``/``scp`` when
you want to shell out to a command; reach for ``acquire`` when you want SFTP
or repeated operations against the same host.
"""

from blackfish.server.config import config
from blackfish.server.remote.exec import (
    CompletedProcess,
    DEFAULT_TIMEOUT,
    RemoteAuthError,
    RemoteCommandError,
    RemoteConnectionError,
    RemoteError,
    RemoteTimeout,
    run,
    scp,
    ssh,
)

# Underscore-prefixed helpers retained at the package level so test code
# (which patches them) doesn't have to know about the internal submodule split.
from blackfish.server.remote.exec import (  # noqa: F401
    _ensure_socket_dir,
    _ssh_transport_error,
)

from blackfish.server.remote.session import (
    RemoteSession,
    acquire,
    close_all,
)

__all__ = [
    "CompletedProcess",
    "DEFAULT_TIMEOUT",
    "RemoteAuthError",
    "RemoteCommandError",
    "RemoteConnectionError",
    "RemoteError",
    "RemoteSession",
    "RemoteTimeout",
    "acquire",
    "close_all",
    "config",
    "run",
    "scp",
    "ssh",
]
