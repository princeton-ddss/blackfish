"""Tests for the async remote-execution module.

`run` is exercised against real local subprocesses (echo / false / sleep).
`ssh` and `scp` mock `asyncio.create_subprocess_exec` so the transport-error
classification and command construction can be tested without a remote host.
"""

from __future__ import annotations

import asyncio
from unittest import mock

import pytest

from blackfish.server import remote
from blackfish.server.remote import (
    CompletedProcess,
    RemoteAuthError,
    RemoteCommandError,
    RemoteConnectionError,
    RemoteTimeout,
)

pytestmark = pytest.mark.anyio


class FakeProc:
    """Stand-in for an asyncio subprocess transport."""

    def __init__(
        self,
        returncode: int = 0,
        stdout: bytes = b"",
        stderr: bytes = b"",
        hang: bool = False,
    ) -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self._hang = hang
        self.killed = False

    async def communicate(self) -> tuple[bytes, bytes]:
        if self._hang:
            await asyncio.sleep(3600)
        return self._stdout, self._stderr

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        return self.returncode


def _patch_exec(proc: FakeProc) -> mock._patch:
    return mock.patch(
        "asyncio.create_subprocess_exec", mock.AsyncMock(return_value=proc)
    )


# --- run: real local subprocesses ---------------------------------------------


async def test_run_success() -> None:
    result = await remote.run(["echo", "hello"])
    assert isinstance(result, CompletedProcess)
    assert result.returncode == 0
    assert result.stdout.strip() == b"hello"


async def test_run_nonzero_raises_command_error() -> None:
    with pytest.raises(RemoteCommandError) as exc_info:
        await remote.run(["false"])
    assert exc_info.value.returncode != 0
    assert exc_info.value.cmd == ["false"]


async def test_run_timeout() -> None:
    with pytest.raises(RemoteTimeout):
        await remote.run(["sleep", "5"], timeout=0.2)


async def test_run_cancellation_propagates() -> None:
    task = asyncio.create_task(remote.run(["sleep", "5"]))
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


# --- ssh: mocked transport ----------------------------------------------------


async def test_ssh_success_builds_command_with_options() -> None:
    proc = FakeProc(returncode=0, stdout=b"RUNNING\n")
    with _patch_exec(proc) as m:
        result = await remote.ssh("user@host", ["sacct", "-j", "1"])
    assert result.stdout == b"RUNNING\n"
    argv = m.call_args.args
    assert argv[0] == "ssh"
    assert "BatchMode=yes" in argv
    assert "ConnectTimeout=10" in argv
    assert "user@host" in argv
    assert argv[-3:] == ("sacct", "-j", "1")


async def test_ssh_auth_failure() -> None:
    proc = FakeProc(returncode=255, stderr=b"Permission denied (publickey).")
    with _patch_exec(proc):
        with pytest.raises(RemoteAuthError):
            await remote.ssh("user@host", ["sacct"])


async def test_ssh_connection_failure() -> None:
    proc = FakeProc(returncode=255, stderr=b"ssh: connect to host port 22: Connection refused")
    with _patch_exec(proc):
        with pytest.raises(RemoteConnectionError):
            await remote.ssh("user@host", ["sacct"])


async def test_ssh_remote_command_failure() -> None:
    proc = FakeProc(returncode=1, stderr=b"sacct: error: invalid job id")
    with _patch_exec(proc):
        with pytest.raises(RemoteCommandError) as exc_info:
            await remote.ssh("user@host", ["sacct", "-j", "bad"])
    assert exc_info.value.returncode == 1


async def test_ssh_timeout() -> None:
    proc = FakeProc(hang=True)
    with _patch_exec(proc):
        with pytest.raises(RemoteTimeout):
            await remote.ssh("user@host", ["sacct"], timeout=0.2)
    assert proc.killed


# --- scp: mocked transport ----------------------------------------------------


async def test_scp_success() -> None:
    proc = FakeProc(returncode=0)
    with _patch_exec(proc) as m:
        await remote.scp("local.sh", "user@host:/remote/local.sh")
    argv = m.call_args.args
    assert argv[0] == "scp"
    assert "BatchMode=yes" in argv
    assert argv[-2:] == ("local.sh", "user@host:/remote/local.sh")


async def test_scp_connection_failure() -> None:
    proc = FakeProc(returncode=255, stderr=b"ssh: Could not resolve hostname host")
    with _patch_exec(proc):
        with pytest.raises(RemoteConnectionError):
            await remote.scp("local.sh", "user@host:/remote/local.sh")
