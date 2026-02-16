"""Tests for pipeline service and transform registry."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base
from app.db.models import DAGVersion, Pipeline, PipelineVersion, Project
from app.services.hashing import canonical_json_dumps, fingerprint_source, hash_steps
from app.services.pipeline_service import (
    PipelineDependencyConflictError,
    add_step,
    create_pipeline,
    delete_step,
    materialize,
    reorder_steps,
    resimulate,
)
from app.services.transform_registry import get_transform_registry, validate_safe_expression

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(engine):
    """Create a database session for testing."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_dag_definition():
    """Create a sample DAG definition for testing."""
    return {
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
        "context": {},
        "metadata": {"sample_size": 100, "seed": 42, "preview_rows": 10},
    }


@pytest.fixture
def project_with_dag(db_session: Session, sample_dag_definition):
    """Create a project with a DAG version."""
    project = Project(name="Test Project", description="Test")
    db_session.add(project)
    db_session.flush()

    dag_version = DAGVersion(
        project_id=project.id,
        version_number=1,
        dag_definition=sample_dag_definition,
        is_current=True,
    )
    db_session.add(dag_version)
    db_session.commit()
    db_session.refresh(project)
    db_session.refresh(dag_version)

    return project, dag_version


# =============================================================================
# Hashing Tests
# =============================================================================


class TestHashing:
    """Tests for hashing utilities."""

    def test_canonical_json_dumps_sorted_keys(self):
        """Test that canonical JSON dumps sorts keys."""
        obj1 = {"b": 1, "a": 2}
        obj2 = {"a": 2, "b": 1}
        assert canonical_json_dumps(obj1) == canonical_json_dumps(obj2)

    def test_fingerprint_source_deterministic(self):
        """Test that source fingerprints are deterministic."""
        fp1 = fingerprint_source("dag_123", 42, 1000)
        fp2 = fingerprint_source("dag_123", 42, 1000)
        assert fp1 == fp2

    def test_fingerprint_source_different_inputs(self):
        """Test that different inputs produce different fingerprints."""
        fp1 = fingerprint_source("dag_123", 42, 1000)
        fp2 = fingerprint_source("dag_123", 43, 1000)  # Different seed
        assert fp1 != fp2

    def test_hash_steps_deterministic(self):
        """Test that steps hashing is deterministic."""
        steps = [
            {"step_id": "s1", "type": "log", "output_column": "log_inc", "params": {"column": "income"}, "order": 1},
        ]
        h1 = hash_steps(steps)
        h2 = hash_steps(steps)
        assert h1 == h2

    def test_hash_steps_ignores_step_id(self):
        """Test that step_id changes don't affect hash (only semantic content)."""
        steps1 = [
            {"step_id": "s1", "type": "log", "output_column": "log_inc", "params": {"column": "income"}, "order": 1},
        ]
        steps2 = [
            {"step_id": "s2", "type": "log", "output_column": "log_inc", "params": {"column": "income"}, "order": 1},
        ]
        # Note: Our implementation does ignore step_id for hashing
        h1 = hash_steps(steps1)
        h2 = hash_steps(steps2)
        assert h1 == h2


# =============================================================================
# Transform Registry Tests
# =============================================================================


class TestTransformRegistry:
    """Tests for transform registry."""

    def test_list_all_transforms(self):
        """Test listing all available transforms."""
        registry = get_transform_registry()
        transforms = registry.list_all()
        
        assert len(transforms) >= 4  # formula, log, sqrt, exp, bin
        names = [t["name"] for t in transforms]
        assert "formula" in names
        assert "log" in names
        assert "sqrt" in names

    def test_get_transform_by_name(self):
        """Test getting a transform by name."""
        registry = get_transform_registry()
        
        formula = registry.get("formula")
        assert formula is not None
        assert formula.name == "formula"

        unknown = registry.get("unknown_transform")
        assert unknown is None


