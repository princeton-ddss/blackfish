"""Tests for remote file operations via REST API with profile parameter."""

import pytest
from unittest import mock
from io import BytesIO
from PIL import Image
from litestar.testing import AsyncTestClient

from blackfish.server.models.profile import SlurmProfile
from blackfish.server.sftp import WriteFileResponse
from datetime import datetime


pytestmark = pytest.mark.anyio


def create_test_png() -> bytes:
    """Create a minimal valid PNG image for testing."""
    img = Image.new("RGB", (10, 10), color="red")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_remote_profile() -> SlurmProfile:
    """Create a test remote profile."""
    return SlurmProfile(
        name="remote-cluster",
        host="remote.example.com",
        user="testuser",
        home_dir="/home/testuser",
        cache_dir="/home/testuser/.cache",
    )


class TestRemoteImageUpload:
    """Test POST /api/image with profile parameter."""

    async def test_upload_image_to_remote_profile(self, client: AsyncTestClient):
        """Test uploading an image to a remote profile via SFTP."""
        png_bytes = create_test_png()
        remote_profile = create_remote_profile()

        mock_response = WriteFileResponse(
            filename="test.png",
            size=len(png_bytes),
            created_at=datetime.now(),
            path="/home/testuser/images/test.png",
        )

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ) as mock_get_profile,
            mock.patch(
                "blackfish.server.asgi.sftp.write_file",
                return_value=mock_response,
            ) as mock_write,
        ):
            response = await client.post(
                "/api/image",
                files={"file": png_bytes},
                data={"path": "images/test.png"},
                params={"profile": "remote-cluster"},
            )

            assert response.status_code == 201
            result = response.json()
            assert result["filename"] == "test.png"
            assert result["size"] == len(png_bytes)

            mock_get_profile.assert_called_once_with("remote-cluster")
            mock_write.assert_called_once_with(
                remote_profile, "images/test.png", png_bytes, update=False
            )

    async def test_upload_image_validates_before_remote(self, client: AsyncTestClient):
        """Test that image validation happens before remote upload attempt."""
        invalid_data = b"This is not an image"

        with mock.patch(
            "blackfish.server.asgi._get_validated_slurm_profile"
        ) as mock_get_profile:
            response = await client.post(
                "/api/image",
                files={"file": invalid_data},
                data={"path": "images/test.png"},
                params={"profile": "remote-cluster"},
            )

            # Should fail validation before trying remote
            assert response.status_code == 400
            assert "Pillow detected invalid image data" in response.json()["detail"]
            # Should not even try to get the remote profile for invalid images
            mock_get_profile.assert_not_called()


class TestRemoteImageDownload:
    """Test GET /api/image with profile parameter."""

    async def test_get_image_from_remote_profile(self, client: AsyncTestClient):
        """Test downloading an image from a remote profile via SFTP."""
        png_bytes = create_test_png()
        remote_profile = create_remote_profile()

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ) as mock_get_profile,
            mock.patch(
                "blackfish.server.asgi.sftp.read_file",
                return_value=png_bytes,
            ) as mock_read,
        ):
            response = await client.get(
                "/api/image",
                params={"path": "images/test.png", "profile": "remote-cluster"},
            )

            assert response.status_code == 200
            assert response.content == png_bytes
            assert response.headers["content-type"] == "image/png"

            mock_get_profile.assert_called_once_with("remote-cluster")
            mock_read.assert_called_once_with(remote_profile, "images/test.png")


class TestRemoteImageUpdate:
    """Test PUT /api/image with profile parameter."""

    async def test_update_image_on_remote_profile(self, client: AsyncTestClient):
        """Test updating an image on a remote profile via SFTP."""
        png_bytes = create_test_png()
        remote_profile = create_remote_profile()

        mock_response = WriteFileResponse(
            filename="test.png",
            size=len(png_bytes),
            created_at=datetime.now(),
            path="/home/testuser/images/test.png",
        )

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ) as mock_get_profile,
            mock.patch(
                "blackfish.server.asgi.sftp.write_file",
                return_value=mock_response,
            ) as mock_write,
        ):
            response = await client.put(
                "/api/image",
                files={"file": png_bytes},
                data={"path": "images/test.png"},
                params={"profile": "remote-cluster"},
            )

            assert response.status_code == 200
            result = response.json()
            assert result["filename"] == "test.png"

            mock_get_profile.assert_called_once_with("remote-cluster")
            mock_write.assert_called_once_with(
                remote_profile, "images/test.png", png_bytes, update=True
            )


