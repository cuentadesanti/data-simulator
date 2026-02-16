"""Comprehensive tests for the modeling service.

This module tests the complete ML modeling workflow including
model fitting, prediction, and artifact management.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base
from app.db.models import DAGVersion, ModelFit, Project
from app.services import modeling_service, pipeline_service
from app.services.model_registry import get_model_registry

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
def sample_dag_with_target():
    """Create a DAG definition with features and targets for modeling.
    
    Uses column names without underscores since the sampler sanitizes them.
    """
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "id": "age",
                "name": "age",
                "kind": "stochastic",
                "dtype": "float",
                "scope": "row",
                "distribution": {"type": "normal", "params": {"mu": 30, "sigma": 10}},
            },
            {
                "id": "income",
                "name": "income",
                "kind": "stochastic",
                "dtype": "float",
                "scope": "row",
                "distribution": {"type": "normal", "params": {"mu": 50000, "sigma": 15000}},
            },
            {
                "id": "spending",
                "name": "spending",
                "kind": "stochastic",
                "dtype": "float",
                "scope": "row",
                "distribution": {"type": "normal", "params": {"mu": 2000, "sigma": 500}},
            },
            {
                "id": "churned",
                "name": "churned",
                "kind": "stochastic",
                "dtype": "int",
                "scope": "row",
                "distribution": {"type": "bernoulli", "params": {"p": 0.3}},
            },
        ],
        "edges": [],
        "context": {},
        "metadata": {"sample_size": 500, "seed": 42, "preview_rows": 10},
    }


@pytest.fixture
def project_with_pipeline(db_session: Session, sample_dag_with_target):
    """Create a project with a pipeline ready for modeling."""
    project = Project(name="Modeling Test Project", description="Test")
    db_session.add(project)
    db_session.flush()

    dag_version = DAGVersion(
        project_id=project.id,
        version_number=1,
        dag_definition=sample_dag_with_target,
        is_current=True,
    )
    db_session.add(dag_version)
    db_session.commit()
    db_session.refresh(project)
    db_session.refresh(dag_version)

    # Create pipeline
    result = pipeline_service.create_pipeline(
        db=db_session,
        project_id=project.id,
        name="Modeling Pipeline",
        source_type="simulation",
        dag_version_id=dag_version.id,
        seed=42,
        sample_size=500,
    )

    return project, dag_version, result["pipeline_id"], result["version_id"]


# =============================================================================
# Model Registry Tests
# =============================================================================


class TestModelRegistry:
    """Tests for the model registry."""

    def test_list_all_models(self):
        """Test listing all available model types."""
        registry = get_model_registry()
        models = registry.list_all()

        assert len(models) >= 1
        names = [m["name"] for m in models]
        assert "linear_regression" in names
        assert "logistic_regression" not in names

    def test_get_linear_regression(self):
        """Test getting linear regression model type."""
        registry = get_model_registry()
        model = registry.get("linear_regression")

        assert model is not None
        assert model.name == "linear_regression"
        assert model.task_type == "regression"

    def test_get_unknown_model(self):
        """Test getting an unknown model returns None."""
        registry = get_model_registry()
        model = registry.get("unknown_model_type")

        assert model is None

    def test_model_parameters(self):
        """Test that models expose their parameters."""
        registry = get_model_registry()
        model = registry.get("linear_regression")

        params = model.parameters
        assert len(params) >= 0


# =============================================================================
# Model Fitting Tests
# =============================================================================


class TestModelFitting:
    """Tests for fitting models on pipeline data."""

    def test_fit_linear_regression(self, db_session: Session, project_with_pipeline):
        """Test fitting a linear regression model."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Test Linear Model",
            model_name="linear_regression",
            target="spending",
            features=["age", "income"],
            model_params={},
            split_spec={"type": "random", "test_size": 0.2, "random_state": 42},
        )

        assert "model_id" in result
        assert "metrics" in result
        assert "r2" in result["metrics"]
        assert "rmse" in result["metrics"]
        assert "mae" in result["metrics"]

        # Check coefficients are returned
        assert "coefficients" in result
        assert result["coefficients"] is not None
        assert "age" in result["coefficients"]
        assert "income" in result["coefficients"]

    def test_fit_ridge_regression(self, db_session: Session, project_with_pipeline):
        """Test fitting a Ridge regression model."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Test Ridge Model",
            model_name="ridge",
            target="spending",
            features=["age", "income"],
            model_params={"alpha": 0.5},
            split_spec={"type": "random", "test_size": 0.2, "random_state": 42},
        )

        assert "model_id" in result
        assert "metrics" in result
        assert "r2" in result["metrics"]

    def test_fit_stores_artifact(self, db_session: Session, project_with_pipeline):
        """Test that fitting stores the model artifact."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Artifact Test Model",
            model_name="linear_regression",
            target="spending",
            features=["age", "income"],
        )

        # Check artifact is stored in database
        model_fit = db_session.get(ModelFit, result["model_id"])
        assert model_fit is not None
        assert model_fit.artifact_blob is not None
        assert len(model_fit.artifact_blob) > 0

    def test_fit_with_default_split_spec(self, db_session: Session, project_with_pipeline):
        """Test fitting with default split specification."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Default Split Model",
            model_name="linear_regression",
            target="spending",
            features=["age", "income"],
            # No split_spec provided - should use defaults
        )

        assert "model_id" in result
        assert "metrics" in result

    def test_fit_invalid_model_name(self, db_session: Session, project_with_pipeline):
        """Test that fitting with invalid model name fails."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        with pytest.raises(ValueError, match="Unknown model"):
            modeling_service.fit_model(
                db=db_session,
                pipeline_version_id=version_id,
                name="Invalid Model",
                model_name="nonexistent_model",
                target="spending",
                features=["age"],
            )

    def test_fit_invalid_version(self, db_session: Session, project_with_pipeline):
        """Test that fitting with invalid version ID fails."""
        with pytest.raises(ValueError, match="not found"):
            modeling_service.fit_model(
                db=db_session,
                pipeline_version_id="nonexistent-version-id",
                name="Invalid Version Model",
                model_name="linear_regression",
                target="spending",
                features=["age"],
            )

    def test_fit_invalid_target_column(self, db_session: Session, project_with_pipeline):
        """Test that fitting with invalid target column fails."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        with pytest.raises(ValueError, match="not found|missing"):
            modeling_service.fit_model(
                db=db_session,
                pipeline_version_id=version_id,
                name="Invalid Target Model",
                model_name="linear_regression",
                target="nonexistent_column",
                features=["age"],
            )

    def test_fit_invalid_feature_column(self, db_session: Session, project_with_pipeline):
        """Test that fitting with invalid feature column fails."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        with pytest.raises(ValueError, match="not found|missing"):
            modeling_service.fit_model(
                db=db_session,
                pipeline_version_id=version_id,
                name="Invalid Feature Model",
                model_name="linear_regression",
                target="spending",
                features=["nonexistent_feature"],
            )