# =============================================================================
# Formula Safety Tests
# =============================================================================


class TestFormulaSafety:
    """Tests for safe formula evaluation."""

    def test_valid_expression_passes(self):
        """Test that valid expressions pass validation."""
        # Should not raise
        validate_safe_expression("log(income) + age * 2", ["income", "age"])
        validate_safe_expression("sqrt(abs(value))", ["value"])
        validate_safe_expression("where(x > 0, 1, 0)", ["x"])

    def test_disallowed_function_rejected(self):
        """Test that disallowed functions are rejected."""
        with pytest.raises(ValueError, match="Function not allowed"):
            validate_safe_expression("eval('import os')", ["data"])

    def test_unknown_column_rejected(self):
        """Test that references to unknown columns are rejected."""
        with pytest.raises(ValueError, match="Unknown column"):
            validate_safe_expression("unknown_col + 1", ["income", "age"])

    def test_expression_too_long_rejected(self):
        """Test that overly long expressions are rejected."""
        long_expr = "x + " * 200 + "x"
        with pytest.raises(ValueError, match="too long"):
            validate_safe_expression(long_expr, ["x"])

    def test_syntax_error_caught(self):
        """Test that syntax errors are caught."""
        with pytest.raises(ValueError, match="Invalid expression syntax"):
            validate_safe_expression("log(income +", ["income"])


# =============================================================================
# Pipeline Service Tests
# =============================================================================