class TestRemoteImageDelete:
    """Test DELETE /api/image with profile parameter."""

    async def test_delete_image_on_remote_profile(self, client: AsyncTestClient):
        """Test deleting an image on a remote profile via SFTP."""
        remote_profile = create_remote_profile()

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ) as mock_get_profile,
            mock.patch(
                "blackfish.server.asgi.sftp.delete_file",
                return_value="/home/testuser/images/test.png",
            ) as mock_delete,
        ):
            response = await client.delete(
                "/api/image",
                params={"path": "images/test.png", "profile": "remote-cluster"},
            )

            assert response.status_code == 200

            mock_get_profile.assert_called_once_with("remote-cluster")
            mock_delete.assert_called_once_with(remote_profile, "images/test.png")


class TestRemoteTextUpload:
    """Test POST /api/text with profile parameter."""

    async def test_upload_text_to_remote_profile(self, client: AsyncTestClient):
        """Test uploading a text file to a remote profile via SFTP."""
        text_content = b"Hello, world!"
        remote_profile = create_remote_profile()

        mock_response = WriteFileResponse(
            filename="test.txt",
            size=len(text_content),
            created_at=datetime.now(),
            path="/home/testuser/docs/test.txt",
        )

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ) as mock_get_profile,
            mock.patch(
                "blackfish.server.asgi.sftp.write_file",
                return_value=mock_response,
            ) as mock_write,
        ):
            response = await client.post(
                "/api/text",
                files={"file": text_content},
                data={"path": "docs/test.txt"},
                params={"profile": "remote-cluster"},
            )

            assert response.status_code == 201
            result = response.json()
            assert result["filename"] == "test.txt"

            mock_get_profile.assert_called_once_with("remote-cluster")
            mock_write.assert_called_once_with(
                remote_profile, "docs/test.txt", text_content, update=False
            )


class TestRemoteTextDownload:
    """Test GET /api/text with profile parameter."""

    async def test_get_text_from_remote_profile(self, client: AsyncTestClient):
        """Test downloading a text file from a remote profile via SFTP."""
        text_content = b"Hello, world!"
        remote_profile = create_remote_profile()

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ) as mock_get_profile,
            mock.patch(
                "blackfish.server.asgi.sftp.read_file",
                return_value=text_content,
            ) as mock_read,
        ):
            response = await client.get(
                "/api/text",
                params={"path": "docs/test.txt", "profile": "remote-cluster"},
            )

            assert response.status_code == 200
            assert response.content == text_content
            assert response.headers["content-type"] == "text/plain; charset=utf-8"

            mock_get_profile.assert_called_once_with("remote-cluster")
            mock_read.assert_called_once_with(remote_profile, "docs/test.txt")

    async def test_get_json_from_remote_profile(self, client: AsyncTestClient):
        """Test downloading a JSON file returns correct content type."""
        json_content = b'{"key": "value"}'
        remote_profile = create_remote_profile()

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.asgi.sftp.read_file",
                return_value=json_content,
            ),
        ):
            response = await client.get(
                "/api/text",
                params={"path": "data/config.json", "profile": "remote-cluster"},
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"


class TestRemoteTextUpdate:
    """Test PUT /api/text with profile parameter."""

    async def test_update_text_on_remote_profile(self, client: AsyncTestClient):
        """Test updating a text file on a remote profile via SFTP."""
        text_content = b"Updated content"
        remote_profile = create_remote_profile()

        mock_response = WriteFileResponse(
            filename="test.txt",
            size=len(text_content),
            created_at=datetime.now(),
            path="/home/testuser/docs/test.txt",
        )

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ) as mock_get_profile,
            mock.patch(
                "blackfish.server.asgi.sftp.write_file",
                return_value=mock_response,
            ) as mock_write,
        ):
            response = await client.put(
                "/api/text",
                files={"file": text_content},
                data={"path": "docs/test.txt"},
                params={"profile": "remote-cluster"},
            )

            assert response.status_code == 200

            mock_get_profile.assert_called_once_with("remote-cluster")
            mock_write.assert_called_once_with(
                remote_profile, "docs/test.txt", text_content, update=True
            )


