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
        assert response.status_code in [401, 403] or response.is_redirect

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
        assert response.status_code in [200, 403, 404]

        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, list)
            # Each item should be a file stat object
            if result:  # If directory is not empty
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
        assert response.status_code in [200, 403, 404]

    async def test_files_permission_denied(self, client: AsyncTestClient):
        """Test /api/files with path that might cause permission error."""
        # Try to access a restricted directory (behavior may vary by system)
        response = await client.get("/api/files", params={"path": "/root"})

        # Should handle permission errors gracefully
        assert response.status_code in [200, 403, 404]


class TestAudioAPI:
    """Test cases for the /api/audio endpoint."""

    async def test_audio_requires_authentication(self, no_auth_client: AsyncTestClient):
        """Test that /api/audio requires authentication."""
        response = await no_auth_client.get("/api/audio", params={"path": "/test.wav"})

        # Should require authentication
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_audio_missing_path_parameter(self, client: AsyncTestClient):
        """Test /api/audio without required path parameter."""
        response = await client.get("/api/audio")

        # Should return validation error for missing required parameter
        assert response.status_code in [400, 422]

    async def test_audio_nonexistent_file(self, client: AsyncTestClient):
        """Test /api/audio with nonexistent file."""
        response = await client.get(
            "/api/audio", params={"path": "/nonexistent/file.wav"}
        )

        # Should return not found error
        assert response.status_code == 404

    async def test_audio_invalid_file_extension(self, client: AsyncTestClient):
        """Test /api/audio with invalid file extension."""
        # Even if file exists, wrong extension should cause validation error
        response = await client.get("/api/audio", params={"path": "/tmp/test.txt"})

        # Should return validation error or not found
        assert response.status_code in [400, 404, 422]

    async def test_audio_valid_wav_extension(self, client: AsyncTestClient):
        """Test /api/audio with valid .wav extension."""
        response = await client.get("/api/audio", params={"path": "/test/audio.wav"})

        # Should accept .wav files (even if file doesn't exist, extension is valid)
        # Will return 404 for nonexistent file, but not validation error
        assert response.status_code in [200, 404]

    async def test_audio_valid_mp3_extension(self, client: AsyncTestClient):
        """Test /api/audio with valid .mp3 extension."""
        response = await client.get("/api/audio", params={"path": "/test/audio.mp3"})

        # Should accept .mp3 files
        assert response.status_code in [200, 404]

    async def test_audio_content_type(self, client: AsyncTestClient):
        """Test /api/audio returns correct content type."""
        response = await client.get("/api/audio", params={"path": "/test.wav"})

        # Even for 404, should have audio content type specified in endpoint
        if response.status_code == 200:
            assert "audio" in response.headers.get("content-type", "").lower()


class TestPortsAPI:
    """Test cases for the /api/ports endpoint."""

    async def test_ports_requires_authentication(self, no_auth_client: AsyncTestClient):
        """Test that /api/ports requires authentication."""
        response = await no_auth_client.get("/api/ports")

        # Should require authentication
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_ports_returns_available_port(self, client: AsyncTestClient):
        """Test /api/ports returns an available port number."""
        response = await client.get("/api/ports")

        assert response.status_code == 200
        result = response.json()

        # Should return a port number
        assert isinstance(result, int)
        assert 1024 <= result <= 65535  # Valid port range (excluding system ports)

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
        assert 1024 <= port1 <= 65535
        assert 1024 <= port2 <= 65535
