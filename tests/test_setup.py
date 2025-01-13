import pytest


from app.setup import (
    create_local_home_dir,
    # create_remote_home_dir,
    check_local_cache_exists,
    # check_remote_cache_exists,
)


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


# def test_create_remote_home_dir(monkeypatch):
# 1 - missing root directory => "Directory <root> does not exist."
# 2 - existing root directory => assert <root>/.blackfish exists
# 3 - network error => "Unable to connect to host: <error>"
# pass


# def test_check_remote_cache_exists(monkeypatch):
# 1 - cache exists => return 1
# 2 - cache missing => raise Exception
# 3 - network error => "Unable to connect to host: <error>"
# pass