class TestRemoteTextDelete:
    """Test DELETE /api/text with profile parameter."""

    async def test_delete_text_on_remote_profile(self, client: AsyncTestClient):
        """Test deleting a text file on a remote profile via SFTP."""
        remote_profile = create_remote_profile()

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ) as mock_get_profile,
            mock.patch(
                "blackfish.server.asgi.sftp.delete_file",
                return_value="/home/testuser/docs/test.txt",
            ) as mock_delete,
        ):
            response = await client.delete(
                "/api/text",
                params={"path": "docs/test.txt", "profile": "remote-cluster"},
            )

            assert response.status_code == 200

            mock_get_profile.assert_called_once_with("remote-cluster")
            mock_delete.assert_called_once_with(remote_profile, "docs/test.txt")


class TestRemoteAudioUpload:
    """Test POST /api/audio with profile parameter."""

    async def test_upload_audio_to_remote_profile(self, client: AsyncTestClient):
        """Test uploading an audio file to a remote profile via SFTP."""
        # Minimal WAV header (not a valid audio, but enough for the endpoint)
        audio_content = b"RIFF" + b"\x00" * 100
        remote_profile = create_remote_profile()

        mock_response = WriteFileResponse(
            filename="test.wav",
            size=len(audio_content),
            created_at=datetime.now(),
            path="/home/testuser/audio/test.wav",
        )

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ) as mock_get_profile,
            mock.patch(
                "blackfish.server.asgi.sftp.write_file",
                return_value=mock_response,
            ) as mock_write,
        ):
            response = await client.post(
                "/api/audio",
                files={"file": audio_content},
                data={"path": "audio/test.wav"},
                params={"profile": "remote-cluster"},
            )

            assert response.status_code == 201
            result = response.json()
            assert result["filename"] == "test.wav"

            mock_get_profile.assert_called_once_with("remote-cluster")
            mock_write.assert_called_once_with(
                remote_profile, "audio/test.wav", audio_content, update=False
            )


class TestRemoteAudioDownload:
    """Test GET /api/audio with profile parameter."""

    async def test_get_audio_from_remote_profile(self, client: AsyncTestClient):
        """Test downloading an audio file from a remote profile via SFTP."""
        audio_content = b"RIFF" + b"\x00" * 100
        remote_profile = create_remote_profile()

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ) as mock_get_profile,
            mock.patch(
                "blackfish.server.asgi.sftp.read_file",
                return_value=audio_content,
            ) as mock_read,
        ):
            response = await client.get(
                "/api/audio",
                params={"path": "audio/test.wav", "profile": "remote-cluster"},
            )

            assert response.status_code == 200
            assert response.content == audio_content
            assert response.headers["content-type"] == "audio/wav"

            mock_get_profile.assert_called_once_with("remote-cluster")
            mock_read.assert_called_once_with(remote_profile, "audio/test.wav")

    async def test_get_mp3_from_remote_profile(self, client: AsyncTestClient):
        """Test downloading an MP3 file returns correct content type."""
        mp3_content = b"\xff\xfb" + b"\x00" * 100  # Minimal MP3 header
        remote_profile = create_remote_profile()

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.asgi.sftp.read_file",
                return_value=mp3_content,
            ),
        ):
            response = await client.get(
                "/api/audio",
                params={"path": "audio/song.mp3", "profile": "remote-cluster"},
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "audio/mpeg"


class TestRemoteAudioUpdate:
    """Test PUT /api/audio with profile parameter."""

    async def test_update_audio_on_remote_profile(self, client: AsyncTestClient):
        """Test updating an audio file on a remote profile via SFTP."""
        audio_content = b"RIFF" + b"\x00" * 100
        remote_profile = create_remote_profile()

        mock_response = WriteFileResponse(
            filename="test.wav",
            size=len(audio_content),
            created_at=datetime.now(),
            path="/home/testuser/audio/test.wav",
        )

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ) as mock_get_profile,
            mock.patch(
                "blackfish.server.asgi.sftp.write_file",
                return_value=mock_response,
            ) as mock_write,
        ):
            response = await client.put(
                "/api/audio",
                files={"file": audio_content},
                data={"path": "audio/test.wav"},
                params={"profile": "remote-cluster"},
            )

            assert response.status_code == 200

            mock_get_profile.assert_called_once_with("remote-cluster")
            mock_write.assert_called_once_with(
                remote_profile, "audio/test.wav", audio_content, update=True
            )


