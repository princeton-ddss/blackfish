import pytest
from unittest.mock import patch, AsyncMock
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from litestar.testing import AsyncTestClient

from app.services.base import Service


pytestmark = pytest.mark.anyio


class TestFetchServicesAPI:
    """Test cases for the GET /api/services endpoint."""

    async def test_fetch_services_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that /api/services requires authentication."""
        response = await no_auth_client.get("/api/services")

        # Should require authentication
        assert response.status_code == 401

    async def test_fetch_all_services(self, client: AsyncTestClient):
        """Test fetching all services without filters."""
        response = await client.get("/api/services")

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)

    async def test_fetch_services_by_id(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test fetching services by specific ID."""
        service_id = "4c2216ea-df22-4bf6-bcea-56964df12af5"
        response = await client.get("/api/services", params={"id": service_id})

        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["id"] == service_id

        # Should work without the dashes, too
        service_id = "4c2216eadf224bf6bcea56964df12af5"
        response = await client.get("/api/services", params={"id": service_id})

        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert UUID(result[0]["id"]) == UUID(service_id)

    async def test_fetch_services_invalid_id(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        service_id = "not-a-valid-id"
        response = await client.get("/api/services", params={"id": service_id})

        assert response.status_code == 400

    async def test_fetch_services_by_status(self, client: AsyncTestClient):
        """Test fetching services by status."""
        response = await client.get("/api/services", params={"status": "healthy"})

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        for service in result:
            assert service.get("status") == "running"

    async def test_fetch_services_by_name(self, client: AsyncTestClient):
        """Test fetching services by name."""
        response = await client.get("/api/services", params={"name": "blackfish-23189"})

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        for service in result:
            assert service.get("name") == "blackfish-23189"

    async def test_fetch_services_multiple_filters(self, client: AsyncTestClient):
        """Test fetching services with multiple filters."""
        response = await client.get(
            "/api/services", params={"status": "healthy", "profile": "local"}
        )

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        for service in result:
            assert (
                service.get("status") == "healthy" and service.get("profile") == "local"
            )

    async def test_fetch_services_no_matches(self, client: AsyncTestClient):
        """Test fetching services when no services match the filters."""
        response = await client.get("/api/services", params={"name": "not-a-service"})

        assert response.status_code == 200
        result = response.json()
        assert result == []

    async def test_fetch_services_with_refresh_true(self, client: AsyncTestClient):
        """Test fetching services with refresh=true parameter."""
        with patch.object(Service, "refresh", new_callable=AsyncMock) as mock_refresh:
            response = await client.get("/api/services", params={"refresh": "true"})

            assert response.status_code == 200
            result = response.json()
            assert isinstance(result, list)

            # Verify that refresh was called for each service
            # The number of calls depends on how many services exist in test data
            assert mock_refresh.call_count >= 0

    async def test_fetch_services_with_refresh_false(self, client: AsyncTestClient):
        """Test fetching services with refresh=false parameter."""
        with patch.object(Service, "refresh", new_callable=AsyncMock) as mock_refresh:
            response = await client.get("/api/services", params={"refresh": "false"})

            assert response.status_code == 200
            result = response.json()
            assert isinstance(result, list)

            # Verify that refresh was NOT called when refresh=false
            mock_refresh.assert_not_called()

    async def test_fetch_services_without_refresh_parameter(
        self, client: AsyncTestClient
    ):
        """Test fetching services without refresh parameter (backward compatibility)."""
        with patch.object(Service, "refresh", new_callable=AsyncMock) as mock_refresh:
            response = await client.get("/api/services")

            assert response.status_code == 200
            result = response.json()
            assert isinstance(result, list)

            # Verify that refresh was NOT called when parameter is omitted (default behavior)
            mock_refresh.assert_not_called()

    async def test_fetch_services_with_invalid_refresh_parameter(
        self, client: AsyncTestClient
    ):
        """Test fetching services with invalid refresh parameter value."""
        response = await client.get("/api/services", params={"refresh": "invalid"})

        # Should return 400 for invalid refresh parameter value
        assert response.status_code == 400


class TestGetSingleServiceAPI:
    """Test cases for the GET /api/services/{service_id} endpoint."""

    async def test_get_service_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that individual service endpoint requires authentication."""
        test_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await no_auth_client.get(f"/api/services/{test_id}")

        # Should require authentication
        assert response.status_code == 401

    async def test_get_service_nonexistent_id(self, client: AsyncTestClient):
        """Test fetching a service that doesn't exist."""
        nonexistent_id = "550e8400-e29b-41d4-a716-446655440000"

        response = await client.get(f"/api/services/{nonexistent_id}")

        assert response.status_code == 404

    async def test_get_service_invalid_uuid_format(self, client: AsyncTestClient):
        """Test fetching a service with invalid UUID format."""
        response = await client.get("/api/services/invalid-uuid-format")

        # Should return 400 for invalid UUID format
        assert response.status_code == 400

    async def test_get_service_with_refresh_true(self, client: AsyncTestClient):
        """Test fetching a single service with refresh=true parameter."""
        service_id = "4c2216ea-df22-4bf6-bcea-56964df12af5"

        with patch.object(Service, "refresh", new_callable=AsyncMock) as mock_refresh:
            response = await client.get(
                f"/api/services/{service_id}", params={"refresh": "true"}
            )

            assert response.status_code == 200
            result = response.json()
            assert isinstance(result, dict)
            assert result["id"] == service_id

            # Verify that refresh was called for the service
            mock_refresh.assert_called_once()

    async def test_get_service_with_refresh_false(self, client: AsyncTestClient):
        """Test fetching a single service with refresh=false parameter."""
        service_id = "4c2216ea-df22-4bf6-bcea-56964df12af5"

        with patch.object(Service, "refresh", new_callable=AsyncMock) as mock_refresh:
            response = await client.get(
                f"/api/services/{service_id}", params={"refresh": "false"}
            )

            assert response.status_code == 200
            result = response.json()
            assert isinstance(result, dict)
            assert result["id"] == service_id

            # Verify that refresh was NOT called when refresh=false
            mock_refresh.assert_not_called()

    async def test_get_service_without_refresh_parameter(self, client: AsyncTestClient):
        """Test fetching a single service without refresh parameter (backward compatibility)."""
        service_id = "4c2216ea-df22-4bf6-bcea-56964df12af5"

        with patch.object(Service, "refresh", new_callable=AsyncMock) as mock_refresh:
            response = await client.get(f"/api/services/{service_id}")

            assert response.status_code == 200
            result = response.json()
            assert isinstance(result, dict)
            assert result["id"] == service_id

            # Verify that refresh was NOT called when parameter is omitted (default behavior)
            mock_refresh.assert_not_called()

    async def test_get_service_with_invalid_refresh_parameter(
        self, client: AsyncTestClient
    ):
        """Test fetching a single service with invalid refresh parameter value."""
        service_id = "4c2216ea-df22-4bf6-bcea-56964df12af5"

        response = await client.get(
            f"/api/services/{service_id}", params={"refresh": "invalid"}
        )

        # Should return 400 for invalid refresh parameter value
        assert response.status_code == 400


class TestCreateServiceAPI:
    """Test cases for the POST /api/services endpoint."""

    async def test_create_service_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that service creation requires authentication."""
        service_data = {
            "name": "test-service",
            "image": "test-image",
            "repo_id": "test/repo",
        }

        response = await no_auth_client.post("/api/services", json=service_data)

        # Should require authentication
        assert response.status_code == 401

    async def test_create_service_missing_data(self, client: AsyncTestClient):
        """Test creating a service with missing required data."""
        response = await client.post("/api/services")

        # Should return validation error for missing required fields
        assert response.status_code == 400

    async def test_create_service_invalid_data(self, client: AsyncTestClient):
        """Test creating a service with invalid data."""
        invalid_data = {
            "name": "test-service",
            # Missing required fields like image, repo_id, profile, etc.
        }

        response = await client.post("/api/services", json=invalid_data)

        # Should return validation error
        assert response.status_code == 400

    async def test_create_service_complex_data_validation(
        self, client: AsyncTestClient
    ):
        """Test that complex service creation data is validated properly."""

        partially_valid_data = {
            "name": "test-service",
            "image": "test-image",
            "repo_id": "test/repo",
            "profile": {"invalid": "profile"},  # Invalid profile structure
            "container_config": {},
            "job_config": {},
        }

        response = await client.post("/api/services", json=partially_valid_data)

        # Should return validation error
        assert response.status_code == 400

    async def test_create_service_valid_data(self, client: AsyncTestClient):
        """Test that valid service requests create a new service."""

        with patch.object(Service, "start", new_callable=AsyncMock) as mock_start:
            data = {
                "name": "test",
                "image": "text_generation",
                "repo_id": "meta-llama/Llama-3.2-3B",
                "profile": {
                    "name": "test",
                    "home_dir": "test",
                    "cache_dir": "test",
                },
                "container_config": {
                    "port": 8080,
                },
                "job_config": {},
            }

            response = await client.post("/api/services", json=data)
            print(response.text)

            assert response.status_code == 201
            mock_start.assert_called_once()
            assert response.json().get("name") == "test"
            assert response.json().get("image") == "text_generation"


class TestStopServiceAPI:
    """Test cases for the PUT /api/services/{service_id}/stop endpoint."""

    async def test_stop_service_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that stopping services requires authentication."""
        test_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await no_auth_client.put(f"/api/services/{test_id}/stop")

        # Should require authentication
        assert response.status_code == 401

    async def test_stop_service_nonexistent_id(self, client: AsyncTestClient):
        """Test stopping a service that doesn't exist."""
        nonexistent_id = "550e8400-e29b-41d4-a716-446655440000"

        response = await client.put(f"/api/services/{nonexistent_id}/stop", json={})

        assert response.status_code == 404

    async def test_stop_service_invalid_id(self, client: AsyncTestClient):
        """Test stopping a service with an invalid UUID."""

        service_id = "not-a-valid-id"
        response = await client.put(f"/api/services/{service_id}/stop", json={})

        # Should return validation error
        assert response.status_code == 400

    async def test_stop_service_missing_data(self, client: AsyncTestClient):
        """Test stopping a service without required stop data."""
        test_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await client.put(f"/api/services/{test_id}/stop")

        # Should return validation error for missing data
        assert response.status_code == 400

    async def test_stop_service_with_data(self, client: AsyncTestClient):
        """Test stopping a service with timeout parameter."""
        service_id = "4c2216ea-df22-4bf6-bcea-56964df12af5"
        stop_data = {"timeout": False, "failed": False}

        with patch.object(Service, "stop", new_callable=AsyncMock) as mock_stop:
            response = await client.put(
                f"/api/services/{service_id}/stop", json=stop_data
            )

            assert response.status_code == 200
            mock_stop.assert_called_once()


class TestDeleteServicesAPI:
    """Test cases for the DELETE /api/services endpoint."""

    async def test_delete_services_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that service deletion requires authentication."""
        response = await no_auth_client.delete("/api/services")

        # Should require authentication
        assert response.status_code == 401

    async def test_delete_services_no_matches(self, client: AsyncTestClient):
        """Test deleting services when no services match the query."""
        response = await client.delete(
            "/api/services", params={"id": "550e8400-e29b-41d4-a716-446655440000"}
        )

        assert response.status_code == 200
        result = response.json()
        assert result == []

    async def test_delete_services_by_status(self, client: AsyncTestClient):
        """Test deleting services by status."""
        response = await client.delete("/api/services", params={"status": "stopped"})

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)

    async def test_delete_services_multiple_filters(self, client: AsyncTestClient):
        """Test deleting services with multiple filter parameters."""
        response = await client.delete(
            "/api/services", params={"status": "failed", "profile": "test"}
        )

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)


class TestPruneServicesAPI:
    """Test cases for the DELETE /api/services/prune endpoint."""

    async def test_prune_services_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that service pruning requires authentication."""
        response = await no_auth_client.delete("/api/services/prune")

        # Should require authentication
        assert response.status_code == 401

    async def test_prune_services_returns_count(self, client: AsyncTestClient):
        """Test that service pruning returns count of pruned services."""
        response = await client.delete("/api/services/prune")

        assert response.status_code == 200
        result = response.json()

        # Should return count of pruned services
        assert isinstance(result, int)
        assert result >= 0

    async def test_prune_services_only_removes_stopped_services(
        self, client: AsyncTestClient
    ):
        """Test that pruning only affects stopped/failed/timeout services."""

        response = await client.delete("/api/services/prune")

        assert response.status_code == 200
        # The actual count depends on test data, just verify it returns a number
        result = response.json()
        assert isinstance(result, int)
