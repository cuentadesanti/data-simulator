"""
Comprehensive tests for database persistence in the Data Simulator.

Tests cover:
1. Project CRUD operations
2. DAGVersion immutability and versioning
3. Content hash deduplication
4. Draft autosave functionality
5. API endpoints for projects

Note: These tests are written in TDD style. Features are not yet implemented,
so most tests are marked with @pytest.mark.skip.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app

# Test client for API tests
client = TestClient(app)


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================


@pytest.fixture
def db_session():
    """Create a test database session.

    This fixture creates an in-memory SQLite database for testing.
    Each test gets a fresh database that is cleaned up after the test.
    """
    # This will be implemented once ORM models are created
    pytest.skip("Database models not implemented yet")

    # Future implementation:
    # engine = create_engine("sqlite:///:memory:")
    # Base.metadata.create_all(engine)
    # SessionLocal = sessionmaker(bind=engine)
    # session = SessionLocal()
    # try:
    #     yield session
    # finally:
    #     session.close()


@pytest.fixture
def sample_project_data() -> dict[str, Any]:
    """Sample project data for testing."""
    return {
        "name": "Test Project",
        "owner_id": None,  # Single-user for now
    }


@pytest.fixture
def sample_dag_graph() -> dict[str, Any]:
    """Sample DAG graph JSON for testing."""
    return {
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
                "kind": "deterministic",
                "dtype": "float",
                "scope": "row",
                "formula": "x * 2",
            },
        ],
        "edges": [{"source": "x", "target": "y"}],
        "metadata": {"sample_size": 100, "seed": 42},
    }


@pytest.fixture
def modified_dag_graph(sample_dag_graph: dict[str, Any]) -> dict[str, Any]:
    """Modified version of sample DAG (different content)."""
    modified = sample_dag_graph.copy()
    modified["nodes"][1]["formula"] = "x * 3"  # Changed formula
    return modified


def compute_content_hash(graph_json: dict[str, Any]) -> str:
    """
    Compute SHA256 hash of DAG content.

    Hash is computed from the model structure only (nodes/edges),
    not from layout or UI metadata.

    Args:
        graph_json: DAG graph JSON

    Returns:
        SHA256 hash as hex string
    """
    # Extract only the semantic content (nodes and edges)
    content = {
        "nodes": graph_json.get("nodes", []),
        "edges": graph_json.get("edges", []),
    }

    # Sort for consistent hashing
    content_str = json.dumps(content, sort_keys=True)
    return hashlib.sha256(content_str.encode()).hexdigest()


# =============================================================================
# 1. Project CRUD Tests
# =============================================================================


class TestProjectCRUD:
    """Tests for Project Create, Read, Update, Delete operations."""

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_create_project(self, db_session: Session, sample_project_data: dict):
        """Test creating a new project."""
        # This test will be implemented once Project model exists
        # from app.db.models import Project

        # Create project
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()
        # db_session.refresh(project)

        # Verify project was created
        # assert project.id is not None
        # assert isinstance(project.id, UUID)
        # assert project.name == sample_project_data["name"]
        # assert project.created_at is not None
        # assert project.updated_at is not None
        # assert project.created_at == project.updated_at
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_create_project_generates_uuid(self, db_session: Session):
        """Test that project IDs are UUIDs."""
        # from app.db.models import Project

        # project = Project(name="Test")
        # db_session.add(project)
        # db_session.commit()

        # assert isinstance(project.id, UUID)
        # assert project.id != UUID("00000000-0000-0000-0000-000000000000")
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_read_project_by_id(self, db_session: Session, sample_project_data: dict):
        """Test reading a project by ID."""
        # from app.db.models import Project

        # Create project
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()
        # project_id = project.id

        # Read project back
        # fetched = db_session.get(Project, project_id)
        # assert fetched is not None
        # assert fetched.id == project_id
        # assert fetched.name == sample_project_data["name"]
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_list_all_projects(self, db_session: Session):
        """Test listing all projects."""
        # from app.db.models import Project

        # Create multiple projects
        # project1 = Project(name="Project 1")
        # project2 = Project(name="Project 2")
        # db_session.add_all([project1, project2])
        # db_session.commit()

        # List all projects
        # projects = db_session.execute(select(Project)).scalars().all()
        # assert len(projects) == 2
        # project_names = {p.name for p in projects}
        # assert project_names == {"Project 1", "Project 2"}
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_update_project_name(self, db_session: Session, sample_project_data: dict):
        """Test updating a project's name."""
        # from app.db.models import Project

        # Create project
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()
        # original_updated_at = project.updated_at

        # Update name
        # project.name = "Updated Name"
        # db_session.commit()
        # db_session.refresh(project)

        # Verify update
        # assert project.name == "Updated Name"
        # assert project.updated_at > original_updated_at
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_delete_project(self, db_session: Session, sample_project_data: dict):
        """Test deleting a project."""
        # from app.db.models import Project

        # Create project
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()
        # project_id = project.id

        # Delete project
        # db_session.delete(project)
        # db_session.commit()

        # Verify deletion
        # fetched = db_session.get(Project, project_id)
        # assert fetched is None
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_project_name_uniqueness_per_owner(self, db_session: Session):
        """Test that project names must be unique per owner."""
        # from app.db.models import Project
        # from sqlalchemy.exc import IntegrityError

        # Same owner cannot have duplicate project names
        # project1 = Project(name="My Project", owner_id=None)
        # project2 = Project(name="My Project", owner_id=None)
        # db_session.add(project1)
        # db_session.commit()

        # db_session.add(project2)
        # with pytest.raises(IntegrityError):
        #     db_session.commit()
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_different_owners_can_have_same_project_name(self, db_session: Session):
        """Test that different owners can have projects with the same name."""
        # from app.db.models import Project

        # owner1_id = uuid4()
        # owner2_id = uuid4()

        # project1 = Project(name="My Project", owner_id=owner1_id)
        # project2 = Project(name="My Project", owner_id=owner2_id)
        # db_session.add_all([project1, project2])
        # db_session.commit()

        # Both should exist
        # assert project1.id != project2.id
        # assert project1.name == project2.name
        pass


