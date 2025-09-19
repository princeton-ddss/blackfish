from unittest import mock
from contextlib import contextmanager

from app.ssh_manager import SSHConnectionManager
from app.utils import get_models, get_revisions, get_model_dir, has_model
from app.models.profile import SlurmProfile, LocalProfile


class MockSFTPClient:
    """Mock SFTP client for testing."""

    def __init__(self):
        self.filesystem = {
            "/test/cache_dir/.blackfish/models": [
                "models--test--model-a",
                "models--test--model-b",
            ],
            "/test/home_dir/.blackfish/models": [
                "models--test--model-c",
            ],
            "/test/cache_dir/.blackfish/models/models--test--model-a/snapshots": [
                "test-commit-a",
                "test-commit-b",
            ],
            "/test/home_dir/.blackfish/models/models--test--model-c/snapshots": [
                "test-commit-c",
            ],
        }

    def listdir(self, path):
        """Mock listdir."""
        return self.filesystem.get(path, [])

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass


class MockConnection:
    """Mock fabric Connection for testing."""

    def __init__(self, host: str, user: str):
        self.host = host
        self.user = user
        self.closed = False

    def run(self, command, hide=True, warn=True):
        """Mock run method."""

        class MockResult:
            ok = True

        return MockResult()

    def sftp(self):
        """Mock SFTP client."""
        return MockSFTPClient()

    def close(self):
        """Mock close."""
        self.closed = True


class MockSSHManager:
    """Mock SSH manager that creates mock connections."""

    def __init__(self):
        self.connections_created = []
        self.shutdown_called = False

    @contextmanager
    def connection(self, host, user):
        conn = MockConnection(host, user)
        self.connections_created.append((host, user))
        try:
            yield conn
        finally:
            pass

    def shutdown(self):
        self.shutdown_called = True


class TestSSHManagerIntegration:
    """Integration tests for SSH manager with utils functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.slurm_profile = SlurmProfile(
            name="test",
            host="test-host",
            user="test-user",
            cache_dir="/test/cache_dir/.blackfish",
            home_dir="/test/home_dir/.blackfish",
        )

        self.local_profile = LocalProfile(
            name="local-test",
            home_dir="/test/home_dir/.blackfish",
            cache_dir="/test/cache_dir/.blackfish",
        )

    def test_get_models_with_ssh_manager(self):
        """Test get_models with explicit SSH manager."""
        mock_manager = MockSSHManager()

        with mock.patch("app.utils.yaspin") as mock_yaspin:
            mock_yaspin.return_value.__enter__.return_value = mock.MagicMock()

            models = get_models(self.slurm_profile, mock_manager)

            # Should have made SSH connection
            assert len(mock_manager.connections_created) == 1
            assert mock_manager.connections_created[0] == ("test-host", "test-user")

            # Should have found models
            expected_models = ["test/model-a", "test/model-b", "test/model-c"]
            assert set(models) == set(expected_models)

    def test_get_models_cli_fallback(self):
        """Test get_models without SSH manager (CLI case)."""
        with mock.patch("app.utils.SSHConnectionManager") as mock_manager_class:
            mock_manager = MockSSHManager()
            mock_manager_class.return_value = mock_manager

            with mock.patch("app.utils.yaspin") as mock_yaspin:
                mock_yaspin.return_value.__enter__.return_value = mock.MagicMock()

                # Call without ssh_manager parameter
                get_models(self.slurm_profile)

                # Should have created and shut down manager
                mock_manager_class.assert_called_once()
                assert mock_manager.shutdown_called is True

                # Should have made SSH connection
                assert len(mock_manager.connections_created) == 1

    def test_get_revisions_with_ssh_manager(self):
        """Test get_revisions with explicit SSH manager."""
        mock_manager = MockSSHManager()

        with mock.patch("app.utils.yaspin") as mock_yaspin:
            mock_yaspin.return_value.__enter__.return_value = mock.MagicMock()

            revisions = get_revisions("test/model-a", self.slurm_profile, mock_manager)

            # Should have made SSH connection
            assert len(mock_manager.connections_created) == 1
            assert mock_manager.connections_created[0] == ("test-host", "test-user")

            # Should have found revisions
            expected_revisions = ["test-commit-a", "test-commit-b"]
            assert set(revisions) == set(expected_revisions)

    def test_get_model_dir_with_ssh_manager(self):
        """Test get_model_dir with explicit SSH manager."""
        mock_manager = MockSSHManager()

        with mock.patch("app.utils.yaspin") as mock_yaspin:
            mock_yaspin.return_value.__enter__.return_value = mock.MagicMock()

            model_dir = get_model_dir(
                "test/model-a", "test-commit-a", self.slurm_profile, mock_manager
            )

            # Should have made SSH connection
            assert len(mock_manager.connections_created) == 1
            assert mock_manager.connections_created[0] == ("test-host", "test-user")

            # Should have found model directory
            expected_dir = "/test/cache_dir/.blackfish/models/models--test--model-a"
            assert model_dir == expected_dir

    def test_has_model_with_ssh_manager(self):
        """Test has_model with explicit SSH manager."""
        mock_manager = MockSSHManager()

        with mock.patch("app.utils.ModelCard") as mock_model_card:
            mock_model_card.load.return_value = mock.MagicMock()

            with mock.patch("app.utils.yaspin") as mock_yaspin:
                mock_yaspin.return_value.__enter__.return_value = mock.MagicMock()

                # Test existing model
                result = has_model("test/model-a", self.slurm_profile, mock_manager)
                assert result is True

                # Test non-existing model
                result = has_model("test/nonexistent", self.slurm_profile, mock_manager)
                assert result is False

    def test_multiple_calls_reuse_manager(self):
        """Test that multiple calls with same manager reuse connections."""
        mock_manager = MockSSHManager()

        with mock.patch("app.utils.yaspin") as mock_yaspin:
            mock_yaspin.return_value.__enter__.return_value = mock.MagicMock()

            # Make multiple calls with same manager
            get_models(self.slurm_profile, mock_manager)
            get_revisions("test/model-a", self.slurm_profile, mock_manager)
            get_model_dir(
                "test/model-a", "test-commit-a", self.slurm_profile, mock_manager
            )

            # All should use same SSH connection details
            assert len(mock_manager.connections_created) == 3
            for host, user in mock_manager.connections_created:
                assert host == "test-host"
                assert user == "test-user"

    def test_local_profile_no_ssh(self):
        """Test that local profiles don't use SSH manager."""
        mock_manager = MockSSHManager()

        with mock.patch("os.listdir") as mock_listdir:
            mock_listdir.side_effect = lambda path: {
                "/test/cache_dir/.blackfish/models": [
                    "models--test--model-a",
                    "models--test--model-b",
                ],
                "/test/home_dir/.blackfish/models": [
                    "models--test--model-c",
                ],
            }.get(path, [])

            with mock.patch("app.utils.yaspin") as mock_yaspin:
                mock_yaspin.return_value.__enter__.return_value = mock.MagicMock()

                models = get_models(self.local_profile, mock_manager)

                # Should not have used SSH manager
                assert len(mock_manager.connections_created) == 0

                # Should still find models locally
                expected_models = ["test/model-a", "test/model-b", "test/model-c"]
                assert set(models) == set(expected_models)


