import pytest
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from litestar.testing import AsyncTestClient
from unittest.mock import patch, AsyncMock

from blackfish.server.jobs.base import BatchJob, BatchJobStatus

pytestmark = pytest.mark.anyio


class TestDeleteBatchJobsAPI:
    """Test cases for the DELETE /api/jobs endpoint."""

    async def test_delete_jobs_no_matches(self, client: AsyncTestClient):
        """Test deleting batch jobs when no jobs match the query."""
        # Use a valid UUID format that doesn't exist in test data
        response = await client.delete(
            "/api/jobs", params={"id": "550e8400-e29b-41d4-a716-446655440000"}
        )

        # Should return success with empty result data
        assert response.status_code == 200
        assert response.json() == []

    async def test_delete_jobs_invalid_uuid_format(self, client: AsyncTestClient):
        """Test that invalid UUID format returns an error."""
        response = await client.delete(
            "/api/jobs", params={"id": "invalid-uuid-format"}
        )

        # Should return a bad request error due to invalid UUID format
        assert response.status_code == 400
        assert "Invalid query statement" in response.json()["detail"]

    async def test_delete_jobs_successful_deletion(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test successful deletion of completed batch jobs."""

        # Set one job to completed status
        completed_job_id = "2a7a8e62-40cc-4240-a825-463e5b11a81f"
        job = await session.get(BatchJob, UUID(completed_job_id))
        if job:
            job.status = BatchJobStatus.COMPLETED
            await session.commit()

        response = await client.delete("/api/jobs", params={"status": "completed"})

        # Should return success with single result indicating successful deletion of job
        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["job_id"] == completed_job_id.replace("-", "")

    async def test_delete_jobs_running_job_error(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test that running jobs cannot be deleted."""
        # Set one job to running status
        running_job_id = "391769fc-5a40-43db-bbfa-cec80a8c3710"
        job = await session.get(BatchJob, UUID(running_job_id))
        if job:
            job.status = BatchJobStatus.RUNNING
            await session.commit()

        response = await client.delete("/api/jobs", params={"id": running_job_id})

        # Should return success with a single result indicating unsuccessful job deletion
        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["message"] == "Batch job is still running"
        assert result[0]["job_id"] == running_job_id.replace("-", "")

    @pytest.mark.parametrize(
        "job_status",
        [
            BatchJobStatus.STOPPED,
            BatchJobStatus.TIMEOUT,
            BatchJobStatus.FAILED,
            BatchJobStatus.COMPLETED,
            None,
        ],
    )
    async def test_delete_jobs_deletable_statuses(
        self, client: AsyncTestClient, session: AsyncSession, job_status
    ):
        """Test that jobs with deletable statuses are successfully deleted."""
        # Set one job to the specified status
        test_job_id = "25058c41-9779-4b16-af6e-3fe5c3902435"
        job = await session.get(BatchJob, UUID(test_job_id))
        if job:
            job.status = job_status
            await session.commit()

        response = await client.delete("/api/jobs", params={"id": test_job_id})

        # Should return success with single result indicating successful deletion
        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["status"] == "ok"

    @pytest.mark.parametrize(
        "job_status",
        [
            BatchJobStatus.SUBMITTED,
            BatchJobStatus.PENDING,
            BatchJobStatus.RUNNING,
        ],
    )
    async def test_delete_jobs_non_deletable_statuses(
        self, client: AsyncTestClient, session: AsyncSession, job_status
    ):
        """Test that running jobs cannot be deleted."""
        # Set one job to the specified running status
        test_job_id = "2a7a8e62-40cc-4240-a825-463e5b11a81f"
        job = await session.get(BatchJob, UUID(test_job_id))
        if job:
            job.status = job_status
            await session.commit()

        response = await client.delete("/api/jobs", params={"id": test_job_id})

        # Should return success with single result indicating unsuccessful job deletion
        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["message"] == "Batch job is still running"

    async def test_delete_jobs_with_filters(
        self, client: AsyncTestClient, session: AsyncSession, jobs
    ):
        """Test deletion with multiple filter parameters."""
        # Set jobs to completed status
        for job_data in jobs[:2]:  # Set first 2 jobs to completed
            job = await session.get(BatchJob, UUID(job_data["data"]["id"]))
            if job:
                job.status = BatchJobStatus.COMPLETED

        await session.commit()

        response = await client.delete(
            "/api/jobs",
            params={
                "pipeline": "speech_recognition",
                "status": "completed",
                "profile": "test",
            },
        )

        # Should return success with two results, each indicating successful job deletion
        assert response.status_code == 200
        result = response.json()
        assert len(result) == 2
        for res in result:
            assert res["status"] == "ok"

    async def test_delete_jobs_mixed_success_error(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test deletion when some jobs succeed and others fail."""
        # Set different statuses for jobs
        completed_job_id = "2a7a8e62-40cc-4240-a825-463e5b11a81f"
        running_job_id = "391769fc-5a40-43db-bbfa-cec80a8c3710"

        completed_job = await session.get(BatchJob, UUID(completed_job_id))
        if completed_job:
            completed_job.status = BatchJobStatus.COMPLETED

        running_job = await session.get(BatchJob, UUID(running_job_id))
        if running_job:
            running_job.status = BatchJobStatus.RUNNING

        await session.commit()

        response = await client.delete("/api/jobs", params={"profile": "test"})

        assert response.status_code == 200
        result = response.json()
        assert len(result) == 2

        # Find the success and error responses
        success_result = next((r for r in result if r["status"] == "ok"), None)
        error_result = next((r for r in result if r["status"] == "error"), None)

        assert success_result is not None
        assert success_result["job_id"] == completed_job_id.replace("-", "")

        assert error_result is not None
        assert error_result["job_id"] == running_job_id.replace("-", "")
        assert error_result["message"] == "Batch job is still running"

    async def test_delete_jobs_authentication_required(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that authentication is required for the delete jobs endpoint."""
        response = await no_auth_client.delete("/api/jobs", params={"id": "test-id"})

        # Should return not authorized error
        assert response.status_code == 401

    async def test_delete_jobs_filters_validation(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test various filter combinations to ensure they work correctly."""
        # Set up jobs with known statuses
        job1_id = "2a7a8e62-40cc-4240-a825-463e5b11a81f"
        job2_id = "391769fc-5a40-43db-bbfa-cec80a8c3710"

        job1 = await session.get(BatchJob, UUID(job1_id))
        if job1:
            job1.status = BatchJobStatus.COMPLETED
            job1.pipeline = "speech_recognition"

        job2 = await session.get(BatchJob, UUID(job2_id))
        if job2:
            job2.status = BatchJobStatus.FAILED
            job2.pipeline = "speech_recognition"

        await session.commit()

        # Test filtering by pipeline only - all test fixture jobs have speech_recognition pipeline
        response = await client.delete(
            "/api/jobs", params={"pipeline": "speech_recognition"}
        )
        assert response.status_code == 200
        result = response.json()
        assert (
            len(result) == 3
        )  # All jobs should match (test fixtures have 3 jobs total)

        # Verify our specific jobs were processed
        job_ids = {r["job_id"] for r in result}
        assert job1_id.replace("-", "") in job_ids
        assert job2_id.replace("-", "") in job_ids


class TestGetBatchJobsAPI:
    """Test cases for the GET /api/jobs endpoint."""

    async def test_fetch_all_jobs(self, client: AsyncTestClient):
        """Test fetching all batch jobs without filters."""
        response = await client.get("/api/jobs")

        assert response.status_code == 200
        result = response.json()
        assert len(result) == 3  # Test fixtures have 3 jobs

    async def test_fetch_jobs_by_id(self, client: AsyncTestClient):
        """Test fetching jobs by specific ID."""
        job_id = "2a7a8e62-40cc-4240-a825-463e5b11a81f"

        response = await client.get("/api/jobs", params={"id": job_id})

        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["id"] == job_id

    async def test_fetch_jobs_by_pipeline(self, client: AsyncTestClient):
        """Test fetching jobs by pipeline."""
        response = await client.get(
            "/api/jobs", params={"pipeline": "speech_recognition"}
        )

        assert response.status_code == 200
        result = response.json()
        assert (
            len(result) == 3
        )  # All test fixture jobs have speech_recognition pipeline

        for job in result:
            assert job["pipeline"] == "speech_recognition"

    async def test_fetch_jobs_by_status(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test fetching jobs by status."""

        # Set one job to a specific status
        job_id = "2a7a8e62-40cc-4240-a825-463e5b11a81f"
        job = await session.get(BatchJob, UUID(job_id))
        if job:
            job.status = BatchJobStatus.COMPLETED
            await session.commit()

        response = await client.get("/api/jobs", params={"status": "completed"})

        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["status"] == "completed"

    async def test_fetch_jobs_by_profile(self, client: AsyncTestClient):
        """Test fetching jobs by profile."""
        response = await client.get("/api/jobs", params={"profile": "test"})

        assert response.status_code == 200
        result = response.json()
        assert len(result) == 2  # First two jobs have "test" profile

        for job in result:
            assert job["profile"] == "test"

    async def test_fetch_jobs_by_multiple_filters(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test fetching jobs with multiple filter combinations."""
        # Set up specific job states
        job1_id = "2a7a8e62-40cc-4240-a825-463e5b11a81f"
        job1 = await session.get(BatchJob, UUID(job1_id))
        if job1:
            job1.status = BatchJobStatus.RUNNING
            await session.commit()

        response = await client.get(
            "/api/jobs",
            params={
                "pipeline": "speech_recognition",
                "status": "running",
                "profile": "test",
            },
        )

        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["id"] == job1_id
        assert result[0]["status"] == "running"
        assert result[0]["pipeline"] == "speech_recognition"
        assert result[0]["profile"] == "test"

    async def test_fetch_jobs_no_matches(self, client: AsyncTestClient):
        """Test fetching jobs when no jobs match the filters."""
        response = await client.get(
            "/api/jobs", params={"pipeline": "nonexistent_pipeline"}
        )

        assert response.status_code == 200
        result = response.json()
        assert result == []

    async def test_fetch_jobs_invalid_uuid_filter(self, client: AsyncTestClient):
        """Test fetching jobs with invalid UUID format in ID filter."""
        response = await client.get("/api/jobs", params={"id": "invalid-uuid"})

        # Should return 400 like the delete endpoint for invalid UUIDs
        assert response.status_code == 400
        assert "Invalid query statement" in response.json()["detail"]

    async def test_fetch_jobs_authentication_required(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that authentication is required for fetching jobs."""
        response = await no_auth_client.get("/api/jobs")

        # Should return not authorized error
        assert response.status_code == 401


class TestGetBatchJobAPI:
    """Test cases for the GET /api/jobs/{id} endpoint."""

    async def test_get_job_by_id_success(self, client: AsyncTestClient):
        """Test successfully fetching a single job by ID."""
        job_id = "2a7a8e62-40cc-4240-a825-463e5b11a81f"

        response = await client.get(f"/api/jobs/{job_id}")

        assert response.status_code == 200
        result = response.json()

        # Verify it returns a single job object (not a list)
        assert isinstance(result, dict)
        assert result["id"] == job_id
        assert result["name"] == "blackfish-1"
        assert result["pipeline"] == "speech_recognition"
        assert "status" in result
        assert "created_at" in result

    async def test_get_job_not_found(self, client: AsyncTestClient):
        """Test fetching a job that doesn't exist."""
        nonexistent_id = "550e8400-e29b-41d4-a716-446655440000"

        response = await client.get(f"/api/jobs/{nonexistent_id}")

        assert response.status_code == 404
        # The 404 response might be HTML from the web interface, so just check the status code
        # In a real API, this should return JSON, but the current implementation redirects to 404.html

    async def test_get_job_invalid_uuid_format(self, client: AsyncTestClient):
        """Test fetching a job with invalid UUID format."""
        response = await client.get("/api/jobs/invalid-uuid-format")

        # Should return 404 for invalid UUID format
        assert response.status_code == 404

    async def test_get_job_authentication_required(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that authentication is required for fetching individual jobs."""
        job_id = "2a7a8e62-40cc-4240-a825-463e5b11a81f"
        response = await no_auth_client.get(f"/api/jobs/{job_id}")

        # Should redirect to login or return auth error
        assert response.status_code in [401, 403] or response.is_redirect

    # TODO: any other query error => 500


class TestStopBatchJobAPI:
    """Test cases for the PUT /api/jobs/{job_id}/stop endpoint."""

    async def test_stop_job_success(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test successfully stopping a job."""
        job_id = "2a7a8e62-40cc-4240-a825-463e5b11a81f"

        # Set the job to running status so it can be stopped
        job = await session.get(BatchJob, UUID(job_id))
        if job:
            job.status = BatchJobStatus.RUNNING
            job.job_id = "50426"  # Mock job ID required for stopping
            await session.commit()

        response = await client.put(f"/api/jobs/{job_id}/stop")

        assert response.status_code == 200
        result = response.json()

        # Should return the stopped job data
        assert isinstance(result, dict)
        assert result["id"] == job_id
        assert result["status"] == "stopped"

    async def test_stop_job_already_completed(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test stopping a job that's already completed."""
        job_id = "391769fc-5a40-43db-bbfa-cec80a8c3710"

        # Set the job to completed status with a job_id
        job = await session.get(BatchJob, UUID(job_id))
        if job:
            job.status = BatchJobStatus.COMPLETED
            job.job_id = "50456"  # Mock job ID
            await session.commit()

        response = await client.put(f"/api/jobs/{job_id}/stop")

        # Returns success with job status completed
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == job_id
        assert result["status"] == "completed"

    async def test_stop_job_not_found(self, client: AsyncTestClient):
        """Test stopping a job that doesn't exist."""
        nonexistent_id = "550e8400-e29b-41d4-a716-446655440000"

        response = await client.put(f"/api/jobs/{nonexistent_id}/stop")

        assert response.status_code == 404

    async def test_stop_job_invalid_uuid_format(self, client: AsyncTestClient):
        """Test stopping a job with invalid UUID format."""
        response = await client.put("/api/jobs/invalid-uuid-format/stop")

        # Should return 404 since the invalid UUID won't match any job
        assert response.status_code == 404

    async def test_stop_job_authentication_required(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that authentication is required for stopping jobs."""
        job_id = "2a7a8e62-40cc-4240-a825-463e5b11a81f"
        response = await no_auth_client.put(f"/api/jobs/{job_id}/stop")

        # Should redirect to login or return auth error
        assert response.status_code == 401

    async def test_stop_job_internal_error_handling(
        self, client: AsyncTestClient, session: AsyncSession
    ):
        """Test that internal errors during job stopping are handled properly."""
        job_id = "25058c41-9779-4b16-af6e-3fe5c3902435"

        job = await session.get(BatchJob, UUID(job_id))
        if job:
            job.status = BatchJobStatus.RUNNING
            job.job_id = None  # Missing Slurm job_id raises an exception in job.stop
            await session.commit()

        response = await client.put(f"/api/jobs/{job_id}/stop")

        # Should return internal server error
        assert response.status_code == 500


class TestCreateBatchJobAPI:
    """Test cases for the POST /api/jobs endpoint."""

    async def test_create_job(self, client: AsyncTestClient):
        """Test creating a job."""

        data = {
            "name": "speech-recognition-batch-test",
            "pipeline": "speech_recognition",
            "repo_id": "openai-whisper",
            "profile": {
                "name": "test",
                "home_dir": "",
                "cache_dir": "",
            },
            "job_config": {},
            "container_config": {
                "model_dir": "",
                "revision": "",
                "kwargs": [],
            },
            "mount": "",
        }

        with patch.object(BatchJob, "start", new_callable=AsyncMock) as mock_start:
            response = await client.post("/api/jobs", json=data)

            # Should return success with job data
            assert response.status_code == 201
            mock_start.assert_called_once()
            job = response.json()
            assert job["name"] == "speech-recognition-batch-test"
            assert job["pipeline"] == "speech_recognition"
            assert job["repo_id"] == "openai-whisper"
            assert job["profile"] == "test"  # only returns the name

    async def test_create_job_missing_request_body(self, client: AsyncTestClient):
        """Test creating a job with missing request body."""
        response = await client.post("/api/jobs")

        # Should return 400 for bad request (missing required fields)
        assert response.status_code == 400

    async def test_create_job_invalid_request_data(self, client: AsyncTestClient):
        """Test creating a job with invalid request data."""
        invalid_data = {
            "name": "test-job",
            # Missing required fields like pipeline, repo_id, profile, etc.
        }

        response = await client.post("/api/jobs", json=invalid_data)

        # Should return 400 for validation error
        assert response.status_code == 400

    async def test_create_job_authentication_required(
        self, no_auth_client: AsyncTestClient
    ):
        """Test that authentication is required for creating jobs."""

        # Even with valid data, should fail authentication first
        valid_data = {
            "name": "speech-recognition-batch-test",
            "pipeline": "speech_recognition",
            "repo_id": "openai-whisper",
            "profile": {
                "name": "test",
                "home_dir": "",
                "cache_dir": "",
            },
            "job_config": {},
            "container_config": {
                "model_dir": "",
                "revision": "",
                "kwargs": [],
            },
            "mount": "",
        }

        response = await no_auth_client.post("/api/jobs", json=valid_data)

        # Should return auth error
        assert response.status_code == 401

    # TODO: this actually returns 200 with an empty body according to code--should it???
    async def test_create_job_unsupported_pipeline(self, client: AsyncTestClient):
        """Test creating a job with unsupported pipeline."""

        # Test that unsupported pipelines are handled
        data = {
            "name": "speech-recognition-batch-test",
            "pipeline": "not_supported",
            "repo_id": "openai-whisper",
            "profile": {
                "name": "test",
                "home_dir": "",
                "cache_dir": "",
            },
            "job_config": {},
            "container_config": {
                "model_dir": "",
                "revision": "",
                "kwargs": [],
            },
            "mount": "",
        }

        response = await client.post("/api/jobs", json=data)

        # Should return validation error for unsupported pipeline
        assert response.status_code == 400
        assert "Invalid pipeline" in response.json()["detail"]
