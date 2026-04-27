import pytest


from blackfish.server.setup import check_local_cache_exists
from blackfish.server.migrations import ensure_app_dir
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


def test_slurm_auto_setup(tmp_path):
    p = tmp_path / ".blackfish"
    ensure_app_dir(p)
    _auto_profile_(p, "default", "slurm", "localhost", "test", home_dir=p, cache_dir=p)
