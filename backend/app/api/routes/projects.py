"""Projects API routes for CRUD operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import crud, get_db
from app.models.dag import DAGDefinition
from app.services.validator import validate_dag

router = APIRouter()


def _ensure_valid_dag(dag_definition: DAGDefinition) -> None:
    """Validate DAG before persistence."""
    validation_result = validate_dag(dag_definition)
    if validation_result.valid:
        return

    errors = validation_result.errors or ["Invalid DAG"]
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid DAG: {'; '.join(errors)}",
    )


# =============================================================================
# Response Schemas
# =============================================================================


class DAGVersionResponse(BaseModel):
    """Response schema for a DAG version."""

    id: str
    version_number: int
    created_at: datetime
    is_current: bool
    name: str | None = None
    description: str | None = None
    parent_version_id: str | None = None

    model_config = {"from_attributes": True}


class DAGVersionDetailResponse(DAGVersionResponse):
    """Response schema for a DAG version with definition."""

    dag_definition: dict[str, Any]
    dag_diff: list[dict[str, Any]] | None = None


class ProjectResponse(BaseModel):
    """Response schema for a project."""

    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    current_version: DAGVersionResponse | None = None

    model_config = {"from_attributes": True}


class ProjectDetailResponse(ProjectResponse):
    """Response schema for a project with current DAG definition."""

    current_dag: dict[str, Any] | None = None


class ProjectListResponse(BaseModel):
    """Response schema for list of projects."""

    projects: list[ProjectResponse]
    total: int


class VersionListResponse(BaseModel):
    """Response schema for list of versions."""

    versions: list[DAGVersionResponse]
    total: int


# =============================================================================
# Request Schemas
# =============================================================================


class ProjectCreate(BaseModel):
    """Request schema for creating a project."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    dag_definition: DAGDefinition | None = None


