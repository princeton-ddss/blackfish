"""API tests for WebSocket remote file browsing."""

import pytest
from unittest import mock

from litestar.testing import AsyncTestClient

from blackfish.server.models.profile import SlurmProfile, LocalProfile


pytestmark = pytest.mark.anyio


class MockSFTPAttr:
    """Mock SFTPAttributes for testing."""

    def __init__(self, filename, st_mode, st_size, st_mtime):
        self.filename = filename
        self.st_mode = st_mode
        self.st_size = st_size
        self.st_mtime = st_mtime


def create_mock_connection_class(mock_sftp):
    """Create a mock Connection class with SFTP support.

    The mock needs to support this pattern:
        self._connection = Connection(host=..., user=...)
        self._connection.__enter__()
        self._sftp = self._connection.sftp().__enter__()
    """
    mock_connection_class = mock.MagicMock()

    # The Connection() call returns a mock instance
    mock_connection_instance = mock.MagicMock()

    # __enter__ returns self (the connection instance)
    mock_connection_instance.__enter__ = mock.MagicMock(
        return_value=mock_connection_instance
    )
    mock_connection_instance.__exit__ = mock.MagicMock(return_value=False)

    # .sftp() returns a context manager that yields the mock_sftp
    mock_sftp_context = mock.MagicMock()
    mock_sftp_context.__enter__ = mock.MagicMock(return_value=mock_sftp)
    mock_sftp_context.__exit__ = mock.MagicMock(return_value=False)
    mock_connection_instance.sftp.return_value = mock_sftp_context

    mock_connection_class.return_value = mock_connection_instance
    return mock_connection_class


