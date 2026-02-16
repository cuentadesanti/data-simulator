"""Tests for rate limiting on expensive endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

# Simple DAG for testing
TEST_DAG = {
    "nodes": [
        {
            "id": "test_node",
            "name": "Test Node",
            "kind": "stochastic",
            "dtype": "float",
            "scope": "row",
            "distribution": {
                "type": "normal",
                "params": {"mu": 0, "sigma": 1},
            },
        }
    ],
    "edges": [],
    "metadata": {"sample_size": 10, "seed": 42},
}


class TestRateLimitingConfiguration:
    """Test rate limiting configuration."""

    def test_rate_limiter_disabled_in_dev(self):
        """Test that rate limiter is disabled in dev environment."""
        from app.core.rate_limiter import IS_DEV_ENVIRONMENT, limiter

        # In dev environment (default), rate limiting should be disabled
        assert IS_DEV_ENVIRONMENT is True
        assert limiter.enabled is False

    def test_generate_not_limited_in_dev(self):
        """Test that /generate is not rate limited in dev environment."""
        with TestClient(app) as client:
            # The limit would be 10/minute if enabled. We check 12 to ensure it's disabled.
            for i in range(12):
                response = client.post("/api/dag/generate?format=json", json=TEST_DAG)
                assert response.status_code == 200, f"Request {i+1} should not be rate limited in dev"

    def test_preview_not_limited_in_dev(self):
        """Test that /preview is not rate limited in dev environment."""
        with TestClient(app) as client:
            # Just test a few to ensure it works
            for i in range(5):
                response = client.post("/api/dag/preview", json=TEST_DAG)
                assert response.status_code == 200, f"Request {i+1} should not be rate limited in dev"


class TestRateLimitingIsolation:
    """Test that rate limiting doesn't affect unrelated endpoints."""

    def test_health_endpoint_not_rate_limited(self):
        """Test that /health is not rate limited."""
        with TestClient(app) as client:
            for i in range(5):
                response = client.get("/health")
                assert response.status_code == 200, f"Health check {i+1} should not be rate limited"

    def test_root_endpoint_not_rate_limited(self):
        """Test that root endpoint is not rate limited."""
        with TestClient(app) as client:
            for i in range(5):
                response = client.get("/")
                assert response.status_code == 200, f"Root {i+1} should not be rate limited"

    def test_validate_endpoint_not_rate_limited(self):
        """Test that /validate is not rate limited."""
        with TestClient(app) as client:
            for i in range(5):
                response = client.post("/api/dag/validate", json=TEST_DAG)
                assert response.status_code == 200, f"Request {i+1} should succeed"



class TestRateLimitConstants:
    """Test that rate limit constants are properly defined."""

    def test_rate_limit_constants_exist(self):
        """Test that rate limit constants are defined."""
        from app.core.rate_limiter import GENERATE_RATE_LIMIT, PREVIEW_RATE_LIMIT

        assert GENERATE_RATE_LIMIT == "10/minute"
        assert PREVIEW_RATE_LIMIT == "30/minute"
