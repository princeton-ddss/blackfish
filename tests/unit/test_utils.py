import os
from unittest import mock
import datetime

from app import utils
from app.models.profile import SlurmProfile


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
        return filesystem[key]

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass


def mock_sftp(conn):
    return MockSFTPClient()


@mock.patch.object(utils.Connection, "sftp", new=mock_sftp)
def test_get_models():
    assert set(utils.get_models(profile)) == set(
        [
            "test/model-a",
            "test/model-b",
            "test/model-c",
            "test/model-d",
        ]
    )


@mock.patch.object(utils.Connection, "sftp", new=mock_sftp)
def test_get_revisions():
    assert set(utils.get_revisions("test/model-a", profile=profile)) == set(
        [
            "test-commit-a",
            "test-commit-b",
        ]
    )


@mock.patch.object(utils.Connection, "sftp", new=mock_sftp)
def test_get_model_dir_some():
    assert (
        utils.get_model_dir("test/model-a", revision="test-commit-a", profile=profile)
        == "/test/cache_dir/.blackfish/models/models--test--model-a"
    )


@mock.patch.object(utils.Connection, "sftp", new=mock_sftp)
def test_get_model_dir_none():
    assert (
        utils.get_model_dir("test/model-a", revision="test-commit-e", profile=profile)
        is None
    )


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
