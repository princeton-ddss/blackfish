"""Unit tests for remote file operations via SFTP."""

import pytest
from unittest import mock

from litestar.exceptions import (
    NotFoundException,
    NotAuthorizedException,
    ValidationException,
)

from blackfish.server.sftp import read_file, write_file, delete_file, WriteFileResponse
from blackfish.server.models.profile import SlurmProfile


@pytest.fixture
def remote_profile():
    """Create a test remote profile."""
    return SlurmProfile(
        name="remote",
        host="remote.example.com",
        user="testuser",
        home_dir="/home/testuser",
        cache_dir="/home/testuser/.cache",
    )


class TestReadFile:
    def test_read_file_success(self, remote_profile):
        mock_file = mock.MagicMock()
        mock_file.read.return_value = b"file content"
        mock_file.__enter__ = mock.MagicMock(return_value=mock_file)
        mock_file.__exit__ = mock.MagicMock(return_value=False)

        mock_sftp = mock.MagicMock()
        mock_sftp.open.return_value = mock_file
        mock_sftp.__enter__ = mock.MagicMock(return_value=mock_sftp)
        mock_sftp.__exit__ = mock.MagicMock(return_value=False)

        mock_conn = mock.MagicMock()
        mock_conn.sftp.return_value = mock_sftp
        mock_conn.__enter__ = mock.MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("blackfish.server.sftp.Connection", return_value=mock_conn):
            result = read_file(remote_profile, "/home/testuser/file.txt")
            assert result == b"file content"
            mock_sftp.open.assert_called_once_with("/home/testuser/file.txt", "rb")

    def test_read_file_not_found(self, remote_profile):
        mock_sftp = mock.MagicMock()
        mock_sftp.open.side_effect = FileNotFoundError()
        mock_sftp.__enter__ = mock.MagicMock(return_value=mock_sftp)
        mock_sftp.__exit__ = mock.MagicMock(return_value=False)

        mock_conn = mock.MagicMock()
        mock_conn.sftp.return_value = mock_sftp
        mock_conn.__enter__ = mock.MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("blackfish.server.sftp.Connection", return_value=mock_conn):
            with pytest.raises(NotFoundException):
                read_file(remote_profile, "/nonexistent/file.txt")

    def test_read_file_permission_denied(self, remote_profile):
        mock_sftp = mock.MagicMock()
        mock_sftp.open.side_effect = PermissionError()
        mock_sftp.__enter__ = mock.MagicMock(return_value=mock_sftp)
        mock_sftp.__exit__ = mock.MagicMock(return_value=False)

        mock_conn = mock.MagicMock()
        mock_conn.sftp.return_value = mock_sftp
        mock_conn.__enter__ = mock.MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("blackfish.server.sftp.Connection", return_value=mock_conn):
            with pytest.raises(NotAuthorizedException):
                read_file(remote_profile, "/protected/file.txt")


