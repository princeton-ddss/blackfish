import tempfile
import pytest
import os
from litestar.testing import AsyncTestClient


pytestmark = pytest.mark.anyio


class TestUploadAudioAPI:
    """Test cases for the POST /api/audio endpoint."""

    async def test_upload_audio_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that /api/audio requires authentication."""

        audio_bytes = self._create_test_audio()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.wav")

            response = await no_auth_client.post(
                "/api/audio",
                files={"file": audio_bytes},
                data={"path": file_path},
            )

            # Should return NotAuthorized error
            assert response.status_code == 401

    async def test_upload_audio_valid_with_path(self, client: AsyncTestClient):
        """Test creating a valid audio file with explicit path."""
        audio_bytes = self._create_test_audio()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.wav")

            response = await client.post(
                "/api/audio",
                files={"file": audio_bytes},
                data={"path": file_path},
            )

            # Should return success
            assert response.status_code == 201

            # Should include filename, size, and created_at
            result = response.json()
            assert result["filename"] == "test.wav"
            assert result["size"] == len(audio_bytes)
            assert "created_at" in result

    async def test_upload_audio_creates_parent_directories(
        self, client: AsyncTestClient
    ):
        """Test that parent directories are created."""
        audio_bytes = self._create_test_audio()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nested", "dirs", "test.wav")

            response = await client.post(
                "/api/audio",
                files={"file": audio_bytes},
                data={"path": file_path},
            )

            # Should return success
            assert response.status_code == 201

            # Should create new directories
            assert os.path.exists(os.path.join(temp_dir, "nested", "dirs"))

    async def test_upload_audio_invalid_extension(self, client: AsyncTestClient):
        """Test that invalid file extensions are rejected."""
        audio_bytes = self._create_test_audio()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.exe")

            response = await client.post(
                "/api/audio",
                files={"file": audio_bytes},
                data={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "Validation failed for POST /api/audio" in result["detail"]

    async def test_upload_audio_valid_extensions(self, client: AsyncTestClient):
        """Test that all valid audio extensions are accepted."""

        valid_extensions = [".wav", ".mp3"]
        audio_bytes = self._create_test_audio()

        with tempfile.TemporaryDirectory() as temp_dir:
            for ext in valid_extensions:
                file_path = os.path.join(temp_dir, f"test{ext}")
                response = await client.post(
                    "/api/audio",
                    files={"file": audio_bytes},
                    data={"path": file_path},
                )

                # Should return success
                assert response.status_code == 201

    async def test_upload_audio_permission_denied(self, client: AsyncTestClient):
        """Test handling of permission denied errors."""

        audio_bytes = self._create_test_audio()

        with tempfile.TemporaryDirectory() as temp_dir:
            restricted_dir = os.path.join(temp_dir, "readonly")
            os.makedirs(restricted_dir)
            os.chmod(restricted_dir, 0o444)

            file_path = os.path.join(restricted_dir, "test.wav")

            try:
                response = await client.post(
                    "/api/audio",
                    files={"file": audio_bytes},
                    data={"path": file_path},
                )

                # Should return permission denied or OS error
                assert response.status_code in [401, 500]
                result = response.json()
                if response.status_code == 401:
                    assert "User does not have permission" in result["detail"]

            finally:
                # Restore permissions for cleanup
                os.chmod(restricted_dir, 0o755)

    async def test_upload_audio_existing_path(self, client: AsyncTestClient):
        """Test that uploading to an existing path returns 400 error."""
        audio_bytes = self._create_test_audio()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.wav")

            # First upload should succeed
            response = await client.post(
                "/api/audio",
                files={"file": audio_bytes},
                data={"path": file_path},
            )
            assert response.status_code == 201

            # Second upload to the same path should fail
            response = await client.post(
                "/api/audio",
                files={"file": audio_bytes},
                data={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "already exists" in result["detail"]

    def _create_test_audio(self) -> bytes:
        """Create a minimal valid audio content for testing (simple WAV header)."""
        # Create a minimal WAV file header
        # This is a very basic 44-byte WAV header for 1 second of silence
        wav_header = b"RIFF"
        wav_header += (36).to_bytes(4, "little")  # File size - 8
        wav_header += b"WAVE"
        wav_header += b"fmt "
        wav_header += (16).to_bytes(4, "little")  # Subchunk1 size
        wav_header += (1).to_bytes(2, "little")  # Audio format (1 = PCM)
        wav_header += (1).to_bytes(2, "little")  # Number of channels
        wav_header += (44100).to_bytes(4, "little")  # Sample rate
        wav_header += (88200).to_bytes(4, "little")  # Byte rate
        wav_header += (2).to_bytes(2, "little")  # Block align
        wav_header += (16).to_bytes(2, "little")  # Bits per sample
        wav_header += b"data"
        wav_header += (0).to_bytes(4, "little")  # Data size
        return wav_header


class TestGetAudioAPI:
    """Test cases for the GET /api/audio endpoint."""

    async def test_get_audio_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that GET /api/audio requires authentication."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.wav")
            self._create_and_save_audio(file_path)

            response = await no_auth_client.get(
                "/api/audio",
                params={"path": file_path},
            )

            # Should return NotAuthorized error
            assert response.status_code == 401

    async def test_get_audio_success(self, client: AsyncTestClient):
        """Test retrieving an existing audio file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.wav")
            original_data = self._create_and_save_audio(file_path)

            response = await client.get(
                "/api/audio",
                params={"path": file_path},
            )

            # Should return success with audio data
            assert response.status_code == 200
            assert response.content == original_data

    async def test_get_audio_not_found(self, client: AsyncTestClient):
        """Test retrieving a non-existent audio file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nonexistent.wav")

            response = await client.get(
                "/api/audio",
                params={"path": file_path},
            )

            # Should return not found error
            assert response.status_code == 404

    async def test_get_audio_is_directory(self, client: AsyncTestClient):
        """Test that attempting to get a directory returns an error."""

        with tempfile.TemporaryDirectory() as temp_dir:
            response = await client.get(
                "/api/audio",
                params={"path": temp_dir},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "not a file" in result["detail"]

    async def test_get_audio_invalid_extension(self, client: AsyncTestClient):
        """Test that files with invalid extensions are rejected."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            with open(file_path, "w") as f:
                f.write("Not an audio file")

            response = await client.get(
                "/api/audio",
                params={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "Invalid file extension" in result["detail"]

    def _create_and_save_audio(self, path: str) -> bytes:
        """Create and save an audio file for testing."""
        # Create a minimal WAV file
        wav_header = b"RIFF"
        wav_header += (36).to_bytes(4, "little")
        wav_header += b"WAVE"
        wav_header += b"fmt "
        wav_header += (16).to_bytes(4, "little")
        wav_header += (1).to_bytes(2, "little")
        wav_header += (1).to_bytes(2, "little")
        wav_header += (44100).to_bytes(4, "little")
        wav_header += (88200).to_bytes(4, "little")
        wav_header += (2).to_bytes(2, "little")
        wav_header += (16).to_bytes(2, "little")
        wav_header += b"data"
        wav_header += (0).to_bytes(4, "little")

        with open(path, "wb") as f:
            f.write(wav_header)
        return wav_header


class TestUpdateAudioAPI:
    """Test cases for the PUT /api/audio endpoint."""

    async def test_update_audio_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that PUT /api/audio requires authentication."""

        audio_bytes = self._create_test_audio()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.wav")
            self._create_and_save_audio(file_path)

            response = await no_auth_client.put(
                "/api/audio",
                files={"file": audio_bytes},
                data={"path": file_path},
            )

            # Should return NotAuthorized error
            assert response.status_code == 401

    async def test_update_audio_success(self, client: AsyncTestClient):
        """Test successfully updating an existing audio file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.wav")
            # Create initial file
            self._create_and_save_audio(file_path)

            # Update with new audio
            new_audio_bytes = self._create_test_audio(sample_rate=48000)
            response = await client.put(
                "/api/audio",
                files={"file": new_audio_bytes},
                data={"path": file_path},
            )

            # Should return success
            assert response.status_code == 200
            result = response.json()
            assert result["filename"] == "test.wav"
            assert result["size"] == len(new_audio_bytes)
            assert "created_at" in result

            # Verify file was actually updated
            with open(file_path, "rb") as f:
                assert f.read() == new_audio_bytes

    async def test_update_audio_not_found(self, client: AsyncTestClient):
        """Test updating a non-existent audio file."""

        audio_bytes = self._create_test_audio()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nonexistent.wav")

            response = await client.put(
                "/api/audio",
                files={"file": audio_bytes},
                data={"path": file_path},
            )

            # Should return not found error
            assert response.status_code == 404

    async def test_update_audio_is_directory(self, client: AsyncTestClient):
        """Test that attempting to update a directory returns an error."""

        audio_bytes = self._create_test_audio()

        with tempfile.TemporaryDirectory() as temp_dir:
            response = await client.put(
                "/api/audio",
                files={"file": audio_bytes},
                data={"path": temp_dir},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            # Check for either our specific message or the general validation failure message
            assert (
                "not a file" in result["detail"]
                or "Validation failed" in result["detail"]
            )

    async def test_update_audio_permission_denied(self, client: AsyncTestClient):
        """Test handling of permission denied errors."""

        audio_bytes = self._create_test_audio()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.wav")
            self._create_and_save_audio(file_path)
            os.chmod(file_path, 0o444)

            try:
                response = await client.put(
                    "/api/audio",
                    files={"file": audio_bytes},
                    data={"path": file_path},
                )

                # Should return permission denied or OS error
                assert response.status_code in [401, 500]

            finally:
                # Restore permissions for cleanup
                os.chmod(file_path, 0o644)

    def _create_test_audio(self, sample_rate: int = 44100) -> bytes:
        """Create a minimal valid audio content for testing."""
        wav_header = b"RIFF"
        wav_header += (36).to_bytes(4, "little")
        wav_header += b"WAVE"
        wav_header += b"fmt "
        wav_header += (16).to_bytes(4, "little")
        wav_header += (1).to_bytes(2, "little")
        wav_header += (1).to_bytes(2, "little")
        wav_header += sample_rate.to_bytes(4, "little")
        wav_header += (sample_rate * 2).to_bytes(4, "little")
        wav_header += (2).to_bytes(2, "little")
        wav_header += (16).to_bytes(2, "little")
        wav_header += b"data"
        wav_header += (0).to_bytes(4, "little")
        return wav_header

    def _create_and_save_audio(self, path: str) -> bytes:
        """Create and save an audio file for testing."""
        data = self._create_test_audio()
        with open(path, "wb") as f:
            f.write(data)
        return data


class TestDeleteAudioAPI:
    """Test cases for the DELETE /api/audio endpoint."""

    async def test_delete_audio_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that DELETE /api/audio requires authentication."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.wav")
            self._create_and_save_audio(file_path)

            response = await no_auth_client.delete(
                "/api/audio",
                params={"path": file_path},
            )

            # Should return NotAuthorized error
            assert response.status_code == 401

    async def test_delete_audio_success(self, client: AsyncTestClient):
        """Test successfully deleting an existing audio file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.wav")
            self._create_and_save_audio(file_path)

            # Verify file exists
            assert os.path.exists(file_path)

            response = await client.delete(
                "/api/audio",
                params={"path": file_path},
            )

            # Should return success
            assert response.status_code == 200
            result = response.json()
            assert result == file_path

            # Verify file was actually deleted
            assert not os.path.exists(file_path)

    async def test_delete_audio_not_found(self, client: AsyncTestClient):
        """Test deleting a non-existent audio file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nonexistent.wav")

            response = await client.delete(
                "/api/audio",
                params={"path": file_path},
            )

            # Should return not found error
            assert response.status_code == 404

    async def test_delete_audio_is_directory(self, client: AsyncTestClient):
        """Test that attempting to delete a directory returns an error."""

        with tempfile.TemporaryDirectory() as temp_dir:
            response = await client.delete(
                "/api/audio",
                params={"path": temp_dir},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "not a file" in result["detail"]

    async def test_delete_audio_invalid_extension(self, client: AsyncTestClient):
        """Test that files with invalid extensions cannot be deleted."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            with open(file_path, "w") as f:
                f.write("Not an audio file")

            response = await client.delete(
                "/api/audio",
                params={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "Invalid file extension" in result["detail"]

    async def test_delete_audio_permission_denied(self, client: AsyncTestClient):
        """Test handling of permission denied errors."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.wav")
            self._create_and_save_audio(file_path)

            # Make parent directory read-only
            os.chmod(temp_dir, 0o555)

            try:
                response = await client.delete(
                    "/api/audio",
                    params={"path": file_path},
                )

                # Should return permission denied or OS error
                assert response.status_code in [401, 500]

            finally:
                # Restore permissions for cleanup
                os.chmod(temp_dir, 0o755)

    def _create_and_save_audio(self, path: str) -> bytes:
        """Create and save an audio file for testing."""
        wav_header = b"RIFF"
        wav_header += (36).to_bytes(4, "little")
        wav_header += b"WAVE"
        wav_header += b"fmt "
        wav_header += (16).to_bytes(4, "little")
        wav_header += (1).to_bytes(2, "little")
        wav_header += (1).to_bytes(2, "little")
        wav_header += (44100).to_bytes(4, "little")
        wav_header += (88200).to_bytes(4, "little")
        wav_header += (2).to_bytes(2, "little")
        wav_header += (16).to_bytes(2, "little")
        wav_header += b"data"
        wav_header += (0).to_bytes(4, "little")

        with open(path, "wb") as f:
            f.write(wav_header)
        return wav_header