class ProjectUpdate(BaseModel):
    """Request schema for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)


class VersionCreate(BaseModel):
    """Request schema for creating a new DAG version."""

    dag_definition: DAGDefinition
    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=1000)
    set_current: bool = True


class VersionUpdate(BaseModel):
    """Request schema for updating an existing DAG version."""

    dag_definition: DAGDefinition
    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=1000)


# =============================================================================
# Project Endpoints
# =============================================================================


@router.get("", response_model=ProjectListResponse)
def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> ProjectListResponse:
    """List all projects."""
    projects = crud.list_projects(db, skip=skip, limit=limit)
    project_responses = []
    for project in projects:
        current_version = project.current_version
        project_responses.append(
            ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                created_at=project.created_at,
                updated_at=project.updated_at,
                current_version=(
                    DAGVersionResponse(
                        id=current_version.id,
                        version_number=current_version.version_number,
                        created_at=current_version.created_at,
                        is_current=current_version.is_current,
                        name=current_version.name,
                        description=current_version.description,
                        parent_version_id=current_version.parent_version_id,
                    )
                    if current_version
                    else None
                ),
            )
        )
    return ProjectListResponse(projects=project_responses, total=len(project_responses))


@router.post("", response_model=ProjectDetailResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    request: ProjectCreate,
    db: Session = Depends(get_db),
) -> ProjectDetailResponse:
    """Create a new project."""
    # Check if project name already exists
    existing = crud.get_project_by_name(db, request.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project with name '{request.name}' already exists",
        )

    project = crud.create_project(
        db,
        name=request.name,
        description=request.description,
        dag_definition=request.dag_definition,
    )

    current_version = project.current_version
    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        current_version=(
            DAGVersionResponse(
                id=current_version.id,
                version_number=current_version.version_number,
                created_at=current_version.created_at,
                is_current=current_version.is_current,
                name=current_version.name,
                description=current_version.description,
                parent_version_id=current_version.parent_version_id,
            )
            if current_version
            else None
        ),
        current_dag=current_version.dag_definition if current_version else None,
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
) -> ProjectDetailResponse:
    """Get a project by ID with current DAG."""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    current_version = project.current_version
    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        current_version=(
            DAGVersionResponse(
                id=current_version.id,
                version_number=current_version.version_number,
                created_at=current_version.created_at,
                is_current=current_version.is_current,
                name=current_version.name,
                description=current_version.description,
                parent_version_id=current_version.parent_version_id,
            )
            if current_version
            else None
        ),
        current_dag=current_version.dag_definition if current_version else None,
    )


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    request: ProjectUpdate,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """Update project metadata."""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    # Check name uniqueness if updating name
    if request.name and request.name != project.name:
        existing = crud.get_project_by_name(db, request.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project with name '{request.name}' already exists",
            )

    project = crud.update_project(
        db,
        project,
        name=request.name,
        description=request.description,
    )

    current_version = project.current_version
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        current_version=(
            DAGVersionResponse(
                id=current_version.id,
                version_number=current_version.version_number,
                created_at=current_version.created_at,
                is_current=current_version.is_current,
                name=current_version.name,
                description=current_version.description,
                parent_version_id=current_version.parent_version_id,
            )
            if current_version
            else None
        ),
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
) -> None:
    """Delete a project and all its versions."""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    crud.delete_project(db, project)


# =============================================================================
# Version Endpoints
# =============================================================================


@router.get("/{project_id}/versions", response_model=VersionListResponse)
def list_versions(
    project_id: str,
    db: Session = Depends(get_db),
) -> VersionListResponse:
    """List all versions for a project."""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    versions = crud.list_versions(db, project_id)
    version_responses = [
        DAGVersionResponse(
            id=v.id,
            version_number=v.version_number,
            created_at=v.created_at,
            is_current=v.is_current,
            name=v.name,
            description=v.description,
            parent_version_id=v.parent_version_id,
        )
        for v in versions
    ]
    return VersionListResponse(versions=version_responses, total=len(version_responses))


@router.post(
    "/{project_id}/versions",
    response_model=DAGVersionDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    project_id: str,
    request: VersionCreate,
    db: Session = Depends(get_db),
) -> DAGVersionDetailResponse:
    """Save a new DAG version for a project."""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    _ensure_valid_dag(request.dag_definition)

    try:
        version = crud.create_version(
            db,
            project_id=project_id,
            dag_definition=request.dag_definition,
            name=request.name,
            description=request.description,
            set_current=request.set_current,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return DAGVersionDetailResponse(
        id=version.id,
        version_number=version.version_number,
        created_at=version.created_at,
        is_current=version.is_current,
        name=version.name,
        description=version.description,
        parent_version_id=version.parent_version_id,
        dag_definition=version.dag_definition,
        dag_diff=version.dag_diff,
    )


@router.get("/{project_id}/versions/{version_id}", response_model=DAGVersionDetailResponse)
def get_version(
    project_id: str,
    version_id: str,
    db: Session = Depends(get_db),
) -> DAGVersionDetailResponse:
    """Get a specific version with its DAG definition."""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    version = crud.get_version(db, version_id)
    if not version or version.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version '{version_id}' not found in project '{project_id}'",
        )

    return DAGVersionDetailResponse(
        id=version.id,
        version_number=version.version_number,
        created_at=version.created_at,
        is_current=version.is_current,
        name=version.name,
        description=version.description,
        parent_version_id=version.parent_version_id,
        dag_definition=version.dag_definition,
        dag_diff=version.dag_diff,
    )


@router.put("/{project_id}/versions/{version_id}", response_model=DAGVersionDetailResponse)
def update_version(
    project_id: str,
    version_id: str,
    request: VersionUpdate,
    db: Session = Depends(get_db),
) -> DAGVersionDetailResponse:
    """Update a specific version's DAG definition in place."""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    version = crud.get_version(db, version_id)
    if not version or version.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version '{version_id}' not found in project '{project_id}'",
        )
    if not version.is_current:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only the current version can be updated in place",
        )

    _ensure_valid_dag(request.dag_definition)

    version = crud.update_version(
        db,
        version=version,
        dag_definition=request.dag_definition,
        name=request.name,
        description=request.description,
    )

    return DAGVersionDetailResponse(
        id=version.id,
        version_number=version.version_number,
        created_at=version.created_at,
        is_current=version.is_current,
        name=version.name,
        description=version.description,
        parent_version_id=version.parent_version_id,
        dag_definition=version.dag_definition,
        dag_diff=version.dag_diff,
    )


@router.post(
    "/{project_id}/versions/{version_id}/set-current",
    response_model=DAGVersionResponse,
)
def set_current_version(
    project_id: str,
    version_id: str,
    db: Session = Depends(get_db),
) -> DAGVersionResponse:
    """Set a version as the current version."""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    version = crud.get_version(db, version_id)
    if not version or version.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version '{version_id}' not found in project '{project_id}'",
        )

    try:
        version = crud.set_current_version(db, version)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return DAGVersionResponse(
        id=version.id,
        version_number=version.version_number,
        created_at=version.created_at,
        is_current=version.is_current,
        name=version.name,
        description=version.description,
        parent_version_id=version.parent_version_id,
    )
