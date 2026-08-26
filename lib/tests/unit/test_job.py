from datetime import datetime, timezone
from unittest import mock

import pytest

from blackfish.server.job import (
    JobState,
    SlurmJob,
    _split_state_start,
    parse_sacct_start,
)
from blackfish.server.remote import CompletedProcess, RemoteConnectionError

pytestmark = pytest.mark.anyio


def _completed(stdout: bytes = b"") -> CompletedProcess:
    return CompletedProcess(returncode=0, stdout=stdout, stderr=b"")


# The test jobs use host="test" (not localhost), so update/fetch_node/
# fetch_port/cancel all take the remote SSH branch and call `remote.ssh`.


@mock.patch.object(SlurmJob, "fetch_port")
@mock.patch.object(SlurmJob, "fetch_node")
@mock.patch("blackfish.server.remote.ssh")
async def test_update_none(mock_ssh, mock_fetch_node, mock_fetch_port):
    mock_ssh.return_value = _completed(b"")
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    await job.update()
    assert job.state == JobState.MISSING
    mock_fetch_node.assert_not_called()
    mock_fetch_port.assert_not_called()


@mock.patch.object(SlurmJob, "fetch_port")
@mock.patch.object(SlurmJob, "fetch_node")
@mock.patch("blackfish.server.remote.ssh")
async def test_update_no_change(mock_ssh, mock_fetch_node, mock_fetch_port):
    mock_ssh.return_value = _completed(b"RUNNING")
    job = SlurmJob(
        job_id=1, user="test", host="test", state=JobState.RUNNING, data_dir="test"
    )
    await job.update()
    assert job.state == JobState.RUNNING
    mock_fetch_node.assert_not_called()
    mock_fetch_port.assert_not_called()


@mock.patch.object(SlurmJob, "fetch_port")
@mock.patch.object(SlurmJob, "fetch_node")
@mock.patch("blackfish.server.remote.ssh")
async def test_update_change(mock_ssh, mock_fetch_node, mock_fetch_port):
    mock_ssh.return_value = _completed(b"RUNNING")
    job = SlurmJob(
        job_id=1, user="test", host="test", state=JobState.PENDING, data_dir="test"
    )
    await job.update()
    assert job.state == JobState.RUNNING
    mock_fetch_node.assert_called()
    mock_fetch_port.assert_called()


@mock.patch("logging.Logger.warning")
@mock.patch.object(SlurmJob, "fetch_port")
@mock.patch.object(SlurmJob, "fetch_node")
@mock.patch("blackfish.server.remote.ssh")
async def test_update_warning(mock_ssh, mock_fetch_node, mock_fetch_port, mock_warning):
    mock_ssh.side_effect = RemoteConnectionError("connection refused")
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    await job.update()
    mock_warning.assert_called()
    mock_fetch_node.assert_not_called()
    mock_fetch_port.assert_not_called()


@mock.patch("blackfish.server.remote.ssh")
async def test_fetch_node_none(mock_ssh):
    mock_ssh.return_value = _completed(b"")
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    await job.fetch_node()
    assert job.node is None


@mock.patch("blackfish.server.remote.ssh")
async def test_fetch_node_some(mock_ssh):
    mock_ssh.return_value = _completed(b"56622858")
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    await job.fetch_node()
    assert job.node == "56622858"


@mock.patch("logging.Logger.warning")
@mock.patch("blackfish.server.remote.ssh")
async def test_fetch_node_warning(mock_ssh, mock_warning):
    mock_ssh.side_effect = RemoteConnectionError("connection refused")
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    await job.fetch_node()
    mock_warning.assert_called()


@mock.patch("blackfish.server.remote.ssh")
async def test_fetch_port_none(mock_ssh):
    mock_ssh.return_value = _completed(b"")
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    await job.fetch_port()
    assert job.port is None


@mock.patch("blackfish.server.remote.ssh")
async def test_fetch_port_some(mock_ssh):
    mock_ssh.return_value = _completed(b"8081")
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    await job.fetch_port()
    assert job.port == 8081


@mock.patch("logging.Logger.warning")
@mock.patch("blackfish.server.remote.ssh")
async def test_fetch_port_warning(mock_ssh, mock_warning):
    mock_ssh.side_effect = RemoteConnectionError("connection refused")
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    await job.fetch_port()
    mock_warning.assert_called()


@mock.patch("logging.Logger.warning")
@mock.patch("blackfish.server.remote.ssh")
async def test_cancel_warning(mock_ssh, mock_warning):
    mock_ssh.side_effect = RemoteConnectionError("connection refused")
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    await job.cancel()
    mock_warning.assert_called()


def test_split_state_start_empty():
    assert _split_state_start(b"") == (b"", b"")


def test_split_state_start_state_only():
    # Older Slurm or a State-only query
    assert _split_state_start(b"RUNNING\n") == (b"RUNNING", b"")


def test_split_state_start_with_start():
    assert _split_state_start(b"RUNNING|2026-08-25T14:49:36\n") == (
        b"RUNNING",
        b"2026-08-25T14:49:36",
    )


def test_split_state_start_first_line_only():
    # sacct can return multiple lines (e.g. steps); we only look at the first.
    assert _split_state_start(b"RUNNING|2026-08-25T14:49:36\nCOMPLETED|...\n") == (
        b"RUNNING",
        b"2026-08-25T14:49:36",
    )


def test_parse_sacct_start_valid():
    assert parse_sacct_start("2026-08-25T14:49:36") == datetime(
        2026, 8, 25, 14, 49, 36, tzinfo=timezone.utc
    )


def test_parse_sacct_start_unknown():
    assert parse_sacct_start("Unknown") is None
    assert parse_sacct_start("unknown") is None
    assert parse_sacct_start("") is None


def test_parse_sacct_start_malformed():
    assert parse_sacct_start("not-a-date") is None


@mock.patch.object(SlurmJob, "fetch_port")
@mock.patch.object(SlurmJob, "fetch_node")
@mock.patch("blackfish.server.remote.ssh")
async def test_update_sets_started_at(mock_ssh, mock_fetch_node, mock_fetch_port):
    mock_ssh.return_value = _completed(b"RUNNING|2026-08-25T14:49:36\n")
    job = SlurmJob(
        job_id=1, user="test", host="test", state=JobState.PENDING, data_dir="test"
    )
    await job.update()
    assert job.state == JobState.RUNNING
    assert job.started_at == datetime(2026, 8, 25, 14, 49, 36, tzinfo=timezone.utc)


@mock.patch.object(SlurmJob, "fetch_port")
@mock.patch.object(SlurmJob, "fetch_node")
@mock.patch("blackfish.server.remote.ssh")
async def test_update_unknown_start_leaves_started_at_none(
    mock_ssh, mock_fetch_node, mock_fetch_port
):
    mock_ssh.return_value = _completed(b"PENDING|Unknown\n")
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    await job.update()
    assert job.state == JobState.PENDING
    assert job.started_at is None
