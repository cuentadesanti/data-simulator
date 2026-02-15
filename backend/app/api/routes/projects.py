"""Projects API routes for CRUD operations."""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import current_user_context
from app.core.project_access import raise_not_found, require_project_owner, require_project_read
from app.db import crud, get_db
from app.db.models import DAGVersion, Pipeline, PipelineVersion, Project, generate_uuid
from app.models.dag import DAGDefinition
from app.services.validator import validate_dag

router = APIRouter()


MAX_FORK_NAME_ATTEMPTS = 10


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
    is_public: bool = False

    model_config = {"from_attributes": True}


class DAGVersionDetailResponse(DAGVersionResponse):
    """Response schema for a DAG version with definition."""

    dag_definition: dict[str, Any]
    dag_diff: list[dict[str, Any]] | None = None


class ProjectResponse(BaseModel):
    """Response schema for a project."""

    id: str
    name: str
    owner_user_id: str
    visibility: str
    forked_from_project_id: str | None = None
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
    visibility: str = Field("private", pattern="^(private|public)$")
    dag_definition: DAGDefinition | None = None


class ProjectUpdate(BaseModel):
    """Request schema for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    visibility: str | None = Field(None, pattern="^(private|public)$")


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


class ShareVersionResponse(BaseModel):
    """Response schema for a shared version."""

    project_id: str
    version_id: str
    is_public: bool
    share_token: str | None = None
    public_path: str | None = None


# =============================================================================
# Serializers / helpers
# =============================================================================


def _serialize_version(version: DAGVersion) -> DAGVersionResponse:
    return DAGVersionResponse(
        id=version.id,
        version_number=version.version_number,
        created_at=version.created_at,
        is_current=version.is_current,
        name=version.name,
        description=version.description,
        parent_version_id=version.parent_version_id,
        is_public=version.is_public,
    )


def _serialize_project(project: Project) -> ProjectResponse:
    current_version = project.current_version
    return ProjectResponse(
        id=project.id,
        name=project.name,
        owner_user_id=project.owner_user_id,
        visibility=project.visibility,
        forked_from_project_id=project.forked_from_project_id,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        current_version=_serialize_version(current_version) if current_version else None,
    )


def _serialize_project_detail(project: Project) -> ProjectDetailResponse:
    current_version = project.current_version
    return ProjectDetailResponse(
        **_serialize_project(project).model_dump(),
        current_dag=current_version.dag_definition if current_version else None,
    )


def _next_fork_name(db: Session, source_name: str) -> str:
    for attempt in range(1, MAX_FORK_NAME_ATTEMPTS + 1):
        if attempt == 1:
            candidate = f"{source_name} (fork)"
        else:
            candidate = f"{source_name} (fork {attempt})"
        if crud.get_project_by_name(db, candidate) is None:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Could not allocate fork name",
    )


def _project_has_upload_backed_pipeline(db: Session, project_id: str) -> bool:
    stmt = (
        select(PipelineVersion.id)
        .join(Pipeline, PipelineVersion.pipeline_id == Pipeline.id)
        .where(Pipeline.project_id == project_id, PipelineVersion.source_upload_id.is_not(None))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def _fork_project(db: Session, source_project: Project, owner_user_id: str) -> Project:
    fork_name = _next_fork_name(db, source_project.name)

    fork_project = Project(
        id=generate_uuid(),
        name=fork_name,
        owner_user_id=owner_user_id,
        visibility="private",
        forked_from_project_id=source_project.id,
        description=source_project.description,
    )
    db.add(fork_project)
    db.flush()

    dag_versions = db.execute(
        select(DAGVersion)
        .where(DAGVersion.project_id == source_project.id)
        .order_by(DAGVersion.version_number.asc())
    ).scalars().all()

    dag_id_map: dict[str, str] = {version.id: generate_uuid() for version in dag_versions}
    for old in dag_versions:
        db.add(
            DAGVersion(
                id=dag_id_map[old.id],
                project_id=fork_project.id,
                version_number=old.version_number,
                name=old.name,
                description=old.description,
                parent_version_id=dag_id_map.get(old.parent_version_id),
                dag_definition=copy.deepcopy(old.dag_definition),
                dag_diff=copy.deepcopy(old.dag_diff) if old.dag_diff is not None else None,
                is_public=False,
                share_token=None,
                is_current=old.is_current,
                created_at=old.created_at,
            )
        )

    source_pipelines = db.execute(
        select(Pipeline).where(Pipeline.project_id == source_project.id)
    ).scalars().all()

    pipeline_version_id_map: dict[str, str] = {}
    new_pipelines: dict[str, Pipeline] = {}

    for old_pipeline in source_pipelines:
        new_pipeline = Pipeline(
            id=generate_uuid(),
            project_id=fork_project.id,
            name=old_pipeline.name,
            source_type=old_pipeline.source_type,
            current_version_id=None,
            created_at=old_pipeline.created_at,
        )
        db.add(new_pipeline)
        db.flush()
        new_pipelines[old_pipeline.id] = new_pipeline

        old_versions = db.execute(
            select(PipelineVersion)
            .where(PipelineVersion.pipeline_id == old_pipeline.id)
            .order_by(PipelineVersion.version_number.asc())
        ).scalars().all()

        for old_version in old_versions:
            new_version_id = generate_uuid()
            pipeline_version_id_map[old_version.id] = new_version_id
            db.add(
                PipelineVersion(
                    id=new_version_id,
                    pipeline_id=new_pipeline.id,
                    version_number=old_version.version_number,
                    steps=copy.deepcopy(old_version.steps),
                    input_schema=copy.deepcopy(old_version.input_schema),
                    output_schema=copy.deepcopy(old_version.output_schema),
                    lineage=copy.deepcopy(old_version.lineage),
                    source_dag_version_id=dag_id_map.get(
                        old_version.source_dag_version_id, old_version.source_dag_version_id
                    ),
                    source_upload_id=None,
                    source_seed=old_version.source_seed,
                    source_sample_size=old_version.source_sample_size,
                    source_fingerprint=old_version.source_fingerprint,
                    steps_hash=old_version.steps_hash,
                    created_at=old_version.created_at,
                )
            )

    for old_pipeline in source_pipelines:
        if old_pipeline.current_version_id is None:
            continue
        remapped_current = pipeline_version_id_map.get(old_pipeline.current_version_id)
        if remapped_current is None:
            raise_not_found()
        new_pipelines[old_pipeline.id].current_version_id = remapped_current

    db.commit()
    db.refresh(fork_project)
    return fork_project


# =============================================================================
# Project Endpoints
# =============================================================================


@router.get("", response_model=ProjectListResponse)
def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict[str, Any] = Depends(current_user_context),
) -> ProjectListResponse:
    """List projects visible to current user."""
    if current_user["is_admin"]:
        projects = crud.list_projects(db, skip=skip, limit=limit)
    else:
        projects = crud.list_projects_for_owner(
            db,
            owner_user_id=current_user["user_id"],
            skip=skip,
            limit=limit,
        )
    project_responses = [_serialize_project(project) for project in projects]
    return ProjectListResponse(projects=project_responses, total=len(project_responses))


@router.get("/discover", response_model=ProjectListResponse)
def discover_projects(
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> ProjectListResponse:
    """Discover public projects not owned by the current user."""
    projects = crud.list_discoverable_projects(db, user_id=current_user["user_id"])
    project_responses = [_serialize_project(project) for project in projects]
    return ProjectListResponse(projects=project_responses, total=len(project_responses))


@router.post("", response_model=ProjectDetailResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    request: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> ProjectDetailResponse:
    """Create a new project."""
    existing = crud.get_project_by_name(db, request.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project with name '{request.name}' already exists",
        )

    project = crud.create_project(
        db,
        name=request.name,
        owner_user_id=current_user["user_id"],
        description=request.description,
        visibility=request.visibility,
        dag_definition=request.dag_definition,
    )

    return _serialize_project_detail(project)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> ProjectDetailResponse:
    """Get a project by ID with current DAG."""
    project = require_project_read(db, project_id, current_user["user_id"])
    return _serialize_project_detail(project)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    request: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> ProjectResponse:
    """Update project metadata."""
    project = require_project_owner(db, project_id, current_user["user_id"])

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
    if request.visibility is not None:
        project.visibility = request.visibility
        db.commit()
        db.refresh(project)

    return _serialize_project(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> None:
    """Delete a project and all its versions."""
    project = require_project_owner(db, project_id, current_user["user_id"])
    crud.delete_project(db, project)


@router.post("/{project_id}/fork", response_model=ProjectDetailResponse, status_code=status.HTTP_201_CREATED)
def fork_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> ProjectDetailResponse:
    """Fork a readable project into a new private project owned by the current user."""
    source_project = require_project_read(db, project_id, current_user["user_id"])

    if _project_has_upload_backed_pipeline(db, source_project.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forking upload-backed projects is not supported yet",
        )

    try:
        forked = _fork_project(db, source_project, current_user["user_id"])
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not allocate fork name",
        ) from error

    return _serialize_project_detail(forked)


# =============================================================================
# Version Endpoints
# =============================================================================


@router.get("/{project_id}/versions", response_model=VersionListResponse)
def list_versions(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> VersionListResponse:
    """List all versions for a project."""
    require_project_read(db, project_id, current_user["user_id"])

    versions = crud.list_versions(db, project_id)
    version_responses = [_serialize_version(version) for version in versions]
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
    current_user: dict[str, str] = Depends(current_user_context),
) -> DAGVersionDetailResponse:
    """Save a new DAG version for a project."""
    require_project_owner(db, project_id, current_user["user_id"])

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
        **_serialize_version(version).model_dump(),
        dag_definition=version.dag_definition,
        dag_diff=version.dag_diff,
    )


@router.get("/{project_id}/versions/{version_id}", response_model=DAGVersionDetailResponse)
def get_version(
    project_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> DAGVersionDetailResponse:
    """Get a specific version with its DAG definition."""
    require_project_read(db, project_id, current_user["user_id"])

    version = crud.get_version(db, version_id)
    if not version or version.project_id != project_id:
        raise_not_found()

    return DAGVersionDetailResponse(
        **_serialize_version(version).model_dump(),
        dag_definition=version.dag_definition,
        dag_diff=version.dag_diff,
    )


@router.put("/{project_id}/versions/{version_id}", response_model=DAGVersionDetailResponse)
def update_version(
    project_id: str,
    version_id: str,
    request: VersionUpdate,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> DAGVersionDetailResponse:
    """Update a specific version's DAG definition in place."""
    require_project_owner(db, project_id, current_user["user_id"])

    version = crud.get_version(db, version_id)
    if not version or version.project_id != project_id:
        raise_not_found()
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
        **_serialize_version(version).model_dump(),
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
    current_user: dict[str, str] = Depends(current_user_context),
) -> DAGVersionResponse:
    """Set a version as the current version."""
    require_project_owner(db, project_id, current_user["user_id"])

    version = crud.get_version(db, version_id)
    if not version or version.project_id != project_id:
        raise_not_found()

    try:
        version = crud.set_current_version(db, version)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return _serialize_version(version)


