import os
from unittest import mock
import datetime

import pytest

from blackfish.server import utils
from blackfish.server.models.profile import SlurmProfile


os.environ["COLUMNS"] = "300"


profile = SlurmProfile(
    name="test",
    host="test",
    user="test",
    cache_dir="/test/cache_dir/.blackfish",
    home_dir="/test/home_dir/.blackfish",
)


filesystem = {
    "/test/cache_dir/.blackfish/models": [
        "models--test--model-a",
        "models--test--model-b",
    ],
    "/test/home_dir/.blackfish/models": [
        "models--test--model-c",
        "models--test--model-d",
    ],
    "/test/cache_dir/.blackfish/models/models--test--model-a/snapshots": [
        "test-commit-a",
        "test-commit-b",
    ],
    "/test/home_dir/.blackfish/models/models--test--model-c/snapshots": [
        "test-commit-a",
        "test-commit-b",
    ],
}


class MockSFTPClient:
    @staticmethod
    def listdir(key):
        try:
            return filesystem[key]
        except KeyError:
            raise FileNotFoundError(key)


def _mock_connection_class():
    """Build a fabric.Connection class mock whose .sftp() returns MockSFTPClient.

    Patches the Connection symbol that RemoteSession._open() uses: each
    Connection(...) call returns an instance with mocked open/close/sftp,
    so no DNS resolution or real socket open happens during tests.
    """
    mock_cls = mock.MagicMock()
    instance = mock_cls.return_value
    instance.open = mock.MagicMock()
    instance.close = mock.MagicMock()
    instance.sftp.return_value = MockSFTPClient()
    return mock_cls


@mock.patch(
    "blackfish.server.remote.session.Connection", new_callable=_mock_connection_class
)
def test_get_models(mock_conn):
    assert set(utils.get_models(profile)) == set(
        [
            "test/model-a",
            "test/model-b",
            "test/model-c",
            "test/model-d",
        ]
    )


@mock.patch(
    "blackfish.server.remote.session.Connection", new_callable=_mock_connection_class
)
def test_get_revisions(mock_conn):
    assert set(utils.get_revisions("test/model-a", profile=profile)) == set(
        [
            "test-commit-a",
            "test-commit-b",
        ]
    )


@mock.patch(
    "blackfish.server.remote.session.Connection", new_callable=_mock_connection_class
)
def test_get_model_dir_some(mock_conn):
    assert (
        utils.get_model_dir("test/model-a", revision="test-commit-a", profile=profile)
        == "/test/cache_dir/.blackfish/models/models--test--model-a"
    )


@mock.patch(
    "blackfish.server.remote.session.Connection", new_callable=_mock_connection_class
)
def test_get_model_dir_none(mock_conn):
    assert (
        utils.get_model_dir("test/model-a", revision="test-commit-e", profile=profile)
        is None
    )


@mock.patch(
    "blackfish.server.remote.session.Connection", new_callable=_mock_connection_class
)
def test_get_models_missing_cache_dir_raises(mock_conn):
    """If cache_dir is missing, raise FileNotFoundError so callers can react."""
    bad_profile = SlurmProfile(
        name="test",
        host="test",
        user="test",
        cache_dir="/missing/cache_dir/.blackfish",
        home_dir="/test/home_dir/.blackfish",
    )
    with pytest.raises(FileNotFoundError):
        utils.get_models(bad_profile)


# TODO
def test_find_port_none():
    pass


def test_format_datetime():
    t1 = datetime.datetime(
        2025, 1, 12, 14, 58, 29, 646404, tzinfo=datetime.timezone.utc
    )

    t0 = datetime.datetime(
        2024, 11, 19, 14, 46, 40, 499539, tzinfo=datetime.timezone.utc
    )
    assert utils.format_datetime(t0, t1) == "54 days ago"

    t0 = datetime.datetime(
        2025, 1, 12, 14, 58, 29, 499539, tzinfo=datetime.timezone.utc
    )
    assert utils.format_datetime(t0, t1) == "Now"

    t0 = datetime.datetime(
        2025, 1, 12, 14, 58, 19, 646404, tzinfo=datetime.timezone.utc
    )
    assert utils.format_datetime(t0, t1) == "10 sec ago"

    t0 = datetime.datetime(
        2025, 1, 12, 14, 55, 29, 646404, tzinfo=datetime.timezone.utc
    )
    assert utils.format_datetime(t0, t1) == "3 min ago"

    # Clock skew: t0 slightly ahead of t1 must read "Now", not wrap to hours.
    t0 = datetime.datetime(2025, 1, 12, 14, 58, 30, 0, tzinfo=datetime.timezone.utc)
    assert utils.format_datetime(t0, t1) == "Now"

    # A naive t0 (e.g. an API timestamp without an offset) is treated as UTC,
    # not a crash on aware/naive subtraction.
    naive_t0 = datetime.datetime(2025, 1, 12, 14, 55, 29, 646404)
    assert utils.format_datetime(naive_t0, t1) == "3 min ago"
