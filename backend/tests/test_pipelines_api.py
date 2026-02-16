"""Tests for pipeline step mutation API endpoints."""

from __future__ import annotations

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import require_auth
from app.core.config import settings
from app.db.database import Base, get_db
from app.main import app


@pytest.fixture(scope="function")
def client():
    """Create test client with isolated in-memory database."""
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

    original_admin_user_ids = settings.admin_user_ids

    async def override_require_auth(request: Request):
        user = request.headers.get("x-test-user", "test-user")
        return {"sub": user, "user_id": user}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_auth] = override_require_auth

    with TestClient(app) as test_client:
        yield test_client

    settings.admin_user_ids = original_admin_user_ids
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _create_project_and_pipeline(client: TestClient) -> tuple[str, str, str]:
    dag_definition = {
        "schema_version": "1.0",
        "nodes": [
            {
                "id": "income",
                "name": "Income",
                "kind": "stochastic",
                "dtype": "float",
                "scope": "row",
                "distribution": {"type": "normal", "params": {"mu": 50000, "sigma": 10000}},
            },
            {
                "id": "age",
                "name": "Age",
                "kind": "stochastic",
                "dtype": "int",
                "scope": "row",
                "distribution": {"type": "uniform", "params": {"low": 18, "high": 65}},
            },
        ],
        "edges": [],
        "metadata": {"sample_size": 100, "seed": 42, "preview_rows": 10},
    }

    project = client.post(
        "/api/projects",
        json={"name": "Pipeline API Project", "dag_definition": dag_definition},
    )
    assert project.status_code == 201
    project_data = project.json()
    project_id = project_data["id"]
    dag_version_id = project_data["current_version"]["id"]

    pipeline = client.post(
        "/api/pipelines",
        json={
            "project_id": project_id,
            "name": "Pipeline API",
            "source": {
                "type": "simulation",
                "dag_version_id": dag_version_id,
                "seed": 42,
                "sample_size": 100,
            },
        },
    )
    assert pipeline.status_code == 201
    pipeline_data = pipeline.json()
    return project_id, pipeline_data["pipeline_id"], pipeline_data["current_version_id"]


def _create_project_and_pipeline_for_user(client: TestClient, user: str) -> tuple[str, str, str]:
    dag_definition = {
        "schema_version": "1.0",
        "nodes": [
            {
                "id": "income",
                "name": "Income",
                "kind": "stochastic",
                "dtype": "float",
                "scope": "row",
                "distribution": {"type": "normal", "params": {"mu": 50000, "sigma": 10000}},
            }
        ],
        "edges": [],
        "metadata": {"sample_size": 100, "seed": 42, "preview_rows": 10},
    }
    project = client.post("/api/projects", json={"name": f"{user}-project", "dag_definition": dag_definition}, headers={"x-test-user": user})
    assert project.status_code == 201
    project_data = project.json()
    project_id = project_data["id"]
    dag_version_id = project_data["current_version"]["id"]
    pipeline = client.post(
        "/api/pipelines",
        json={
            "project_id": project_id,
            "name": f"{user}-pipeline",
            "source": {
                "type": "simulation",
                "dag_version_id": dag_version_id,
                "seed": 42,
                "sample_size": 100,
            },
        },
        headers={"x-test-user": user},
    )
    assert pipeline.status_code == 201
    return project_id, pipeline.json()["pipeline_id"], pipeline.json()["current_version_id"]


def _add_formula_step(
    client: TestClient, pipeline_id: str, version_id: str, output: str, expression: str
) -> str:
    response = client.post(
        f"/api/pipelines/{pipeline_id}/versions/{version_id}/steps",
        json={
            "step": {
                "type": "formula",
                "output_column": output,
                "params": {"expression": expression},
            },
            "preview_limit": 50,
        },
    )
    assert response.status_code == 200
    return response.json()["new_version_id"]


def _get_current_version_detail(client: TestClient, pipeline_id: str) -> dict:
    response = client.get(f"/api/pipelines/{pipeline_id}")
    assert response.status_code == 200
    return response.json()["current_version"]