@router.post(
    "/{project_id}/versions/{version_id}/share",
    response_model=ShareVersionResponse,
)
def share_version(
    project_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> ShareVersionResponse:
    """Enable public sharing for a DAG version and return its share token."""
    require_project_owner(db, project_id, current_user["user_id"])

    version = crud.get_version(db, version_id)
    if not version or version.project_id != project_id:
        raise_not_found()

    version = crud.set_version_public(db, version, True)

    return ShareVersionResponse(
        project_id=project_id,
        version_id=version_id,
        is_public=version.is_public,
        share_token=version.share_token,
        public_path=(
            f"/api/public/dags/{version.share_token}" if version.share_token else None
        ),
    )


@router.delete(
    "/{project_id}/versions/{version_id}/share",
    response_model=ShareVersionResponse,
)
def unshare_version(
    project_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(current_user_context),
) -> ShareVersionResponse:
    """Disable public sharing for a DAG version."""
    require_project_owner(db, project_id, current_user["user_id"])

    version = crud.get_version(db, version_id)
    if not version or version.project_id != project_id:
        raise_not_found()

    version = crud.set_version_public(db, version, False)

    return ShareVersionResponse(
        project_id=project_id,
        version_id=version_id,
        is_public=version.is_public,
        share_token=version.share_token,
        public_path=None,
    )