class TestWriteFile:
    def test_write_file_new_success(self, remote_profile):
        mock_file = mock.MagicMock()
        mock_file.__enter__ = mock.MagicMock(return_value=mock_file)
        mock_file.__exit__ = mock.MagicMock(return_value=False)

        mock_sftp = mock.MagicMock()
        mock_sftp.stat.side_effect = FileNotFoundError()  # File doesn't exist
        mock_sftp.open.return_value = mock_file
        mock_sftp.__enter__ = mock.MagicMock(return_value=mock_sftp)
        mock_sftp.__exit__ = mock.MagicMock(return_value=False)

        mock_conn = mock.MagicMock()
        mock_conn.sftp.return_value = mock_sftp
        mock_conn.__enter__ = mock.MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("blackfish.server.sftp.Connection", return_value=mock_conn):
            result = write_file(
                remote_profile, "/home/testuser/new.txt", b"content", update=False
            )
            assert isinstance(result, WriteFileResponse)
            assert result.filename == "new.txt"
            assert result.size == 7
            assert result.path == "/home/testuser/new.txt"

    def test_write_file_new_already_exists(self, remote_profile):
        mock_sftp = mock.MagicMock()
        mock_sftp.stat.return_value = mock.MagicMock()  # File exists
        mock_sftp.__enter__ = mock.MagicMock(return_value=mock_sftp)
        mock_sftp.__exit__ = mock.MagicMock(return_value=False)

        mock_conn = mock.MagicMock()
        mock_conn.sftp.return_value = mock_sftp
        mock_conn.__enter__ = mock.MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("blackfish.server.sftp.Connection", return_value=mock_conn):
            with pytest.raises(ValidationException):
                write_file(
                    remote_profile,
                    "/home/testuser/existing.txt",
                    b"content",
                    update=False,
                )

    def test_write_file_update_success(self, remote_profile):
        mock_file = mock.MagicMock()
        mock_file.__enter__ = mock.MagicMock(return_value=mock_file)
        mock_file.__exit__ = mock.MagicMock(return_value=False)

        mock_sftp = mock.MagicMock()
        mock_sftp.stat.return_value = mock.MagicMock()  # File exists
        mock_sftp.open.return_value = mock_file
        mock_sftp.__enter__ = mock.MagicMock(return_value=mock_sftp)
        mock_sftp.__exit__ = mock.MagicMock(return_value=False)

        mock_conn = mock.MagicMock()
        mock_conn.sftp.return_value = mock_sftp
        mock_conn.__enter__ = mock.MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("blackfish.server.sftp.Connection", return_value=mock_conn):
            result = write_file(
                remote_profile, "/home/testuser/existing.txt", b"updated", update=True
            )
            assert isinstance(result, WriteFileResponse)
            assert result.filename == "existing.txt"

    def test_write_file_update_not_found(self, remote_profile):
        mock_sftp = mock.MagicMock()
        mock_sftp.stat.side_effect = FileNotFoundError()
        mock_sftp.__enter__ = mock.MagicMock(return_value=mock_sftp)
        mock_sftp.__exit__ = mock.MagicMock(return_value=False)

        mock_conn = mock.MagicMock()
        mock_conn.sftp.return_value = mock_sftp
        mock_conn.__enter__ = mock.MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("blackfish.server.sftp.Connection", return_value=mock_conn):
            with pytest.raises(NotFoundException):
                write_file(
                    remote_profile, "/nonexistent/file.txt", b"content", update=True
                )


class TestDeleteFile:
    def test_delete_file_success(self, remote_profile):
        mock_sftp = mock.MagicMock()
        mock_sftp.__enter__ = mock.MagicMock(return_value=mock_sftp)
        mock_sftp.__exit__ = mock.MagicMock(return_value=False)

        mock_conn = mock.MagicMock()
        mock_conn.sftp.return_value = mock_sftp
        mock_conn.__enter__ = mock.MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("blackfish.server.sftp.Connection", return_value=mock_conn):
            result = delete_file(remote_profile, "/home/testuser/file.txt")
            assert result == "/home/testuser/file.txt"
            mock_sftp.remove.assert_called_once_with("/home/testuser/file.txt")

    def test_delete_file_not_found(self, remote_profile):
        mock_sftp = mock.MagicMock()
        mock_sftp.remove.side_effect = FileNotFoundError()
        mock_sftp.__enter__ = mock.MagicMock(return_value=mock_sftp)
        mock_sftp.__exit__ = mock.MagicMock(return_value=False)

        mock_conn = mock.MagicMock()
        mock_conn.sftp.return_value = mock_sftp
        mock_conn.__enter__ = mock.MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("blackfish.server.sftp.Connection", return_value=mock_conn):
            with pytest.raises(NotFoundException):
                delete_file(remote_profile, "/nonexistent/file.txt")

    def test_delete_file_permission_denied(self, remote_profile):
        mock_sftp = mock.MagicMock()
        mock_sftp.remove.side_effect = PermissionError()
        mock_sftp.__enter__ = mock.MagicMock(return_value=mock_sftp)
        mock_sftp.__exit__ = mock.MagicMock(return_value=False)

        mock_conn = mock.MagicMock()
        mock_conn.sftp.return_value = mock_sftp
        mock_conn.__enter__ = mock.MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("blackfish.server.sftp.Connection", return_value=mock_conn):
            with pytest.raises(NotAuthorizedException):
                delete_file(remote_profile, "/protected/file.txt")
