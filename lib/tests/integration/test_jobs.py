import pytest

from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_jobs_no_auth(no_auth_client: AsyncClient) -> None:
    response = await no_auth_client.get("/api/jobs")
    assert response.status_code == 401, (
        "Jobs should return 401 Unauthorized when no auth token is provided"
    )

    response = await no_auth_client.get(
        "/api/jobs/2a7a8e62-40cc-4240-a825-463e5b11a81f"
    )
    assert response.status_code == 401, (
        "Jobs should return 401 Unauthorized when no auth token is provided"
    )

    response = await no_auth_client.post(
        "/api/jobs",
        json={
            "name": "test-job",
            "pipeline": "speech_recognition",
            "repo_id": "openai/whisper-large-v3",
            "profile": {
                "name": "test",
                "home_dir": "/home/test/.blackfish",
                "cache_dir": "/home/test/.blackfish",
            },
            "job_config": {
                "gres": 0,
            },
            "container_config": {
                "model_dir": "/home/test/.blackfish/models/models--openai/whisper-large-v3",
                "revision": "1",
                "kwargs": ["--language", "en"],
            },
            "mount": "/home/test",
        },
    )
    assert response.status_code == 401, (
        "Jobs should return 401 Unauthorized when no auth token is provided"
    )

    response = await no_auth_client.put(
        "/api/jobs/2a7a8e62-40cc-4240-a825-463e5b11a81f/stop"
    )
    assert response.status_code == 401, (
        "Jobs should return 401 Unauthorized when no auth token is provided"
    )

    response = await no_auth_client.delete(
        "/api/jobs?id=2a7a8e62-40cc-4240-a825-463e5b11a81f"
    )
    assert response.status_code == 401, (
        "Jobs should return 401 Unauthorized when no auth token is provided"
    )


async def test_jobs_create(client: AsyncClient) -> None:
    # response = await client.post(
    #     "/api/jobs",
    #     json={
    #         "name": "test-job",
    #         "pipeline": "speech_recognition",
    #         "repo_id": "openai/whisper-large-v3",
    #         "profile": {
    #             "name": "test",
    #             "home_dir": "/home/test/.blackfish",
    #             "cache_dir": "/home/test/.blackfish",
    #         },
    #         "job_config": {
    #             "gres": 0,
    #         },
    #         "container_config": {
    #             "model_dir": "/home/test/.blackfish/models/models--openai/whisper-large-v3",
    #             "revision": "1",
    #             "kwargs": ["--language", "en"],
    #         },
    #         "mount": "/home/test",
    #     },
    # )
    # assert (
    #     response.status_code == 201
    # ), "Jobs should return 201 Created for valid requests"

    response = await client.post(
        "/api/jobs",
        json={
            "name": "test-job",
            "pipeline": "speech_recognition",
            "repo_id": "openai/whisper-large-v3",
            "profile": {
                "name": "test",
                "home_dir": "/home/test/.blackfish",
                "cache_dir": "/home/test/.blackfish",
            },
            # Missing job_config!
            "container_config": {
                "model_dir": "/home/test/.blackfish/models/models--openai/whisper-large-v3",
                "revision": "1",
                "kwargs": ["--language", "en"],
            },
            # Missing mount!
        },
    )
    assert response.status_code == 400, (
        "Jobs should return 400 Bad Request for malformed requests"
    )


# async def test_jobs_list(client: AsyncClient) -> None:

#     response = await client.get("/api/jobs")
#     assert response.status_code == 200, "Jobs should return 200 OK for valid requests"
#     assert len(response.json()) > 0, "Jobs should return a non-empty list of jobs"

#     response = await client.get("/api/jobs?id=2a7a8e62-40cc-4240-a825-463e5b11a81f")
#     assert (
#         response.status_code == 200
#     ), "Jobs should return 200 OK for valid requests with query parameters"
#     assert len(response.json()) == 1, "Jobs should return a list of length one"

#     response = await client.get("/api/jobs?pipeline=does-not-exist")
#     assert (
#         response.status_code == 200
#     ), "Jobs should return 200 OK for valid requests with query parameters"
#     assert len(response.json()) == 0, "Jobs should return a list of length zero"


# async def test_jobs_get(client: AsyncClient) -> None:

#     response = await client.get("/api/jobs/2a7a8e62-40cc-4240-a825-463e5b11a81f")
#     assert response.status_code == 200, "Jobs should return 200 OK for existing job ID"

#     response = await client.get("/api/jobs/99999999-9999-9999-9999-999999999999")
#     assert (
#         response.status_code == 404
#     ), "Jobs should return 404 Not Found for non-existent job ID"


# async def test_jobs_stop(client: AsyncClient) -> None:

#     response = await client.post("/api/jobs/2a7a8e62-40cc-4240-a825-463e5b11a81f/stop")
#     assert (
#         response.status_code == 200
#     ), "Jobs should return 200 OK when job is successfully stopped"

#     response = await client.post("/api/jobs/99999999-9999-9999-9999-999999999999/stop")
#     assert (
#         response.status_code == 404
#     ), "Jobs should return 404 Not Found for non-existent job ID"


# async def test_delete_job(client: AsyncClient) -> None:
#     response = await client.delete("/api/jobs?name=blackfish-1")
#     assert (
#         response.status_code == 200
#     ), "Jobs should return 200 OK when a job is successfully deleted"
#     assert len(response.json()) == 1, "Jobs should return the deleted job"

#     response = await client.delete("/api/jobs?pipeline=speech_recognition")
#     assert (
#         response.status_code == 200
#     ), "Jobs should return 200 OK when a job is successfully deleted"
#     assert len(response.json()) == 2, "Jobs should return a list of deleted jobs"
