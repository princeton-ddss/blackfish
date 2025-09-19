import pytest
from unittest.mock import patch
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from litestar.testing import AsyncTestClient

from app.models.model import Model

pytestmark = pytest.mark.anyio


class TestFetchModelsAPI:
    """Test cases for the GET /api/models endpoint."""

    async def test_fetch_models_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that /api/models requires authentication."""
        response = await no_auth_client.get("/api/models")

        # Should require authentication
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_fetch_all_models(self, client: AsyncTestClient):
        """Test fetching all models without filters."""
        response = await client.get("/api/models")

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)  # Test fixtures include model data

    async def test_fetch_models_by_profile(self, client: AsyncTestClient):
        """Test fetching models by profile."""
        response = await client.get("/api/models", params={"profile": "test"})

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) == 2
        for model in result:
            assert model.get("profile") == "test"

    async def test_fetch_models_by_image(self, client: AsyncTestClient):
        """Test fetching models by image."""
        response = await client.get("/api/models", params={"image": "text_generation"})

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) == 2
        for model in result:
            assert model.get("image") == "text_generation"

    async def test_fetch_models_with_refresh(self, client: AsyncTestClient):
        """Test fetching models with refresh parameter."""

        # TODO: This is a bit complicated because we call app.asgi.find_models for each test profile, but there is no actual model data to find.
        # We can either add test data dummy files or mock the call, but the return of each mocked call should be different.

        pass

    async def test_fetch_models_refresh_with_profile(self, client: AsyncTestClient):
        """Test refreshing models for specific profile."""

        with patch("app.asgi.find_models") as mock_find_models:
            # Return fixture data for "default" profile
            mock_find_models.return_value = [
                Model(
                    **{
                        "id": "cc64bbef-816c-4070-941d-3dabece7a3b9",
                        "repo": "openai/whisper-large-v3",
                        "profile": "default",
                        "revision": "1",
                        "image": "speech_recognition",
                        "model_dir": "/home/test/.blackfish/models/models--openai/whisper-large-v3",
                    }
                ),
                Model(
                    **{
                        "id": "0022468b-3182-4381-a76a-25d06248398f",
                        "repo": "openai/whisper-tiny",
                        "profile": "default",
                        "revision": "2",
                        "image": "speech_recognition",
                        "model_dir": "/home/test/.blackfish/models/models--openai/whisper-tiny",
                    }
                ),
            ]

            response = await client.get(
                "/api/models", params={"profile": "default", "refresh": True}
            )

            assert response.status_code == 200
            mock_find_models.assert_called_once()
            result = response.json()
            assert isinstance(result, list)
            assert len(result) == 2
            for model in result:
                assert model.get("profile") == "default"

    @pytest.mark.parametrize("refresh", [True, False])
    async def test_fetch_models_nonexistent_profile(
        self, refresh, client: AsyncTestClient
    ):
        """Test fetching models for nonexistent profile with refresh."""
        response = await client.get(
            "/api/models",
            params={
                "profile": "nonexistent-profile",
                "refresh": refresh,
            },
        )

        assert response.status_code == 200
        result = response.json()
        # Should return empty list for nonexistent profile
        assert result == []

    async def test_fetch_models_multiple_parameters(self, client: AsyncTestClient):
        """Test fetching models with multiple filter parameters."""
        response = await client.get(
            "/api/models",
            params={"profile": "test", "image": "text_generation", "refresh": False},
        )

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) == 1
        model = result[0]
        assert (
            model.get("profile") == "test" and model.get("image") == "text_generation"
        )


class TestGetSingleModelAPI:
    """Test cases for the GET /api/models/{model_id} endpoint."""

    async def test_get_model_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that individual model endpoint requires authentication."""
        test_id = "test-model-id"
        response = await no_auth_client.get(f"/api/models/{test_id}")

        # Should require authentication
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_get_model_by_id_success(self, client: AsyncTestClient, models):
        """Test successfully fetching a single model by ID."""
        # Use a model from the test fixtures
        if models:
            model_id = models[0]["id"]

            response = await client.get(f"/api/models/{model_id}")

            assert response.status_code == 200
            result = response.json()

            # Verify it returns a single model object
            assert isinstance(result, dict)
            assert result["id"] == model_id

    async def test_get_model_nonexistent_id(self, client: AsyncTestClient):
        """Test fetching a model that doesn't exist."""
        nonexistent_id = "85ef13c5-529f-5579-8023-6f5823897ee8"

        response = await client.get(f"/api/models/{nonexistent_id}")

        assert response.status_code == 404

    async def test_invalid_id(self, client: AsyncTestClient):
        """Test that the endpoint returns error code."""

        test_id = "test-log-model-id"

        response = await client.get(f"/api/models/{test_id}")

        # Should return bad request error
        assert response.status_code == 400


