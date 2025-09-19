import time
from unittest import mock

from app.ssh_manager import SSHConnectionManager, ConnectionInfo, ManagedConnection


class MockConnection:
    """Mock fabric Connection for testing."""

    def __init__(self, host: str, user: str, should_fail: bool = False):
        self.host = host
        self.user = user
        self.should_fail = should_fail
        self.closed = False
        self.run_calls = []

    def run(self, command, hide=True, warn=True):
        """Mock run method."""
        self.run_calls.append(command)
        if self.should_fail:
            raise Exception("Mock connection failure")

        # Mock result object
        class MockResult:
            ok = True

        return MockResult()

    def close(self):
        """Mock close method."""
        self.closed = True


class TestConnectionInfo:
    """Test ConnectionInfo dataclass."""

    def test_connection_info_key(self):
        """Test that connection info generates correct key."""
        info = ConnectionInfo(host="test-host", user="test-user")
        assert info.key() == "test-user@test-host"

    def test_connection_info_equality(self):
        """Test connection info equality."""
        info1 = ConnectionInfo(host="host1", user="user1")
        info2 = ConnectionInfo(host="host1", user="user1")
        info3 = ConnectionInfo(host="host2", user="user1")

        assert info1.key() == info2.key()
        assert info1.key() != info3.key()


class TestManagedConnection:
    """Test ManagedConnection functionality."""

    def test_managed_connection_creation(self):
        """Test creating a managed connection."""
        mock_conn = MockConnection("test-host", "test-user")
        info = ConnectionInfo(host="test-host", user="test-user")

        managed = ManagedConnection(
            connection=mock_conn, info=info, last_used=time.time()
        )

        assert managed.connection == mock_conn
        assert managed.info == info
        assert managed.is_connected is True

    def test_is_alive_success(self):
        """Test connection health check when connection is alive."""
        mock_conn = MockConnection("test-host", "test-user")
        info = ConnectionInfo(host="test-host", user="test-user")

        managed = ManagedConnection(
            connection=mock_conn, info=info, last_used=time.time()
        )

        assert managed.is_alive() is True
        assert managed.is_connected is True
        assert "true" in mock_conn.run_calls

    def test_is_alive_failure(self):
        """Test connection health check when connection is dead."""
        mock_conn = MockConnection("test-host", "test-user", should_fail=True)
        info = ConnectionInfo(host="test-host", user="test-user")

        managed = ManagedConnection(
            connection=mock_conn, info=info, last_used=time.time()
        )

        assert managed.is_alive() is False
        assert managed.is_connected is False

    def test_touch_updates_timestamp(self):
        """Test that touch updates the last_used timestamp."""
        mock_conn = MockConnection("test-host", "test-user")
        info = ConnectionInfo(host="test-host", user="test-user")

        initial_time = time.time()
        managed = ManagedConnection(
            connection=mock_conn, info=info, last_used=initial_time
        )

        time.sleep(0.01)  # Small delay
        managed.touch()

        assert managed.last_used > initial_time


