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
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    original_admin_user_ids = settings.admin_user_ids

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def override_require_auth(request: Request):
        user = request.headers.get("x-test-user", "test-user")
        return {"sub": user}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_auth] = override_require_auth

    with TestClient(app) as test_client:
        yield test_client

    settings.admin_user_ids = original_admin_user_ids
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _create_pipeline(client: TestClient, user: str) -> str:
    dag = {
        "schema_version": "1.0",
        "nodes": [
            {
                "id": "x",
                "name": "X",
                "kind": "stochastic",
                "dtype": "float",
                "scope": "row",
                "distribution": {"type": "normal", "params": {"mu": 0, "sigma": 1}},
            },
            {
                "id": "y",
                "name": "Y",
                "kind": "stochastic",
                "dtype": "float",
                "scope": "row",
                "distribution": {"type": "normal", "params": {"mu": 5, "sigma": 2}},
            },
        ],
        "edges": [],
        "metadata": {"sample_size": 100, "seed": 42},
    }
    project = client.post(
        "/api/projects", json={"name": f"{user}-modeling", "dag_definition": dag},
        headers={"x-test-user": user},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]
    dag_version_id = project.json()["current_version"]["id"]

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
    return pipeline.json()["current_version_id"]


def _fit_model(client: TestClient, pipeline_version_id: str, user: str) -> str:
    response = client.post(
        "/api/modeling/fit",
        json={
            "pipeline_version_id": pipeline_version_id,
            "name": "lr-fit",
            "model_name": "linear_regression",
            "target": "y",
            "features": ["x"],
            "model_params": {},
            "split_spec": {"type": "random", "test_size": 0.2, "random_state": 42},
        },
        headers={"x-test-user": user},
    )
    assert response.status_code == 200
    return response.json()["model_id"]


def test_non_owner_cannot_access_model_fit(client: TestClient):
    version_id = _create_pipeline(client, "alice")
    model_id = _fit_model(client, version_id, "alice")

    response = client.get(f"/api/modeling/fits/{model_id}", headers={"x-test-user": "bob"})
    assert response.status_code == 404


def test_admin_can_access_model_fit_across_owners(client: TestClient):
    settings.admin_user_ids = "admin-user"
    version_id = _create_pipeline(client, "alice")
    model_id = _fit_model(client, version_id, "alice")

    response = client.get(f"/api/modeling/fits/{model_id}", headers={"x-test-user": "admin-user"})
    assert response.status_code == 200

    list_response = client.get("/api/modeling/fits", headers={"x-test-user": "admin-user"})
    assert list_response.status_code == 200
    assert list_response.json()["total_count"] >= 1

