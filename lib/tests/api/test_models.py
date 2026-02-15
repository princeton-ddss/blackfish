import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from litestar.testing import AsyncTestClient

from blackfish.server.models.model import Model

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

    async def test_fetch_models_by_image_includes_compatible_pipelines(
        self, client: AsyncTestClient
    ):
        """Test that fetching models by image includes compatible pipeline types.

        For example, text-generation should also return image-text-to-text models
        (VLMs like LLaVA) since vLLM can serve them via the chat completions API.
        """
        # Create a VLM model with image-text-to-text pipeline
        vlm_model = {
            "id": f"{uuid4()}",
            "repo": "llava-hf/llava-1.5-7b-hf",
            "profile": "default",
            "revision": "main",
            "image": "image-text-to-text",
            "model_dir": "/home/test/.blackfish/models/models--llava-hf/llava-1.5-7b-hf",
        }
        create_response = await client.post("/api/models", json=vlm_model)
        assert create_response.status_code == 201

        # Query for text-generation models
        response = await client.get("/api/models", params={"image": "text-generation"})

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)

        # Should include both text-generation and image-text-to-text models
        images = {model.get("image") for model in result}
        assert "image-text-to-text" in images

        # Verify the VLM model is in the results
        vlm_ids = [m["id"] for m in result if m["image"] == "image-text-to-text"]
        assert vlm_model["id"] in vlm_ids

    async def test_refresh_preserves_existing_model_ids(self, client: AsyncTestClient):
        """Test that refresh preserves IDs for models that already exist."""
        # Get existing model ID before refresh
        response = await client.get("/api/models", params={"profile": "default"})
        assert response.status_code == 200
        existing_models = response.json()
        assert len(existing_models) > 0
        existing_id = existing_models[0]["id"]
        existing_repo = existing_models[0]["repo"]
        existing_revision = existing_models[0]["revision"]

        # Use AsyncMock for async function find_models
        mock_find_models = AsyncMock(return_value=[
            Model(
                repo=existing_repo,
                profile="default",
                revision=existing_revision,
                image="unknown",  # find_models now returns "unknown"
                model_dir="/home/test/.blackfish/models/test",
                metadata_=None,
            ),
        ])
        mock_fetch = MagicMock(return_value=("text-generation", {"model_size_gb": 1.0}))

        with patch("blackfish.server.asgi.find_models", mock_find_models):
            with patch("blackfish.server.asgi.fetch_model_info_from_hub", mock_fetch):
                response = await client.get(
                    "/api/models", params={"profile": "default", "refresh": True}
                )

                assert response.status_code == 200
                result = response.json()
                assert len(result) == 1
                # ID should be preserved
                assert result[0]["id"] == existing_id

    async def test_refresh_adds_new_models(self, client: AsyncTestClient):
        """Test that refresh adds models that are on filesystem but not in DB."""
        mock_find_models = AsyncMock(return_value=[
            Model(
                repo="openai/whisper-large-v3",
                profile="default",
                revision="1",
                image="unknown",
                model_dir="/home/test/.blackfish/models/models--openai/whisper-large-v3",
                metadata_=None,
            ),
            Model(
                repo="new-org/new-model",
                profile="default",
                revision="main",
                image="unknown",
                model_dir="/home/test/.blackfish/models/models--new-org/new-model",
                metadata_=None,
            ),
        ])
        mock_fetch = MagicMock(return_value=("text-generation", {"model_size_gb": 1.0}))

        with patch("blackfish.server.asgi.find_models", mock_find_models):
            with patch("blackfish.server.asgi.fetch_model_info_from_hub", mock_fetch):
                response = await client.get(
                    "/api/models", params={"profile": "default", "refresh": True}
                )

                assert response.status_code == 200
                result = response.json()
                # Should have the new model
                repos = [m["repo"] for m in result]
                assert "new-org/new-model" in repos

    async def test_refresh_deletes_stale_models(self, client: AsyncTestClient):
        """Test that refresh removes models in DB but not on filesystem."""
        # Get existing model
        response = await client.get("/api/models", params={"profile": "default"})
        existing_models = response.json()
        assert len(existing_models) > 0

        mock_find_models = AsyncMock(return_value=[])

        with patch("blackfish.server.asgi.find_models", mock_find_models):
            response = await client.get(
                "/api/models", params={"profile": "default", "refresh": True}
            )

            assert response.status_code == 200
            result = response.json()
            # All models should be deleted
            assert len(result) == 0

    async def test_fetch_models_refresh_with_profile(self, client: AsyncTestClient):
        """Test refreshing models for specific profile."""
        # Use repos/revisions that match existing fixture data for default profile
        # Fixture has: whisper-large-v3 (rev=1, default), Llama-3.2-3B (rev=3, default)
        mock_find_models = AsyncMock(return_value=[
            Model(
                repo="openai/whisper-large-v3",
                profile="default",
                revision="1",  # Same as fixture
                image="unknown",
                model_dir="/home/test/.blackfish/models/models--openai/whisper-large-v3",
                metadata_=None,
            ),
            Model(
                repo="meta-llama/Llama-3.2-3B",
                profile="default",
                revision="3",  # Same as fixture
                image="unknown",
                model_dir="/home/test/.blackfish/models/models--meta-llama/Llama-3.2-3B",
                metadata_=None,
            ),
        ])
        mock_fetch = MagicMock(return_value=("speech-recognition", {"model_size_gb": 1.0}))

        with patch("blackfish.server.asgi.find_models", mock_find_models):
            with patch("blackfish.server.asgi.fetch_model_info_from_hub", mock_fetch):
                response = await client.get(
                    "/api/models", params={"profile": "default", "refresh": True}
                )

                assert response.status_code == 200
                mock_find_models.assert_called_once()
                result = response.json()
                assert isinstance(result, list)
                assert len(result) == 2
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


