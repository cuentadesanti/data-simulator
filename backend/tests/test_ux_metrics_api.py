"""Tests for the UX Metrics API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import require_auth
from app.db.database import Base, get_db
from app.main import app


@pytest.fixture(scope="function")
def client():
    """Create test client with fresh database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def override_require_auth():
        return {"sub": "test-user", "user_id": "test-user"}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_auth] = override_require_auth

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


class TestUXEventsIngestion:
    """Test UX event ingestion endpoint."""

    def test_ingest_events_success(self, client):
        """Test successful event ingestion."""
        response = client.post(
            "/api/ux/events",
            json={
                "events": [
                    {"event_type": "click", "path_id": "HP-1", "stage": "source", "action": "test"},
                    {"event_type": "flow_started", "path_id": "HP-2"},
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ingested"] == 2

    def test_ingest_empty_batch(self, client):
        """Test ingesting an empty batch succeeds with zero count."""
        response = client.post("/api/ux/events", json={"events": []})
        assert response.status_code == 200
        assert response.json()["ingested"] == 0

    def test_ingest_exceeds_max_batch_size(self, client):
        """Test that batches exceeding 500 events are rejected."""
        events = [{"event_type": "click"} for _ in range(501)]
        response = client.post("/api/ux/events", json={"events": events})
        assert response.status_code == 422

    def test_ingest_event_type_too_long(self, client):
        """Test that event_type exceeding 100 chars is rejected."""
        response = client.post(
            "/api/ux/events",
            json={"events": [{"event_type": "x" * 101}]},
        )
        assert response.status_code == 422


class TestKPISnapshot:
    """Test KPI snapshot endpoint."""

    def test_snapshot_empty(self, client):
        """Test KPI snapshot with no events returns zeroed KPIs."""
        response = client.get("/api/ux/kpi-snapshot")
        assert response.status_code == 200
        data = response.json()
        assert data["window_hours"] == 168
        assert "kpis" in data
        assert data["kpis"]["avg_clicks_happy_path"] == 0.0
        assert data["kpis"]["completion_rate_pct"] == 0.0

    def test_snapshot_with_events(self, client):
        """Test KPI snapshot correctly computes from ingested events."""
        # Ingest some events
        client.post(
            "/api/ux/events",
            json={
                "events": [
                    {"event_type": "click", "path_id": "HP-1", "stage": "source", "action": "add_node"},
                    {"event_type": "click", "path_id": "HP-1", "stage": "source", "action": "preview"},
                    {"event_type": "flow_started", "path_id": "HP-1"},
                    {"event_type": "flow_completed", "path_id": "HP-1"},
                    {"event_type": "feedback_latency", "action": "preview", "latency_ms": 200},
                    {"event_type": "visible_actions_snapshot", "metadata": {"count": 5}},
                ]
            },
        )

        response = client.get("/api/ux/kpi-snapshot")
        assert response.status_code == 200
        data = response.json()
        kpis = data["kpis"]

        assert kpis["avg_clicks_happy_path"] == 2.0  # 2 clicks on HP-1
        assert kpis["completion_rate_pct"] == 100.0  # 1 started, 1 completed
        assert kpis["p95_feedback_latency_ms"] == 200.0  # single sample
        assert kpis["visible_primary_actions"] == 5.0

    def test_snapshot_window_filtering(self, client):
        """Test that window parameter is accepted and validated."""
        # Valid window
        response = client.get("/api/ux/kpi-snapshot?window=24")
        assert response.status_code == 200
        assert response.json()["window_hours"] == 24

        # Invalid window (too small)
        response = client.get("/api/ux/kpi-snapshot?window=0")
        assert response.status_code == 422

        # Invalid window (too large)
        response = client.get("/api/ux/kpi-snapshot?window=99999")
        assert response.status_code == 422