# =============================================================================
# 2. DAGVersion Immutability Tests
# =============================================================================


class TestDAGVersionImmutability:
    """Tests for DAGVersion immutability and versioning."""

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_create_dag_version(
        self, db_session: Session, sample_project_data: dict, sample_dag_graph: dict
    ):
        """Test creating a DAG version."""
        # from app.db.models import Project, DAGVersion

        # Create project first
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()

        # Create version
        # content_hash = compute_content_hash(sample_dag_graph)
        # version = DAGVersion(
        #     project_id=project.id,
        #     version_number=1,
        #     content_hash=content_hash,
        #     graph_json=sample_dag_graph,
        #     message="Initial version"
        # )
        # db_session.add(version)
        # db_session.commit()

        # Verify version
        # assert version.id is not None
        # assert version.version_number == 1
        # assert version.content_hash == content_hash
        # assert version.graph_json == sample_dag_graph
        # assert version.created_at is not None
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_dag_versions_are_insert_only(
        self, db_session: Session, sample_project_data: dict, sample_dag_graph: dict
    ):
        """Test that DAG versions cannot be updated (INSERT-only)."""
        # from app.db.models import Project, DAGVersion

        # Create project and version
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()

        # version = DAGVersion(
        #     project_id=project.id,
        #     version_number=1,
        #     content_hash=compute_content_hash(sample_dag_graph),
        #     graph_json=sample_dag_graph,
        # )
        # db_session.add(version)
        # db_session.commit()

        # Attempt to modify version should be prevented
        # This could be enforced via:
        # 1. Database trigger
        # 2. ORM event listener
        # 3. Application-level check

        # Example: Try to modify graph_json
        # original_graph = version.graph_json
        # version.graph_json = {"nodes": [], "edges": []}

        # Should raise error or be prevented
        # with pytest.raises(Exception):  # Specific exception TBD
        #     db_session.commit()
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_version_numbers_auto_increment_per_project(
        self, db_session: Session, sample_project_data: dict, sample_dag_graph: dict
    ):
        """Test that version numbers auto-increment per project."""
        # from app.db.models import Project, DAGVersion

        # Create project
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()

        # Create multiple versions
        # version1 = DAGVersion(
        #     project_id=project.id,
        #     version_number=1,
        #     content_hash=compute_content_hash(sample_dag_graph),
        #     graph_json=sample_dag_graph,
        # )
        # modified_graph = sample_dag_graph.copy()
        # modified_graph["nodes"][0]["name"] = "Modified"
        # version2 = DAGVersion(
        #     project_id=project.id,
        #     version_number=2,
        #     content_hash=compute_content_hash(modified_graph),
        #     graph_json=modified_graph,
        # )

        # db_session.add_all([version1, version2])
        # db_session.commit()

        # Verify version numbers
        # assert version1.version_number == 1
        # assert version2.version_number == 2
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_different_projects_have_independent_version_numbers(
        self, db_session: Session, sample_dag_graph: dict
    ):
        """Test that version numbers are independent per project."""
        # from app.db.models import Project, DAGVersion

        # Create two projects
        # project1 = Project(name="Project 1")
        # project2 = Project(name="Project 2")
        # db_session.add_all([project1, project2])
        # db_session.commit()

        # Create version 1 for both projects
        # version1_p1 = DAGVersion(
        #     project_id=project1.id,
        #     version_number=1,
        #     content_hash=compute_content_hash(sample_dag_graph),
        #     graph_json=sample_dag_graph,
        # )
        # version1_p2 = DAGVersion(
        #     project_id=project2.id,
        #     version_number=1,
        #     content_hash=compute_content_hash(sample_dag_graph),
        #     graph_json=sample_dag_graph,
        # )

        # db_session.add_all([version1_p1, version1_p2])
        # db_session.commit()

        # Both should have version_number=1
        # assert version1_p1.version_number == 1
        # assert version1_p2.version_number == 1
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_get_latest_version_for_project(
        self, db_session: Session, sample_project_data: dict, sample_dag_graph: dict
    ):
        """Test retrieving the latest version for a project."""
        # from app.db.models import Project, DAGVersion

        # Create project with multiple versions
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()

        # for i in range(1, 4):
        #     version = DAGVersion(
        #         project_id=project.id,
        #         version_number=i,
        #         content_hash=compute_content_hash(sample_dag_graph),
        #         graph_json=sample_dag_graph,
        #     )
        #     db_session.add(version)
        # db_session.commit()

        # Get latest version
        # latest = (
        #     db_session.execute(
        #         select(DAGVersion)
        #         .where(DAGVersion.project_id == project.id)
        #         .order_by(DAGVersion.version_number.desc())
        #         .limit(1)
        #     )
        #     .scalar_one()
        # )

        # assert latest.version_number == 3
        pass


