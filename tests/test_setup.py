import pytest


from app.setup import (
    create_local_home_dir,
    check_local_cache_exists,
)
from app.cli.profile import _auto_profile_


def test_create_local_home_dir_existing_root(tmp_path):
    p = tmp_path / ".blackfish"
    create_local_home_dir(p)
    assert p.exists()


def test_create_local_home_dir_missing_root(tmp_path):
    p = tmp_path / "missing" / ".blackfish"
    with pytest.raises(Exception):
        create_local_home_dir(p)


def test_check_local_cache_exists_existing_dir(tmp_path):
    check_local_cache_exists(tmp_path)


def test_check_local_cache_exists_missing_dir(tmp_path):
    with pytest.raises(Exception):
        check_local_cache_exists(tmp_path / "missing")


def test_local_auto_setup(tmp_path):
    p = tmp_path / ".blackfish"
    create_local_home_dir(p)
    _auto_profile_(p, "default", "local", None, None, home_dir=p, cache_dir=p)


def test_slurm_auto_setup(tmp_path):
    p = tmp_path / ".blackfish"
    create_local_home_dir(p)
    _auto_profile_(p, "default", "slurm", "localhost", "test", home_dir=p, cache_dir=p)
