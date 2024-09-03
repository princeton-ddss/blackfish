from unittest import mock

from app import utils
from app.config import SlurmRemote


profile = SlurmRemote(
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
    assert utils.get_models(profile) == [
        "test/model-a",
        "test/model-b",
        "test/model-c",
        "test/model-d",
    ]


@mock.patch.object(utils.Connection, "sftp", new=mock_sftp)
def test_get_revisions():
    assert utils.get_revisions("test/model-a", profile=profile) == [
        "test-commit-a",
        "test-commit-b",
    ]


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
