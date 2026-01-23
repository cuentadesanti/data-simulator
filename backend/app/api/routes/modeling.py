"""Modeling API routes for training and prediction."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import modeling_service
from app.services.model_registry import get_model_registry

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class SplitSpec(BaseModel):
    """Train/test split specification."""
    
    type: str = Field("random", description="Split type")
    test_size: float = Field(0.2, ge=0.0, le=1.0, description="Test set proportion")
    random_state: int = Field(42, description="Random seed for reproducibility")


class FitRequest(BaseModel):
    """Request schema for fitting a model."""
    
    pipeline_version_id: str = Field(..., description="Pipeline version to use")
    name: str = Field(..., min_length=1, max_length=255, description="Model name")
    model_name: str = Field(..., description="Model type (e.g., 'linear_regression')")
    target: str | None = Field(None, description="Target column name")
    features: list[str] = Field(..., min_length=1, description="Feature column names")
    model_params: dict[str, Any] = Field(default_factory=dict, description="Model hyperparameters")
    split_spec: SplitSpec = Field(default_factory=SplitSpec, description="Train/test split config")


class FitResponse(BaseModel):
    """Response schema for fitting a model."""
    
    model_id: str
    metrics: dict[str, float]
    coefficients: dict[str, float] | None
    diagnostics: dict[str, Any] | None


class PredictRequest(BaseModel):
    """Request schema for prediction."""
    
    model_id: str = Field(..., description="ID of the fitted model")
    pipeline_version_id: str | None = Field(None, description="Pipeline version to predict on")
    limit: int = Field(1000, ge=1, le=10000, description="Maximum rows to return")


class PredictResponse(BaseModel):
    """Response schema for prediction."""
    
    predictions: list[float | None]
    preview_rows_with_pred: list[dict[str, Any]]


class ModelParameter(BaseModel):
    """Parameter definition for a model type."""
    
    name: str
    display_name: str
    type: str
    required: bool
    default: Any | None
    description: str


class ModelTypeInfo(BaseModel):
    """Information about a model type."""
    
    name: str
    display_name: str
    description: str
    task_type: str
    parameters: list[ModelParameter]


class ModelsListResponse(BaseModel):
    """Response schema for listing model types."""
    
    models: list[ModelTypeInfo]


class ModelFitSummary(BaseModel):
    """Summary of a model fit."""
    
    id: str
    name: str
    model_type: str
    task_type: str
    target_column: str | None = None
    metrics: dict[str, float]
    created_at: str


class ModelFitDetail(BaseModel):
    """Detailed model fit information."""
    
    id: str
    pipeline_version_id: str
    name: str
    model_type: str
    task_type: str
    target_column: str | None = None
    feature_spec: dict[str, Any]
    split_spec: dict[str, Any]
    model_params: dict[str, Any]
    metrics: dict[str, float]
    coefficients: dict[str, float] | None
    diagnostics: dict[str, Any] | None
    created_at: str


class ModelFitsListResponse(BaseModel):
    """Response schema for listing model fits."""
    
    model_fits: list[ModelFitSummary]
    total_count: int = Field(..., description="Total number of model fits matching the filter")


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/fit", response_model=FitResponse)
def fit_model(
    request: FitRequest,
    db: Session = Depends(get_db),
) -> FitResponse:
    """Fit a model on pipeline data.
    
    Trains the specified model type on the given pipeline version,
    computing train/test metrics and storing the fitted model.
    """
    try:
        result = modeling_service.fit_model(
            db=db,
            pipeline_version_id=request.pipeline_version_id,
            name=request.name,
            model_name=request.model_name,
            target=request.target,
            features=request.features,
            model_params=request.model_params,
            split_spec=request.split_spec.model_dump(),
        )
        return FitResponse(
            model_id=result["model_id"],
            metrics=result["metrics"],
            coefficients=result["coefficients"],
            diagnostics=result["diagnostics"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/predict", response_model=PredictResponse)
def predict(
    request: PredictRequest,
    db: Session = Depends(get_db),
) -> PredictResponse:
    """Generate predictions using a fitted model.
    
    Applies the fitted model to the pipeline data to generate predictions.
    """
    try:
        result = modeling_service.predict(
            db=db,
            model_id=request.model_id,
            pipeline_version_id=request.pipeline_version_id,
            limit=request.limit,
        )
        return PredictResponse(
            predictions=result["predictions"],
            preview_rows_with_pred=result["preview_rows_with_pred"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/models", response_model=ModelsListResponse)
def list_models() -> ModelsListResponse:
    """List all available model types.
    
    Returns metadata about each model type including name, task type,
    and parameter definitions for UI rendering.
    """
    registry = get_model_registry()
    models_data = registry.list_all()
    
    models = [
        ModelTypeInfo(
            name=m["name"],
            display_name=m["display_name"],
            description=m["description"],
            task_type=m["task_type"],
            parameters=[ModelParameter(**p) for p in m["parameters"]],
        )
        for m in models_data
    ]
    
    return ModelsListResponse(models=models)


@router.get("/fits", response_model=ModelFitsListResponse)
def list_model_fits(
    pipeline_version_id: str | None = Query(None, description="Filter by pipeline version"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> ModelFitsListResponse:
    """List model fits with pagination.
    
    Optionally filter by pipeline version. Supports pagination via limit/offset.
    """
    result = modeling_service.list_model_fits(db, pipeline_version_id, limit, offset)
    return ModelFitsListResponse(
        model_fits=[ModelFitSummary(**m) for m in result["model_fits"]],
        total_count=result["total_count"],
    )


@router.get("/fits/{model_id}", response_model=ModelFitDetail)
def get_model_fit(
    model_id: str,
    db: Session = Depends(get_db),
) -> ModelFitDetail:
    """Get model fit details."""
    result = modeling_service.get_model_fit(db, model_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )
    return ModelFitDetail(**result)