class TestPipelineService:
    """Tests for pipeline service operations."""

    def test_create_pipeline(self, db_session: Session, project_with_dag):
        """Test creating a pipeline from a simulation source."""
        project, dag_version = project_with_dag

        result = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Test Pipeline",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )

        assert "pipeline_id" in result
        assert "version_id" in result
        assert "schema" in result
        assert len(result["schema"]) == 2  # income and age columns

        # Verify pipeline exists in DB
        pipeline = db_session.get(Pipeline, result["pipeline_id"])
        assert pipeline is not None
        assert pipeline.name == "Test Pipeline"
        assert pipeline.source_type == "simulation"

    def test_add_formula_step(self, db_session: Session, project_with_dag):
        """Test adding a formula step to a pipeline."""
        project, dag_version = project_with_dag

        # Create pipeline
        created = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Test Pipeline",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )

        # Add a formula step
        result = add_step(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=created["version_id"],
            step_spec={
                "type": "formula",
                "output_column": "income_per_year",
                "params": {"expression": "income * 12"},
            },
            preview_limit=10,
        )

        assert "new_version_id" in result
        assert result["new_version_id"] != created["version_id"]  # New version created
        assert "income_per_year" in result["added_columns"]
        
        # Check schema includes new column
        col_names = [c["name"] for c in result["schema"]]
        assert "income_per_year" in col_names

    def test_add_log_step(self, db_session: Session, project_with_dag):
        """Test adding a log transform step."""
        project, dag_version = project_with_dag

        created = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Test Pipeline",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )

        result = add_step(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=created["version_id"],
            step_spec={
                "type": "log",
                "output_column": "log_income",
                "params": {"column": "income"},
            },
            preview_limit=10,
        )

        assert "log_income" in result["added_columns"]
        assert result["warnings"] >= 0  # May have warnings for negative values

    def test_materialize_pipeline(self, db_session: Session, project_with_dag):
        """Test materializing pipeline data."""
        project, dag_version = project_with_dag

        created = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Test Pipeline",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )

        result = materialize(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=created["version_id"],
            limit=50,
        )

        assert len(result["rows"]) == 50
        assert len(result["schema"]) == 2

    def test_duplicate_column_rejected(self, db_session: Session, project_with_dag):
        """Test that adding a duplicate column without allow_overwrite fails."""
        project, dag_version = project_with_dag

        created = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Test Pipeline",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )

        with pytest.raises(ValueError, match="already exists"):
            add_step(
                db=db_session,
                pipeline_id=created["pipeline_id"],
                version_id=created["version_id"],
                step_spec={
                    "type": "formula",
                    "output_column": "income",  # Already exists
                    "params": {"expression": "income * 2"},
                },
            )

    def test_determinism_same_source_same_steps(self, db_session: Session, project_with_dag):
        """Test that same source + same steps produce identical hashes."""
        project, dag_version = project_with_dag

        # Create two pipelines with same config
        created1 = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Pipeline 1",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )

        created2 = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Pipeline 2",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )

        v1 = db_session.get(PipelineVersion, created1["version_id"])
        v2 = db_session.get(PipelineVersion, created2["version_id"])

        assert v1.source_fingerprint == v2.source_fingerprint
        assert v1.steps_hash == v2.steps_hash

    def test_delete_leaf_step_creates_new_version(self, db_session: Session, project_with_dag):
        """Deleting a leaf step should create a new version with that step removed."""
        project, dag_version = project_with_dag
        created = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Delete leaf pipeline",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )
        v2 = add_step(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=created["version_id"],
            step_spec={
                "type": "formula",
                "output_column": "income_x2",
                "params": {"expression": "income * 2"},
            },
        )
        v3 = add_step(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=v2["new_version_id"],
            step_spec={
                "type": "formula",
                "output_column": "income_x4",
                "params": {"expression": "income_x2 * 2"},
            },
        )

        result = delete_step(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=v3["new_version_id"],
            step_id=db_session.get(PipelineVersion, v3["new_version_id"]).steps[-1]["step_id"],
            cascade=False,
            preview_limit=20,
        )

        assert len(result["steps"]) == 1
        assert result["steps"][0]["output_column"] == "income_x2"
        assert result["removed_step_ids"]
        assert result["new_version_id"] != v3["new_version_id"]

    def test_delete_with_dependency_conflict_and_cascade(self, db_session: Session, project_with_dag):
        """Deleting a parent step without cascade should fail; with cascade should pass."""
        project, dag_version = project_with_dag
        created = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Cascade delete pipeline",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )
        v2 = add_step(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=created["version_id"],
            step_spec={
                "type": "formula",
                "output_column": "income_x2",
                "params": {"expression": "income * 2"},
            },
        )
        v3 = add_step(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=v2["new_version_id"],
            step_spec={
                "type": "formula",
                "output_column": "income_x4",
                "params": {"expression": "income_x2 * 2"},
            },
        )
        version = db_session.get(PipelineVersion, v3["new_version_id"])
        parent_step_id = version.steps[0]["step_id"]

        with pytest.raises(PipelineDependencyConflictError):
            delete_step(
                db=db_session,
                pipeline_id=created["pipeline_id"],
                version_id=v3["new_version_id"],
                step_id=parent_step_id,
                cascade=False,
            )

        cascaded = delete_step(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=v3["new_version_id"],
            step_id=parent_step_id,
            cascade=True,
        )
        assert cascaded["steps"] == []
        assert len(cascaded["removed_step_ids"]) == 2
        assert "income_x2" in cascaded["affected_columns"]
        assert "income_x4" in cascaded["affected_columns"]

    def test_reorder_steps_valid_and_invalid(self, db_session: Session, project_with_dag):
        """Reordering should allow dependency-safe moves and reject invalid dependency order."""
        project, dag_version = project_with_dag
        created = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Reorder pipeline",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )
        v2 = add_step(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=created["version_id"],
            step_spec={
                "type": "log",
                "output_column": "log_income",
                "params": {"column": "income"},
            },
        )
        v3 = add_step(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=v2["new_version_id"],
            step_spec={
                "type": "sqrt",
                "output_column": "sqrt_age",
                "params": {"column": "age"},
            },
        )

        v3_obj = db_session.get(PipelineVersion, v3["new_version_id"])
        original_hash = v3_obj.steps_hash
        ids = [step["step_id"] for step in v3_obj.steps]
        reordered = reorder_steps(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=v3["new_version_id"],
            step_ids=[ids[1], ids[0]],
        )
        assert [step["step_id"] for step in reordered["steps"]] == [ids[1], ids[0]]
        assert db_session.get(PipelineVersion, reordered["new_version_id"]).steps_hash != original_hash

        # Build dependency chain and assert invalid reorder is rejected.
        v4 = add_step(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=reordered["new_version_id"],
            step_spec={
                "type": "formula",
                "output_column": "income_chain",
                "params": {"expression": "log_income * 2"},
            },
        )
        v4_obj = db_session.get(PipelineVersion, v4["new_version_id"])
        chain_ids = [step["step_id"] for step in v4_obj.steps]
        with pytest.raises(PipelineDependencyConflictError):
            reorder_steps(
                db=db_session,
                pipeline_id=created["pipeline_id"],
                version_id=v4["new_version_id"],
                step_ids=[chain_ids[2], chain_ids[0], chain_ids[1]],
            )


