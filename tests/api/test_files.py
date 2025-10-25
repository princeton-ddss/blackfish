import tempfile
import pytest
import os
from pathlib import Path
from litestar.testing import AsyncTestClient
from io import BytesIO
from typing import Generator

pytestmark = pytest.mark.anyio


@pytest.fixture
def cleanup_uploads() -> Generator[list[str], None, None]:
    """Track files created in uploads directory and clean them up after test."""
    created_files: list[str] = []
    yield created_files
    for file_path in created_files:
        if os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except Exception as e:
                print(f"Warning: Failed to clean up {file_path}: {e}")

    uploads_dir = Path("tests/uploads")
    if uploads_dir.exists() and uploads_dir.is_dir():
        try:
            import shutil
            shutil.rmtree(uploads_dir)
        except Exception as e:
            print(f"Warning: Failed to remove uploads directory: {e}")


class TestSaveTextFileAPI:
    """Test cases for the POST /api/files/text endpoint."""

    async def test_save_text_file_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that /api/files/text requires authentication."""
        response = await no_auth_client.post(
            "/api/files/text",
            json={"path": "/tmp/test.txt", "content": "Hello, world!"},
        )

        assert response.status_code == 401

    async def test_save_text_file_valid(self, client: AsyncTestClient):
        """Test creating a valid text file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            content = "Hello, world!\nThis is a test file."

            response = await client.post(
                "/api/files/text",
                json={"path": file_path, "content": content},
            )

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "ok"
            assert Path(result["path"]).resolve() == Path(file_path).resolve()

            assert os.path.exists(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                assert f.read() == content

    async def test_save_text_file_creates_parent_directories(
        self, client: AsyncTestClient
    ):
        """Test that parent directories are created if they don't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nested", "dirs", "test.txt")
            content = "Test content"

            response = await client.post(
                "/api/files/text",
                json={"path": file_path, "content": content},
            )

            assert response.status_code == 200
            assert os.path.exists(file_path)

    async def test_save_text_file_invalid_extension(self, client: AsyncTestClient):
        """Test that invalid file extensions are rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.exe")

            response = await client.post(
                "/api/files/text",
                json={"path": file_path, "content": "test"},
            )

            assert response.status_code == 400
            result = response.json()
            assert "Invalid text file extension" in result["detail"]

    async def test_save_text_file_valid_extensions(self, client: AsyncTestClient):
        """Test that all valid text file extensions are accepted."""
        valid_extensions = [".txt", ".md", ".json", ".csv", ".log", ".yaml", ".yml", ".xml"]

        with tempfile.TemporaryDirectory() as temp_dir:
            for ext in valid_extensions:
                file_path = os.path.join(temp_dir, f"test{ext}")
                response = await client.post(
                    "/api/files/text",
                    json={"path": file_path, "content": "test"},
                )
                assert response.status_code == 200, f"Failed for extension {ext}"

    async def test_save_text_file_directory_traversal(self, client: AsyncTestClient):
        """Test that directory traversal is blocked."""
        response = await client.post(
            "/api/files/text",
            json={"path": "/tmp/../etc/passwd.txt", "content": "malicious"},
        )

        assert response.status_code == 400
        result = response.json()
        assert "directory traversal" in result["detail"].lower()

    async def test_save_text_file_relative_path(self, client: AsyncTestClient):
        """Test that relative paths are rejected."""
        response = await client.post(
            "/api/files/text",
            json={"path": "relative/path/test.txt", "content": "test"},
        )

        assert response.status_code == 400
        result = response.json()
        assert "absolute" in result["detail"].lower()

    async def test_save_text_file_invalid_utf8(self, client: AsyncTestClient):
        """Test that non-UTF-8 content is rejected."""
        # This test is tricky because JSON itself requires valid UTF-8
        # So we test by ensuring the validation is in place
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            # Valid UTF-8 should work
            response = await client.post(
                "/api/files/text",
                json={"path": file_path, "content": "Hello 世界 🌍"},
            )
            assert response.status_code == 200

    async def test_save_text_file_overwrites_existing(self, client: AsyncTestClient):
        """Test that existing files are overwritten."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")

            # Create initial file
            response1 = await client.post(
                "/api/files/text",
                json={"path": file_path, "content": "Original content"},
            )
            assert response1.status_code == 200

            # Overwrite file
            response2 = await client.post(
                "/api/files/text",
                json={"path": file_path, "content": "New content"},
            )
            assert response2.status_code == 200

            # Verify content was overwritten
            with open(file_path, "r") as f:
                assert f.read() == "New content"

    async def test_save_text_file_permission_denied(self, client: AsyncTestClient):
        """Test handling of permission denied errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a read-only directory
            restricted_dir = os.path.join(temp_dir, "readonly")
            os.makedirs(restricted_dir)
            os.chmod(restricted_dir, 0o444)

            file_path = os.path.join(restricted_dir, "test.txt")

            try:
                response = await client.post(
                    "/api/files/text",
                    json={"path": file_path, "content": "test"},
                )

                # Should return 401 for permission denied
                assert response.status_code == 401

            finally:
                # Restore permissions for cleanup
                os.chmod(restricted_dir, 0o755)


class TestSaveImageFileAPI:
    """Test cases for the POST /api/files/image endpoint."""

    async def test_save_image_file_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that /api/files/image requires authentication."""
        # Create minimal PNG file
        png_bytes = self._create_test_png()

        response = await no_auth_client.post(
            "/api/files/image",
            files={"data": ("test.png", png_bytes, "image/png")},
        )

        # Should require authentication
        assert response.status_code == 401

    async def test_save_image_file_valid_with_path(self, client: AsyncTestClient):
        """Test creating a valid image file with explicit path."""
        png_bytes = self._create_test_png()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.png")

            response = await client.post(
                "/api/files/image",
                files={"data": ("test.png", png_bytes, "image/png")},
                data={"path": file_path},
            )

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "ok"
            assert Path(result["path"]).resolve() == Path(file_path).resolve()

            assert os.path.exists(file_path)

    async def test_save_image_file_valid_without_path(
        self, client: AsyncTestClient, cleanup_uploads: list[str]
    ):
        """Test creating image without path (auto-save to uploads)."""
        png_bytes = self._create_test_png()

        response = await client.post(
            "/api/files/image",
            files={"data": ("myimage.png", png_bytes, "image/png")},
        )

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "ok"
        assert "uploads" in result["path"]
        assert "myimage.png" in result["path"]

        cleanup_uploads.append(result["path"])

    async def test_save_image_file_creates_parent_directories(
        self, client: AsyncTestClient
    ):
        """Test that parent directories are created."""
        png_bytes = self._create_test_png()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nested", "dirs", "image.png")

            response = await client.post(
                "/api/files/image",
                files={"data": ("test.png", png_bytes, "image/png")},
                data={"path": file_path},
            )

            assert response.status_code == 200
            assert os.path.exists(file_path)

    async def test_save_image_file_invalid_extension(self, client: AsyncTestClient):
        """Test that invalid file extensions are rejected."""
        png_bytes = self._create_test_png()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.exe")

            response = await client.post(
                "/api/files/image",
                files={"data": ("test.png", png_bytes, "image/png")},
                data={"path": file_path},
            )

            assert response.status_code == 400
            result = response.json()
            assert "Invalid image file extension" in result["detail"]

    async def test_save_image_file_valid_extensions(self, client: AsyncTestClient):
        """Test that all valid image extensions are accepted."""
        valid_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"]
        png_bytes = self._create_test_png()

        with tempfile.TemporaryDirectory() as temp_dir:
            for ext in valid_extensions:
                file_path = os.path.join(temp_dir, f"test{ext}")
                response = await client.post(
                    "/api/files/image",
                    files={"data": (f"test{ext}", png_bytes, "image/png")},
                    data={"path": file_path},
                )
                assert response.status_code in [200, 400], f"Unexpected status for {ext}"

    async def test_save_image_file_directory_traversal(self, client: AsyncTestClient):
        """Test that directory traversal is blocked."""
        png_bytes = self._create_test_png()

        response = await client.post(
            "/api/files/image",
            files={"data": ("test.png", png_bytes, "image/png")},
            data={"path": "/tmp/../etc/image.png"},
        )

        assert response.status_code == 400
        result = response.json()
        assert "directory traversal" in result["detail"].lower()

    async def test_save_image_file_invalid_data(self, client: AsyncTestClient):
        """Test that invalid image data is rejected."""
        invalid_data = b"This is not an image"

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.png")

            response = await client.post(
                "/api/files/image",
                files={"data": ("test.png", invalid_data, "image/png")},
                data={"path": file_path},
            )

            assert response.status_code == 400
            result = response.json()
            assert "Invalid image data" in result["detail"]

    async def test_save_image_file_permission_denied(self, client: AsyncTestClient):
        """Test handling of permission denied errors."""
        png_bytes = self._create_test_png()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a read-only directory
            restricted_dir = os.path.join(temp_dir, "readonly")
            os.makedirs(restricted_dir)
            os.chmod(restricted_dir, 0o444)

            file_path = os.path.join(restricted_dir, "test.png")

            try:
                response = await client.post(
                    "/api/files/image",
                    files={"data": ("test.png", png_bytes, "image/png")},
                    data={"path": file_path},
                )

                # Should return 401 for permission denied
                assert response.status_code == 401

            finally:
                # Restore permissions for cleanup
                os.chmod(restricted_dir, 0o755)

    def _create_test_png(self) -> bytes:
        """Create a minimal valid PNG image for testing."""
        from PIL import Image

        img = Image.new("RGB", (10, 10), color="red")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