class TestCreateModelAPI:
    """Test cases for the POST /api/models endpoint."""

    async def test_create_model_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that model creation requires authentication."""
        model_data = {"id": "test-model", "profile": "test", "name": "Test Model"}

        response = await no_auth_client.post("/api/models", json=model_data)

        # Should require authentication
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_create_model_missing_data(self, client: AsyncTestClient):
        """Test creating a model with missing required data."""
        response = await client.post("/api/models")

        # Should return bad request error
        assert response.status_code == 400

    async def test_create_model_invalid_data(self, client: AsyncTestClient):
        """Test creating a model with invalid data."""
        invalid_data = {
            "invalid_field": "value",
            # Missing required Model fields
        }

        response = await client.post("/api/models", json=invalid_data)

        # Should return validation error
        assert response.status_code == 400

    async def test_create_model_valid_data(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test creating a model with valid data. This endpoint only adds a model to the database."""
        model_data = {
            "id": f"{uuid4()}",
            "repo": "test/repo",
            "profile": "test",
            "revision": "test",
            "image": "test-image",
            "model_dir": "test",
        }

        response = await client.post("/api/models", json=model_data)

        # Should create the model successfully
        assert response.status_code == 201

        if response.status_code in [200, 201]:
            result = response.json()
            assert isinstance(result, dict)
            assert result["id"] == model_data["id"]

    async def test_create_model_duplicate_id(self, client: AsyncTestClient):
        """Test creating a model with duplicate ID."""
        model_data = {
            "id": f"{uuid4()}",
            "repo": "test/repo",
            "profile": "test",
            "revision": "test",
            "image": "test-image",
            "model_dir": "test",
        }

        # Create the model first time
        first_response = await client.post("/api/models", json=model_data)

        # Try to create again with same ID
        second_response = await client.post("/api/models", json=model_data)

        # Should return successful creation
        assert first_response.status_code == 201
        # Should return resource conflict/duplicate
        assert second_response.status_code == 409


class TestDeleteModelAPI:
    """Test cases for the DELETE /api/models/{model_id} endpoint."""

    async def test_delete_model_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that model deletion requires authentication."""
        test_id = "test-model-id"
        response = await no_auth_client.delete(f"/api/models/{test_id}")

        # Should require authentication
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_delete_model_invalid_id(self, client: AsyncTestClient):
        """Test deleting a model that doesn't exist."""
        invalid_id = "invalid_uuid"

        response = await client.delete(f"/api/models/{invalid_id}")

        # Should return bad request error
        assert response.status_code == 400

    async def test_delete_model_nonexistent_id(self, client: AsyncTestClient):
        """Test deleting a model that doesn't exist."""
        nonexistent_id = "85ef13c5-529f-5579-8023-6f5823897ee8"

        response = await client.delete(f"/api/models/{nonexistent_id}")

        # Should return not found error
        assert response.status_code == 404

    async def test_delete_model_success(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test successfully deleting a model."""
        # First create a model to delete
        model_data = {
            "id": f"delete-test-{uuid4()}",
            "profile": "test",
            "name": "Model to Delete",
            "repo_id": "test/repo",
            "image": "test-image",
            "size": 1000000,
            "filename": "model.bin",
        }

        create_response = await client.post("/api/models", json=model_data)

        if create_response.status_code == 201:
            model_id = model_data["id"]
            delete_response = await client.delete(f"/api/models/{model_id}")

            # Should delete successfully
            assert delete_response.status_code == 204
            assert delete_response.content == {}

            # Verify model is deleted by trying to fetch it
            get_response = await client.get(f"/api/models/{model_id}")
            assert get_response.status_code == 404
