"""
Tests for async job handling in the Data Simulator.

Tests verify:
1. Sync vs Async threshold (50K rows)
2. Job status endpoint
3. Job lifecycle (pending → running → completed/failed)
4. Output storage
5. Error handling

Most tests are marked with @pytest.mark.skip since async jobs are not yet implemented.
These tests serve as TDD specifications for the feature.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# Test DAG fixtures
SIMPLE_DAG = {
    "nodes": [
        {
            "id": "x",
            "name": "X",
            "kind": "stochastic",
            "dtype": "float",
            "scope": "row",
            "distribution": {"type": "normal", "params": {"mu": 100, "sigma": 10}},
        },
        {
            "id": "y",
            "name": "Y",
            "kind": "deterministic",
            "dtype": "float",
            "scope": "row",
            "formula": "x * 2",
        },
    ],
    "edges": [{"source": "x", "target": "y"}],
    "metadata": {"sample_size": 100, "seed": 42},
}


def make_dag(sample_size: int, seed: int = 42) -> dict[str, Any]:
    """Create a test DAG with specified sample size."""
    dag = SIMPLE_DAG.copy()
    dag["metadata"] = {"sample_size": sample_size, "seed": seed}
    return dag


class TestSyncVsAsyncThreshold:
    """Tests for the 50K row threshold that determines sync vs async processing."""

    def test_small_dataset_returns_streaming_response(self):
        """
        Sample size <= 50000 should return streaming CSV/JSON/Parquet directly.
        This is the current behavior (already implemented).
        """
        dag = make_dag(sample_size=100)
        response = client.post("/api/dag/generate?format=csv", json=dag)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

        # Should have actual CSV content, not job_id
        content = response.text
        assert "x,y" in content, "Should return CSV headers"
        assert "job_id" not in content, "Should not return job_id for small dataset"

    def test_exactly_50k_rows_returns_streaming_response(self):
        """
        Sample size = 50000 (at threshold) should still stream synchronously.
        """
        dag = make_dag(sample_size=50_000)
        response = client.post("/api/dag/generate?format=csv", json=dag)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

        # Should stream the data
        content = response.text
        lines = content.strip().split("\n")
        # Header + 50000 data rows
        assert len(lines) == 50_001, f"Expected 50001 lines, got {len(lines)}"

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_large_dataset_returns_job_id(self):
        """
        Sample size > 50000 should return job_id for async processing.

        Response should be JSON:
        {
            "job_id": "abc123...",
            "status": "pending",
            "message": "Job queued for processing"
        }
        """
        dag = make_dag(sample_size=50_001)
        response = client.post("/api/dag/generate?format=csv", json=dag)

        assert response.status_code == 202, "Should return 202 Accepted for async job"
        data = response.json()

        assert "job_id" in data, "Response should contain job_id"
        assert data["status"] == "pending", "Initial status should be pending"
        assert len(data["job_id"]) > 0, "job_id should not be empty"

        # Should not return streaming data
        assert (
            "content-type" not in response.headers
            or response.headers["content-type"] == "application/json"
        )

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_very_large_dataset_returns_job_id(self):
        """
        Large datasets (1M rows) should return job_id.
        """
        dag = make_dag(sample_size=1_000_000)
        response = client.post("/api/dag/generate?format=csv", json=dag)

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_async_threshold_works_for_all_formats(self):
        """
        The 50K threshold should apply to all formats: csv, json, parquet.
        """
        dag = make_dag(sample_size=100_000)

        for format_type in ["csv", "json", "parquet"]:
            response = client.post(f"/api/dag/generate?format={format_type}", json=dag)

            assert response.status_code == 202, (
                f"Format {format_type} should trigger async for >50K rows"
            )
            data = response.json()
            assert "job_id" in data, f"Format {format_type} should return job_id"

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_job_id_is_unique(self):
        """
        Each async job should get a unique job_id.
        """
        dag = make_dag(sample_size=100_000)

        response1 = client.post("/api/dag/generate?format=csv", json=dag)
        response2 = client.post("/api/dag/generate?format=csv", json=dag)

        job_id_1 = response1.json()["job_id"]
        job_id_2 = response2.json()["job_id"]

        assert job_id_1 != job_id_2, "Each job should have unique ID"


class TestJobStatusEndpoint:
    """Tests for GET /api/jobs/{job_id} endpoint."""

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_job_status_endpoint_exists(self):
        """
        GET /api/jobs/{job_id} should exist and be accessible.
        """
        # Create a job first
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Check status
        status_response = client.get(f"/api/jobs/{job_id}")

        assert status_response.status_code == 200
        data = status_response.json()
        assert "job_id" in data
        assert "status" in data

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_job_status_response_schema(self):
        """
        Job status response should match expected schema:
        {
            "job_id": "abc123",
            "status": "completed",  # pending|running|completed|failed
            "progress": 100,
            "download_url": "/outputs/abc123/data.parquet",
            "expires_at": "2026-01-18T10:30:00Z",
            "metadata": {
                "sample_size": 100000,
                "format": "csv",
                "seed": 42,
                "created_at": "2026-01-17T10:30:00Z",
                "started_at": "2026-01-17T10:30:01Z",
                "completed_at": "2026-01-17T10:30:45Z"
            }
        }
        """
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        status_response = client.get(f"/api/jobs/{job_id}")
        data = status_response.json()

        # Required fields
        assert "job_id" in data
        assert "status" in data
        assert "progress" in data
        assert "metadata" in data

        # Status should be valid
        assert data["status"] in ["pending", "running", "completed", "failed"]

        # Progress should be 0-100
        assert 0 <= data["progress"] <= 100

        # Metadata should contain job details
        assert "sample_size" in data["metadata"]
        assert "format" in data["metadata"]
        assert "created_at" in data["metadata"]

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_pending_job_has_no_download_url(self):
        """
        Pending jobs should not have download_url yet.
        """
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Immediately check status (should be pending)
        status_response = client.get(f"/api/jobs/{job_id}")
        data = status_response.json()

        assert data["status"] == "pending"
        assert data["download_url"] is None or "download_url" not in data
        assert data["progress"] == 0

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_completed_job_has_download_url(self):
        """
        Completed jobs should have download_url and expires_at.
        """
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Wait for job to complete (or mock completion)
        # In real implementation, this would poll until completed
        # For now, assume we can check a completed job

        status_response = client.get(f"/api/jobs/{job_id}")
        data = status_response.json()

        if data["status"] == "completed":
            assert "download_url" in data
            assert data["download_url"] is not None
            assert data["progress"] == 100
            assert "expires_at" in data

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_running_job_has_progress(self):
        """
        Running jobs should show progress between 0 and 100.
        """
        dag = make_dag(sample_size=1_000_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Poll until we catch it in running state
        max_attempts = 10
        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()

            if data["status"] == "running":
                assert 0 < data["progress"] < 100, (
                    "Running job should have progress between 0 and 100"
                )
                break

            time.sleep(0.1)

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_invalid_job_id_returns_404(self):
        """
        Non-existent job_id should return 404.
        """
        response = client.get("/api/jobs/nonexistent-job-id-12345")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data or "error" in data

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_malformed_job_id_returns_404(self):
        """
        Malformed job_id should return 404 or 400.
        """
        response = client.get("/api/jobs/../../etc/passwd")

        assert response.status_code in [400, 404]

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_job_status_includes_format_in_metadata(self):
        """
        Job metadata should include the requested format.
        """
        dag = make_dag(sample_size=100_000)

        for format_type in ["csv", "json", "parquet"]:
            create_response = client.post(f"/api/dag/generate?format={format_type}", json=dag)
            job_id = create_response.json()["job_id"]

            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()

            assert data["metadata"]["format"] == format_type


class TestJobLifecycle:
    """Tests for job state transitions: pending → running → completed/failed."""

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_job_starts_as_pending(self):
        """
        Newly created jobs should have status="pending".
        """
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)

        assert create_response.status_code == 202
        data = create_response.json()
        assert data["status"] == "pending"

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_job_transitions_to_running(self):
        """
        Jobs should transition from pending to running.
        """
        dag = make_dag(sample_size=500_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Poll until job is running
        max_attempts = 50
        found_running = False

        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()

            if data["status"] == "running":
                found_running = True
                assert "started_at" in data["metadata"]
                break

            time.sleep(0.1)

        assert found_running, "Job should transition to running state"

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_job_transitions_to_completed(self):
        """
        Jobs should transition to completed when done.
        """
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Poll until completed
        max_attempts = 100
        found_completed = False

        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()

            if data["status"] == "completed":
                found_completed = True
                assert data["progress"] == 100
                assert "download_url" in data
                assert data["download_url"] is not None
                assert "completed_at" in data["metadata"]
                break

            time.sleep(0.2)

        assert found_completed, "Job should eventually complete"

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_job_never_goes_backwards(self):
        """
        Jobs should never transition backwards (e.g., running → pending).
        """
        dag = make_dag(sample_size=500_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        states_seen = []
        state_order = {"pending": 0, "running": 1, "completed": 2, "failed": 2}

        for _ in range(50):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            state = data["status"]
            states_seen.append(state)

            if state in ["completed", "failed"]:
                break

            time.sleep(0.1)

        # Check that states are monotonically increasing
        for i in range(len(states_seen) - 1):
            current = state_order[states_seen[i]]
            next_state = state_order[states_seen[i + 1]]
            assert next_state >= current, (
                f"Job went backwards: {states_seen[i]} → {states_seen[i + 1]}"
            )

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_job_progress_increases_monotonically(self):
        """
        Job progress should only increase, never decrease.
        """
        dag = make_dag(sample_size=1_000_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        progress_values = []

        for _ in range(50):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            progress_values.append(data["progress"])

            if data["status"] in ["completed", "failed"]:
                break

            time.sleep(0.1)

        # Check monotonically increasing
        for i in range(len(progress_values) - 1):
            assert progress_values[i + 1] >= progress_values[i], (
                f"Progress decreased: {progress_values[i]} → {progress_values[i + 1]}"
            )

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_completed_job_stays_completed(self):
        """
        Once completed, job status should not change.
        """
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Wait for completion
        max_attempts = 100
        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            if data["status"] == "completed":
                break
            time.sleep(0.2)

        # Check multiple times that it stays completed
        for _ in range(5):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            assert data["status"] == "completed"
            time.sleep(0.1)

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_job_failure_with_invalid_dag(self):
        """
        Jobs with invalid DAGs should transition to failed status.
        """
        # Create DAG that will fail during generation
        invalid_dag = {
            "nodes": [
                {
                    "id": "x",
                    "name": "X",
                    "kind": "deterministic",
                    "dtype": "float",
                    "scope": "row",
                    "formula": "1 / 0",  # Division by zero
                },
            ],
            "edges": [],
            "metadata": {"sample_size": 100_000, "seed": 42},
        }

        create_response = client.post("/api/dag/generate?format=csv", json=invalid_dag)
        job_id = create_response.json()["job_id"]

        # Poll until failed
        max_attempts = 50
        found_failed = False

        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()

            if data["status"] == "failed":
                found_failed = True
                assert "error" in data or "error_message" in data["metadata"]
                assert data["download_url"] is None or "download_url" not in data
                break

            time.sleep(0.1)

        assert found_failed, "Invalid job should fail"


class TestOutputStorage:
    """Tests for file storage in outputs/{job_id}/ directory."""

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_output_directory_created_for_job(self):
        """
        Each job should have its own directory: outputs/{job_id}/
        """
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Wait for completion
        max_attempts = 100
        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            if data["status"] == "completed":
                break
            time.sleep(0.2)

        # Check directory exists
        output_dir = Path(f"./outputs/{job_id}")
        assert output_dir.exists(), f"Output directory should exist: {output_dir}"
        assert output_dir.is_dir(), "Output path should be a directory"

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_output_file_created_in_job_directory(self):
        """
        Generated file should be stored in outputs/{job_id}/data.{format}
        """
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=parquet", json=dag)
        job_id = create_response.json()["job_id"]

        # Wait for completion
        max_attempts = 100
        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            if data["status"] == "completed":
                break
            time.sleep(0.2)

        # Check file exists
        output_file = Path(f"./outputs/{job_id}/data.parquet")
        assert output_file.exists(), f"Output file should exist: {output_file}"
        assert output_file.stat().st_size > 0, "Output file should not be empty"

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_metadata_json_created(self):
        """
        Each job should create a metadata.json file with job details.
        """
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Wait for completion
        max_attempts = 100
        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            if data["status"] == "completed":
                break
            time.sleep(0.2)

        # Check metadata.json
        metadata_file = Path(f"./outputs/{job_id}/metadata.json")
        assert metadata_file.exists(), "metadata.json should exist"

        with open(metadata_file) as f:
            metadata = json.load(f)

        assert metadata["job_id"] == job_id
        assert "sample_size" in metadata
        assert "format" in metadata
        assert "created_at" in metadata
        assert "completed_at" in metadata

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_download_url_points_to_output_file(self):
        """
        download_url should point to the actual output file.
        """
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Wait for completion
        max_attempts = 100
        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            if data["status"] == "completed":
                break
            time.sleep(0.2)

        status_response = client.get(f"/api/jobs/{job_id}")
        data = status_response.json()

        download_url = data["download_url"]
        assert download_url.startswith("/outputs/") or download_url.startswith("outputs/")
        assert job_id in download_url
        assert download_url.endswith(".csv")

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_download_endpoint_serves_file(self):
        """
        GET {download_url} should serve the actual file.
        """
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Wait for completion
        max_attempts = 100
        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            if data["status"] == "completed":
                break
            time.sleep(0.2)

        status_response = client.get(f"/api/jobs/{job_id}")
        data = status_response.json()
        download_url = data["download_url"]

        # Download the file
        download_response = client.get(download_url)
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "text/csv; charset=utf-8"

        # Should be actual CSV content
        content = download_response.text
        assert "x,y" in content
        lines = content.strip().split("\n")
        assert len(lines) == 100_001  # header + 100K rows

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_expiration_tracking(self):
        """
        Jobs should have expires_at timestamp (default 24 hours).
        """
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Wait for completion
        max_attempts = 100
        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            if data["status"] == "completed":
                break
            time.sleep(0.2)

        status_response = client.get(f"/api/jobs/{job_id}")
        data = status_response.json()

        assert "expires_at" in data

        # Parse timestamp
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        now = datetime.now(expires_at.tzinfo)

        # Should expire in approximately 24 hours
        time_until_expiry = expires_at - now
        assert timedelta(hours=23) < time_until_expiry < timedelta(hours=25)

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_expired_job_files_can_be_cleaned_up(self):
        """
        System should be able to clean up expired job files.
        This test checks that cleanup is possible, not that it happens automatically.
        """
        # Create job with short expiration
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Wait for completion
        max_attempts = 100
        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            if data["status"] == "completed":
                break
            time.sleep(0.2)

        output_dir = Path(f"./outputs/{job_id}")
        assert output_dir.exists()

        # Cleanup endpoint should exist (or manual cleanup should be possible)
        # This is a placeholder - actual implementation may vary
        # Could be: DELETE /api/jobs/{job_id}
        # Or a background task that cleans up expired jobs


class TestErrorHandling:
    """Tests for error cases in async job handling."""

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_invalid_job_id_returns_404(self):
        """
        Non-existent job IDs should return 404.
        """
        response = client.get("/api/jobs/this-job-does-not-exist")
        assert response.status_code == 404

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_failed_job_includes_error_details(self):
        """
        Failed jobs should include error message in response.
        """
        # Create a job that will fail
        invalid_dag = {
            "nodes": [
                {
                    "id": "x",
                    "name": "X",
                    "kind": "deterministic",
                    "dtype": "float",
                    "scope": "row",
                    "formula": "undefined_variable * 2",
                },
            ],
            "edges": [],
            "metadata": {"sample_size": 100_000, "seed": 42},
        }

        create_response = client.post("/api/dag/generate?format=csv", json=invalid_dag)
        job_id = create_response.json()["job_id"]

        # Wait for failure
        max_attempts = 50
        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            if data["status"] == "failed":
                break
            time.sleep(0.1)

        status_response = client.get(f"/api/jobs/{job_id}")
        data = status_response.json()

        assert data["status"] == "failed"
        assert "error" in data or "error_message" in data["metadata"]

        # Error message should be informative
        error_msg = data.get("error") or data["metadata"].get("error_message")
        assert len(error_msg) > 0
        assert "undefined_variable" in error_msg.lower() or "error" in error_msg.lower()

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_failed_job_has_no_download_url(self):
        """
        Failed jobs should not have download_url.
        """
        invalid_dag = {
            "nodes": [
                {
                    "id": "x",
                    "name": "X",
                    "kind": "deterministic",
                    "dtype": "float",
                    "scope": "row",
                    "formula": "1 / 0",
                },
            ],
            "edges": [],
            "metadata": {"sample_size": 100_000, "seed": 42},
        }

        create_response = client.post("/api/dag/generate?format=csv", json=invalid_dag)
        job_id = create_response.json()["job_id"]

        # Wait for failure
        max_attempts = 50
        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            if data["status"] == "failed":
                break
            time.sleep(0.1)

        status_response = client.get(f"/api/jobs/{job_id}")
        data = status_response.json()

        assert data["download_url"] is None or "download_url" not in data

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_download_nonexistent_file_returns_404(self):
        """
        Attempting to download non-existent file should return 404.
        """
        response = client.get("/outputs/fake-job-id/data.csv")
        assert response.status_code == 404

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_job_id_path_traversal_prevented(self):
        """
        Job IDs with path traversal attempts should be rejected.
        """
        # Try to access files outside outputs directory
        response = client.get("/api/jobs/../../etc/passwd")
        assert response.status_code in [400, 404]

        response = client.get("/outputs/../../../etc/passwd")
        assert response.status_code in [400, 404]

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_concurrent_jobs_dont_interfere(self):
        """
        Multiple concurrent jobs should not interfere with each other.
        """
        dag1 = make_dag(sample_size=100_000, seed=42)
        dag2 = make_dag(sample_size=200_000, seed=123)

        # Create two jobs
        response1 = client.post("/api/dag/generate?format=csv", json=dag1)
        response2 = client.post("/api/dag/generate?format=csv", json=dag2)

        job_id_1 = response1.json()["job_id"]
        job_id_2 = response2.json()["job_id"]

        assert job_id_1 != job_id_2

        # Both should complete successfully
        max_attempts = 100
        completed = {job_id_1: False, job_id_2: False}

        for _ in range(max_attempts):
            for job_id in [job_id_1, job_id_2]:
                if not completed[job_id]:
                    status_response = client.get(f"/api/jobs/{job_id}")
                    data = status_response.json()
                    if data["status"] == "completed":
                        completed[job_id] = True

            if all(completed.values()):
                break

            time.sleep(0.2)

        assert all(completed.values()), "Both jobs should complete"

        # Check that outputs are different
        status1 = client.get(f"/api/jobs/{job_id_1}").json()
        status2 = client.get(f"/api/jobs/{job_id_2}").json()

        assert status1["metadata"]["sample_size"] == 100_000
        assert status2["metadata"]["sample_size"] == 200_000

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_max_output_size_enforced(self):
        """
        Jobs exceeding max output size should fail gracefully.
        """
        # Try to create a job that would exceed max_output_size_mb (500MB)
        # This would require ~10M rows with many columns
        huge_dag = {
            "nodes": [
                {
                    "id": f"col_{i}",
                    "name": f"Column {i}",
                    "kind": "stochastic",
                    "dtype": "float",
                    "scope": "row",
                    "distribution": {"type": "normal", "params": {"mu": 0, "sigma": 1}},
                }
                for i in range(50)  # 50 columns
            ],
            "edges": [],
            "metadata": {"sample_size": 5_000_000, "seed": 42},  # 5M rows * 50 cols
        }

        create_response = client.post("/api/dag/generate?format=csv", json=huge_dag)

        # Should either reject immediately or fail during generation
        if create_response.status_code == 400:
            # Rejected immediately
            assert "size" in create_response.json()["detail"].lower()
        else:
            # Accepted but should fail
            job_id = create_response.json()["job_id"]

            max_attempts = 100
            for _ in range(max_attempts):
                status_response = client.get(f"/api/jobs/{job_id}")
                data = status_response.json()
                if data["status"] == "failed":
                    error_msg = data.get("error", "")
                    assert "size" in error_msg.lower() or "limit" in error_msg.lower()
                    break
                time.sleep(0.2)


class TestAsyncJobsIntegration:
    """Integration tests for complete async job workflow."""

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_complete_async_workflow_csv(self):
        """
        Test complete workflow: create job → poll status → download CSV.
        """
        # 1. Create job
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)

        assert create_response.status_code == 202
        job_id = create_response.json()["job_id"]

        # 2. Poll until completed
        max_attempts = 100
        completed = False

        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()

            assert data["status"] in ["pending", "running", "completed"]

            if data["status"] == "completed":
                completed = True
                download_url = data["download_url"]
                break

            time.sleep(0.2)

        assert completed, "Job should complete"

        # 3. Download file
        download_response = client.get(download_url)
        assert download_response.status_code == 200

        # 4. Verify content
        content = download_response.text
        lines = content.strip().split("\n")
        assert len(lines) == 100_001  # header + 100K rows
        assert lines[0] == "x,y"

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_complete_async_workflow_parquet(self):
        """
        Test complete workflow with Parquet format.
        """
        # 1. Create job
        dag = make_dag(sample_size=100_000)
        create_response = client.post("/api/dag/generate?format=parquet", json=dag)

        assert create_response.status_code == 202
        job_id = create_response.json()["job_id"]

        # 2. Poll until completed
        max_attempts = 100
        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            if data["status"] == "completed":
                download_url = data["download_url"]
                break
            time.sleep(0.2)

        # 3. Download and parse Parquet
        download_response = client.get(download_url)
        assert download_response.status_code == 200

        df = pd.read_parquet(BytesIO(download_response.content))
        assert len(df) == 100_000
        assert "x" in df.columns
        assert "y" in df.columns

    @pytest.mark.skip(reason="Async jobs not implemented yet")
    def test_job_metadata_matches_dag_config(self):
        """
        Job metadata should accurately reflect the DAG configuration.
        """
        dag = make_dag(sample_size=150_000, seed=999)
        create_response = client.post("/api/dag/generate?format=csv", json=dag)
        job_id = create_response.json()["job_id"]

        # Wait for completion
        max_attempts = 100
        for _ in range(max_attempts):
            status_response = client.get(f"/api/jobs/{job_id}")
            data = status_response.json()
            if data["status"] == "completed":
                break
            time.sleep(0.2)

        status_response = client.get(f"/api/jobs/{job_id}")
        data = status_response.json()

        assert data["metadata"]["sample_size"] == 150_000
        assert data["metadata"]["seed"] == 999
        assert data["metadata"]["format"] == "csv"
