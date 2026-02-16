"""Tests for the Projects API endpoints."""

from __future__ import annotations

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import DataSimulatorError, settings
from app.core.auth import require_auth
from app.db.database import Base, get_db
from app.main import app


@pytest.fixture(scope="function")
def client():
    """Create test client with fresh database."""
    # Create in-memory SQLite for testing with StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Required for in-memory SQLite with threads
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        """Override database dependency for testing."""
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    original_admin_user_ids = settings.admin_user_ids

    async def override_require_auth(request: Request):
        """Override auth dependency for testing."""
        user = request.headers.get("x-test-user", "test-user")
        return {"sub": user, "user_id": user}

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_auth] = override_require_auth

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    settings.admin_user_ids = original_admin_user_ids
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


class TestProjectsCRUD:
    """Test project CRUD operations via API."""

    def test_list_projects_empty(self, client):
        """Test listing projects when none exist."""
        response = client.get("/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert data["projects"] == []
        assert data["total"] == 0

    def test_create_project(self, client):
        """Test creating a new project."""
        response = client.post(
            "/api/projects",
            json={"name": "Test Project", "description": "A test project"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] == "A test project"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_project_without_description(self, client):
        """Test creating a project without description."""
        response = client.post(
            "/api/projects",
            json={"name": "Test Project"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] is None

    def test_create_project_duplicate_name_fails(self, client):
        """Test that duplicate project names fail."""
        client.post("/api/projects", json={"name": "Duplicate"})
        response = client.post("/api/projects", json={"name": "Duplicate"})
        assert response.status_code == 409

    def test_get_project(self, client):
        """Test getting a project by ID."""
        create_response = client.post(
            "/api/projects",
            json={"name": "Test Project"},
        )
        project_id = create_response.json()["id"]

        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == "Test Project"

    def test_get_nonexistent_project_returns_404(self, client):
        """Test that getting a nonexistent project returns 404."""
        response = client.get("/api/projects/nonexistent-id")
        assert response.status_code == 404

    def test_update_project(self, client):
        """Test updating a project."""
        create_response = client.post(
            "/api/projects",
            json={"name": "Original Name"},
        )
        project_id = create_response.json()["id"]

        response = client.put(
            f"/api/projects/{project_id}",
            json={"name": "Updated Name", "description": "New description"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "New description"

    def test_delete_project(self, client):
        """Test deleting a project."""
        create_response = client.post(
            "/api/projects",
            json={"name": "To Delete"},
        )
        project_id = create_response.json()["id"]

        response = client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/projects/{project_id}")
        assert get_response.status_code == 404

    def test_list_projects(self, client):
        """Test listing multiple projects."""
        client.post("/api/projects", json={"name": "Project 1"})
        client.post("/api/projects", json={"name": "Project 2"})

        response = client.get("/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["projects"]) == 2

    def test_non_owner_cannot_access_project(self, client):
        create_response = client.post(
            "/api/projects",
            json={"name": "Private Project"},
            headers={"x-test-user": "alice"},
        )
        project_id = create_response.json()["id"]

        response = client.get(f"/api/projects/{project_id}", headers={"x-test-user": "bob"})
        assert response.status_code == 404

    def test_admin_can_access_other_users_project(self, client):
        settings.admin_user_ids = "admin-user"
        create_response = client.post(
            "/api/projects",
            json={"name": "Owner Project"},
            headers={"x-test-user": "alice"},
        )
        project_id = create_response.json()["id"]

        response = client.get(f"/api/projects/{project_id}", headers={"x-test-user": "admin-user"})
        assert response.status_code == 200

    def test_non_admin_project_list_is_owner_scoped(self, client):
        client.post("/api/projects", json={"name": "A1"}, headers={"x-test-user": "alice"})
        client.post("/api/projects", json={"name": "B1"}, headers={"x-test-user": "bob"})

        response = client.get("/api/projects", headers={"x-test-user": "alice"})
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_admin_project_list_sees_all_projects(self, client):
        settings.admin_user_ids = "admin-user"
        client.post("/api/projects", json={"name": "A2"}, headers={"x-test-user": "alice"})
        client.post("/api/projects", json={"name": "B2"}, headers={"x-test-user": "bob"})

        response = client.get("/api/projects", headers={"x-test-user": "admin-user"})
        assert response.status_code == 200
        assert response.json()["total"] == 2


class TestDAGVersions:
    """Test DAG version operations via API."""

    @pytest.fixture
    def project_with_dag(self, client):
        """Create a project with an initial DAG for testing."""
        response = client.post(
            "/api/projects",
            json={
                "name": "Test Project",
                "dag_definition": {
                    "nodes": [
                        {
                            "id": "x",
                            "name": "X",
                            "kind": "stochastic",
                            "dtype": "float",
                            "scope": "row",
                            "distribution": {"type": "normal", "params": {"mu": 0, "sigma": 1}},
                        }
                    ],
                    "edges": [],
                    "metadata": {"sample_size": 100, "seed": 42},
                },
            },
        )
        return response.json()

    def test_create_project_with_dag(self, client, project_with_dag):
        """Test creating a project with an initial DAG."""
        data = project_with_dag
        assert data["current_version"] is not None
        assert data["current_version"]["version_number"] == 1
        assert data["current_version"]["is_current"] is True
        assert data["current_dag"] is not None
        assert len(data["current_dag"]["nodes"]) == 1

    def test_create_project_with_complex_dag(self, client):
        """Test creating a project with a complex DAG (multiple nodes & edges)."""
        complex_dag = {
            "schema_version": "1.0",
            "nodes": [
                {
                    "id": "node_sales",
                    "name": "Sales",
                    "kind": "stochastic",
                    "dtype": "float",
                    "scope": "row",
                    "distribution": {"type": "normal", "params": {"mu": 100, "sigma": 20}},
                },
                {
                    "id": "node_tax",
                    "name": "Tax Rate",
                    "kind": "stochastic",
                    "dtype": "float",
                    "scope": "global",
                    "distribution": {"type": "uniform", "params": {"low": 0.05, "high": 0.10}},
                },
                {
                    "id": "node_total",
                    "name": "Total",
                    "kind": "deterministic",
                    "dtype": "float",
                    "scope": "row",
                    "formula": "node_sales * (1 + node_tax)",
                },
            ],
            "edges": [
                {"source": "node_sales", "target": "node_total"},
                {"source": "node_tax", "target": "node_total"},
            ],
            "metadata": {"sample_size": 200, "preview_rows": 10},
        }

        response = client.post(
            "/api/projects",
            json={"name": "Complex Project", "dag_definition": complex_dag},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["current_dag"] is not None
        assert len(data["current_dag"]["nodes"]) == 3
        assert len(data["current_dag"]["edges"]) == 2

        # Verify edge connectivity
        edges = data["current_dag"]["edges"]
        assert any(e["source"] == "node_sales" and e["target"] == "node_total" for e in edges)
        assert any(e["source"] == "node_tax" and e["target"] == "node_total" for e in edges)

    def test_list_versions(self, client, project_with_dag):
        """Test listing versions for a project."""
        project_id = project_with_dag["id"]

        response = client.get(f"/api/projects/{project_id}/versions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["versions"]) == 1
        assert data["versions"][0]["version_number"] == 1

    def test_create_new_version(self, client, project_with_dag):
        """Test creating a new DAG version."""
        project_id = project_with_dag["id"]

        response = client.post(
            f"/api/projects/{project_id}/versions",
            json={
                "dag_definition": {
                    "nodes": [
                        {
                            "id": "x",
                            "name": "X Modified",
                            "kind": "stochastic",
                            "dtype": "float",
                            "scope": "row",
                            "distribution": {"type": "normal", "params": {"mu": 10, "sigma": 2}},
                        }
                    ],
                    "edges": [],
                    "metadata": {"sample_size": 200, "seed": 123},
                },
                "set_current": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["version_number"] == 2
        assert data["is_current"] is True

    def test_get_specific_version(self, client, project_with_dag):
        """Test getting a specific version."""
        project_id = project_with_dag["id"]
        version_id = project_with_dag["current_version"]["id"]

        response = client.get(f"/api/projects/{project_id}/versions/{version_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["version_number"] == 1
        assert "dag_definition" in data

    def test_set_current_version(self, client, project_with_dag):
        """Test setting a version as current."""
        project_id = project_with_dag["id"]

        # Create a second version (not current)
        create_response = client.post(
            f"/api/projects/{project_id}/versions",
            json={
                "dag_definition": {
                    "nodes": [
                        {
                            "id": "y",
                            "name": "Y",
                            "kind": "stochastic",
                            "dtype": "float",
                            "scope": "row",
                            "distribution": {"type": "uniform", "params": {"low": 0, "high": 1}},
                        }
                    ],
                    "edges": [],
                    "metadata": {"sample_size": 50},
                },
                "set_current": False,
            },
        )
        version2_id = create_response.json()["id"]

        # Set it as current
        response = client.post(f"/api/projects/{project_id}/versions/{version2_id}/set-current")
        assert response.status_code == 200
        data = response.json()
        assert data["is_current"] is True

        # Verify project now has this as current
        project_response = client.get(f"/api/projects/{project_id}")
        project_data = project_response.json()
        assert project_data["current_version"]["id"] == version2_id

    def test_delete_project_cascades_to_versions(self, client, project_with_dag):
        """Test that deleting a project deletes all its versions."""
        project_id = project_with_dag["id"]

        # Delete project
        response = client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 204

        # Versions should be gone (project doesn't exist)
        versions_response = client.get(f"/api/projects/{project_id}/versions")
        assert versions_response.status_code == 404
