"""Modeling API routes for training and prediction."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import modeling_service
from app.services.model_registry import get_model_registry

router = APIRouter()


# =============================================================================
# Error Schemas
# =============================================================================

ModelingErrorCode = Literal[
    "PIPELINE_NOT_FOUND",
    "MODEL_NOT_FOUND",
    "UNKNOWN_MODEL_TYPE",
    "MISSING_TARGET",
    "INVALID_TARGET",
    "INVALID_FEATURES",
    "NO_VALID_ROWS",
    "INTEGRITY_ERROR",
    "VALIDATION_ERROR",
]


class ModelingError(BaseModel):
    """Structured error for modeling operations."""

    code: ModelingErrorCode = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    field: str | None = Field(None, description="Field that caused the error (if applicable)")
    suggestion: str | None = Field(None, description="Suggestion for fixing the error")
    context: dict[str, Any] | None = Field(None, description="Additional context")


class ModelingErrorResponse(BaseModel):
    """Error response with structured errors."""

    success: Literal[False] = False
    errors: list[ModelingError] = Field(..., description="List of structured errors")


def _parse_modeling_error(error: ValueError) -> ModelingError:
    """Parse a ValueError into a structured ModelingError."""
    msg = str(error)

    if "not found" in msg.lower():
        if "pipeline version" in msg.lower():
            return ModelingError(
                code="PIPELINE_NOT_FOUND",
                message=msg,
                suggestion="Ensure the pipeline exists and has materialized data",
            )
        elif "model" in msg.lower() and "type" not in msg.lower():
            return ModelingError(
                code="MODEL_NOT_FOUND",
                message=msg,
                suggestion="Check that the model ID is correct",
            )
        elif "target column" in msg.lower():
            return ModelingError(
                code="INVALID_TARGET",
                message=msg,
                field="target",
                suggestion="Select a valid numeric column as the target",
            )
        elif "feature" in msg.lower():
            return ModelingError(
                code="INVALID_FEATURES",
                message=msg,
                field="features",
                suggestion="Ensure all selected features exist in the pipeline schema",
            )

    if "unknown model type" in msg.lower():
        return ModelingError(
            code="UNKNOWN_MODEL_TYPE",
            message=msg,
            field="model_name",
            suggestion="Select a valid model type from the available options",
        )

    if "target column is required" in msg.lower():
        return ModelingError(
            code="MISSING_TARGET",
            message=msg,
            field="target",
            suggestion="Select a target column for regression",
        )

    if "no valid rows" in msg.lower():
        return ModelingError(
            code="NO_VALID_ROWS",
            message=msg,
            suggestion="Check for null values in your data or adjust feature selection",
        )

    if "integrity" in msg.lower() or "signature" in msg.lower():
        return ModelingError(
            code="INTEGRITY_ERROR",
            message=msg,
            suggestion="The model data may be corrupted. Try re-fitting the model.",
        )

    # Default fallback
    return ModelingError(
        code="VALIDATION_ERROR",
        message=msg,
    )


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
    choices: list[Any] = Field(default_factory=list)
    min_value: float | None = None
    max_value: float | None = None
    recommended_min: float | None = None
    recommended_max: float | None = None
    log_scale: bool | None = None
    ui_group: str | None = None


class ModelVideoLink(BaseModel):
    """Link to a learning resource for a model."""

    title: str
    url: str


class ModelTypeInfo(BaseModel):
    """Information about a model type."""
    
    name: str
    display_name: str
    description: str
    task_type: str
    parameters: list[ModelParameter]
    # UI metadata
    icon: str | None = None
    complexity: int | None = None
    coming_soon: bool = False
    tags: list[str] = Field(default_factory=list)
    video_links: list[ModelVideoLink] = Field(default_factory=list)


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


@router.post(
    "/fit",
    response_model=FitResponse,
    responses={400: {"model": ModelingErrorResponse}},
)
def fit_model(
    request: FitRequest,
    db: Session = Depends(get_db),
) -> FitResponse | JSONResponse:
    """Fit a model on pipeline data.

    Trains the specified model type on the given pipeline version,
    computing train/test metrics and storing the fitted model.

    Returns structured errors on failure with field-specific suggestions.
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
        error = _parse_modeling_error(e)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "errors": [error.model_dump(exclude_none=True)]},
        )


@router.post(
    "/predict",
    response_model=PredictResponse,
    responses={400: {"model": ModelingErrorResponse}},
)
def predict(
    request: PredictRequest,
    db: Session = Depends(get_db),
) -> PredictResponse | JSONResponse:
    """Generate predictions using a fitted model.

    Applies the fitted model to the pipeline data to generate predictions.

    Returns structured errors on failure with suggestions.
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
        error = _parse_modeling_error(e)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "errors": [error.model_dump(exclude_none=True)]},
        )


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
            parameters=[
                ModelParameter(**{**p, "choices": p.get("choices") or []})
                for p in m["parameters"]
            ],
            icon=m.get("icon"),
            complexity=m.get("complexity"),
            coming_soon=m.get("coming_soon", False),
            tags=m.get("tags", []),
            video_links=[ModelVideoLink(**v) for v in m.get("video_links", [])],
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