# =============================================================================
# Prediction Tests
# =============================================================================


class TestPrediction:
    """Tests for generating predictions."""

    def test_predict_returns_values(self, db_session: Session, project_with_pipeline):
        """Test that predict returns prediction values."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        # First fit a model
        fit_result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Prediction Test Model",
            model_name="linear_regression",
            target="spending",
            features=["age", "income"],
        )

        # Then predict
        predict_result = modeling_service.predict(
            db=db_session,
            model_id=fit_result["model_id"],
            limit=100,
        )

        assert "predictions" in predict_result
        assert "preview_rows_with_pred" in predict_result
        assert len(predict_result["predictions"]) == 100
        assert len(predict_result["preview_rows_with_pred"]) == 100

    def test_predict_adds_prediction_column(self, db_session: Session, project_with_pipeline):
        """Test that predictions are included in preview rows."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        fit_result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Prediction Column Model",
            model_name="linear_regression",
            target="spending",
            features=["age", "income"],
        )

        predict_result = modeling_service.predict(
            db=db_session,
            model_id=fit_result["model_id"],
            limit=10,
        )

        # Each row should have the prediction column
        for row in predict_result["preview_rows_with_pred"]:
            assert "_prediction" in row

    def test_predict_invalid_model_id(self, db_session: Session, project_with_pipeline):
        """Test that predicting with invalid model ID fails."""
        with pytest.raises(ValueError, match="not found"):
            modeling_service.predict(
                db=db_session,
                model_id="nonexistent-model-id",
                limit=100,
            )

    def test_predict_with_different_limit(self, db_session: Session, project_with_pipeline):
        """Test prediction with different limit values."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        fit_result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Limit Test Model",
            model_name="linear_regression",
            target="spending",
            features=["age", "income"],
        )

        for limit in [10, 50, 100]:
            predict_result = modeling_service.predict(
                db=db_session,
                model_id=fit_result["model_id"],
                limit=limit,
            )
            assert len(predict_result["predictions"]) == limit


# =============================================================================
# Model Query Tests
# =============================================================================


class TestModelQueries:
    """Tests for querying model fits."""

    def test_get_model_fit(self, db_session: Session, project_with_pipeline):
        """Test getting model fit details."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        fit_result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Query Test Model",
            model_name="linear_regression",
            target="spending",
            features=["age", "income"],
        )

        model_detail = modeling_service.get_model_fit(db_session, fit_result["model_id"])

        assert model_detail is not None
        assert model_detail["id"] == fit_result["model_id"]
        assert model_detail["name"] == "Query Test Model"
        assert model_detail["model_type"] == "linear_regression"
        assert model_detail["task_type"] == "regression"
        assert model_detail["target_column"] == "spending"

    def test_get_nonexistent_model_fit(self, db_session: Session):
        """Test that getting nonexistent model returns None."""
        result = modeling_service.get_model_fit(db_session, "nonexistent-id")
        assert result is None

    def test_list_model_fits(self, db_session: Session, project_with_pipeline):
        """Test listing model fits."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        # Create multiple models
        for i in range(3):
            modeling_service.fit_model(
                db=db_session,
                pipeline_version_id=version_id,
                name=f"List Test Model {i}",
                model_name="linear_regression",
                target="spending",
                features=["age", "income"],
            )

        result = modeling_service.list_model_fits(db_session)

        assert result["total_count"] >= 3
        assert len(result["model_fits"]) >= 3

    def test_list_model_fits_by_version(self, db_session: Session, project_with_pipeline):
        """Test listing model fits filtered by pipeline version."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        # Create a model for this version
        modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Version Filter Model",
            model_name="linear_regression",
            target="spending",
            features=["age", "income"],
        )

        result = modeling_service.list_model_fits(db_session, pipeline_version_id=version_id)

        assert result["total_count"] >= 1
        assert len(result["model_fits"]) >= 1