class TestRealSSHManagerIntegration:
    """Integration tests with real SSH manager (but mocked connections)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.slurm_profile = SlurmProfile(
            name="test",
            host="test-host",
            user="test-user",
            cache_dir="/test/cache_dir/.blackfish",
            home_dir="/test/home_dir/.blackfish",
        )

    def teardown_method(self):
        """Clean up SSH managers."""
        pass

    @mock.patch("app.ssh_manager.Connection")
    def test_real_ssh_manager_connection_reuse(self, mock_connection_class):
        """Test that real SSH manager reuses connections across utils calls."""
        mock_conn = MockConnection("test-host", "test-user")
        mock_connection_class.return_value = mock_conn

        ssh_manager = SSHConnectionManager()

        try:
            with mock.patch("app.utils.yaspin") as mock_yaspin:
                mock_yaspin.return_value.__enter__.return_value = mock.MagicMock()

                # Multiple calls should reuse the same connection
                get_models(self.slurm_profile, ssh_manager)
                get_revisions("test/model-a", self.slurm_profile, ssh_manager)

                # Should have created connection only once
                assert mock_connection_class.call_count == 1

                # Should have reused connection
                status = ssh_manager.get_status()
                assert len(status) == 1
                assert "test-user@test-host" in status

        finally:
            ssh_manager.shutdown()

    @mock.patch("app.ssh_manager.Connection")
    def test_cli_fallback_creates_temporary_manager(self, mock_connection_class):
        """Test CLI fallback creates and destroys temporary manager."""
        mock_conn = MockConnection("test-host", "test-user")
        mock_connection_class.return_value = mock_conn

        with mock.patch("app.utils.yaspin") as mock_yaspin:
            mock_yaspin.return_value.__enter__.return_value = mock.MagicMock()

            # Call without ssh_manager (CLI case)
            get_models(self.slurm_profile)

            # Should have created connection
            assert mock_connection_class.call_count == 1

            # Should have closed connection after use
            assert mock_conn.closed is True
