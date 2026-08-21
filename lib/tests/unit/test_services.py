import pytest
from unittest.mock import patch, MagicMock
import psutil

from blackfish.server.services.base import Service, ServiceLaunchError


pytestmark = pytest.mark.anyio


class TestCloseTunnel:
    """Test cases for Service.close_tunnel method."""

    async def test_close_tunnel_handles_access_denied_on_name(self, session):
        """Test that AccessDenied on p.info['name'] doesn't crash close_tunnel."""
        service = Service(port=8080)

        # Simulate AccessDenied
        mock_proc_with_error = MagicMock()
        mock_proc_with_error.info.get.side_effect = psutil.AccessDenied(pid=1234)

        with patch("blackfish.server.services.base.psutil.process_iter") as mock_iter:
            mock_iter.return_value = [mock_proc_with_error]
            # Should not raise
            await service.close_tunnel(session)

        # Port should always be set to None
        assert service.port is None

    async def test_close_tunnel_handles_no_such_process(self, session):
        """Test that NoSuchProcess during iteration is handled."""
        service = Service(port=8080)

        mock_proc = MagicMock()
        mock_proc.info.get.side_effect = psutil.NoSuchProcess(pid=1234)

        with patch("blackfish.server.services.base.psutil.process_iter") as mock_iter:
            mock_iter.return_value = [mock_proc]
            await service.close_tunnel(session)

        assert service.port is None

    async def test_close_tunnel_handles_zombie_process(self, session):
        """Test that ZombieProcess during iteration is handled."""
        service = Service(port=8080)

        mock_proc = MagicMock()
        mock_proc.info.get.side_effect = psutil.ZombieProcess(pid=1234)

        with patch("blackfish.server.services.base.psutil.process_iter") as mock_iter:
            mock_iter.return_value = [mock_proc]
            await service.close_tunnel(session)

        assert service.port is None

    async def test_close_tunnel_handles_access_denied_on_connections(self, session):
        """Test that AccessDenied on p.net_connections() is handled."""
        service = Service(port=8080)

        mock_proc = MagicMock()
        mock_proc.info.get.return_value = "ssh"
        mock_proc.pid = 1234
        mock_proc.net_connections.side_effect = psutil.AccessDenied(pid=1234)

        with patch("blackfish.server.services.base.psutil.process_iter") as mock_iter:
            mock_iter.return_value = [mock_proc]
            await service.close_tunnel(session)

        assert service.port is None

    async def test_close_tunnel_kills_matching_ssh_process(self, session):
        """Test that close_tunnel kills the correct ssh process."""
        service = Service(port=8080)

        mock_conn = MagicMock()
        mock_conn.laddr.port = 8080

        mock_proc = MagicMock()
        mock_proc.info.get.return_value = "ssh"
        mock_proc.pid = 1234
        mock_proc.net_connections.return_value = [mock_conn]

        with patch("blackfish.server.services.base.psutil.process_iter") as mock_iter:
            mock_iter.return_value = [mock_proc]
            await service.close_tunnel(session)

        mock_proc.kill.assert_called_once()
        assert service.port is None

    async def test_close_tunnel_skips_non_ssh_processes(self, session):
        """Test that close_tunnel only considers ssh processes."""
        service = Service(port=8080)

        mock_proc = MagicMock()
        mock_proc.info.get.return_value = "python"  # Not ssh
        mock_proc.pid = 1234

        with patch("blackfish.server.services.base.psutil.process_iter") as mock_iter:
            mock_iter.return_value = [mock_proc]
            await service.close_tunnel(session)

        # Should not try to get connections for non-ssh processes
        mock_proc.net_connections.assert_not_called()
        assert service.port is None

    async def test_close_tunnel_skips_ssh_on_different_port(self, session):
        """Test that close_tunnel doesn't kill ssh on different port."""
        service = Service(port=8080)

        mock_conn = MagicMock()
        mock_conn.laddr.port = 9999  # Different port

        mock_proc = MagicMock()
        mock_proc.info.get.return_value = "ssh"
        mock_proc.pid = 1234
        mock_proc.net_connections.return_value = [mock_conn]

        with patch("blackfish.server.services.base.psutil.process_iter") as mock_iter:
            mock_iter.return_value = [mock_proc]
            await service.close_tunnel(session)

        mock_proc.kill.assert_not_called()
        assert service.port is None

    async def test_close_tunnel_noop_when_port_is_none(self, session):
        """Test that close_tunnel does nothing when port is None."""
        service = Service(port=None)

        with patch("blackfish.server.services.base.psutil.process_iter") as mock_iter:
            await service.close_tunnel(session)

        # Should not iterate processes when port is None
        mock_iter.assert_not_called()

    async def test_close_tunnel_handles_mixed_accessible_processes(self, session):
        """Test close_tunnel with mix of accessible and inaccessible processes."""
        service = Service(port=8080)

        # First process raises AccessDenied
        mock_proc_denied = MagicMock()
        mock_proc_denied.info.get.side_effect = psutil.AccessDenied(pid=1111)

        # Second process is the one we want to kill
        mock_conn = MagicMock()
        mock_conn.laddr.port = 8080
        mock_proc_target = MagicMock()
        mock_proc_target.info.get.return_value = "ssh"
        mock_proc_target.pid = 2222
        mock_proc_target.net_connections.return_value = [mock_conn]

        with patch("blackfish.server.services.base.psutil.process_iter") as mock_iter:
            mock_iter.return_value = [mock_proc_denied, mock_proc_target]
            await service.close_tunnel(session)

        # Should skip denied process and kill the target
        mock_proc_target.kill.assert_called_once()
        assert service.port is None