# =============================================================================
# 3. Content Hash Deduplication Tests
# =============================================================================


class TestContentHashDeduplication:
    """Tests for content hash-based deduplication."""

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_compute_content_hash_ignores_layout(self):
        """Test that content hash only considers model structure, not layout."""
        graph1 = {
            "nodes": [{"id": "x", "name": "X"}],
            "edges": [],
            "layout": {"x": {"x": 100, "y": 200}},
        }

        graph2 = {
            "nodes": [{"id": "x", "name": "X"}],
            "edges": [],
            "layout": {"x": {"x": 300, "y": 400}},  # Different layout
        }

        hash1 = compute_content_hash(graph1)
        hash2 = compute_content_hash(graph2)

        assert hash1 == hash2, "Content hash should ignore layout differences"

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_compute_content_hash_detects_model_changes(
        self, sample_dag_graph: dict, modified_dag_graph: dict
    ):
        """Test that content hash changes when model structure changes."""
        hash1 = compute_content_hash(sample_dag_graph)
        hash2 = compute_content_hash(modified_dag_graph)

        assert hash1 != hash2, "Content hash should change when model changes"

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_duplicate_content_hash_prevents_new_version(
        self, db_session: Session, sample_project_data: dict, sample_dag_graph: dict
    ):
        """Test that duplicate content_hash prevents creating a new version."""
        # from app.db.models import Project, DAGVersion
        # from app.services.version_service import create_version

        # Create project
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()

        # Create first version
        # version1 = create_version(
        #     db_session, project.id, sample_dag_graph, "Initial version"
        # )
        # assert version1.version_number == 1

        # Try to create version with same content
        # version2 = create_version(
        #     db_session, project.id, sample_dag_graph, "Duplicate content"
        # )

        # Should return existing version, not create new one
        # assert version2.id == version1.id
        # assert version2.version_number == 1
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_different_content_hash_creates_new_version(
        self,
        db_session: Session,
        sample_project_data: dict,
        sample_dag_graph: dict,
        modified_dag_graph: dict,
    ):
        """Test that different content_hash creates a new version."""
        # from app.db.models import Project
        # from app.services.version_service import create_version

        # Create project
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()

        # Create first version
        # version1 = create_version(
        #     db_session, project.id, sample_dag_graph, "Version 1"
        # )
        # assert version1.version_number == 1

        # Create version with different content
        # version2 = create_version(
        #     db_session, project.id, modified_dag_graph, "Version 2"
        # )

        # Should create new version
        # assert version2.id != version1.id
        # assert version2.version_number == 2
        # assert version2.content_hash != version1.content_hash
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_content_hash_is_sha256(self, sample_dag_graph: dict):
        """Test that content hash is a valid SHA256 hex string."""
        content_hash = compute_content_hash(sample_dag_graph)

        # SHA256 produces 64 hex characters
        assert len(content_hash) == 64
        assert all(c in "0123456789abcdef" for c in content_hash)


