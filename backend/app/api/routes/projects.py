"""Projects API routes for CRUD operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import crud, get_db
from app.models.dag import DAGDefinition

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================


class DAGVersionResponse(BaseModel):
    """Response schema for a DAG version."""

    id: str
    version_number: int
    created_at: datetime
    is_current: bool

    model_config = {"from_attributes": True}


class DAGVersionDetailResponse(DAGVersionResponse):
    """Response schema for a DAG version with definition."""

    dag_definition: dict[str, Any]


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
    set_current: bool = True


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

    version = crud.create_version(
        db,
        project_id=project_id,
        dag_definition=request.dag_definition,
        set_current=request.set_current,
    )

    return DAGVersionDetailResponse(
        id=version.id,
        version_number=version.version_number,
        created_at=version.created_at,
        is_current=version.is_current,
        dag_definition=version.dag_definition,
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
        dag_definition=version.dag_definition,
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

    version = crud.set_current_version(db, version)

    return DAGVersionResponse(
        id=version.id,
        version_number=version.version_number,
        created_at=version.created_at,
        is_current=version.is_current,
    )
