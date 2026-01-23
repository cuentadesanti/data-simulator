"""Pipeline API routes for CRUD operations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import pipeline_service

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class SimulationSource(BaseModel):
    """Source configuration for simulation-based pipeline."""
    
    type: str = Field("simulation", description="Source type")
    dag_version_id: str = Field(..., description="ID of the DAG version to use")
    seed: int = Field(..., description="Random seed for reproducibility")
    sample_size: int = Field(..., ge=1, le=100000, description="Number of rows to generate")


class PipelineCreateRequest(BaseModel):
    """Request schema for creating a pipeline."""
    
    project_id: str = Field(..., description="ID of the parent project")
    name: str = Field(..., min_length=1, max_length=255, description="Pipeline name")
    source: SimulationSource = Field(..., description="Source configuration")


class PipelineCreateResponse(BaseModel):
    """Response schema for pipeline creation."""
    
    pipeline_id: str
    current_version_id: str
    schema: list[dict[str, Any]]


class StepSpec(BaseModel):
    """Specification for a transform step."""
    
    type: str = Field(..., description="Transform type (e.g., 'formula', 'log')")
    output_column: str = Field(..., description="Name for the output column")
    params: dict[str, Any] = Field(default_factory=dict, description="Transform parameters")
    allow_overwrite: bool = Field(False, description="Allow overwriting existing column")


class AddStepRequest(BaseModel):
    """Request schema for adding a step."""
    
    step: StepSpec
    preview_limit: int = Field(200, ge=1, le=1000, description="Preview row limit")


class AddStepResponse(BaseModel):
    """Response schema for adding a step."""
    
    new_version_id: str
    schema: list[dict[str, Any]]
    added_columns: list[str]
    preview_rows: list[dict[str, Any]]
    warnings: int


class MaterializeResponse(BaseModel):
    """Response schema for materialization."""
    
    schema: list[dict[str, Any]]
    rows: list[dict[str, Any]]


class ResimulateRequest(BaseModel):
    """Request schema for resimulation."""
    
    seed: int = Field(..., description="New random seed")
    sample_size: int = Field(..., ge=1, le=100000, description="New sample size")


class ResimulateResponse(BaseModel):
    """Response schema for resimulation."""
    
    new_pipeline_id: str
    current_version_id: str


class PipelineVersionSummary(BaseModel):
    """Summary of a pipeline version."""
    
    id: str
    version_number: int
    steps_count: int
    created_at: str


class PipelineDetail(BaseModel):
    """Detailed pipeline information."""
    
    id: str
    project_id: str
    name: str
    source_type: str
    created_at: str


class CurrentVersionDetail(BaseModel):
    """Details of the current pipeline version."""
    
    id: str
    version_number: int
    steps: list[dict[str, Any]]
    input_schema: list[dict[str, Any]]
    output_schema: list[dict[str, Any]]
    lineage: list[dict[str, Any]]


class PipelineResponse(BaseModel):
    """Response schema for getting a pipeline."""
    
    pipeline: PipelineDetail
    current_version: CurrentVersionDetail | None
    versions_summary: list[PipelineVersionSummary]


class PipelineSummary(BaseModel):
    """Summary of a pipeline for listing."""
    
    id: str
    name: str
    source_type: str
    current_version_id: str | None
    versions_count: int
    created_at: str


class PipelineListResponse(BaseModel):
    """Response schema for listing pipelines."""
    
    pipelines: list[PipelineSummary]


# =============================================================================
# Endpoints
# =============================================================================


@router.post("", response_model=PipelineCreateResponse, status_code=status.HTTP_201_CREATED)
def create_pipeline(
    request: PipelineCreateRequest,
    db: Session = Depends(get_db),
) -> PipelineCreateResponse:
    """Create a new pipeline from a simulation source.
    
    Creates a pipeline with version 1 containing empty transform steps.
    The input schema is inferred from the simulation source.
    """
    try:
        result = pipeline_service.create_pipeline(
            db=db,
            project_id=request.project_id,
            name=request.name,
            source_type=request.source.type,
            dag_version_id=request.source.dag_version_id,
            seed=request.source.seed,
            sample_size=request.source.sample_size,
        )
        return PipelineCreateResponse(
            pipeline_id=result["pipeline_id"],
            current_version_id=result["version_id"],
            schema=result["schema"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{pipeline_id}/versions/{version_id}/steps",
    response_model=AddStepResponse,
)
def add_step(
    pipeline_id: str,
    version_id: str,
    request: AddStepRequest,
    db: Session = Depends(get_db),
) -> AddStepResponse:
    """Add a transform step to a pipeline.
    
    Creates a new version with the additional step. The new version
    becomes the current version.
    """
    try:
        result = pipeline_service.add_step(
            db=db,
            pipeline_id=pipeline_id,
            version_id=version_id,
            step_spec=request.step.model_dump(),
            preview_limit=request.preview_limit,
        )
        return AddStepResponse(
            new_version_id=result["new_version_id"],
            schema=result["schema"],
            added_columns=result["added_columns"],
            preview_rows=result["preview_rows"],
            warnings=result["warnings"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{pipeline_id}/versions/{version_id}/materialization",
    response_model=MaterializeResponse,
)
def materialize(
    pipeline_id: str,
    version_id: str,
    limit: int = Query(1000, ge=1, le=10000, description="Max rows to return"),
    columns: str | None = Query(None, description="Comma-separated column names"),
    db: Session = Depends(get_db),
) -> MaterializeResponse:
    """Materialize a pipeline version to data.
    
    Generates the data by loading the source and applying all transform
    steps in order.
    """
    try:
        column_list = None
        if columns:
            column_list = [c.strip() for c in columns.split(",") if c.strip()]
        
        result = pipeline_service.materialize(
            db=db,
            pipeline_id=pipeline_id,
            version_id=version_id,
            limit=limit,
            columns=column_list,
        )
        return MaterializeResponse(
            schema=result["schema"],
            rows=result["rows"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{pipeline_id}/versions/{version_id}/resimulate",
    response_model=ResimulateResponse,
)
def resimulate(
    pipeline_id: str,
    version_id: str,
    request: ResimulateRequest,
    db: Session = Depends(get_db),
) -> ResimulateResponse:
    """Create a new pipeline with different seed/sample_size.
    
    Copies the transform steps from the source version to create
    a new pipeline with a different source configuration.
    """
    try:
        result = pipeline_service.resimulate(
            db=db,
            pipeline_id=pipeline_id,
            version_id=version_id,
            seed=request.seed,
            sample_size=request.sample_size,
        )
        return ResimulateResponse(
            new_pipeline_id=result["new_pipeline_id"],
            current_version_id=result["version_id"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(
    pipeline_id: str,
    db: Session = Depends(get_db),
) -> PipelineResponse:
    """Get pipeline details with current version and version history."""
    result = pipeline_service.get_pipeline(db, pipeline_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline '{pipeline_id}' not found",
        )
    
    return PipelineResponse(
        pipeline=PipelineDetail(**result["pipeline"]),
        current_version=CurrentVersionDetail(**result["current_version"]) if result["current_version"] else None,
        versions_summary=[PipelineVersionSummary(**v) for v in result["versions_summary"]],
    )


@router.get("", response_model=PipelineListResponse)
def list_pipelines(
    project_id: str = Query(..., description="Project ID to list pipelines for"),
    db: Session = Depends(get_db),
) -> PipelineListResponse:
    """List all pipelines for a project."""
    pipelines = pipeline_service.list_pipelines(db, project_id)
    return PipelineListResponse(
        pipelines=[PipelineSummary(**p) for p in pipelines]
    )
