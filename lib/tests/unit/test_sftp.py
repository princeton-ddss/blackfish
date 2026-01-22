"""Unit tests for remote file operations."""

import pytest
from unittest import mock

from blackfish.server.sftp import (
    format_permissions,
    sftp_listdir,
    sftp_stat,
    sftp_exists,
    sftp_mkdir,
    sftp_delete,
    sftp_rename,
)


class TestFormatPermissions:
    def test_full_permissions(self):
        assert format_permissions(0o777) == "rwxrwxrwx"

    def test_no_permissions(self):
        assert format_permissions(0o000) == "---------"

    def test_typical_file(self):
        assert format_permissions(0o644) == "rw-r--r--"

    def test_typical_dir(self):
        assert format_permissions(0o755) == "rwxr-xr-x"

    def test_read_only(self):
        assert format_permissions(0o444) == "r--r--r--"

    def test_execute_only(self):
        assert format_permissions(0o111) == "--x--x--x"


class MockSFTPAttr:
    """Mock SFTPAttributes for testing."""

    def __init__(self, filename, st_mode, st_size, st_mtime):
        self.filename = filename
        self.st_mode = st_mode
        self.st_size = st_size
        self.st_mtime = st_mtime


class TestSftpListdir:
    def test_list_directory(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.listdir_attr.return_value = [
            MockSFTPAttr("file1.txt", 0o100644, 1024, 1704067200),
            MockSFTPAttr("dir1", 0o040755, 4096, 1704067200),
        ]

        results = sftp_listdir(mock_sftp, "/home/testuser/documents")

        assert len(results) == 2
        assert results[0].name == "file1.txt"
        assert results[0].path == "/home/testuser/documents/file1.txt"
        assert results[0].is_dir is False
        assert results[0].size == 1024
        assert results[0].permissions == "rw-r--r--"
        assert results[1].name == "dir1"
        assert results[1].path == "/home/testuser/documents/dir1"
        assert results[1].is_dir is True
        assert results[1].permissions == "rwxr-xr-x"

    def test_list_excludes_hidden_by_default(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.listdir_attr.return_value = [
            MockSFTPAttr(".hidden", 0o100644, 1024, 1704067200),
            MockSFTPAttr("visible.txt", 0o100644, 1024, 1704067200),
        ]

        results = sftp_listdir(mock_sftp, "/home/testuser/documents", hidden=False)

        assert len(results) == 1
        assert results[0].name == "visible.txt"

    def test_list_includes_hidden_when_requested(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.listdir_attr.return_value = [
            MockSFTPAttr(".hidden", 0o100644, 1024, 1704067200),
            MockSFTPAttr("visible.txt", 0o100644, 1024, 1704067200),
        ]

        results = sftp_listdir(mock_sftp, "/home/testuser/documents", hidden=True)

        assert len(results) == 2

    def test_list_not_found(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.listdir_attr.side_effect = FileNotFoundError()

        with pytest.raises(FileNotFoundError):
            sftp_listdir(mock_sftp, "/home/testuser/nonexistent")

    def test_list_permission_denied(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.listdir_attr.side_effect = PermissionError()

        with pytest.raises(PermissionError):
            sftp_listdir(mock_sftp, "/home/testuser/protected")

    def test_list_empty_directory(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.listdir_attr.return_value = []

        results = sftp_listdir(mock_sftp, "/home/testuser/empty")

        assert len(results) == 0

    def test_list_connection_error(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.listdir_attr.side_effect = Exception("Connection reset by peer")

        with pytest.raises(OSError) as exc_info:
            sftp_listdir(mock_sftp, "/home/testuser/somedir")
        assert "Connection reset by peer" in str(exc_info.value)


class TestSftpStat:
    def test_stat_file(self):
        mock_sftp = mock.MagicMock()
        mock_attr = mock.MagicMock()
        mock_attr.st_mode = 0o100644
        mock_attr.st_size = 2048
        mock_attr.st_mtime = 1704067200
        mock_sftp.stat.return_value = mock_attr

        result = sftp_stat(mock_sftp, "/home/testuser/file.txt")

        assert result.name == "file.txt"
        assert result.path == "/home/testuser/file.txt"
        assert result.is_dir is False
        assert result.size == 2048
        assert result.permissions == "rw-r--r--"

    def test_stat_directory(self):
        mock_sftp = mock.MagicMock()
        mock_attr = mock.MagicMock()
        mock_attr.st_mode = 0o040755
        mock_attr.st_size = 4096
        mock_attr.st_mtime = 1704067200
        mock_sftp.stat.return_value = mock_attr

        result = sftp_stat(mock_sftp, "/home/testuser/mydir")

        assert result.name == "mydir"
        assert result.path == "/home/testuser/mydir"
        assert result.is_dir is True
        assert result.permissions == "rwxr-xr-x"

    def test_stat_not_found(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.stat.side_effect = FileNotFoundError()

        with pytest.raises(FileNotFoundError):
            sftp_stat(mock_sftp, "/home/testuser/nonexistent")

    def test_stat_permission_denied(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.stat.side_effect = PermissionError()

        with pytest.raises(PermissionError):
            sftp_stat(mock_sftp, "/home/testuser/protected")


class TestSftpExists:
    def test_exists_true(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.stat.return_value = mock.MagicMock()

        assert sftp_exists(mock_sftp, "/home/testuser/existing") is True

    def test_exists_false(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.stat.side_effect = FileNotFoundError()

        assert sftp_exists(mock_sftp, "/home/testuser/nonexistent") is False


class TestSftpMkdir:
    def test_mkdir_success(self):
        mock_sftp = mock.MagicMock()

        # Should not raise
        sftp_mkdir(mock_sftp, "/home/testuser/newdir")

        mock_sftp.mkdir.assert_called_once_with("/home/testuser/newdir")

    def test_mkdir_parent_not_found(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.mkdir.side_effect = FileNotFoundError()

        with pytest.raises(FileNotFoundError):
            sftp_mkdir(mock_sftp, "/home/testuser/nonexistent/newdir")

    def test_mkdir_permission_denied(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.mkdir.side_effect = PermissionError()

        with pytest.raises(PermissionError):
            sftp_mkdir(mock_sftp, "/home/testuser/protected/newdir")

    def test_mkdir_already_exists(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.mkdir.side_effect = IOError("File exists")

        with pytest.raises(ValueError) as exc_info:
            sftp_mkdir(mock_sftp, "/home/testuser/existing")
        assert "already exists" in str(exc_info.value).lower()


class TestSftpDelete:
    def test_delete_file(self):
        mock_sftp = mock.MagicMock()
        mock_attr = mock.MagicMock()
        mock_attr.st_mode = 0o100644  # Regular file
        mock_sftp.stat.return_value = mock_attr

        sftp_delete(mock_sftp, "/home/testuser/file.txt")

        mock_sftp.remove.assert_called_once_with("/home/testuser/file.txt")
        mock_sftp.rmdir.assert_not_called()

    def test_delete_directory(self):
        mock_sftp = mock.MagicMock()
        mock_attr = mock.MagicMock()
        mock_attr.st_mode = 0o040755  # Directory
        mock_sftp.stat.return_value = mock_attr

        sftp_delete(mock_sftp, "/home/testuser/mydir")

        mock_sftp.rmdir.assert_called_once_with("/home/testuser/mydir")
        mock_sftp.remove.assert_not_called()

    def test_delete_not_found(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.stat.side_effect = FileNotFoundError()

        with pytest.raises(FileNotFoundError):
            sftp_delete(mock_sftp, "/home/testuser/nonexistent")

    def test_delete_permission_denied(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.stat.side_effect = PermissionError()

        with pytest.raises(PermissionError):
            sftp_delete(mock_sftp, "/home/testuser/protected")

    def test_delete_directory_not_empty(self):
        mock_sftp = mock.MagicMock()
        mock_attr = mock.MagicMock()
        mock_attr.st_mode = 0o040755  # Directory
        mock_sftp.stat.return_value = mock_attr
        mock_sftp.rmdir.side_effect = IOError("Directory not empty")

        with pytest.raises(ValueError) as exc_info:
            sftp_delete(mock_sftp, "/home/testuser/nonemptydir")
        assert "not empty" in str(exc_info.value).lower()


class TestSftpRename:
    def test_rename_success(self):
        mock_sftp = mock.MagicMock()

        sftp_rename(
            mock_sftp, "/home/testuser/oldname.txt", "/home/testuser/newname.txt"
        )

        mock_sftp.rename.assert_called_once_with(
            "/home/testuser/oldname.txt",
            "/home/testuser/newname.txt",
        )

    def test_rename_not_found(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.rename.side_effect = FileNotFoundError()

        with pytest.raises(FileNotFoundError):
            sftp_rename(
                mock_sftp, "/home/testuser/nonexistent", "/home/testuser/newname"
            )

    def test_rename_permission_denied(self):
        mock_sftp = mock.MagicMock()
        mock_sftp.rename.side_effect = PermissionError()

        with pytest.raises(PermissionError):
            sftp_rename(mock_sftp, "/home/testuser/protected", "/home/testuser/newname")

    def test_rename_move_to_different_dir(self):
        mock_sftp = mock.MagicMock()

        sftp_rename(
            mock_sftp, "/home/testuser/file.txt", "/home/testuser/subdir/file.txt"
        )

        mock_sftp.rename.assert_called_once_with(
            "/home/testuser/file.txt",
            "/home/testuser/subdir/file.txt",
        )