class TestRemoteAudioDelete:
    """Test DELETE /api/audio with profile parameter."""

    async def test_delete_audio_on_remote_profile(self, client: AsyncTestClient):
        """Test deleting an audio file on a remote profile via SFTP."""
        remote_profile = create_remote_profile()

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ) as mock_get_profile,
            mock.patch(
                "blackfish.server.asgi.sftp.delete_file",
                return_value="/home/testuser/audio/test.wav",
            ) as mock_delete,
        ):
            response = await client.delete(
                "/api/audio",
                params={"path": "audio/test.wav", "profile": "remote-cluster"},
            )

            assert response.status_code == 200

            mock_get_profile.assert_called_once_with("remote-cluster")
            mock_delete.assert_called_once_with(remote_profile, "audio/test.wav")


class TestRemoteFileErrorHandling:
    """Test error handling for remote file operations."""

    async def test_remote_profile_not_found(self, client: AsyncTestClient):
        """Test error when remote profile doesn't exist."""
        from litestar.exceptions import NotFoundException

        png_bytes = create_test_png()

        with mock.patch(
            "blackfish.server.asgi._get_validated_slurm_profile",
            side_effect=NotFoundException("Profile 'nonexistent' not found"),
        ):
            response = await client.post(
                "/api/image",
                files={"file": png_bytes},
                data={"path": "images/test.png"},
                params={"profile": "nonexistent"},
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    async def test_remote_connection_error(self, client: AsyncTestClient):
        """Test error when SFTP connection fails."""
        from litestar.exceptions import InternalServerException

        png_bytes = create_test_png()
        remote_profile = create_remote_profile()

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.asgi.sftp.write_file",
                side_effect=InternalServerException("SFTP connection failed"),
            ),
        ):
            response = await client.post(
                "/api/image",
                files={"file": png_bytes},
                data={"path": "images/test.png"},
                params={"profile": "remote-cluster"},
            )

            # InternalServerException returns 500 status
            # Note: Litestar sanitizes the error message for 500 errors
            assert response.status_code == 500

    async def test_remote_permission_denied(self, client: AsyncTestClient):
        """Test error when permission denied on remote."""
        from litestar.exceptions import NotAuthorizedException

        png_bytes = create_test_png()
        remote_profile = create_remote_profile()

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.asgi.sftp.write_file",
                side_effect=NotAuthorizedException("Permission denied"),
            ),
        ):
            response = await client.post(
                "/api/image",
                files={"file": png_bytes},
                data={"path": "images/test.png"},
                params={"profile": "remote-cluster"},
            )

            assert response.status_code == 401

    async def test_remote_file_not_found(self, client: AsyncTestClient):
        """Test error when remote file doesn't exist."""
        from litestar.exceptions import NotFoundException

        remote_profile = create_remote_profile()

        with (
            mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile",
                return_value=remote_profile,
            ),
            mock.patch(
                "blackfish.server.asgi.sftp.read_file",
                side_effect=NotFoundException("Remote file not found"),
            ),
        ):
            response = await client.get(
                "/api/image",
                params={"path": "images/nonexistent.png", "profile": "remote-cluster"},
            )

            assert response.status_code == 404


class TestLocalFallback:
    """Test that local operations still work when profile is not specified."""

    async def test_upload_without_profile_uses_local(self, client: AsyncTestClient):
        """Test that upload without profile parameter uses local filesystem."""
        import tempfile
        import os

        png_bytes = create_test_png()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.png")

            with mock.patch(
                "blackfish.server.asgi._get_validated_slurm_profile"
            ) as mock_get_profile:
                response = await client.post(
                    "/api/image",
                    files={"file": png_bytes},
                    data={"path": file_path},
                    # No profile parameter
                )

                assert response.status_code == 201
                # Should not call get_remote_profile when profile is None
                mock_get_profile.assert_not_called()

                # File should exist locally
                assert os.path.exists(file_path)
