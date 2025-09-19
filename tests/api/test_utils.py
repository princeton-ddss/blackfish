import tempfile
import pytest
from litestar.testing import AsyncTestClient

pytestmark = pytest.mark.anyio


class TestInfoAPI:
    """Test cases for the /api/info endpoint."""

    async def test_info_requires_authentication(self, no_auth_client: AsyncTestClient):
        """Test that /api/info requires authentication."""
        response = await no_auth_client.get("/api/info")

        # Should require authentication
        assert response.status_code == 401 or response.is_redirect

    async def test_info_returns_server_info(self, client: AsyncTestClient):
        """Test /api/info returns server information."""
        response = await client.get("/api/info")

        assert response.status_code == 200
        result = response.json()

        # Should contain app fixture configuration information
        assert isinstance(result, dict)
        assert result.get("HOST") == "localhost"
        assert result.get("PORT") == 8000
        assert result.get("STATIC_DIR").endswith("src")
        assert result.get("HOME_DIR").endswith("tests")
        assert result.get("DEBUG") == 0
        assert result.get("CONTAINER_PROVIDER") == "docker"


class TestFilesAPI:
    """Test cases for the /api/files endpoint."""

    async def test_files_requires_authentication(self, no_auth_client: AsyncTestClient):
        """Test that /api/files requires authentication."""
        response = await no_auth_client.get("/api/files", params={"path": "/tmp"})

        # Should require authentication
        assert response.status_code == 401

    async def test_files_missing_path_parameter(self, client: AsyncTestClient):
        """Test /api/files without required path parameter."""
        response = await client.get("/api/files")

        # Should return validation error for missing required parameter
        assert response.status_code == 400

    async def test_files_valid_directory(self, client: AsyncTestClient):
        """Test /api/files with valid directory path."""
        # Use /tmp as a directory that should exist on most systems
        response = await client.get("/api/files", params={"path": "/tmp"})

        # Should return list of files or 404/403 depending on permissions
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        if result:  # If directory is not empty
            # Each item should be a file stat object
            file_stat = result[0]
            expected_keys = ["name", "path", "is_dir", "size"]
            for key in expected_keys:
                assert key in file_stat

    async def test_files_nonexistent_path(self, client: AsyncTestClient):
        """Test /api/files with nonexistent path."""
        response = await client.get("/api/files", params={"path": "/nonexistent/path"})

        # Should return not found error
        assert response.status_code == 404

    async def test_files_hidden_parameter(self, client: AsyncTestClient):
        """Test /api/files with hidden parameter."""
        response = await client.get(
            "/api/files", params={"path": "/tmp", "hidden": True}
        )

        # Should accept hidden parameter
        assert response.status_code == 200

    async def test_files_permission_denied(self, client: AsyncTestClient):
        """Test /api/files with path that might cause permission error."""

        # Try to access a restricted directory (behavior may vary by system)
        response = await client.get("/api/files", params={"path": "/root"})

        # Should handle permission errors gracefully
        assert response.status_code == 401


class TestAudioAPI:
    """Test cases for the /api/audio endpoint."""

    async def test_audio_requires_authentication(self, no_auth_client: AsyncTestClient):
        """Test that /api/audio requires authentication."""
        response = await no_auth_client.get("/api/audio", params={"path": "/test.wav"})

        # Should require authentication
        assert response.status_code == 401

    async def test_audio_missing_path_parameter(self, client: AsyncTestClient):
        """Test /api/audio without required path parameter."""
        response = await client.get("/api/audio")

        # Should return validation error for missing required parameter
        assert response.status_code == 400

    async def test_audio_nonexistent_file(self, client: AsyncTestClient):
        """Test /api/audio with nonexistent file."""
        response = await client.get(
            "/api/audio", params={"path": "/nonexistent/file.wav"}
        )

        # Should return not found error
        assert response.status_code == 404

    async def test_audio_invalid_file_extension(self, client: AsyncTestClient):
        """Test /api/audio with invalid file extension."""

        # Create a temporary file with wrong extension to test validation
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(b"dummy content")
            tmp_path = tmp_file.name

        try:
            response = await client.get("/api/audio", params={"path": tmp_path})
            # Should return validation error
            assert response.status_code == 400
        finally:
            # Clean up the temporary file
            import os

            os.unlink(tmp_path)

    async def test_audio_valid_extension(self, client: AsyncTestClient):
        """Test /api/audio with valid .wav extension."""

        # Create temporary .mp3 and .wav files
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3_file:
            mp3_file.write(b"mp3")
            mp3_path = mp3_file.name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
            wav_file.write(b"wav")
            wav_path = wav_file.name

        try:
            response = await client.get("/api/audio", params={"path": mp3_path})
            assert response.status_code == 200
            assert "audio" in response.headers.get("content-type", "").lower()
            response = await client.get("/api/audio", params={"path": wav_path})
            assert response.status_code == 200
            assert "audio" in response.headers.get("content-type", "").lower()
        finally:
            import os

            os.unlink(mp3_path)
            os.unlink(wav_path)


class TestPortsAPI:
    """Test cases for the /api/ports endpoint."""

    async def test_ports_requires_authentication(self, no_auth_client: AsyncTestClient):
        """Test that /api/ports requires authentication."""
        response = await no_auth_client.get("/api/ports")

        # Should require authentication
        assert response.status_code == 401

    async def test_ports_returns_available_port(self, client: AsyncTestClient):
        """Test /api/ports returns an available port number."""
        response = await client.get("/api/ports")

        assert response.status_code == 200
        result = response.json()

        # Should return a port number in default range
        assert isinstance(result, int)
        assert 8080 <= result <= 8900

    async def test_ports_multiple_calls_different_ports(self, client: AsyncTestClient):
        """Test that multiple calls to /api/ports can return different ports."""
        response1 = await client.get("/api/ports")
        response2 = await client.get("/api/ports")

        assert response1.status_code == 200
        assert response2.status_code == 200

        port1 = response1.json()
        port2 = response2.json()

        # Both should be valid port numbers
        assert isinstance(port1, int)
        assert isinstance(port2, int)
        assert 8080 <= port1 <= 8900
        assert 8080 <= port2 <= 8900
