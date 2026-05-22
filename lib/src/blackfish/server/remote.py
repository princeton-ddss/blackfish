"""Async subprocess and SSH/SCP execution with timeouts and structured errors.

Every outbound command in Blackfish — local subprocess, remote exec, remote
copy — should go through this module rather than calling ``subprocess``
directly. It provides:

- :func:`run` — run a command locally
- :func:`ssh` — run a command on a remote host
- :func:`scp` — copy a file to/from a remote host

All three are built on :func:`asyncio.create_subprocess_exec` for true async,
cancellable I/O, and all take a mandatory ``timeout``. A hung SSH call no
longer blocks the event loop — it is cancelled when the timeout elapses.

Failure is reported through a small exception hierarchy:

    RemoteError
    ├── RemoteTimeout           — the call exceeded its timeout
    ├── RemoteConnectionError   — SSH transport failed (unreachable / refused / DNS)
    ├── RemoteAuthError         — SSH transport failed (authentication rejected)
    └── RemoteCommandError      — the command ran and exited non-zero

Catch :class:`RemoteError` to treat any failure uniformly; catch a subclass to
distinguish (e.g. a dead login node from a command that merely failed).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

# Default per-call timeout (seconds). Generous enough for slow login nodes,
# short enough that a truly hung call surfaces quickly.
DEFAULT_TIMEOUT = 60.0

# SSH exit code reserved for transport-level failure (connection/auth), as
# opposed to a non-zero exit from the remote command itself.
_SSH_TRANSPORT_EXIT = 255

# Baked into every ssh/scp invocation:
# - ConnectTimeout: cap the TCP/handshake wait so an unreachable host fails fast
# - ServerAliveInterval: detect a dropped connection mid-command
# - BatchMode: never prompt for a password/passphrase — fail instead of hanging
_SSH_OPTIONS = [
    "-o",
    "ConnectTimeout=10",
    "-o",
    "ServerAliveInterval=15",
    "-o",
    "BatchMode=yes",
]


class RemoteError(Exception):
    """Base class for all remote-execution failures."""


class RemoteTimeout(RemoteError):
    """A call exceeded its timeout and was cancelled."""


class RemoteConnectionError(RemoteError):
    """SSH transport failed: host unreachable, connection refused, or DNS failure."""


class RemoteAuthError(RemoteError):
    """SSH transport failed: authentication was rejected."""


class RemoteCommandError(RemoteError):
    """The command ran to completion but exited with a non-zero status."""

    def __init__(
        self, cmd: list[str], returncode: int, stdout: bytes, stderr: bytes
    ) -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        detail = stderr.decode("utf-8", "replace").strip()
        super().__init__(
            f"Command {cmd[0]!r} exited with status {returncode}"
            + (f": {detail}" if detail else "")
        )


@dataclass
class CompletedProcess:
    """The result of a successful (exit 0) command."""

    returncode: int
    stdout: bytes
    stderr: bytes


async def _exec(cmd: list[str], timeout: float) -> tuple[int, bytes, bytes]:
    """Run ``cmd`` via asyncio, enforcing ``timeout``. Returns (rc, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        # Kill the orphaned process before propagating, so a cancelled or
        # timed-out call doesn't leave a subprocess behind.
        proc.kill()
        await proc.wait()
        raise
    return proc.returncode or 0, stdout, stderr


async def run(cmd: list[str], *, timeout: float = DEFAULT_TIMEOUT) -> CompletedProcess:
    """Run ``cmd`` locally.

    Args:
        cmd: the command and its arguments.
        timeout: seconds to wait before cancelling the call.

    Returns:
        CompletedProcess on exit 0.

    Raises:
        RemoteTimeout: the command did not finish within ``timeout``.
        RemoteCommandError: the command exited non-zero.
    """
    try:
        returncode, stdout, stderr = await _exec(cmd, timeout)
    except asyncio.TimeoutError:
        raise RemoteTimeout(f"{cmd[0]!r} timed out after {timeout}s") from None
    if returncode != 0:
        raise RemoteCommandError(cmd, returncode, stdout, stderr)
    return CompletedProcess(returncode, stdout, stderr)


async def ssh(
    destination: str, command: list[str], *, timeout: float = DEFAULT_TIMEOUT
) -> CompletedProcess:
    """Run ``command`` on a remote host via SSH.

    Args:
        destination: the SSH destination, e.g. ``"user@host"`` or ``"host"``.
        command: the command and its arguments to run on the remote host.
        timeout: seconds to wait before cancelling the call.

    Returns:
        CompletedProcess on exit 0.

    Raises:
        RemoteTimeout: the call did not finish within ``timeout``.
        RemoteAuthError: SSH authentication was rejected.
        RemoteConnectionError: the host was unreachable or the connection failed.
        RemoteCommandError: the remote command ran and exited non-zero.
    """
    cmd = ["ssh", *_SSH_OPTIONS, destination, *command]
    try:
        returncode, stdout, stderr = await _exec(cmd, timeout)
    except asyncio.TimeoutError:
        raise RemoteTimeout(
            f"ssh to {destination!r} timed out after {timeout}s"
        ) from None
    if returncode == _SSH_TRANSPORT_EXIT:
        raise _ssh_transport_error(destination, stderr)
    if returncode != 0:
        raise RemoteCommandError(cmd, returncode, stdout, stderr)
    return CompletedProcess(returncode, stdout, stderr)


async def scp(src: str, dst: str, *, timeout: float = DEFAULT_TIMEOUT) -> None:
    """Copy a file with SCP.

    Either ``src`` or ``dst`` may be a remote path of the form
    ``user@host:/path``.

    Args:
        src: the source path (local or remote).
        dst: the destination path (local or remote).
        timeout: seconds to wait before cancelling the call.

    Raises:
        RemoteTimeout: the copy did not finish within ``timeout``.
        RemoteAuthError: SSH authentication was rejected.
        RemoteConnectionError: the host was unreachable or the connection failed.
        RemoteCommandError: scp ran and exited non-zero for another reason.
    """
    cmd = ["scp", *_SSH_OPTIONS, src, dst]
    try:
        returncode, stdout, stderr = await _exec(cmd, timeout)
    except asyncio.TimeoutError:
        raise RemoteTimeout(
            f"scp {src!r} -> {dst!r} timed out after {timeout}s"
        ) from None
    if returncode == _SSH_TRANSPORT_EXIT:
        # Either src or dst may be the remote endpoint; name both so the
        # message is unambiguous regardless of copy direction.
        raise _ssh_transport_error(f"{src} -> {dst}", stderr)
    if returncode != 0:
        raise RemoteCommandError(cmd, returncode, stdout, stderr)


def _ssh_transport_error(destination: str, stderr: bytes) -> RemoteError:
    """Classify an SSH exit-255 failure as an auth or connection error.

    Best-effort: SSH error wording varies by version and locale, so this
    matches on a few stable substrings and defaults to a connection error.
    """
    detail = stderr.decode("utf-8", "replace").strip()
    lowered = detail.lower()
    # "authentication fail" covers "authentication failed" and
    # "...too many authentication failures".
    auth_markers = ("permission denied", "publickey", "authentication fail")
    if any(marker in lowered for marker in auth_markers):
        return RemoteAuthError(
            f"SSH authentication to {destination!r} failed: {detail}"
        )
    return RemoteConnectionError(f"Could not connect to {destination!r}: {detail}")
