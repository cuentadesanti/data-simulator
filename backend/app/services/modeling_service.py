"""Modeling service for fitting and predicting with ML models.

This module provides the business logic for training models on pipeline data,
storing fitted model artifacts, and generating predictions.
"""

from __future__ import annotations

import base64
import logging
import pickle
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session

from app.db.models import ModelFit, PipelineVersion
from app.services.model_registry import get_model_registry
from app.services.pipeline_service import _materialize_to_df

logger = logging.getLogger(__name__)


# =============================================================================
# Model Fitting
# =============================================================================


def fit_model(
    db: Session,
    pipeline_version_id: str,
    name: str,
    model_name: str,
    target: str,
    features: list[str],
    model_params: dict[str, Any] | None = None,
    split_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fit a model on pipeline data.
    
    Args:
        db: Database session
        pipeline_version_id: ID of the pipeline version to use
        name: Name for the fitted model
        model_name: Name of the model type (e.g., "linear_regression")
        target: Name of the target column
        features: List of feature column names
        model_params: Optional model hyperparameters
        split_spec: Optional train/test split specification
            {type: "random", test_size: 0.2, random_state: 42}
        
    Returns:
        Dict with model_id, metrics, coefficients, diagnostics
        
    Raises:
        ValueError: If model or columns not found
    """
    # Default split spec
    if split_spec is None:
        split_spec = {"type": "random", "test_size": 0.2, "random_state": 42}
    
    # Default model params
    if model_params is None:
        model_params = {}
    
    # Get the pipeline version
    version = db.get(PipelineVersion, pipeline_version_id)
    if not version:
        logger.error(f"Pipeline version not found: {pipeline_version_id}")
        raise ValueError(f"Pipeline version '{pipeline_version_id}' not found")
    
    # Get the model type
    registry = get_model_registry()
    model_type = registry.get(model_name)
    if not model_type:
        logger.error(f"Unknown model type: {model_name}. Available: {[m['name'] for m in registry.list_all()]}")
        raise ValueError(f"Unknown model type: {model_name}")
    
    logger.info(f"Fitting model: name={name}, model_type={model_name}, target={target}, features={features}")
    
    # Materialize the data
    df = _materialize_to_df(db, version)
    logger.debug(f"Materialized data: {len(df)} rows, columns={list(df.columns)}")
    
    # Validate columns exist
    all_columns = set(df.columns)
    
    # Target is required for regression
    if not target:
        raise ValueError("Target column is required for regression")
    if target not in all_columns:
        raise ValueError(f"Target column '{target}' not found")
    
    missing_features = [f for f in features if f not in all_columns]
    if missing_features:
        raise ValueError(f"Feature columns not found: {missing_features}")
    
    # Select columns
    feature_cols = features
    
    # Prepare data - drop rows with nulls
    cols_to_check = [target] + feature_cols
    subset = df[cols_to_check].dropna()
    
    if len(subset) == 0:
        logger.error(f"No valid rows after dropping nulls from columns: {cols_to_check}")
        raise ValueError("No valid rows after dropping nulls")
    
    X = subset[feature_cols].values
    y = subset[target].values
    
    logger.debug(f"Data prepared: X.shape={X.shape}, y.shape={y.shape}")
    
    # Split data
    split_type = split_spec.get("type", "random")
    if split_type == "random":
        test_size = split_spec.get("test_size", 0.2)
        random_state = split_spec.get("random_state", 42)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
    else:
        # No split - use all data
        X_train, X_test = X, X
        y_train, y_test = y, y
    
    # Fit the model
    logger.info(f"Fitting {model_name} with params: {model_params}")
    try:
        model, train_metrics, artifacts = model_type.fit(X_train, y_train, model_params)
        logger.info(f"Model fitted successfully. Train metrics: {train_metrics}")
    except Exception as e:
        logger.exception(f"Failed to fit model {model_name}: {e}")
        raise
    
    # Compute test metrics
    try:
        y_pred = model_type.predict(model, X_test)
        
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        test_metrics = {
            "test_r2": float(r2_score(y_test, y_pred)),
            "test_mae": float(mean_absolute_error(y_test, y_pred)),
            "test_rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        }
        logger.debug(f"Test metrics computed: {test_metrics}")
    except Exception as e:
        logger.exception(f"Failed to compute test metrics: {e}")
        raise
    
    # Combine train and test metrics
    all_metrics = {**train_metrics, **test_metrics}
    logger.info(f"All metrics: {all_metrics}")
    
    # Get coefficients
    coefficients = model_type.coefficients(model, feature_cols)
    
    # Get diagnostics
    diagnostics = model_type.diagnostics(model, X_test, y_test)
    
    # Serialize model to base64 pickle for storage
    artifact_blob = base64.b64encode(pickle.dumps(model)).decode("utf-8")
    
    # Create ModelFit record
    model_fit = ModelFit(
        pipeline_version_id=pipeline_version_id,
        name=name,
        model_type=model_name,
        task_type=model_type.task_type,
        target_column=target,
        feature_spec={"columns": feature_cols},
        split_spec=split_spec,
        model_params=model_params,
        artifact_blob=artifact_blob,
        metrics=all_metrics,
        coefficients=coefficients,
        diagnostics=diagnostics,
    )
    db.add(model_fit)
    db.commit()
    db.refresh(model_fit)
    
    return {
        "model_id": model_fit.id,
        "metrics": all_metrics,
        "coefficients": coefficients,
        "diagnostics": diagnostics,
    }


# =============================================================================
# Prediction
# =============================================================================


def predict(
    db: Session,
    model_id: str,
    pipeline_version_id: str | None = None,
    limit: int = 1000,
) -> dict[str, Any]:
    """Generate predictions using a fitted model.
    
    Args:
        db: Database session
        model_id: ID of the fitted model
        pipeline_version_id: Optional different pipeline version to predict on
            (defaults to the version the model was trained on)
        limit: Maximum rows to return
        
    Returns:
        Dict with predictions and preview_rows_with_pred
        
    Raises:
        ValueError: If model or version not found
    """
    # Get the model fit record
    model_fit = db.get(ModelFit, model_id)
    if not model_fit:
        raise ValueError(f"Model '{model_id}' not found")
    
    # Use the original pipeline version if not specified
    if pipeline_version_id is None:
        pipeline_version_id = model_fit.pipeline_version_id
    
    # Get pipeline version
    version = db.get(PipelineVersion, pipeline_version_id)
    if not version:
        raise ValueError(f"Pipeline version '{pipeline_version_id}' not found")
    
    # Materialize the data
    df = _materialize_to_df(db, version)
    
    # Get feature columns
    feature_cols = model_fit.feature_spec.get("columns", [])
    
    # Validate columns exist
    missing = [f for f in feature_cols if f not in df.columns]
    if missing:
        raise ValueError(f"Feature columns not found: {missing}")
    
    # Prepare data - keep track of valid rows
    feature_df = df[feature_cols]
    valid_mask = ~feature_df.isna().any(axis=1)
    
    X = feature_df[valid_mask].values
    
    # Load the model
    model = pickle.loads(base64.b64decode(model_fit.artifact_blob))
    
    # Get model type for prediction
    registry = get_model_registry()
    model_type = registry.get(model_fit.model_type)
    
    # Generate predictions for valid rows
    predictions = model_type.predict(model, X)
    
    # Add predictions back to DataFrame
    result_df = df.copy()
    result_df["_prediction"] = np.nan
    result_df.loc[valid_mask, "_prediction"] = predictions
    
    # Apply limit and convert to records
    result_df = result_df.head(limit)
    
    return {
        "predictions": result_df["_prediction"].tolist(),
        "preview_rows_with_pred": result_df.to_dict(orient="records"),
    }


# =============================================================================
# Model Queries
# =============================================================================


def get_model_fit(db: Session, model_id: str) -> dict[str, Any] | None:
    """Get model fit details.
    
    Args:
        db: Database session
        model_id: ID of the model fit
        
    Returns:
        Model fit details or None if not found
    """
    model_fit = db.get(ModelFit, model_id)
    if not model_fit:
        return None
    
    return {
        "id": model_fit.id,
        "pipeline_version_id": model_fit.pipeline_version_id,
        "name": model_fit.name,
        "model_type": model_fit.model_type,
        "task_type": model_fit.task_type,
        "target_column": model_fit.target_column,
        "feature_spec": model_fit.feature_spec,
        "split_spec": model_fit.split_spec,
        "model_params": model_fit.model_params,
        "metrics": model_fit.metrics,
        "coefficients": model_fit.coefficients,
        "diagnostics": model_fit.diagnostics,
        "created_at": model_fit.created_at.isoformat(),
    }


def list_model_fits(
    db: Session, 
    pipeline_version_id: str | None = None
) -> list[dict[str, Any]]:
    """List model fits.
    
    Args:
        db: Database session
        pipeline_version_id: Optional filter by pipeline version
        
    Returns:
        List of model fit summaries
    """
    from sqlalchemy import select
    
    stmt = select(ModelFit)
    if pipeline_version_id:
        stmt = stmt.where(ModelFit.pipeline_version_id == pipeline_version_id)
    
    model_fits = db.execute(stmt).scalars().all()
    
    return [
        {
            "id": m.id,
            "name": m.name,
            "model_type": m.model_type,
            "task_type": m.task_type,
            "target_column": m.target_column,
            "metrics": m.metrics,
            "created_at": m.created_at.isoformat(),
        }
        for m in model_fits
    ]