class TestSSHConnectionManager:
    """Test SSH Connection Manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = SSHConnectionManager(max_idle_time=1, cleanup_interval=0.1)

    def teardown_method(self):
        """Clean up after tests."""
        if hasattr(self, "manager"):
            self.manager.shutdown()

    def test_manager_initialization(self):
        """Test SSH manager initializes correctly."""
        assert self.manager._max_idle_time == 1
        assert self.manager._cleanup_interval == 0.1
        assert len(self.manager._connections) == 0
        assert self.manager._shutdown is False

    def test_get_status_empty(self):
        """Test get_status when no connections exist."""
        status = self.manager.get_status()
        assert isinstance(status, dict)
        assert len(status) == 0

    @mock.patch("app.ssh_manager.Connection")
    def test_get_connection_new(self, mock_connection_class):
        """Test getting a new connection."""
        mock_conn = MockConnection("test-host", "test-user")
        mock_connection_class.return_value = mock_conn

        connection = self.manager.get_connection("test-host", "test-user")

        assert connection == mock_conn
        assert len(self.manager._connections) == 1
        assert "test-user@test-host" in self.manager._connections

        # Verify connection was tested
        assert "true" in mock_conn.run_calls

    @mock.patch("app.ssh_manager.Connection")
    def test_get_connection_reuse(self, mock_connection_class):
        """Test reusing an existing connection."""
        mock_conn = MockConnection("test-host", "test-user")
        mock_connection_class.return_value = mock_conn

        # First call creates connection
        connection1 = self.manager.get_connection("test-host", "test-user")
        initial_calls = len(mock_conn.run_calls)

        # Second call should reuse
        connection2 = self.manager.get_connection("test-host", "test-user")

        assert connection1 == connection2
        assert len(self.manager._connections) == 1
        # Should have made one additional call to check if alive
        assert len(mock_conn.run_calls) == initial_calls + 1

    @mock.patch("app.ssh_manager.Connection")
    def test_connection_context_manager(self, mock_connection_class):
        """Test using connection through context manager."""
        mock_conn = MockConnection("test-host", "test-user")
        mock_connection_class.return_value = mock_conn

        with self.manager.connection("test-host", "test-user") as conn:
            assert conn == mock_conn

        # Connection should still be in pool after context exit
        assert len(self.manager._connections) == 1

    @mock.patch("app.ssh_manager.Connection")
    def test_close_connection(self, mock_connection_class):
        """Test explicitly closing a connection."""
        mock_conn = MockConnection("test-host", "test-user")
        mock_connection_class.return_value = mock_conn

        # Create connection
        self.manager.get_connection("test-host", "test-user")
        assert len(self.manager._connections) == 1

        # Close it
        self.manager.close_connection("test-host", "test-user")
        assert len(self.manager._connections) == 0
        assert mock_conn.closed is True

    @mock.patch("app.ssh_manager.Connection")
    def test_close_all_connections(self, mock_connection_class):
        """Test closing all connections."""
        mock_conn1 = MockConnection("host1", "user1")
        mock_conn2 = MockConnection("host2", "user2")

        mock_connection_class.side_effect = [mock_conn1, mock_conn2]

        # Create multiple connections
        self.manager.get_connection("host1", "user1")
        self.manager.get_connection("host2", "user2")
        assert len(self.manager._connections) == 2

        # Close all
        self.manager.close_all()
        assert len(self.manager._connections) == 0
        assert mock_conn1.closed is True
        assert mock_conn2.closed is True

    @mock.patch("app.ssh_manager.Connection")
    def test_cleanup_idle_connections(self, mock_connection_class):
        """Test that idle connections are cleaned up."""
        mock_conn = MockConnection("test-host", "test-user")
        mock_connection_class.return_value = mock_conn

        # Create connection
        self.manager.get_connection("test-host", "test-user")
        assert len(self.manager._connections) == 1

        # Manually set last_used to be old
        key = "test-user@test-host"
        self.manager._connections[key].last_used = time.time() - 10  # 10 seconds ago

        # Trigger cleanup
        self.manager._cleanup_idle_connections()

        # Connection should be removed
        assert len(self.manager._connections) == 0
        assert mock_conn.closed is True

    @mock.patch("app.ssh_manager.Connection")
    def test_cleanup_dead_connections(self, mock_connection_class):
        """Test that dead connections are cleaned up."""
        # Create a connection that initially works but then fails
        mock_conn = MockConnection("test-host", "test-user", should_fail=False)
        mock_connection_class.return_value = mock_conn

        # Create connection (should succeed)
        self.manager.get_connection("test-host", "test-user")
        assert len(self.manager._connections) == 1

        # Now make the connection fail health checks
        mock_conn.should_fail = True
        managed_conn = list(self.manager._connections.values())[0]
        managed_conn.is_connected = False

        # Trigger cleanup
        self.manager._cleanup_idle_connections()

        # Connection should be removed
        assert len(self.manager._connections) == 0
        assert mock_conn.closed is True

    @mock.patch("app.ssh_manager.Connection")
    def test_get_status_with_connections(self, mock_connection_class):
        """Test get_status with active connections."""
        mock_conn = MockConnection("test-host", "test-user")
        mock_connection_class.return_value = mock_conn

        # Create connection
        self.manager.get_connection("test-host", "test-user")

        status = self.manager.get_status()

        assert len(status) == 1
        assert "test-user@test-host" in status

        conn_status = status["test-user@test-host"]
        assert conn_status["host"] == "test-host"
        assert conn_status["user"] == "test-user"
        assert "last_used" in conn_status
        assert "is_connected" in conn_status
        assert "idle_time" in conn_status

    def test_shutdown(self):
        """Test manager shutdown."""
        # Shutdown should work without errors
        self.manager.shutdown()

        assert self.manager._shutdown is True
        assert len(self.manager._connections) == 0

    @mock.patch("app.ssh_manager.Connection")
    def test_connection_recovery(self, mock_connection_class):
        """Test that dead connections are replaced with new ones."""
        # First connection that works initially
        initial_conn = MockConnection("test-host", "test-user", should_fail=False)
        # Second connection that will work
        live_conn = MockConnection("test-host", "test-user", should_fail=False)

        mock_connection_class.side_effect = [initial_conn, live_conn]

        # Create initial connection
        connection1 = self.manager.get_connection("test-host", "test-user")
        assert connection1 == initial_conn
        assert len(self.manager._connections) == 1

        # Make the first connection fail
        initial_conn.should_fail = True

        # Get connection again - should detect failure and create new one
        connection2 = self.manager.get_connection("test-host", "test-user")
        assert connection2 == live_conn
        assert connection2 != connection1

        # Old connection should be closed
        assert initial_conn.closed is True
