from __future__ import annotations

import io

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import require_auth
from app.db.database import Base, get_db
from app.db.models import Project
from app.main import app


@pytest.fixture(scope="function")
def test_context():
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

    async def override_require_auth(request: Request):
        user = request.headers.get("x-test-user", "user_A")
        return {"sub": user}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_auth] = override_require_auth

    with TestClient(app) as client:
        yield client, TestingSessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _sample_dag() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "id": "income",
                "name": "income",
                "kind": "stochastic",
                "dtype": "float",
                "scope": "row",
                "distribution": {"type": "normal", "params": {"mu": 50000, "sigma": 10000}},
            }
        ],
        "edges": [],
        "context": {},
        "metadata": {"sample_size": 100, "seed": 42, "preview_rows": 10},
    }


def _create_project(
    client: TestClient, *, user: str, name: str, visibility: str = "private", with_dag: bool = False,
) -> dict:
    payload = {"name": name, "visibility": visibility}
    if with_dag:
        payload["dag_definition"] = _sample_dag()
    response = client.post("/api/projects", json=payload, headers={"x-test-user": user})
    assert response.status_code == 201
    return response.json()


def _create_pipeline_simulation(client: TestClient, *, user: str, project_id: str, dag_version_id: str) -> dict:
    response = client.post(
        "/api/pipelines",
        json={
            "project_id": project_id,
            "name": "Pipeline 1",
            "source": {
                "type": "simulation",
                "dag_version_id": dag_version_id,
                "seed": 42,
                "sample_size": 100,
            },
        },
        headers={"x-test-user": user},
    )
    assert response.status_code == 201
    return response.json()