# =============================================================================
# Integration Tests
# =============================================================================


class TestModelingIntegration:
    """Integration tests for the full modeling workflow."""

    def test_full_workflow(self, db_session: Session, project_with_pipeline):
        """Test the complete workflow: fit -> predict -> query."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        # 1. Fit model
        fit_result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Full Workflow Model",
            model_name="linear_regression",
            target="spending",
            features=["age", "income"],
            split_spec={"type": "random", "test_size": 0.2, "random_state": 42},
        )

        # 2. Predict
        predict_result = modeling_service.predict(
            db=db_session,
            model_id=fit_result["model_id"],
            limit=50,
        )

        assert len(predict_result["predictions"]) == 50

        # 3. Query
        model_detail = modeling_service.get_model_fit(db_session, fit_result["model_id"])

        assert model_detail["name"] == "Full Workflow Model"
        assert model_detail["coefficients"] is not None

    def test_multiple_models_same_pipeline(self, db_session: Session, project_with_pipeline):
        """Test fitting multiple models on the same pipeline."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        # Fit linear regression
        lr_result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Linear Model",
            model_name="linear_regression",
            target="spending",
            features=["age", "income"],
        )

        # Fit ridge regression
        ridge_result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Ridge Model",
            model_name="ridge",
            target="spending",
            features=["age", "income"],
        )

        # Both should have valid model IDs
        assert lr_result["model_id"] != ridge_result["model_id"]

        # Both should be retrievable
        lr_detail = modeling_service.get_model_fit(db_session, lr_result["model_id"])
        ridge_detail = modeling_service.get_model_fit(db_session, ridge_result["model_id"])

        assert lr_detail["model_type"] == "linear_regression"
        assert ridge_detail["model_type"] == "ridge"


# =============================================================================
# Model Integrity Tests
# =============================================================================


class TestModelIntegrity:
    """Tests for model artifact integrity checking."""

    def test_signed_model_loads_correctly(self, db_session: Session, project_with_pipeline):
        """Test that models with valid signatures load correctly."""
        project, dag_version, pipeline_id, version_id = project_with_pipeline

        # Fit a model (which serializes with HMAC signature)
        fit_result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Integrity Test Model",
            model_name="linear_regression",
            target="spending",
            features=["age", "income"],
        )

        # Predict should work (validates signature internally)
        predict_result = modeling_service.predict(
            db=db_session,
            model_id=fit_result["model_id"],
            limit=10,
        )

        assert len(predict_result["predictions"]) == 10

    def test_tampered_blob_rejected(self, db_session: Session, project_with_pipeline):
        """Test that tampered model blobs are rejected."""
        import json

        project, dag_version, pipeline_id, version_id = project_with_pipeline

        # Fit a model
        fit_result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Tamper Test Model",
            model_name="linear_regression",
            target="spending",
            features=["age", "income"],
        )

        # Get the model fit record
        model_fit = db_session.get(ModelFit, fit_result["model_id"])

        # Tamper with the blob
        data = json.loads(model_fit.artifact_blob)
        # Modify the blob slightly
        blob_bytes = list(data["blob"].encode())
        if blob_bytes[-5:-1]:
            blob_bytes[-3] = ord('X')  # Modify a character
        data["blob"] = bytes(blob_bytes).decode(errors='ignore')
        model_fit.artifact_blob = json.dumps(data)
        db_session.commit()

        # Prediction should fail with integrity error
        with pytest.raises((ValueError, Exception)):
            modeling_service.predict(
                db=db_session,
                model_id=fit_result["model_id"],
                limit=10,
            )

    def test_invalid_signature_rejected(self, db_session: Session, project_with_pipeline):
        """Test that models with invalid signatures are rejected."""
        import json

        project, dag_version, pipeline_id, version_id = project_with_pipeline

        # Fit a model
        fit_result = modeling_service.fit_model(
            db=db_session,
            pipeline_version_id=version_id,
            name="Bad Sig Model",
            model_name="linear_regression",
            target="spending",
            features=["age", "income"],
        )

        # Get the model fit record and change the signature
        model_fit = db_session.get(ModelFit, fit_result["model_id"])
        data = json.loads(model_fit.artifact_blob)
        data["signature"] = "invalid_signature_0123456789abcdef"
        model_fit.artifact_blob = json.dumps(data)
        db_session.commit()

        # Prediction should fail
        with pytest.raises(ValueError, match="integrity"):
            modeling_service.predict(
                db=db_session,
                model_id=fit_result["model_id"],
                limit=10,
            )
