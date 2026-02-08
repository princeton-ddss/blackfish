import pytest
from unittest.mock import patch, MagicMock
import psutil

from blackfish.server.services.base import Service


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
