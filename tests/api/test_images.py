import tempfile
import pytest
import os
from litestar.testing import AsyncTestClient
from io import BytesIO
from PIL import Image


pytestmark = pytest.mark.anyio


class TestUploadImageAPI:
    """Test cases for the POST /api/images endpoint."""

    async def test_upload_image_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that /api/images requires authentication."""

        png_bytes = self._create_test_png()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "text.png")

            response = await no_auth_client.post(
                "/api/images",
                files={"file": png_bytes},
                data={"path": file_path},
            )

            # Should return NotAuthorized error
            assert response.status_code == 401

    async def test_upload_image_valid_with_path(self, client: AsyncTestClient):
        """Test creating a valid image file with explicit path."""
        png_bytes = self._create_test_png()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.png")

            response = await client.post(
                "/api/images",
                files={"file": png_bytes},
                data={"path": file_path},
            )

            # Should return success
            assert response.status_code == 201

            # Should include filename, size, and created_at
            result = response.json()
            assert result["filename"] == "test.png"
            assert result["size"] == len(png_bytes)
            assert "created_at" in result

    async def test_upload_image_creates_parent_directories(
        self, client: AsyncTestClient
    ):
        """Test that parent directories are created."""
        png_bytes = self._create_test_png()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nested", "dirs", "test.png")

            response = await client.post(
                "/api/images",
                files={"file": png_bytes},
                data={"path": file_path},
            )

            # Should return success
            assert response.status_code == 201

            # Should create new directories
            assert os.path.exists(os.path.join(temp_dir, "nested", "dirs"))

    async def test_upload_image_invalid_extension(self, client: AsyncTestClient):
        """Test that invalid file extensions are rejected."""
        png_bytes = self._create_test_png()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.exe")

            response = await client.post(
                "/api/images",
                files={"file": png_bytes},
                data={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "Validation failed for POST /api/images" in result["detail"]

    async def test_upload_image_valid_extensions(self, client: AsyncTestClient):
        """Test that all valid image extensions are accepted."""

        valid_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"]
        png_bytes = self._create_test_png()

        with tempfile.TemporaryDirectory() as temp_dir:
            for ext in valid_extensions:
                file_path = os.path.join(temp_dir, f"test{ext}")
                response = await client.post(
                    "/api/images",
                    files={"file": png_bytes},
                    data={"path": file_path},
                )

                # Should return success
                assert response.status_code == 201

    async def test_upload_image_invalid_data(self, client: AsyncTestClient):
        """Test that invalid image data is rejected."""

        invalid_data = b"This is not an image"

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.png")

            response = await client.post(
                "/api/images",
                files={"file": invalid_data},
                data={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "Pillow detected invalid image data" in result["detail"]

    async def test_upload_image_permission_denied(self, client: AsyncTestClient):
        """Test handling of permission denied errors."""

        png_bytes = self._create_test_png()

        with tempfile.TemporaryDirectory() as temp_dir:
            restricted_dir = os.path.join(temp_dir, "readonly")
            os.makedirs(restricted_dir)
            os.chmod(restricted_dir, 0o444)

            file_path = os.path.join(restricted_dir, "test.png")

            try:
                response = await client.post(
                    "/api/images",
                    files={"file": png_bytes},
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

    async def test_upload_image_existing_path(self, client: AsyncTestClient):
        """Test that uploading to an existing path returns 400 error."""
        png_bytes = self._create_test_png()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.png")

            # First upload should succeed
            response = await client.post(
                "/api/images",
                files={"file": png_bytes},
                data={"path": file_path},
            )
            assert response.status_code == 201

            # Second upload to the same path should fail
            response = await client.post(
                "/api/images",
                files={"file": png_bytes},
                data={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "already exists" in result["detail"]

    def _create_test_png(self) -> bytes:
        """Create a minimal valid PNG image for testing."""
        img = Image.new("RGB", (10, 10), color="red")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()


class TestGetImageAPI:
    """Test cases for the GET /api/images endpoint."""

    async def test_get_image_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that GET /api/images requires authentication."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.png")
            self._create_and_save_png(file_path)

            response = await no_auth_client.get(
                "/api/images",
                params={"path": file_path},
            )

            # Should return NotAuthorized error
            assert response.status_code == 401

    async def test_get_image_success(self, client: AsyncTestClient):
        """Test retrieving an existing image file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.png")
            original_data = self._create_and_save_png(file_path)

            response = await client.get(
                "/api/images",
                params={"path": file_path},
            )

            # Should return success with image data
            assert response.status_code == 200
            assert response.content == original_data

    async def test_get_image_not_found(self, client: AsyncTestClient):
        """Test retrieving a non-existent image."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nonexistent.png")

            response = await client.get(
                "/api/images",
                params={"path": file_path},
            )

            # Should return not found error
            assert response.status_code == 404

    async def test_get_image_is_directory(self, client: AsyncTestClient):
        """Test that attempting to get a directory returns an error."""

        with tempfile.TemporaryDirectory() as temp_dir:
            response = await client.get(
                "/api/images",
                params={"path": temp_dir},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "not a file" in result["detail"]

    async def test_get_image_invalid_extension(self, client: AsyncTestClient):
        """Test that files with invalid extensions are rejected."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            with open(file_path, "w") as f:
                f.write("Not an image")

            response = await client.get(
                "/api/images",
                params={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "Invalid image file extension" in result["detail"]

    async def test_get_image_corrupted_file(self, client: AsyncTestClient):
        """Test that corrupted image files are rejected."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "corrupted.png")
            with open(file_path, "wb") as f:
                f.write(b"This is not a valid PNG file")

            response = await client.get(
                "/api/images",
                params={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "Invalid image file" in result["detail"]

    def _create_and_save_png(self, path: str) -> bytes:
        """Create and save a PNG image for testing."""
        img = Image.new("RGB", (10, 10), color="blue")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        data = buffer.getvalue()
        with open(path, "wb") as f:
            f.write(data)
        return data