# =============================================================================
# Resimulate Tests
# =============================================================================


class TestResimulate:
    """Tests for resimulate functionality."""

    def test_resimulate_creates_new_pipeline(self, db_session: Session, project_with_dag):
        """Test that resimulate creates a new pipeline."""
        project, dag_version = project_with_dag

        # Create original pipeline
        created = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Original Pipeline",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )

        # Resimulate with different seed
        result = resimulate(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=created["version_id"],
            seed=123,
            sample_size=100,
        )

        assert "new_pipeline_id" in result
        assert "version_id" in result
        assert result["new_pipeline_id"] != created["pipeline_id"]

        # Verify new pipeline exists
        new_pipeline = db_session.get(Pipeline, result["new_pipeline_id"])
        assert new_pipeline is not None
        assert "(resimulated)" in new_pipeline.name

    def test_resimulate_copies_steps(self, db_session: Session, project_with_dag):
        """Test that resimulate copies steps from source version."""
        project, dag_version = project_with_dag

        # Create pipeline and add a step
        created = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Original Pipeline",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )

        step_result = add_step(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=created["version_id"],
            step_spec={
                "type": "formula",
                "output_column": "double_income",
                "params": {"expression": "income * 2"},
            },
        )

        # Resimulate from version with step
        result = resimulate(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=step_result["new_version_id"],
            seed=123,
            sample_size=100,
        )

        # Verify steps were copied
        new_version = db_session.get(PipelineVersion, result["version_id"])
        assert new_version is not None
        assert len(new_version.steps) == 1
        assert new_version.steps[0]["output_column"] == "double_income"

    def test_resimulate_different_seed_changes_fingerprint(self, db_session: Session, project_with_dag):
        """Test that different seed produces different source fingerprint."""
        project, dag_version = project_with_dag

        created = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Original Pipeline",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )

        result = resimulate(
            db=db_session,
            pipeline_id=created["pipeline_id"],
            version_id=created["version_id"],
            seed=999,  # Different seed
            sample_size=100,
        )

        original_version = db_session.get(PipelineVersion, created["version_id"])
        new_version = db_session.get(PipelineVersion, result["version_id"])

        # Different seed should produce different fingerprint
        assert original_version.source_fingerprint != new_version.source_fingerprint
        # But same steps hash (same empty steps)
        assert original_version.steps_hash == new_version.steps_hash

    def test_resimulate_invalid_version_raises(self, db_session: Session, project_with_dag):
        """Test that resimulate with invalid version raises error."""
        project, dag_version = project_with_dag

        created = create_pipeline(
            db=db_session,
            project_id=project.id,
            name="Original Pipeline",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=100,
        )

        with pytest.raises(ValueError, match="not found"):
            resimulate(
                db=db_session,
                pipeline_id=created["pipeline_id"],
                version_id="invalid-version-id",
                seed=123,
                sample_size=100,
            )
