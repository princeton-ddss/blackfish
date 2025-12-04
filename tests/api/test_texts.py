import tempfile
import pytest
import os
from litestar.testing import AsyncTestClient


pytestmark = pytest.mark.anyio


class TestUploadTextAPI:
    """Test cases for the POST /api/texts endpoint."""

    async def test_upload_text_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that /api/texts requires authentication."""

        text_bytes = self._create_test_text()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")

            response = await no_auth_client.post(
                "/api/texts",
                files={"file": text_bytes},
                data={"path": file_path},
            )

            # Should return NotAuthorized error
            assert response.status_code == 401

    async def test_upload_text_valid_with_path(self, client: AsyncTestClient):
        """Test creating a valid text file with explicit path."""
        text_bytes = self._create_test_text()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")

            response = await client.post(
                "/api/texts",
                files={"file": text_bytes},
                data={"path": file_path},
            )

            # Should return success
            assert response.status_code == 201

            # Should include filename, size, and created_at
            result = response.json()
            assert result["filename"] == "test.txt"
            assert result["size"] == len(text_bytes)
            assert "created_at" in result

    async def test_upload_text_creates_parent_directories(
        self, client: AsyncTestClient
    ):
        """Test that parent directories are created."""
        text_bytes = self._create_test_text()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nested", "dirs", "test.txt")

            response = await client.post(
                "/api/texts",
                files={"file": text_bytes},
                data={"path": file_path},
            )

            # Should return success
            assert response.status_code == 201

            # Should create new directories
            assert os.path.exists(os.path.join(temp_dir, "nested", "dirs"))

    async def test_upload_text_invalid_extension(self, client: AsyncTestClient):
        """Test that invalid file extensions are rejected."""
        text_bytes = self._create_test_text()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.exe")

            response = await client.post(
                "/api/texts",
                files={"file": text_bytes},
                data={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "Validation failed for POST /api/texts" in result["detail"]

    async def test_upload_text_valid_extensions(self, client: AsyncTestClient):
        """Test that all valid text extensions are accepted."""

        valid_extensions = [
            ".txt",
            ".md",
            ".json",
            ".csv",
            ".xml",
            ".yaml",
            ".yml",
            ".log",
        ]
        text_bytes = self._create_test_text()

        with tempfile.TemporaryDirectory() as temp_dir:
            for ext in valid_extensions:
                file_path = os.path.join(temp_dir, f"test{ext}")
                response = await client.post(
                    "/api/texts",
                    files={"file": text_bytes},
                    data={"path": file_path},
                )

                # Should return success
                assert response.status_code == 201

    async def test_upload_text_invalid_data(self, client: AsyncTestClient):
        """Test that invalid UTF-8 data is rejected."""

        invalid_data = b"\x80\x81\x82\x83"  # Invalid UTF-8 bytes

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")

            response = await client.post(
                "/api/texts",
                files={"file": invalid_data},
                data={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "invalid UTF-8 text data" in result["detail"]

    async def test_upload_text_permission_denied(self, client: AsyncTestClient):
        """Test handling of permission denied errors."""

        text_bytes = self._create_test_text()

        with tempfile.TemporaryDirectory() as temp_dir:
            restricted_dir = os.path.join(temp_dir, "readonly")
            os.makedirs(restricted_dir)
            os.chmod(restricted_dir, 0o444)

            file_path = os.path.join(restricted_dir, "test.txt")

            try:
                response = await client.post(
                    "/api/texts",
                    files={"file": text_bytes},
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

    async def test_upload_text_existing_path(self, client: AsyncTestClient):
        """Test that uploading to an existing path returns 400 error."""
        text_bytes = self._create_test_text()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")

            # First upload should succeed
            response = await client.post(
                "/api/texts",
                files={"file": text_bytes},
                data={"path": file_path},
            )
            assert response.status_code == 201

            # Second upload to the same path should fail
            response = await client.post(
                "/api/texts",
                files={"file": text_bytes},
                data={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "already exists" in result["detail"]

    def _create_test_text(self) -> bytes:
        """Create a minimal valid text content for testing."""
        return b"This is a test text file.\nWith multiple lines.\n"


class TestGetTextAPI:
    """Test cases for the GET /api/texts endpoint."""

    async def test_get_text_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that GET /api/texts requires authentication."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            self._create_and_save_text(file_path)

            response = await no_auth_client.get(
                "/api/texts",
                params={"path": file_path},
            )

            # Should return NotAuthorized error
            assert response.status_code == 401

    async def test_get_text_success(self, client: AsyncTestClient):
        """Test retrieving an existing text file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            original_data = self._create_and_save_text(file_path)

            response = await client.get(
                "/api/texts",
                params={"path": file_path},
            )

            # Should return success with text data
            assert response.status_code == 200
            assert response.content == original_data

    async def test_get_text_not_found(self, client: AsyncTestClient):
        """Test retrieving a non-existent text file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nonexistent.txt")

            response = await client.get(
                "/api/texts",
                params={"path": file_path},
            )

            # Should return not found error
            assert response.status_code == 404

    async def test_get_text_is_directory(self, client: AsyncTestClient):
        """Test that attempting to get a directory returns an error."""

        with tempfile.TemporaryDirectory() as temp_dir:
            response = await client.get(
                "/api/texts",
                params={"path": temp_dir},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "not a file" in result["detail"]

    async def test_get_text_invalid_extension(self, client: AsyncTestClient):
        """Test that files with invalid extensions are rejected."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.exe")
            with open(file_path, "w") as f:
                f.write("Not a valid extension")

            response = await client.get(
                "/api/texts",
                params={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "Invalid text file extension" in result["detail"]

    async def test_get_text_corrupted_file(self, client: AsyncTestClient):
        """Test that corrupted text files (invalid UTF-8) are rejected."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "corrupted.txt")
            with open(file_path, "wb") as f:
                f.write(b"\x80\x81\x82\x83")  # Invalid UTF-8

            response = await client.get(
                "/api/texts",
                params={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "Invalid text file" in result["detail"]

    def _create_and_save_text(self, path: str) -> bytes:
        """Create and save a text file for testing."""
        data = b"This is test content.\nLine 2.\nLine 3.\n"
        with open(path, "wb") as f:
            f.write(data)
        return data


class TestUpdateTextAPI:
    """Test cases for the PUT /api/texts endpoint."""

    async def test_update_text_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that PUT /api/texts requires authentication."""

        text_bytes = self._create_test_text()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            self._create_and_save_text(file_path)

            response = await no_auth_client.put(
                "/api/texts",
                files={"file": text_bytes},
                data={"path": file_path},
            )

            # Should return NotAuthorized error
            assert response.status_code == 401

    async def test_update_text_success(self, client: AsyncTestClient):
        """Test successfully updating an existing text file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            # Create initial file
            self._create_and_save_text(file_path, content="Original content")

            # Update with new content
            new_text_bytes = b"Updated content\nNew line\n"
            response = await client.put(
                "/api/texts",
                files={"file": new_text_bytes},
                data={"path": file_path},
            )

            # Should return success
            assert response.status_code == 200
            result = response.json()
            assert result["filename"] == "test.txt"
            assert result["size"] == len(new_text_bytes)
            assert "created_at" in result

            # Verify file was actually updated
            with open(file_path, "rb") as f:
                assert f.read() == new_text_bytes

    async def test_update_text_not_found(self, client: AsyncTestClient):
        """Test updating a non-existent text file."""

        text_bytes = self._create_test_text()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nonexistent.txt")

            response = await client.put(
                "/api/texts",
                files={"file": text_bytes},
                data={"path": file_path},
            )

            # Should return not found error
            assert response.status_code == 404

    async def test_update_text_is_directory(self, client: AsyncTestClient):
        """Test that attempting to update a directory returns an error."""

        text_bytes = self._create_test_text()

        with tempfile.TemporaryDirectory() as temp_dir:
            response = await client.put(
                "/api/texts",
                files={"file": text_bytes},
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

    async def test_update_text_invalid_data(self, client: AsyncTestClient):
        """Test that invalid UTF-8 data is rejected."""

        invalid_data = b"\x80\x81\x82\x83"  # Invalid UTF-8

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            self._create_and_save_text(file_path)

            response = await client.put(
                "/api/texts",
                files={"file": invalid_data},
                data={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "invalid UTF-8 text data" in result["detail"]

    async def test_update_text_permission_denied(self, client: AsyncTestClient):
        """Test handling of permission denied errors."""

        text_bytes = self._create_test_text()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            self._create_and_save_text(file_path)
            os.chmod(file_path, 0o444)

            try:
                response = await client.put(
                    "/api/texts",
                    files={"file": text_bytes},
                    data={"path": file_path},
                )

                # Should return permission denied or OS error
                assert response.status_code in [401, 500]

            finally:
                # Restore permissions for cleanup
                os.chmod(file_path, 0o644)

    def _create_test_text(self) -> bytes:
        """Create a minimal valid text content for testing."""
        return b"This is a test text file.\n"

    def _create_and_save_text(
        self, path: str, content: str = "Test content\n"
    ) -> bytes:
        """Create and save a text file for testing."""
        data = content.encode("utf-8")
        with open(path, "wb") as f:
            f.write(data)
        return data


class TestDeleteTextAPI:
    """Test cases for the DELETE /api/texts endpoint."""

    async def test_delete_text_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that DELETE /api/texts requires authentication."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            self._create_and_save_text(file_path)

            response = await no_auth_client.delete(
                "/api/texts",
                params={"path": file_path},
            )

            # Should return NotAuthorized error
            assert response.status_code == 401

    async def test_delete_text_success(self, client: AsyncTestClient):
        """Test successfully deleting an existing text file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            self._create_and_save_text(file_path)

            # Verify file exists
            assert os.path.exists(file_path)

            response = await client.delete(
                "/api/texts",
                params={"path": file_path},
            )

            # Should return success
            assert response.status_code == 200
            result = response.json()
            assert "Successfully deleted" in result["message"]

            # Verify file was actually deleted
            assert not os.path.exists(file_path)

    async def test_delete_text_not_found(self, client: AsyncTestClient):
        """Test deleting a non-existent text file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nonexistent.txt")

            response = await client.delete(
                "/api/texts",
                params={"path": file_path},
            )

            # Should return not found error
            assert response.status_code == 404

    async def test_delete_text_is_directory(self, client: AsyncTestClient):
        """Test that attempting to delete a directory returns an error."""

        with tempfile.TemporaryDirectory() as temp_dir:
            response = await client.delete(
                "/api/texts",
                params={"path": temp_dir},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "not a file" in result["detail"]

    async def test_delete_text_invalid_extension(self, client: AsyncTestClient):
        """Test that files with invalid extensions cannot be deleted."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.exe")
            with open(file_path, "w") as f:
                f.write("Not a text file")

            response = await client.delete(
                "/api/texts",
                params={"path": file_path},
            )

            # Should return validation error
            assert response.status_code == 400
            result = response.json()
            assert "Invalid text file extension" in result["detail"]

    async def test_delete_text_permission_denied(self, client: AsyncTestClient):
        """Test handling of permission denied errors."""

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            self._create_and_save_text(file_path)

            # Make parent directory read-only
            os.chmod(temp_dir, 0o555)

            try:
                response = await client.delete(
                    "/api/texts",
                    params={"path": file_path},
                )

                # Should return permission denied or OS error
                assert response.status_code in [401, 500]

            finally:
                # Restore permissions for cleanup
                os.chmod(temp_dir, 0o755)

    def _create_and_save_text(self, path: str) -> bytes:
        """Create and save a text file for testing."""
        data = b"This is test content for deletion.\n"
        with open(path, "wb") as f:
            f.write(data)
        return data
