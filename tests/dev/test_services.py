import pytest

from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_services_no_auth(no_auth_client: AsyncClient) -> None:
    response = await no_auth_client.get("/api/services")
    assert response.status_code == 401, (
        "Services should return 401 Unauthorized when no auth token is provided"
    )

    response = await no_auth_client.get(
        "/api/services/4c2216ea-df22-4bf6-bcea-56964df12af5"
    )
    assert response.status_code == 401, (
        "Services should return 401 Unauthorized when no auth token is provided"
    )

    response = await no_auth_client.post(
        "/api/services",
        json={
            "name": "test-service",
            "image": "speech_recognition",
            "repo_id": "openai/whisper-large-v3",
            "profile": {
                "name": "test",
                "home_dir": "/home/test/.blackfish",
                "cache_dir": "/home/test/.blackfish",
            },
            "container_config": {
                "model_dir": "/home/test/.blackfish/models/models--openai/whisper-large-v3",
                "revision": "1",
            },
            "job_config": {
                "gres": 0,
            },
            "mount": "/home/test",
            "grace_period": 180,
        },
    )
    assert response.status_code == 401, (
        "Services should return 401 Unauthorized when no auth token is provided"
    )

    response = await no_auth_client.put(
        "/api/services/4c2216ea-df22-4bf6-bcea-56964df12af5/stop"
    )
    assert response.status_code == 401, (
        "Services should return 401 Unauthorized when no auth token is provided"
    )

    response = await no_auth_client.delete(
        "/api/services/4c2216ea-df22-4bf6-bcea-56964df12af5"
    )
    assert response.status_code == 401, (
        "Services should return 401 Unauthorized when no auth token is provided"
    )


async def test_services_list(client: AsyncClient) -> None:
    response = await client.get("/api/services")
    assert response.status_code == 200, (
        "Services should return 200 OK when authenticated"
    )
    assert len(response.json()) > 0, (
        "Response should be a list of services with non-zero length"
    )

    response = await client.get("/api/services?name=blackfish-1")
    assert response.status_code == 200, (
        "Services should return 200 OK when authenticated"
    )
    assert len(response.json()) == 1, (
        "Response should be a list of services of length one"
    )


async def test_services_get(client: AsyncClient) -> None:
    response = await client.get("/api/services/4c2216ea-df22-4bf6-bcea-56964df12af5")
    assert response.status_code == 200, (
        "Services should return 200 OK when authenticated"
    )

    response = await client.get("/api/services/99999999-9999-9999-9999-999999999999")
    assert response.status_code == 404, (
        "Services should return 404 Not Found for non-existent service ID"
    )


async def test_services_create(client: AsyncClient) -> None:
    response = await client.post(
        "/api/services",
        json={
            "name": "test-service",
            "image": "speech_recognition",
            "repo_id": "openai/whisper-large-v3",
            "profile": {
                "name": "test",
                "home_dir": "/home/test/.blackfish",
                "cache_dir": "/home/test/.blackfish",
            },
            "container_config": {
                "model_dir": "/home/test/.blackfish/models/models--openai/whisper-large-v3",
                "revision": "1",
            },
            "job_config": {
                "gres": 0,
            },
            "mount": "/home/test",
            "grace_period": 180,
        },
    )
    assert response.status_code == 201, (
        "Services should return 201 Created when service is successfully created"
    )

    response = await client.post(
        "/api/services",
        json={
            "name": "test-service",
            "image": "speech_recognition",
            "repo_id": "openai/whisper-large-v3",
            # Missing profile!
            "container_config": {
                "model_dir": "/home/test/.blackfish/models/models--openai/whisper-large-v3",
                "revision": "1",
            },
            # Missing job_config!
            "mount": "/home/test",
            "grace_period": 180,
        },
    )
    assert response.status_code == 400, (
        "Services should return 400 Bad Request for malformed request"
    )


async def test_services_stop(client: AsyncClient) -> None:
    response = await client.put(
        "/api/services/4c2216ea-df22-4bf6-bcea-56964df12af5/stop"
    )
    assert response.status_code == 200, (
        "Services should return 200 OK when service is stopped successfully"
    )

    response = await client.put(
        "/api/services/99999999-9999-9999-9999-999999999999/stop"
    )
    assert response.status_code == 404, (
        "Services should return 404 Not Found for non-existent service ID"
    )


async def test_services_delete(
    client: AsyncClient, auth_header: dict[str, str]
) -> None:
    response = await client.delete("/api/services/4c2216ea-df22-4bf6-bcea-56964df12af5")
    assert response.status_code == 204, (
        "Services should return 204 No Content when service is deleted successfully"
    )

    response = await client.delete("/api/services/99999999-9999-9999-9999-999999999999")
    assert response.status_code == 404, (
        "Services should return 404 Not Found for non-existent service ID"
    )