def test_delete_step_dependency_conflict_returns_409(client: TestClient):
    _, pipeline_id, version_id = _create_project_and_pipeline(client)
    version_id = _add_formula_step(client, pipeline_id, version_id, "income_x2", "income * 2")
    version_id = _add_formula_step(client, pipeline_id, version_id, "income_x4", "income_x2 * 2")

    current = _get_current_version_detail(client, pipeline_id)
    parent_step_id = current["steps"][0]["step_id"]

    response = client.delete(
        f"/api/pipelines/{pipeline_id}/versions/{version_id}/steps/{parent_step_id}",
        params={"cascade": "false", "preview_limit": 50},
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "affected_step_ids" in detail
    assert "affected_columns" in detail
    assert len(detail["affected_step_ids"]) >= 1


def test_delete_step_cascade_success(client: TestClient):
    _, pipeline_id, version_id = _create_project_and_pipeline(client)
    version_id = _add_formula_step(client, pipeline_id, version_id, "income_x2", "income * 2")
    version_id = _add_formula_step(client, pipeline_id, version_id, "income_x4", "income_x2 * 2")
    current = _get_current_version_detail(client, pipeline_id)

    response = client.delete(
        f"/api/pipelines/{pipeline_id}/versions/{version_id}/steps/{current['steps'][0]['step_id']}",
        params={"cascade": "true", "preview_limit": 50},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["removed_step_ids"]) == 2
    assert payload["steps"] == []
    assert "income_x2" in payload["affected_columns"]


def test_reorder_steps_success(client: TestClient):
    _, pipeline_id, version_id = _create_project_and_pipeline(client)
    response_1 = client.post(
        f"/api/pipelines/{pipeline_id}/versions/{version_id}/steps",
        json={
            "step": {"type": "log", "output_column": "log_income", "params": {"column": "income"}},
            "preview_limit": 50,
        },
    )
    assert response_1.status_code == 200
    version_id = response_1.json()["new_version_id"]
    response_2 = client.post(
        f"/api/pipelines/{pipeline_id}/versions/{version_id}/steps",
        json={
            "step": {"type": "sqrt", "output_column": "sqrt_age", "params": {"column": "age"}},
            "preview_limit": 50,
        },
    )
    assert response_2.status_code == 200
    version_id = response_2.json()["new_version_id"]

    current = _get_current_version_detail(client, pipeline_id)
    step_ids = [step["step_id"] for step in current["steps"]]

    reorder = client.post(
        f"/api/pipelines/{pipeline_id}/versions/{version_id}/steps/reorder",
        json={"step_ids": [step_ids[1], step_ids[0]], "preview_limit": 50},
    )
    assert reorder.status_code == 200
    payload = reorder.json()
    assert [step["step_id"] for step in payload["steps"]] == [step_ids[1], step_ids[0]]


def test_reorder_steps_invalid_dependency_returns_409(client: TestClient):
    _, pipeline_id, version_id = _create_project_and_pipeline(client)
    response_1 = client.post(
        f"/api/pipelines/{pipeline_id}/versions/{version_id}/steps",
        json={
            "step": {"type": "formula", "output_column": "income_x2", "params": {"expression": "income * 2"}},
            "preview_limit": 50,
        },
    )
    assert response_1.status_code == 200
    version_id = response_1.json()["new_version_id"]
    response_2 = client.post(
        f"/api/pipelines/{pipeline_id}/versions/{version_id}/steps",
        json={
            "step": {
                "type": "formula",
                "output_column": "income_x4",
                "params": {"expression": "income_x2 * 2"},
            },
            "preview_limit": 50,
        },
    )
    assert response_2.status_code == 200
    version_id = response_2.json()["new_version_id"]
    current = _get_current_version_detail(client, pipeline_id)
    step_ids = [step["step_id"] for step in current["steps"]]

    reorder = client.post(
        f"/api/pipelines/{pipeline_id}/versions/{version_id}/steps/reorder",
        json={"step_ids": [step_ids[1], step_ids[0]], "preview_limit": 50},
    )
    assert reorder.status_code == 409
    detail = reorder.json()["detail"]
    assert "affected_columns" in detail


def test_non_owner_cannot_get_pipeline(client: TestClient):
    _, pipeline_id, _ = _create_project_and_pipeline_for_user(client, "alice")
    response = client.get(f"/api/pipelines/{pipeline_id}", headers={"x-test-user": "bob"})
    assert response.status_code == 404


def test_admin_can_get_other_users_pipeline(client: TestClient):
    settings.admin_user_ids = "admin-user"
    _, pipeline_id, _ = _create_project_and_pipeline_for_user(client, "alice")
    response = client.get(f"/api/pipelines/{pipeline_id}", headers={"x-test-user": "admin-user"})
    assert response.status_code == 200
