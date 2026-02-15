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


def _create_project(client: TestClient, name: str, user: str = "alice") -> str:
    response = client.post(
        "/api/projects",
        json={"name": name},
        headers={"x-test-user": user},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _upload_csv(client: TestClient, project_id: str, user: str = "alice") -> str:
    csv_bytes = b"id,value\n1,10\n2,20\n"
    response = client.post(
        "/api/sources/upload",
        data={"project_id": project_id},
        files={"file": ("sample.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers={"x-test-user": user},
    )
    assert response.status_code == 201
    return response.json()["source_id"]


def test_sources_crud_enforces_ownership(client: TestClient):
    project_id = _create_project(client, "Sources Project", user="alice")
    source_id = _upload_csv(client, project_id, user="alice")

    get_owner = client.get(f"/api/sources/{source_id}", headers={"x-test-user": "alice"})
    assert get_owner.status_code == 200
    assert get_owner.json()["project_id"] == project_id

    get_other = client.get(f"/api/sources/{source_id}", headers={"x-test-user": "bob"})
    assert get_other.status_code == 404

    list_owner = client.get("/api/sources", params={"project_id": project_id}, headers={"x-test-user": "alice"})
    assert list_owner.status_code == 200
    assert len(list_owner.json()["sources"]) == 1

    list_other = client.get("/api/sources", params={"project_id": project_id}, headers={"x-test-user": "bob"})
    assert list_other.status_code == 404

    delete_other = client.delete(f"/api/sources/{source_id}", headers={"x-test-user": "bob"})
    assert delete_other.status_code == 404

    delete_owner = client.delete(f"/api/sources/{source_id}", headers={"x-test-user": "alice"})
    assert delete_owner.status_code == 204

    missing = client.get(f"/api/sources/{source_id}", headers={"x-test-user": "alice"})
    assert missing.status_code == 404


def test_admin_can_access_sources_across_owners(client: TestClient):
    settings.admin_user_ids = "admin-user"
    project_id = _create_project(client, "Admin Sources", user="alice")
    source_id = _upload_csv(client, project_id, user="alice")

    get_admin = client.get(f"/api/sources/{source_id}", headers={"x-test-user": "admin-user"})
    assert get_admin.status_code == 200

    list_admin = client.get("/api/sources", params={"project_id": project_id}, headers={"x-test-user": "admin-user"})
    assert list_admin.status_code == 200
    assert len(list_admin.json()["sources"]) == 1
    original_admin_user_ids = settings.admin_user_ids