def _upload_source(client: TestClient, *, user: str, project_id: str) -> str:
    csv_bytes = b"a,b\n1,2\n3,4\n"
    response = client.post(
        "/api/sources/upload",
        data={"project_id": project_id},
        files={"file": ("dataset.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers={"x-test-user": user},
    )
    assert response.status_code == 201
    return response.json()["source_id"]


def test_private_project_denied_for_other_user(test_context):
    client, _ = test_context
    project = _create_project(client, user="user_A", name="A Private", visibility="private")

    denied = client.get(f"/api/projects/{project['id']}", headers={"x-test-user": "user_B"})
    assert denied.status_code == 404


def test_public_project_readable_but_not_mutable_by_other_user(test_context):
    client, _ = test_context
    project = _create_project(client, user="user_A", name="A Public", visibility="public")

    readable = client.get(f"/api/projects/{project['id']}", headers={"x-test-user": "user_B"})
    assert readable.status_code == 200

    denied_update = client.put(
        f"/api/projects/{project['id']}",
        json={"description": "hijack"},
        headers={"x-test-user": "user_B"},
    )
    assert denied_update.status_code == 404

    denied_delete = client.delete(f"/api/projects/{project['id']}", headers={"x-test-user": "user_B"})
    assert denied_delete.status_code == 404


def test_list_owner_only_and_discover_excludes_legacy(test_context):
    client, SessionLocal = test_context
    _create_project(client, user="user_A", name="A Public Discover", visibility="public")
    _create_project(client, user="user_A", name="A Private Hidden", visibility="private")
    _create_project(client, user="user_B", name="B Own 1", visibility="private")
    _create_project(client, user="user_B", name="B Own 2", visibility="public")

    with SessionLocal() as db:
        db.add(Project(name="Legacy Public", owner_user_id="legacy", visibility="public"))
        db.commit()

    mine = client.get("/api/projects", headers={"x-test-user": "user_B"})
    assert mine.status_code == 200
    mine_names = {p["name"] for p in mine.json()["projects"]}
    assert mine_names == {"B Own 1", "B Own 2"}

    discover = client.get("/api/projects/discover", headers={"x-test-user": "user_B"})
    assert discover.status_code == 200
    discover_names = {p["name"] for p in discover.json()["projects"]}
    assert discover_names == {"A Public Discover"}


def test_fork_public_project_creates_private_owned_fork(test_context):
    client, _ = test_context
    source = _create_project(client, user="user_A", name="Fork Source", visibility="public", with_dag=True)
    _create_pipeline_simulation(
        client,
        user="user_A",
        project_id=source["id"],
        dag_version_id=source["current_version"]["id"],
    )

    fork_response = client.post(f"/api/projects/{source['id']}/fork", headers={"x-test-user": "user_B"})
    assert fork_response.status_code == 201
    forked = fork_response.json()
    assert forked["owner_user_id"] == "user_B"
    assert forked["visibility"] == "private"
    assert forked["forked_from_project_id"] == source["id"]
    assert forked["name"] == "Fork Source (fork)"

    list_pipelines = client.get(
        "/api/pipelines",
        params={"project_id": forked["id"]},
        headers={"x-test-user": "user_B"},
    )
    assert list_pipelines.status_code == 200
    assert len(list_pipelines.json()["pipelines"]) == 1


def test_fork_upload_backed_project_is_blocked(test_context):
    client, _ = test_context
    source = _create_project(client, user="user_A", name="Upload Fork Source", visibility="public")
    source_id = _upload_source(client, user="user_A", project_id=source["id"])

    create_pipeline = client.post(
        "/api/pipelines",
        json={
            "project_id": source["id"],
            "name": "Upload Pipeline",
            "source": {"type": "upload", "source_id": source_id},
        },
        headers={"x-test-user": "user_A"},
    )
    assert create_pipeline.status_code == 201

    fork_response = client.post(f"/api/projects/{source['id']}/fork", headers={"x-test-user": "user_B"})
    assert fork_response.status_code == 400
    assert "upload-backed" in fork_response.json()["detail"]


def test_fork_unreadable_project_returns_404(test_context):
    client, _ = test_context
    source = _create_project(client, user="user_A", name="Private Source", visibility="private")

    fork_response = client.post(f"/api/projects/{source['id']}/fork", headers={"x-test-user": "user_B"})
    assert fork_response.status_code == 404


def test_pipeline_access_is_scoped_through_project_access(test_context):
    client, _ = test_context
    source = _create_project(client, user="user_A", name="Pipeline Scoped", visibility="private", with_dag=True)
    pipeline = _create_pipeline_simulation(
        client,
        user="user_A",
        project_id=source["id"],
        dag_version_id=source["current_version"]["id"],
    )

    denied_read = client.get(f"/api/pipelines/{pipeline['pipeline_id']}", headers={"x-test-user": "user_B"})
    assert denied_read.status_code == 404

    make_public = client.put(
        f"/api/projects/{source['id']}",
        json={"visibility": "public"},
        headers={"x-test-user": "user_A"},
    )
    assert make_public.status_code == 200

    allowed_read = client.get(f"/api/pipelines/{pipeline['pipeline_id']}", headers={"x-test-user": "user_B"})
    assert allowed_read.status_code == 200

    denied_write = client.post(
        f"/api/pipelines/{pipeline['pipeline_id']}/versions/{pipeline['current_version_id']}/steps",
        json={
            "step": {
                "type": "formula",
                "output_column": "x2",
                "params": {"expression": "income * 2"},
            }
        },
        headers={"x-test-user": "user_B"},
    )
    assert denied_write.status_code == 404


def test_fork_name_retry_limit_returns_409(test_context):
    client, _ = test_context
    source = _create_project(client, user="user_A", name="Name Collision", visibility="public")

    _create_project(client, user="user_A", name="Name Collision (fork)", visibility="private")
    for attempt in range(2, 11):
        _create_project(client, user="user_A", name=f"Name Collision (fork {attempt})", visibility="private")

    fork_response = client.post(f"/api/projects/{source['id']}/fork", headers={"x-test-user": "user_B"})
    assert fork_response.status_code == 409
