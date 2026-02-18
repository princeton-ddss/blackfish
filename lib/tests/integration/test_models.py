import pytest

from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_models_no_auth(no_auth_client: AsyncClient) -> None:
    response = await no_auth_client.get("/api/models")
    assert response.status_code == 401

    response = await no_auth_client.get(
        "/api/models/cc64bbef-816c-4070-941d-3dabece7a3b9"
    )
    assert response.status_code == 401

    response = await no_auth_client.post(
        "/api/models",
        json={
            "repo": "test/model",
            "profile": "default",
            "revision": "main",
            "image": "text-generation",
            "model_dir": "/tmp/test",
        },
    )
    assert response.status_code == 401

    response = await no_auth_client.delete(
        "/api/models/cc64bbef-816c-4070-941d-3dabece7a3b9"
    )
    assert response.status_code == 401


async def test_models_list(client: AsyncClient) -> None:
    response = await client.get("/api/models")
    assert response.status_code == 200
    assert len(response.json()) == 5

    response = await client.get("/api/models?image=speech_recognition")
    assert response.status_code == 200
    assert len(response.json()) == 2

    # response = await client.get("/api/models?refresh=true")
    # assert response.status_code == 200
    # assert len(response.json()) == 4

    # response = await client.get("/api/models?image=speech_recognition&refresh=true")
    # assert response.status_code == 200
    # assert len(response.json()) == 2

    response = await client.get("/api/models?profile=does-not-exist")
    assert response.status_code == 200
    assert len(response.json()) == 0

    response = await client.get("/api/models?profile=default")
    assert response.status_code == 200
    assert len(response.json()) == 3


async def test_models_get(client: AsyncClient) -> None:
    response = await client.get("/api/models/cc64bbef-816c-4070-941d-3dabece7a3b9")
    assert response.status_code == 200

    response = await client.get("/api/models/99999999-9999-9999-9999-999999999999")
    assert response.status_code == 404


async def test_create_model(client: AsyncClient) -> None:
    response = await client.post(
        "/api/models",
        json={
            "repo": "new-org/new-model",
            "profile": "default",
            "revision": "v1.0",
            "image": "text-generation",
            "model_dir": "/tmp/models/new-org--new-model",
        },
    )
    assert response.status_code == 201
    result = response.json()
    assert result["repo"] == "new-org/new-model"
    assert "id" in result


async def test_delete_model(client: AsyncClient) -> None:
    response = await client.delete("/api/models/cc64bbef-816c-4070-941d-3dabece7a3b9")
    assert response.status_code == 204