class TestRemoteFileBrowserWebSocket:
    """Test WebSocket remote file browser endpoint."""

    async def test_connect_with_invalid_profile(
        self,
        client: AsyncTestClient,
    ):
        """Test connection fails gracefully with non-existent profile."""
        with mock.patch(
            "blackfish.server.browser.deserialize_profile", return_value=None
        ):
            with await client.websocket_connect("/ws/files/nonexistent") as ws:
                data = ws.receive_json()
                assert data["status"] == "error"
                assert data["error"]["code"] == "invalid_profile"

    async def test_connect_with_local_profile(
        self,
        client: AsyncTestClient,
    ):
        """Test connection fails for local profiles."""
        local_profile = LocalProfile(
            name="local",
            home_dir="/home/local",
            cache_dir="/home/local/.cache",
        )

        with mock.patch(
            "blackfish.server.browser.deserialize_profile", return_value=local_profile
        ):
            with await client.websocket_connect("/ws/files/local") as ws:
                data = ws.receive_json()
                assert data["status"] == "error"
                assert data["error"]["code"] == "invalid_profile"

    async def test_connect_with_localhost_slurm_profile(
        self,
        client: AsyncTestClient,
    ):
        """Test connection fails for localhost SlurmProfile."""
        localhost_profile = SlurmProfile(
            name="localhost",
            host="localhost",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        with mock.patch(
            "blackfish.server.browser.deserialize_profile",
            return_value=localhost_profile,
        ):
            with await client.websocket_connect("/ws/files/localhost") as ws:
                data = ws.receive_json()
                assert data["status"] == "error"
                assert data["error"]["code"] == "invalid_profile"

    async def test_connection_success(
        self,
        client: AsyncTestClient,
    ):
        """Test successful connection to remote profile."""
        remote_profile = SlurmProfile(
            name="remote",
            host="remote.example.com",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        mock_sftp = mock.MagicMock()
        mock_connection_class = create_mock_connection_class(mock_sftp)

        with (
            mock.patch(
                "blackfish.server.browser.deserialize_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.browser.Connection",
                mock_connection_class,
            ),
        ):

            with await client.websocket_connect("/ws/files/remote") as ws:
                data = ws.receive_json()
                assert data["status"] == "connected"
                assert data["profile"] == "remote"
                assert data["home_dir"] == "/home/testuser"

    async def test_list_directory(
        self,
        client: AsyncTestClient,
    ):
        """Test listing directory contents via WebSocket."""
        remote_profile = SlurmProfile(
            name="remote",
            host="remote.example.com",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        mock_sftp = mock.MagicMock()
        mock_sftp.listdir_attr.return_value = [
            MockSFTPAttr("file1.txt", 0o100644, 1024, 1704067200),
            MockSFTPAttr("dir1", 0o040755, 4096, 1704067200),
        ]
        mock_connection_class = create_mock_connection_class(mock_sftp)

        with (
            mock.patch(
                "blackfish.server.browser.deserialize_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.browser.Connection",
                mock_connection_class,
            ),
        ):

            with await client.websocket_connect("/ws/files/remote") as ws:
                # Receive connection success
                data = ws.receive_json()
                assert data["status"] == "connected"

                # Send list request
                ws.send_json({
                    "id": "req-1",
                    "action": "list",
                    "path": "/documents",
                })

                response = ws.receive_json()
                assert response["id"] == "req-1"
                assert response["status"] == "ok"
                assert response["action"] == "list"
                assert len(response["entries"]) == 2
                assert response["entries"][0]["name"] == "file1.txt"
                assert response["entries"][0]["is_dir"] is False
                assert response["entries"][1]["name"] == "dir1"
                assert response["entries"][1]["is_dir"] is True

    async def test_stat_file(
        self,
        client: AsyncTestClient,
    ):
        """Test getting file stats via WebSocket."""
        remote_profile = SlurmProfile(
            name="remote",
            host="remote.example.com",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        mock_sftp = mock.MagicMock()
        mock_attr = mock.MagicMock()
        mock_attr.st_mode = 0o100644
        mock_attr.st_size = 2048
        mock_attr.st_mtime = 1704067200
        mock_sftp.stat.return_value = mock_attr
        mock_connection_class = create_mock_connection_class(mock_sftp)

        with (
            mock.patch(
                "blackfish.server.browser.deserialize_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.browser.Connection",
                mock_connection_class,
            ),
        ):

            with await client.websocket_connect("/ws/files/remote") as ws:
                # Receive connection success
                data = ws.receive_json()
                assert data["status"] == "connected"

                # Send stat request
                ws.send_json({
                    "id": "req-1",
                    "action": "stat",
                    "path": "file.txt",
                })

                response = ws.receive_json()
                assert response["id"] == "req-1"
                assert response["status"] == "ok"
                assert response["action"] == "stat"
                assert response["entry"]["name"] == "file.txt"
                assert response["entry"]["size"] == 2048
                assert response["entry"]["is_dir"] is False

    async def test_exists_true(
        self,
        client: AsyncTestClient,
    ):
        """Test checking if path exists via WebSocket."""
        remote_profile = SlurmProfile(
            name="remote",
            host="remote.example.com",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        mock_sftp = mock.MagicMock()
        mock_sftp.stat.return_value = mock.MagicMock()  # Path exists
        mock_connection_class = create_mock_connection_class(mock_sftp)

        with (
            mock.patch(
                "blackfish.server.browser.deserialize_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.browser.Connection",
                mock_connection_class,
            ),
        ):

            with await client.websocket_connect("/ws/files/remote") as ws:
                data = ws.receive_json()
                assert data["status"] == "connected"

                ws.send_json({
                    "id": "req-1",
                    "action": "exists",
                    "path": "existing_file.txt",
                })

                response = ws.receive_json()
                assert response["id"] == "req-1"
                assert response["status"] == "ok"
                assert response["action"] == "exists"
                assert response["data"]["exists"] is True

    async def test_exists_false(
        self,
        client: AsyncTestClient,
    ):
        """Test checking if non-existent path exists via WebSocket."""
        remote_profile = SlurmProfile(
            name="remote",
            host="remote.example.com",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        mock_sftp = mock.MagicMock()
        mock_sftp.stat.side_effect = FileNotFoundError()
        mock_connection_class = create_mock_connection_class(mock_sftp)

        with (
            mock.patch(
                "blackfish.server.browser.deserialize_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.browser.Connection",
                mock_connection_class,
            ),
        ):

            with await client.websocket_connect("/ws/files/remote") as ws:
                data = ws.receive_json()
                assert data["status"] == "connected"

                ws.send_json({
                    "id": "req-1",
                    "action": "exists",
                    "path": "nonexistent.txt",
                })

                response = ws.receive_json()
                assert response["id"] == "req-1"
                assert response["status"] == "ok"
                assert response["action"] == "exists"
                assert response["data"]["exists"] is False

    async def test_mkdir(
        self,
        client: AsyncTestClient,
    ):
        """Test creating directory via WebSocket."""
        remote_profile = SlurmProfile(
            name="remote",
            host="remote.example.com",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        mock_sftp = mock.MagicMock()
        mock_connection_class = create_mock_connection_class(mock_sftp)

        with (
            mock.patch(
                "blackfish.server.browser.deserialize_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.browser.Connection",
                mock_connection_class,
            ),
        ):

            with await client.websocket_connect("/ws/files/remote") as ws:
                data = ws.receive_json()
                assert data["status"] == "connected"

                ws.send_json({
                    "id": "req-1",
                    "action": "mkdir",
                    "path": "new_directory",
                })

                response = ws.receive_json()
                assert response["id"] == "req-1"
                assert response["status"] == "ok"
                assert response["action"] == "mkdir"
                mock_sftp.mkdir.assert_called_once_with("/home/testuser/new_directory")

    async def test_delete_file(
        self,
        client: AsyncTestClient,
    ):
        """Test deleting file via WebSocket."""
        remote_profile = SlurmProfile(
            name="remote",
            host="remote.example.com",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        mock_sftp = mock.MagicMock()
        mock_attr = mock.MagicMock()
        mock_attr.st_mode = 0o100644  # Regular file
        mock_sftp.stat.return_value = mock_attr
        mock_connection_class = create_mock_connection_class(mock_sftp)

        with (
            mock.patch(
                "blackfish.server.browser.deserialize_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.browser.Connection",
                mock_connection_class,
            ),
        ):

            with await client.websocket_connect("/ws/files/remote") as ws:
                data = ws.receive_json()
                assert data["status"] == "connected"

                ws.send_json({
                    "id": "req-1",
                    "action": "delete",
                    "path": "file_to_delete.txt",
                })

                response = ws.receive_json()
                assert response["id"] == "req-1"
                assert response["status"] == "ok"
                assert response["action"] == "delete"
                mock_sftp.remove.assert_called_once_with(
                    "/home/testuser/file_to_delete.txt"
                )

    async def test_rename(
        self,
        client: AsyncTestClient,
    ):
        """Test renaming file via WebSocket."""
        remote_profile = SlurmProfile(
            name="remote",
            host="remote.example.com",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        mock_sftp = mock.MagicMock()
        mock_connection_class = create_mock_connection_class(mock_sftp)

        with (
            mock.patch(
                "blackfish.server.browser.deserialize_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.browser.Connection",
                mock_connection_class,
            ),
        ):

            with await client.websocket_connect("/ws/files/remote") as ws:
                data = ws.receive_json()
                assert data["status"] == "connected"

                ws.send_json({
                    "id": "req-1",
                    "action": "rename",
                    "old_path": "old_name.txt",
                    "new_path": "new_name.txt",
                })

                response = ws.receive_json()
                assert response["id"] == "req-1"
                assert response["status"] == "ok"
                assert response["action"] == "rename"
                mock_sftp.rename.assert_called_once_with(
                    "/home/testuser/old_name.txt",
                    "/home/testuser/new_name.txt",
                )

    async def test_invalid_action(
        self,
        client: AsyncTestClient,
    ):
        """Test handling of invalid action."""
        remote_profile = SlurmProfile(
            name="remote",
            host="remote.example.com",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        mock_sftp = mock.MagicMock()
        mock_connection_class = create_mock_connection_class(mock_sftp)

        with (
            mock.patch(
                "blackfish.server.browser.deserialize_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.browser.Connection",
                mock_connection_class,
            ),
        ):

            with await client.websocket_connect("/ws/files/remote") as ws:
                data = ws.receive_json()
                assert data["status"] == "connected"

                ws.send_json({
                    "id": "req-1",
                    "action": "invalid_action",
                    "path": "/some/path",
                })

                response = ws.receive_json()
                assert response["id"] == "req-1"
                assert response["status"] == "error"
                assert response["error"]["code"] == "unknown_action"

    async def test_missing_path_field(
        self,
        client: AsyncTestClient,
    ):
        """Test handling of missing path field."""
        remote_profile = SlurmProfile(
            name="remote",
            host="remote.example.com",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        mock_sftp = mock.MagicMock()
        mock_connection_class = create_mock_connection_class(mock_sftp)

        with (
            mock.patch(
                "blackfish.server.browser.deserialize_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.browser.Connection",
                mock_connection_class,
            ),
        ):

            with await client.websocket_connect("/ws/files/remote") as ws:
                data = ws.receive_json()
                assert data["status"] == "connected"

                ws.send_json({
                    "id": "req-1",
                    "action": "stat",
                    # Missing "path" field
                })

                response = ws.receive_json()
                assert response["id"] == "req-1"
                assert response["status"] == "error"
                assert response["error"]["code"] == "invalid_request"

    async def test_path_not_found_error(
        self,
        client: AsyncTestClient,
    ):
        """Test handling of path not found error."""
        remote_profile = SlurmProfile(
            name="remote",
            host="remote.example.com",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        mock_sftp = mock.MagicMock()
        mock_sftp.listdir_attr.side_effect = FileNotFoundError()
        mock_connection_class = create_mock_connection_class(mock_sftp)

        with (
            mock.patch(
                "blackfish.server.browser.deserialize_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.browser.Connection",
                mock_connection_class,
            ),
        ):

            with await client.websocket_connect("/ws/files/remote") as ws:
                data = ws.receive_json()
                assert data["status"] == "connected"

                ws.send_json({
                    "id": "req-1",
                    "action": "list",
                    "path": "/nonexistent",
                })

                response = ws.receive_json()
                assert response["id"] == "req-1"
                assert response["status"] == "error"
                assert response["error"]["code"] == "not_found"

    async def test_permission_denied_error(
        self,
        client: AsyncTestClient,
    ):
        """Test handling of permission denied error."""
        remote_profile = SlurmProfile(
            name="remote",
            host="remote.example.com",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        mock_sftp = mock.MagicMock()
        mock_sftp.listdir_attr.side_effect = PermissionError()
        mock_connection_class = create_mock_connection_class(mock_sftp)

        with (
            mock.patch(
                "blackfish.server.browser.deserialize_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.browser.Connection",
                mock_connection_class,
            ),
        ):

            with await client.websocket_connect("/ws/files/remote") as ws:
                data = ws.receive_json()
                assert data["status"] == "connected"

                ws.send_json({
                    "id": "req-1",
                    "action": "list",
                    "path": "/protected",
                })

                response = ws.receive_json()
                assert response["id"] == "req-1"
                assert response["status"] == "error"
                assert response["error"]["code"] == "permission_denied"
