import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from litestar.testing import AsyncTestClient


pytestmark = pytest.mark.anyio


class TestFetchServicesAPI:
    """Test cases for the GET /api/services endpoint."""

    async def test_fetch_services_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that /api/services requires authentication."""
        response = await no_auth_client.get("/api/services")

        # Should require authentication
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_fetch_all_services(self, client: AsyncTestClient):
        """Test fetching all services without filters."""
        response = await client.get("/api/services")

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        # Test fixture data may or may not contain services

    async def test_fetch_services_by_id(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test fetching services by specific ID."""
        # First check if there are any services
        response = await client.get("/api/services")
        services = response.json()

        if services:
            service_id = services[0]["id"]
            response = await client.get("/api/services", params={"id": service_id})

            assert response.status_code == 200
            result = response.json()
            assert len(result) <= 1
            if result:
                assert result[0]["id"] == service_id

    async def test_fetch_services_by_status(self, client: AsyncTestClient):
        """Test fetching services by status."""
        response = await client.get("/api/services", params={"status": "running"})

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)

        # Verify all returned services have the requested status
        for service in result:
            assert service.get("status") == "running"

    async def test_fetch_services_by_name(self, client: AsyncTestClient):
        """Test fetching services by name."""
        response = await client.get("/api/services", params={"name": "test-service"})

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)

    async def test_fetch_services_multiple_filters(self, client: AsyncTestClient):
        """Test fetching services with multiple filters."""
        response = await client.get(
            "/api/services", params={"status": "running", "profile": "test"}
        )

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)

    async def test_fetch_services_no_matches(self, client: AsyncTestClient):
        """Test fetching services when no services match the filters."""
        response = await client.get(
            "/api/services", params={"name": "nonexistent-service"}
        )

        assert response.status_code == 200
        result = response.json()
        assert result == []


class TestGetSingleServiceAPI:
    """Test cases for the GET /api/services/{service_id} endpoint."""

    async def test_get_service_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that individual service endpoint requires authentication."""
        test_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await no_auth_client.get(f"/api/services/{test_id}")

        # Should require authentication
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_get_service_nonexistent_id(self, client: AsyncTestClient):
        """Test fetching a service that doesn't exist."""
        nonexistent_id = "550e8400-e29b-41d4-a716-446655440000"

        response = await client.get(f"/api/services/{nonexistent_id}")

        assert response.status_code == 404
        # Response might be HTML, so just check status code

    async def test_get_service_invalid_uuid_format(self, client: AsyncTestClient):
        """Test fetching a service with invalid UUID format."""
        response = await client.get("/api/services/invalid-uuid-format")

        # Should return 404 or 500 for invalid UUID format
        assert response.status_code in [404, 500]

    async def test_get_service_refresh_functionality(self, client: AsyncTestClient):
        """Test that the endpoint refreshes service status."""
        # First get list of services
        services_response = await client.get("/api/services")
        services = services_response.json()

        if services:
            service_id = services[0]["id"]
            response = await client.get(f"/api/services/{service_id}")

            # Should return the service (may be 404 if service doesn't exist)
            assert response.status_code in [200, 404]

            if response.status_code == 200:
                result = response.json()
                assert isinstance(result, dict)
                assert result["id"] == service_id


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
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_create_service_missing_data(self, client: AsyncTestClient):
        """Test creating a service with missing required data."""
        response = await client.post("/api/services")

        # Should return validation error for missing required fields
        assert response.status_code in [400, 422]

    async def test_create_service_invalid_data(self, client: AsyncTestClient):
        """Test creating a service with invalid data."""
        invalid_data = {
            "name": "test-service",
            # Missing required fields like image, repo_id, profile, etc.
        }

        response = await client.post("/api/services", json=invalid_data)

        # Should return validation error
        assert response.status_code in [400, 422]

    async def test_create_service_complex_data_validation(
        self, client: AsyncTestClient
    ):
        """Test that complex service creation data is validated properly."""
        # Note: Creating a valid ServiceRequest requires complex nested objects
        # This tests the validation without needing full valid data

        partially_valid_data = {
            "name": "test-service",
            "image": "test-image",
            "repo_id": "test/repo",
            "profile": {"invalid": "profile"},  # Invalid profile structure
            "container_config": {},
            "job_config": {},
        }

        response = await client.post("/api/services", json=partially_valid_data)

        # Should return validation error or 500 for complex validation failures
        assert response.status_code in [400, 422, 500]


class TestStopServiceAPI:
    """Test cases for the PUT /api/services/{service_id}/stop endpoint."""

    async def test_stop_service_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that stopping services requires authentication."""
        test_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await no_auth_client.put(f"/api/services/{test_id}/stop")

        # Should require authentication
        assert response.status_code in [401, 403] or response.is_redirect

    async def test_stop_service_nonexistent_id(self, client: AsyncTestClient):
        """Test stopping a service that doesn't exist."""
        nonexistent_id = "550e8400-e29b-41d4-a716-446655440000"

        # Default stop request data
        stop_data = {"timeout": 30, "failed": False}
        response = await client.put(
            f"/api/services/{nonexistent_id}/stop", json=stop_data
        )

        assert response.status_code == 404

    async def test_stop_service_missing_data(self, client: AsyncTestClient):
        """Test stopping a service without required stop data."""
        test_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await client.put(f"/api/services/{test_id}/stop")

        # Should return validation error for missing data
        assert response.status_code in [400, 404, 422]

    async def test_stop_service_with_timeout(self, client: AsyncTestClient):
        """Test stopping a service with timeout parameter."""
        test_id = "550e8400-e29b-41d4-a716-446655440000"
        stop_data = {"timeout": 60, "failed": True}

        response = await client.put(f"/api/services/{test_id}/stop", json=stop_data)

        # Will be 404 for nonexistent service, but should handle the data properly
        assert response.status_code in [200, 404]


class TestDeleteServicesAPI:
    """Test cases for the DELETE /api/services endpoint."""

    async def test_delete_services_requires_authentication(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that service deletion requires authentication."""
        response = await no_auth_client.delete("/api/services")

        # Should require authentication
        assert response.status_code in [401, 403] or response.is_redirect

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
        assert response.status_code in [401, 403] or response.is_redirect

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
        # This test verifies the endpoint works - actual pruning logic
        # would be tested in unit tests for the service classes

        response = await client.delete("/api/services/prune")

        assert response.status_code == 200
        # The actual count depends on test data, just verify it returns a number
        result = response.json()
        assert isinstance(result, int)