class TestServiceLaunchError:
    """Test cases for ServiceLaunchError exception class."""

    def test_ssh_error_message(self):
        """Test SSH error message includes host."""
        error = ServiceLaunchError("ssh", "cluster.example.com")
        assert "Could not connect to cluster.example.com" in error.user_message()
        assert str(error) == error.user_message()

    def test_copy_error_message(self):
        """Test copy error message includes host."""
        error = ServiceLaunchError("copy", "cluster.example.com")
        assert "Failed to copy files to cluster.example.com" in error.user_message()

    def test_submit_error_message(self):
        """Test submit error message includes host."""
        error = ServiceLaunchError("submit", "cluster.example.com")
        assert "Job submission failed on cluster.example.com" in error.user_message()

    def test_script_error_message(self):
        """Test script error message."""
        error = ServiceLaunchError("script", "localhost")
        assert "Failed to generate the launch script" in error.user_message()

    def test_profile_error_message(self):
        """Test profile error message."""
        error = ServiceLaunchError("profile", "localhost")
        assert "Profile configuration is missing or invalid" in error.user_message()

    def test_container_error_message(self):
        """Test container error message mentions Docker and nvidia-container-toolkit."""
        error = ServiceLaunchError("container", "localhost")
        message = error.user_message()
        assert "Docker" in message
        assert "nvidia-container-toolkit" in message

    def test_unknown_error_type_returns_fallback(self):
        """Test that unknown error types return fallback message."""
        error = ServiceLaunchError("unknown_type", "localhost")
        assert error.user_message() == "Failed to launch service."

    def test_details_parameter_stored(self):
        """Test that details parameter is stored on the exception."""
        error = ServiceLaunchError("ssh", "localhost", details="Connection refused")
        assert error.details == "Connection refused"

    def test_details_included_in_message(self):
        """Test that details are appended to user message when provided."""
        error = ServiceLaunchError(
            "ssh", "cluster.example.com", details="Connection refused"
        )
        message = error.user_message()
        assert "Could not connect to cluster.example.com" in message
        assert "(Connection refused)" in message

    def test_message_without_details(self):
        """Test that message works without details."""
        error = ServiceLaunchError("ssh", "cluster.example.com")
        message = error.user_message()
        assert "Could not connect to cluster.example.com" in message
        assert "(" not in message  # No parentheses when no details

    def test_error_attributes(self):
        """Test that error type and host are accessible as attributes."""
        error = ServiceLaunchError("submit", "hpc.princeton.edu")
        assert error.error_type == "submit"
        assert error.host == "hpc.princeton.edu"


class TestServiceImagePinning:
    """Tests for the persisted container image (``image_ref``) on services.

    A service records the image it launched with so that a restart reuses it
    rather than following a changed configuration default.
    """

    def _service(self, **kwargs):
        from uuid import UUID

        from blackfish.server.job import JobScheduler
        from blackfish.server.services.text_generation import TextGeneration

        defaults = {
            "id": UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
            "name": "test-service",
            "model": "meta-llama/Llama-3.1-8B-Instruct",
            "profile": "default",
            "host": "localhost",
            "user": "alice",
            "home_dir": "/home/alice/.blackfish",
            "cache_dir": "/scratch/cache",
            "scheduler": JobScheduler.Slurm,
            "grace_period": 180,
        }
        defaults.update(kwargs)
        return TextGeneration(**defaults)

    def _render(self, service):
        from blackfish.server.job import SlurmJobConfig
        from blackfish.server.services.text_generation import TextGenerationConfig

        return service.render_job_script(
            TextGenerationConfig(port=8080),
            SlurmJobConfig(name="test-service"),
        )

    def test_render_uses_configured_default_when_unpinned(self):
        """No pin -> the configured default SIF, i.e. today's behavior."""
        from blackfish.server.images import DEFAULT_IMAGES

        script = self._render(self._service(image_ref=None))

        assert DEFAULT_IMAGES["text_generation"].sif in script

    def test_render_uses_the_pin_when_set(self):
        """A pin overrides the configured default in the launch script."""
        from blackfish.server.images import DEFAULT_IMAGES

        script = self._render(self._service(image_ref="vllm/vllm-openai:v9.9.9"))

        assert "vllm-openai_v9.9.9.sif" in script
        assert DEFAULT_IMAGES["text_generation"].sif not in script

    def test_render_backfills_image_ref_when_unpinned(self):
        """An unpinned render records what it actually used, so a later
        restart reuses that image instead of a changed default."""
        from blackfish.server.images import DEFAULT_IMAGES

        service = self._service(image_ref=None)
        self._render(service)

        assert service.image_ref == DEFAULT_IMAGES["text_generation"].docker_ref

    def test_render_does_not_overwrite_an_existing_pin(self):
        """Backfill only fills a blank; a user-supplied pin survives."""
        service = self._service(image_ref="vllm/vllm-openai:v9.9.9")
        self._render(service)

        assert service.image_ref == "vllm/vllm-openai:v9.9.9"
