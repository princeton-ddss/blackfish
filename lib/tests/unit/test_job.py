from unittest import mock

import pytest

from blackfish.server.job import JobState, SlurmJob
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
