"""Pipeline API routes for CRUD operations."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import current_user_context
from app.core.project_access import raise_not_found, require_project_owner, require_project_read
from app.db import crud, get_db
from app.db.models import Pipeline
from app.services import pipeline_service

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class SimulationSource(BaseModel):
    """Source configuration for simulation-based pipeline."""

    type: Literal["simulation"] = Field("simulation", description="Source type")
    dag_version_id: str = Field(..., description="ID of the DAG version to use")
    seed: int = Field(..., description="Random seed for reproducibility")
    sample_size: int = Field(..., ge=1, le=100000, description="Number of rows to generate")


class UploadSource(BaseModel):
    """Source configuration for upload-based pipeline."""

    type: Literal["upload"] = Field("upload", description="Source type")
    source_id: str = Field(..., description="Uploaded source identifier")


class PipelineCreateRequest(BaseModel):
    """Request schema for creating a pipeline."""

    project_id: str = Field(..., description="ID of the parent project")
    name: str = Field(..., min_length=1, max_length=255, description="Pipeline name")
    source: SimulationSource | UploadSource = Field(..., description="Source configuration")


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


class PipelineVersionMutationResponse(BaseModel):
    """Response schema for step delete/reorder operations."""

    new_version_id: str
    schema: list[dict[str, Any]]
    preview_rows: list[dict[str, Any]]
    warnings: int
    steps: list[dict[str, Any]]
    lineage: list[dict[str, Any]]


class DeleteStepResponse(PipelineVersionMutationResponse):
    """Response schema for deleting a step."""

    removed_step_ids: list[str]
    affected_columns: list[str]


class ReorderStepsRequest(BaseModel):
    """Request schema for reordering transform steps."""

    step_ids: list[str] = Field(..., min_length=1, description="Ordered list of step IDs")
    preview_limit: int = Field(200, ge=1, le=1000, description="Preview row limit")


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
# Helpers
# =============================================================================


def _require_pipeline_project(
    db: Session,
    pipeline_id: str,
    user_id: str,
    *,
    require_owner: bool,
) -> Pipeline:
    pipeline = db.get(Pipeline, pipeline_id)
    if not pipeline:
        raise_not_found()

    if require_owner:
        require_project_owner(db, pipeline.project_id, user_id)
    else:
        require_project_read(db, pipeline.project_id, user_id)

    return pipeline


# =============================================================================
# Endpoints
# =============================================================================


@router.post("", response_model=PipelineCreateResponse, status_code=status.HTTP_201_CREATED)
def create_pipeline(
    request: PipelineCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> PipelineCreateResponse:
    """Create a new pipeline from a simulation or upload source."""
    user_id = current_user["user_id"]
    require_project_owner(db, request.project_id, user_id)

    try:
        if isinstance(request.source, UploadSource):
            source = crud.get_uploaded_source(db, request.source.source_id)
            if not source:
                raise_not_found()
            if source.project_id != request.project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded source must belong to the target project",
                )
        else:
            dag_version = crud.get_version(db, request.source.dag_version_id)
            if not dag_version:
                raise_not_found()
            if dag_version.project_id != request.project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="DAG version must belong to the target project",
                )

        result = pipeline_service.create_pipeline(
            db=db,
            project_id=request.project_id,
            name=request.name,
            source_type=request.source.type,
            dag_version_id=request.source.dag_version_id if isinstance(request.source, SimulationSource) else None,
            seed=request.source.seed if isinstance(request.source, SimulationSource) else None,
            sample_size=request.source.sample_size if isinstance(request.source, SimulationSource) else None,
            upload_source_id=request.source.source_id if isinstance(request.source, UploadSource) else None,
        )
        return PipelineCreateResponse(
            pipeline_id=result["pipeline_id"],
            current_version_id=result["version_id"],
            schema=result["schema"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/{pipeline_id}/versions/{version_id}/steps",
    response_model=AddStepResponse,
)
def add_step(
    pipeline_id: str,
    version_id: str,
    request: AddStepRequest,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> AddStepResponse:
    """Add a transform step to a pipeline."""
    _require_pipeline_project(db, pipeline_id, current_user["user_id"], require_owner=True)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/{pipeline_id}/versions/{version_id}/steps/reorder",
    response_model=PipelineVersionMutationResponse,
)
def reorder_steps(
    pipeline_id: str,
    version_id: str,
    request: ReorderStepsRequest,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> PipelineVersionMutationResponse:
    """Reorder transform steps, creating a new pipeline version."""
    _require_pipeline_project(db, pipeline_id, current_user["user_id"], require_owner=True)
    try:
        result = pipeline_service.reorder_steps(
            db=db,
            pipeline_id=pipeline_id,
            version_id=version_id,
            step_ids=request.step_ids,
            preview_limit=request.preview_limit,
        )
        return PipelineVersionMutationResponse(**result)
    except pipeline_service.PipelineDependencyConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(e),
                "affected_step_ids": e.affected_step_ids,
                "affected_columns": e.affected_columns,
            },
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete(
    "/{pipeline_id}/versions/{version_id}/steps/{step_id}",
    response_model=DeleteStepResponse,
)
def delete_step(
    pipeline_id: str,
    version_id: str,
    step_id: str,
    cascade: bool = Query(False, description="Whether to remove downstream dependent steps"),
    preview_limit: int = Query(200, ge=1, le=1000, description="Preview row limit"),
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> DeleteStepResponse:
    """Delete a transform step and optionally cascade to dependent steps."""
    _require_pipeline_project(db, pipeline_id, current_user["user_id"], require_owner=True)
    try:
        result = pipeline_service.delete_step(
            db=db,
            pipeline_id=pipeline_id,
            version_id=version_id,
            step_id=step_id,
            cascade=cascade,
            preview_limit=preview_limit,
        )
        return DeleteStepResponse(**result)
    except pipeline_service.PipelineDependencyConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(e),
                "affected_step_ids": e.affected_step_ids,
                "affected_columns": e.affected_columns,
            },
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


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
    current_user: dict[str, str] = Depends(current_user_context),
) -> MaterializeResponse:
    """Materialize a pipeline version to data."""
    _require_pipeline_project(db, pipeline_id, current_user["user_id"], require_owner=False)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/{pipeline_id}/versions/{version_id}/resimulate",
    response_model=ResimulateResponse,
)
def resimulate(
    pipeline_id: str,
    version_id: str,
    request: ResimulateRequest,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> ResimulateResponse:
    """Create a new pipeline with different seed/sample_size."""
    _require_pipeline_project(db, pipeline_id, current_user["user_id"], require_owner=True)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(
    pipeline_id: str,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> PipelineResponse:
    """Get pipeline details with current version and version history."""
    _require_pipeline_project(db, pipeline_id, current_user["user_id"], require_owner=False)
    result = pipeline_service.get_pipeline(db, pipeline_id)
    if not result:
        raise_not_found()

    return PipelineResponse(
        pipeline=PipelineDetail(**result["pipeline"]),
        current_version=CurrentVersionDetail(**result["current_version"]) if result["current_version"] else None,
        versions_summary=[PipelineVersionSummary(**v) for v in result["versions_summary"]],
    )


@router.get("", response_model=PipelineListResponse)
def list_pipelines(
    project_id: str = Query(..., description="Project ID to list pipelines for"),
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> PipelineListResponse:
    """List all pipelines for a project."""
    require_project_read(db, project_id, current_user["user_id"])
    pipelines = pipeline_service.list_pipelines(db, project_id)
    return PipelineListResponse(
        pipelines=[PipelineSummary(**p) for p in pipelines]
    )
