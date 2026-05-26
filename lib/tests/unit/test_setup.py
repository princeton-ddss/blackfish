from unittest import mock

import pytest


from blackfish.server.setup import check_local_cache_exists
from blackfish.server.bootstrap import ensure_app_dir
from blackfish.cli.profile import _auto_profile_


def test_check_local_cache_exists_existing_dir(tmp_path):
    check_local_cache_exists(tmp_path)


def test_check_local_cache_exists_missing_dir(tmp_path):
    with pytest.raises(Exception):
        check_local_cache_exists(tmp_path / "missing")


def test_local_auto_setup(tmp_path):
    p = tmp_path / ".blackfish"
    ensure_app_dir(p)
    _auto_profile_(p, "default", "local", None, None, home_dir=p, cache_dir=p)


@mock.patch("blackfish.cli.profile.TigerFlowClient")
def test_slurm_auto_setup(mock_tigerflow_client, tmp_path):
    # Pretend TigerFlow is already healthy on the remote — otherwise
    # _setup_profile falls into TigerFlowClient.setup(), which creates a venv
    # and pip-installs tigerflow/tigerflow-ml for real (network-dependent,
    # ~20s). The test's purpose is to verify _auto_profile_ wires up a slurm
    # profile, not to exercise the install path.
    instance = mock_tigerflow_client.return_value
    instance.check_health = mock.AsyncMock(
        return_value=mock.MagicMock(tigerflow="1.0.0", tigerflow_ml="1.0.0")
    )
    instance.check_capabilities = mock.AsyncMock()

    p = tmp_path / ".blackfish"
    ensure_app_dir(p)
    _auto_profile_(p, "default", "slurm", "localhost", "test", home_dir=p, cache_dir=p)