# =============================================================================
# 4. Draft Autosave Tests
# =============================================================================


class TestDraftAutosave:
    """Tests for draft autosave functionality."""

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_create_draft(
        self, db_session: Session, sample_project_data: dict, sample_dag_graph: dict
    ):
        """Test creating a draft."""
        # from app.db.models import Project, Draft

        # Create project
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()

        # Create draft
        # draft = Draft(
        #     project_id=project.id,
        #     graph_json=sample_dag_graph,
        # )
        # db_session.add(draft)
        # db_session.commit()

        # Verify draft
        # assert draft.project_id == project.id
        # assert draft.graph_json == sample_dag_graph
        # assert draft.updated_at is not None
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_one_draft_per_project(
        self, db_session: Session, sample_project_data: dict, sample_dag_graph: dict
    ):
        """Test that only one draft exists per project."""
        # from app.db.models import Project, Draft
        # from sqlalchemy.exc import IntegrityError

        # Create project
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()

        # Create first draft
        # draft1 = Draft(project_id=project.id, graph_json=sample_dag_graph)
        # db_session.add(draft1)
        # db_session.commit()

        # Try to create second draft for same project
        # draft2 = Draft(project_id=project.id, graph_json={})
        # db_session.add(draft2)

        # Should fail due to unique constraint on project_id
        # with pytest.raises(IntegrityError):
        #     db_session.commit()
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_draft_upsert_behavior(
        self,
        db_session: Session,
        sample_project_data: dict,
        sample_dag_graph: dict,
        modified_dag_graph: dict,
    ):
        """Test draft upsert (update if exists, insert if not)."""
        # from app.db.models import Project, Draft
        # from app.services.draft_service import upsert_draft

        # Create project
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()

        # First upsert - should insert
        # draft1 = upsert_draft(db_session, project.id, sample_dag_graph)
        # assert draft1.graph_json == sample_dag_graph
        # updated_at_1 = draft1.updated_at

        # Second upsert - should update
        # draft2 = upsert_draft(db_session, project.id, modified_dag_graph)
        # assert draft2.project_id == draft1.project_id
        # assert draft2.graph_json == modified_dag_graph
        # assert draft2.updated_at > updated_at_1

        # Should still be only one draft
        # drafts = db_session.execute(
        #     select(Draft).where(Draft.project_id == project.id)
        # ).scalars().all()
        # assert len(drafts) == 1
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_draft_updates_timestamp(
        self, db_session: Session, sample_project_data: dict, sample_dag_graph: dict
    ):
        """Test that draft updates timestamp on each save."""
        # from app.db.models import Project, Draft
        # import time

        # Create project and draft
        # project = Project(**sample_project_data)
        # draft = Draft(project_id=project.id, graph_json=sample_dag_graph)
        # db_session.add_all([project, draft])
        # db_session.commit()
        # original_updated_at = draft.updated_at

        # Wait a bit and update
        # time.sleep(0.1)
        # draft.graph_json = {"nodes": [], "edges": []}
        # db_session.commit()
        # db_session.refresh(draft)

        # Timestamp should be updated
        # assert draft.updated_at > original_updated_at
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_draft_independent_from_versions(
        self, db_session: Session, sample_project_data: dict, sample_dag_graph: dict
    ):
        """Test that draft is independent from versions."""
        # from app.db.models import Project, DAGVersion, Draft

        # Create project
        # project = Project(**sample_project_data)
        # db_session.add(project)
        # db_session.commit()

        # Create a version
        # version = DAGVersion(
        #     project_id=project.id,
        #     version_number=1,
        #     content_hash=compute_content_hash(sample_dag_graph),
        #     graph_json=sample_dag_graph,
        # )
        # db_session.add(version)
        # db_session.commit()

        # Create a draft with different content
        # modified_graph = sample_dag_graph.copy()
        # modified_graph["nodes"][0]["name"] = "Draft Version"
        # draft = Draft(project_id=project.id, graph_json=modified_graph)
        # db_session.add(draft)
        # db_session.commit()

        # Both should exist independently
        # assert version.graph_json != draft.graph_json
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_delete_project_cascades_to_draft(
        self, db_session: Session, sample_project_data: dict, sample_dag_graph: dict
    ):
        """Test that deleting a project deletes its draft."""
        # from app.db.models import Project, Draft

        # Create project and draft
        # project = Project(**sample_project_data)
        # draft = Draft(project_id=project.id, graph_json=sample_dag_graph)
        # db_session.add_all([project, draft])
        # db_session.commit()
        # project_id = project.id

        # Delete project
        # db_session.delete(project)
        # db_session.commit()

        # Draft should be deleted too (cascade)
        # remaining_drafts = db_session.execute(
        #     select(Draft).where(Draft.project_id == project_id)
        # ).scalars().all()
        # assert len(remaining_drafts) == 0
        pass