class TestDeleteModelsAPI:
    """Test cases for the DELETE /api/models endpoint with query parameters."""

    async def test_delete_models_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that model deletion requires authentication."""
        response = await no_auth_client.delete(
            "/api/models", params={"profile": "test"}
        )

        # Should require authentication
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_delete_models_no_parameters(self, client: AsyncTestClient):
        """Test deleting models without any query parameters."""
        response = await client.delete("/api/models")

        # Should return validation error
        assert response.status_code == 400

    async def test_delete_models_by_profile(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test deleting models by profile."""
        # Create test models
        model1 = {
            "id": f"{uuid4()}",
            "repo": "test/model1",
            "profile": "delete-test-profile",
            "revision": "v1",
            "image": "test-image",
            "model_dir": "/test/path1",
        }
        model2 = {
            "id": f"{uuid4()}",
            "repo": "test/model2",
            "profile": "delete-test-profile",
            "revision": "v1",
            "image": "test-image",
            "model_dir": "/test/path2",
        }

        await client.post("/api/models", json=model1)
        await client.post("/api/models", json=model2)

        # Delete by profile
        response = await client.delete(
            "/api/models", params={"profile": "delete-test-profile"}
        )

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) == 2
        for item in result:
            assert item["status"] == "ok"

    async def test_delete_models_by_repo_id(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test deleting models by repo_id."""
        # Create test models
        model1 = {
            "id": f"{uuid4()}",
            "repo": "unique/test-repo",
            "profile": "profile1",
            "revision": "v1",
            "image": "test-image",
            "model_dir": "/test/path1",
        }
        model2 = {
            "id": f"{uuid4()}",
            "repo": "unique/test-repo",
            "profile": "profile2",
            "revision": "v2",
            "image": "test-image",
            "model_dir": "/test/path2",
        }

        await client.post("/api/models", json=model1)
        await client.post("/api/models", json=model2)

        # Delete by repo_id
        response = await client.delete(
            "/api/models", params={"repo_id": "unique/test-repo"}
        )

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) == 2
        for item in result:
            assert item["status"] == "ok"

    async def test_delete_models_by_revision(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test deleting models by revision."""
        # Create test models
        model1 = {
            "id": f"{uuid4()}",
            "repo": "test/model1",
            "profile": "profile1",
            "revision": "unique-revision-123",
            "image": "test-image",
            "model_dir": "/test/path1",
        }

        await client.post("/api/models", json=model1)

        # Delete by revision
        response = await client.delete(
            "/api/models", params={"revision": "unique-revision-123"}
        )

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["status"] == "ok"

    async def test_delete_models_by_multiple_params(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test deleting models by multiple query parameters."""
        # Create test models
        model1 = {
            "id": f"{uuid4()}",
            "repo": "multi/test-repo",
            "profile": "multi-profile",
            "revision": "multi-v1",
            "image": "test-image",
            "model_dir": "/test/path1",
        }
        model2 = {
            "id": f"{uuid4()}",
            "repo": "multi/test-repo",
            "profile": "multi-profile",
            "revision": "multi-v2",
            "image": "test-image",
            "model_dir": "/test/path2",
        }

        await client.post("/api/models", json=model1)
        await client.post("/api/models", json=model2)

        # Delete by repo_id and profile
        response = await client.delete(
            "/api/models",
            params={"repo_id": "multi/test-repo", "profile": "multi-profile"},
        )

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) == 2

    async def test_delete_models_nonexistent(self, client: AsyncTestClient):
        """Test deleting models that don't exist."""
        response = await client.delete(
            "/api/models", params={"profile": "nonexistent-profile"}
        )

        assert response.status_code == 200
        result = response.json()
        # Should return empty list
        assert result == []

    async def test_delete_models_specific_combination(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test deleting models by specific combination of repo_id, profile, and revision."""
        # Create test models
        model1 = {
            "id": f"{uuid4()}",
            "repo": "specific/repo",
            "profile": "specific-profile",
            "revision": "specific-v1",
            "image": "test-image",
            "model_dir": "/test/path1",
        }
        model2 = {
            "id": f"{uuid4()}",
            "repo": "specific/repo",
            "profile": "specific-profile",
            "revision": "specific-v2",
            "image": "test-image",
            "model_dir": "/test/path2",
        }

        await client.post("/api/models", json=model1)
        await client.post("/api/models", json=model2)

        # Delete only one specific model
        response = await client.delete(
            "/api/models",
            params={
                "repo_id": "specific/repo",
                "profile": "specific-profile",
                "revision": "specific-v1",
            },
        )

        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["status"] == "ok"

        # Verify the other model still exists
        get_response = await client.get(
            "/api/models", params={"profile": "specific-profile"}
        )
        remaining_models = get_response.json()
        assert len(remaining_models) == 1
        assert remaining_models[0]["revision"] == "specific-v2"
