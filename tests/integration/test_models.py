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
            "repo": "openai/whisper-small",
            "profile": "default",
            "revision": "1",
            "image": "speech_recognition",
            "model_dir": "/home/test/.blackfish/models/models--openai/whisper-small",
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
    assert len(response.json()) == 4

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
    assert len(response.json()) == 4


async def test_models_get(client: AsyncClient) -> None:
    response = await client.get("/api/models/cc64bbef-816c-4070-941d-3dabece7a3b9")
    assert response.status_code == 200

    response = await client.get("/api/models/99999999-9999-9999-9999-999999999999")
    assert response.status_code == 404


async def test_models_create(client: AsyncClient) -> None:
    response = await client.post(
        "/api/models",
        json={
            "repo": "openai/whisper-small",
            "profile": "default",
            "revision": "1",
            "image": "speech_recognition",
            "model_dir": "/home/test/.blackfish/models/models--openai/whisper-small",
        },
    )
    assert response.status_code == 201

    response = await client.post(
        "/api/models",
        json={
            "repo": "openai/whisper-small",
            "profile": "default",
            "revision": "1",
        },
    )
    assert response.status_code == 400


async def test_delete_model(client: AsyncClient) -> None:
    response = await client.delete("/api/models/cc64bbef-816c-4070-941d-3dabece7a3b9")
    assert response.status_code == 204