# =============================================================================
# 5. API Endpoint Tests
# =============================================================================


class TestProjectAPIEndpoints:
    """Tests for /api/projects endpoints."""

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_get_projects_empty(self):
        """Test GET /api/projects returns empty list initially."""
        response = client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_create_project_via_api(self, sample_project_data: dict):
        """Test POST /api/projects creates a project."""
        response = client.post("/api/projects", json=sample_project_data)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_project_data["name"]
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_create_project_returns_uuid(self, sample_project_data: dict):
        """Test that created project has valid UUID."""
        response = client.post("/api/projects", json=sample_project_data)

        data = response.json()
        project_id = data["id"]

        # Should be valid UUID
        try:
            UUID(project_id)
        except ValueError:
            pytest.fail(f"Invalid UUID: {project_id}")

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_get_projects_returns_list(self, sample_project_data: dict):
        """Test GET /api/projects returns list of projects."""
        # Create a few projects
        client.post("/api/projects", json={"name": "Project 1"})
        client.post("/api/projects", json={"name": "Project 2"})

        response = client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

        names = {p["name"] for p in data}
        assert names == {"Project 1", "Project 2"}

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_get_project_by_id(self, sample_project_data: dict):
        """Test GET /api/projects/{id} returns specific project."""
        # Create project
        create_response = client.post("/api/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Get project
        response = client.get(f"/api/projects/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == sample_project_data["name"]

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_get_nonexistent_project_returns_404(self):
        """Test GET /api/projects/{id} with nonexistent ID returns 404."""
        fake_id = str(uuid4())
        response = client.get(f"/api/projects/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_update_project_via_api(self, sample_project_data: dict):
        """Test PUT /api/projects/{id} updates project."""
        # Create project
        create_response = client.post("/api/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Update project
        update_data = {"name": "Updated Name"}
        response = client.put(f"/api/projects/{project_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["updated_at"] > data["created_at"]

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_update_nonexistent_project_returns_404(self):
        """Test PUT /api/projects/{id} with nonexistent ID returns 404."""
        fake_id = str(uuid4())
        update_data = {"name": "New Name"}
        response = client.put(f"/api/projects/{fake_id}", json=update_data)

        assert response.status_code == 404

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_delete_project_via_api(self, sample_project_data: dict):
        """Test DELETE /api/projects/{id} deletes project."""
        # Create project
        create_response = client.post("/api/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Delete project
        response = client.delete(f"/api/projects/{project_id}")

        assert response.status_code == 204

        # Verify deletion
        get_response = client.get(f"/api/projects/{project_id}")
        assert get_response.status_code == 404

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_delete_nonexistent_project_returns_404(self):
        """Test DELETE /api/projects/{id} with nonexistent ID returns 404."""
        fake_id = str(uuid4())
        response = client.delete(f"/api/projects/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_create_project_with_duplicate_name_fails(self):
        """Test that creating project with duplicate name fails."""
        project_data = {"name": "Duplicate Name"}

        # Create first project
        response1 = client.post("/api/projects", json=project_data)
        assert response1.status_code == 201

        # Try to create second with same name
        response2 = client.post("/api/projects", json=project_data)
        assert response2.status_code == 400

        error_data = response2.json()
        assert "name" in error_data["detail"].lower()

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_create_project_validates_required_fields(self):
        """Test that creating project requires name field."""
        response = client.post("/api/projects", json={})

        assert response.status_code == 422  # Validation error

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_get_project_includes_version_count(self, sample_project_data: dict):
        """Test that GET /api/projects/{id} includes version count."""
        # Create project
        create_response = client.post("/api/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Get project
        response = client.get(f"/api/projects/{project_id}")

        data = response.json()
        assert "version_count" in data
        assert data["version_count"] == 0  # No versions yet

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_get_project_includes_has_draft(self, sample_project_data: dict):
        """Test that GET /api/projects/{id} includes has_draft flag."""
        # Create project
        create_response = client.post("/api/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Get project
        response = client.get(f"/api/projects/{project_id}")

        data = response.json()
        assert "has_draft" in data
        assert data["has_draft"] is False  # No draft yet


# =============================================================================
# 6. Integration Tests
# =============================================================================


class TestPersistenceIntegration:
    """Integration tests for the complete persistence workflow."""

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_full_workflow_create_project_with_versions(
        self, sample_project_data: dict, sample_dag_graph: dict, modified_dag_graph: dict
    ):
        """Test complete workflow: create project, save draft, create versions."""
        # 1. Create project
        create_response = client.post("/api/projects", json=sample_project_data)
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # 2. Save draft
        draft_response = client.put(
            f"/api/projects/{project_id}/draft", json={"graph_json": sample_dag_graph}
        )
        assert draft_response.status_code == 200

        # 3. Create first version
        version1_response = client.post(
            f"/api/projects/{project_id}/versions",
            json={"graph_json": sample_dag_graph, "message": "Initial version"},
        )
        assert version1_response.status_code == 201
        version1 = version1_response.json()
        assert version1["version_number"] == 1

        # 4. Update draft
        draft2_response = client.put(
            f"/api/projects/{project_id}/draft", json={"graph_json": modified_dag_graph}
        )
        assert draft2_response.status_code == 200

        # 5. Create second version
        version2_response = client.post(
            f"/api/projects/{project_id}/versions",
            json={"graph_json": modified_dag_graph, "message": "Updated formula"},
        )
        assert version2_response.status_code == 201
        version2 = version2_response.json()
        assert version2["version_number"] == 2

        # 6. List versions
        versions_response = client.get(f"/api/projects/{project_id}/versions")
        assert versions_response.status_code == 200
        versions = versions_response.json()
        assert len(versions) == 2

        # 7. Get specific version
        version_response = client.get(
            f"/api/projects/{project_id}/versions/{version1['version_number']}"
        )
        assert version_response.status_code == 200

        # 8. Delete project (should cascade to drafts and versions)
        delete_response = client.delete(f"/api/projects/{project_id}")
        assert delete_response.status_code == 204

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_draft_to_version_promotion(self, sample_project_data: dict, sample_dag_graph: dict):
        """Test promoting a draft to a version."""
        # Create project
        create_response = client.post("/api/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Save draft
        client.put(f"/api/projects/{project_id}/draft", json={"graph_json": sample_dag_graph})

        # Promote draft to version
        response = client.post(
            f"/api/projects/{project_id}/versions/from-draft",
            json={"message": "Promoted from draft"},
        )

        assert response.status_code == 201
        version = response.json()
        assert version["version_number"] == 1
        assert version["graph_json"] == sample_dag_graph

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_version_rollback(
        self, sample_project_data: dict, sample_dag_graph: dict, modified_dag_graph: dict
    ):
        """Test rolling back to a previous version."""
        # Create project
        create_response = client.post("/api/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Create version 1
        client.post(
            f"/api/projects/{project_id}/versions",
            json={"graph_json": sample_dag_graph, "message": "Version 1"},
        )

        # Create version 2
        client.post(
            f"/api/projects/{project_id}/versions",
            json={"graph_json": modified_dag_graph, "message": "Version 2"},
        )

        # Rollback to version 1 (create new version with old content)
        response = client.post(
            f"/api/projects/{project_id}/versions/1/rollback",
            json={"message": "Rollback to version 1"},
        )

        # Should create version 3 with same content as version 1
        # (but NOT with same content_hash, since message is different)
        assert response.status_code == 201
        version3 = response.json()
        assert version3["version_number"] == 3
        assert version3["graph_json"] == sample_dag_graph


# =============================================================================
# 7. Performance and Edge Case Tests
# =============================================================================


class TestPersistenceEdgeCases:
    """Edge case and performance tests."""

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_large_graph_json_storage(self, sample_project_data: dict):
        """Test storing large graph JSON (many nodes)."""
        # Create large graph
        large_graph = {
            "nodes": [
                {
                    "id": f"node_{i}",
                    "name": f"Node {i}",
                    "kind": "stochastic",
                    "dtype": "float",
                    "scope": "row",
                    "distribution": {"type": "normal", "params": {"mu": 0, "sigma": 1}},
                }
                for i in range(500)  # 500 nodes
            ],
            "edges": [],
            "metadata": {"sample_size": 100},
        }

        # Create project and version
        create_response = client.post("/api/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        version_response = client.post(
            f"/api/projects/{project_id}/versions",
            json={"graph_json": large_graph, "message": "Large graph"},
        )

        assert version_response.status_code == 201

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_concurrent_draft_updates(self, sample_project_data: dict, sample_dag_graph: dict):
        """Test concurrent draft updates (last write wins)."""
        # This would require async test setup
        # Create project
        # Simulate concurrent draft updates
        # Verify last write wins
        pass

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_project_with_many_versions(self, sample_project_data: dict, sample_dag_graph: dict):
        """Test project with many versions."""
        # Create project
        create_response = client.post("/api/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Create 100 versions
        for i in range(100):
            modified_graph = sample_dag_graph.copy()
            modified_graph["nodes"][0]["name"] = f"Version {i}"

            client.post(
                f"/api/projects/{project_id}/versions",
                json={"graph_json": modified_graph, "message": f"Version {i}"},
            )

        # List versions
        response = client.get(f"/api/projects/{project_id}/versions")
        assert response.status_code == 200
        versions = response.json()
        assert len(versions) == 100

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_empty_graph_json(self, sample_project_data: dict):
        """Test handling empty graph JSON."""
        create_response = client.post("/api/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        empty_graph = {"nodes": [], "edges": [], "metadata": {"sample_size": 0}}

        response = client.put(f"/api/projects/{project_id}/draft", json={"graph_json": empty_graph})

        # Should accept empty graph
        assert response.status_code == 200

    @pytest.mark.skip(reason="Persistence not implemented yet")
    def test_version_creation_with_same_content_hash(
        self, sample_project_data: dict, sample_dag_graph: dict
    ):
        """Test that creating version with same content_hash returns existing version."""
        # Create project
        create_response = client.post("/api/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Create first version
        response1 = client.post(
            f"/api/projects/{project_id}/versions",
            json={"graph_json": sample_dag_graph, "message": "Version 1"},
        )
        version1 = response1.json()

        # Try to create version with same content (but different message)
        response2 = client.post(
            f"/api/projects/{project_id}/versions",
            json={"graph_json": sample_dag_graph, "message": "Version 1 duplicate"},
        )
        version2 = response2.json()

        # Should return existing version, not create new one
        assert version2["id"] == version1["id"]
        assert version2["version_number"] == version1["version_number"]
