from __future__ import annotations

import io

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


def _create_project(client: TestClient, name: str, user: str) -> str:
    response = client.post("/api/projects", json={"name": name}, headers={"x-test-user": user})
    assert response.status_code == 201
    return response.json()["id"]


def _upload_source(client: TestClient, project_id: str, user: str) -> str:
    csv_bytes = b"a,b\n1,2\n3,4\n"
    response = client.post(
        "/api/sources/upload",
        data={"project_id": project_id},
        files={"file": ("dataset.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers={"x-test-user": user},
    )
    assert response.status_code == 201
    return response.json()["source_id"]


def test_create_pipeline_from_upload_happy_path(client: TestClient):
    project_id = _create_project(client, "Pipeline Upload Project", user="alice")
    source_id = _upload_source(client, project_id, user="alice")

    response = client.post(
        "/api/pipelines",
        json={
            "project_id": project_id,
            "name": "Upload Pipeline",
            "source": {
                "type": "upload",
                "source_id": source_id,
            },
        },
        headers={"x-test-user": "alice"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "pipeline_id" in body
    assert "current_version_id" in body
    assert [col["name"] for col in body["schema"]] == ["a", "b"]


def test_create_pipeline_from_upload_forbidden_for_non_owner(client: TestClient):
    project_id = _create_project(client, "Owned Project", user="alice")
    source_id = _upload_source(client, project_id, user="alice")

    response = client.post(
        "/api/pipelines",
        json={
            "project_id": project_id,
            "name": "Forbidden Upload Pipeline",
            "source": {
                "type": "upload",
                "source_id": source_id,
            },
        },
        headers={"x-test-user": "bob"},
    )
    assert response.status_code == 404


def test_create_pipeline_from_upload_rejects_cross_project_source(client: TestClient):
    project_a = _create_project(client, "Project A", user="alice")
    project_b = _create_project(client, "Project B", user="alice")
    source_id = _upload_source(client, project_a, user="alice")

    response = client.post(
        "/api/pipelines",
        json={
            "project_id": project_b,
            "name": "Cross Project Upload Pipeline",
            "source": {
                "type": "upload",
                "source_id": source_id,
            },
        },
        headers={"x-test-user": "alice"},
    )
    assert response.status_code == 400


def test_admin_can_create_pipeline_from_other_users_source(client: TestClient):
    settings.admin_user_ids = "admin-user"
    project_id = _create_project(client, "Owner Project Admin", user="alice")
    source_id = _upload_source(client, project_id, user="alice")

    response = client.post(
        "/api/pipelines",
        json={
            "project_id": project_id,
            "name": "Admin Upload Pipeline",
            "source": {
                "type": "upload",
                "source_id": source_id,
            },
        },
        headers={"x-test-user": "admin-user"},
    )
    assert response.status_code == 201
    original_admin_user_ids = settings.admin_user_ids
