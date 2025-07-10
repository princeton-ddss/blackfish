import subprocess
from unittest import mock

from app.job import JobState, SlurmJob


@mock.patch.object(SlurmJob, "fetch_port")
@mock.patch.object(SlurmJob, "fetch_node")
@mock.patch("subprocess.check_output")
def test_update_none(mock_check_output, mock_fetch_node, mock_fetch_port):
    mock_check_output.return_value = b""
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    job.update()
    assert job.state == JobState.MISSING
    mock_fetch_node.assert_not_called()
    mock_fetch_port.assert_not_called()


@mock.patch.object(SlurmJob, "fetch_port")
@mock.patch.object(SlurmJob, "fetch_node")
@mock.patch("subprocess.check_output")
def test_update_no_change(mock_check_output, mock_fetch_node, mock_fetch_port):
    mock_check_output.return_value = b"RUNNING"
    job = SlurmJob(
        job_id=1, user="test", host="test", state=JobState.RUNNING, data_dir="test"
    )
    job.update()
    assert job.state == JobState.RUNNING
    mock_fetch_node.assert_not_called()
    mock_fetch_port.assert_not_called()


@mock.patch.object(SlurmJob, "fetch_port")
@mock.patch.object(SlurmJob, "fetch_node")
@mock.patch("subprocess.check_output")
def test_update_change(mock_check_output, mock_fetch_node, mock_fetch_port):
    mock_check_output.return_value = b"RUNNING"
    job = SlurmJob(
        job_id=1, user="test", host="test", state=JobState.PENDING, data_dir="test"
    )
    job.update()
    assert job.state == JobState.RUNNING
    mock_fetch_node.assert_called()
    mock_fetch_port.assert_called()


@mock.patch("logging.Logger.warning")
@mock.patch.object(SlurmJob, "fetch_port")
@mock.patch.object(SlurmJob, "fetch_node")
@mock.patch("subprocess.check_output")
def test_update_warning(
    mock_check_output, mock_fetch_node, mock_fetch_port, mock_warning
):
    mock_check_output.side_effect = subprocess.CalledProcessError(None, None)
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    job.update()
    mock_warning.assert_called()
    mock_fetch_node.assert_not_called()
    mock_fetch_port.assert_not_called()


@mock.patch("subprocess.check_output")
def test_fetch_node_none(mock_check_output):
    mock_check_output.return_value = b""
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    job.fetch_node()
    assert job.node is None


@mock.patch("subprocess.check_output")
def test_fetch_node_some(mock_check_output):
    mock_check_output.return_value = b"56622858"
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    job.fetch_node()
    assert job.node == "56622858"


@mock.patch("logging.Logger.warning")
@mock.patch("subprocess.check_output")
def test_fetch_node_warning(mock_check_output, mock_warning):
    mock_check_output.side_effect = subprocess.CalledProcessError(None, None)
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    job.fetch_node()
    mock_warning.assert_called()


@mock.patch("subprocess.check_output")
def test_fetch_port_none(mock_check_output):
    mock_check_output.return_value = b""
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    job.fetch_port()
    assert job.port is None


@mock.patch("subprocess.check_output")
def test_fetch_port_some(mock_check_output):
    mock_check_output.return_value = b"8081"
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    job.fetch_port()
    assert job.port == 8081


@mock.patch("logging.Logger.warning")
@mock.patch("subprocess.check_output")
def test_fetch_port_warning(mock_check_output, mock_warning):
    mock_check_output.side_effect = subprocess.CalledProcessError(None, None)
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    job.fetch_port()
    mock_warning.assert_called()


@mock.patch("logging.Logger.warning")
@mock.patch("subprocess.check_output")
def test_cancel_warning(mock_check_output, mock_warning):
    mock_check_output.side_effect = subprocess.CalledProcessError(None, None)
    job = SlurmJob(job_id=1, user="test", host="test", data_dir="test")
    job.update()
    mock_warning.assert_called()
