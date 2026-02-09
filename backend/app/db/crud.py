"""CRUD operations for database models."""

from __future__ import annotations

import json
import logging
import secrets
from typing import Any

import jsonpatch
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import DAGVersion, Project, UploadedSource, UXEvent
from app.models.dag import DAGDefinition

logger = logging.getLogger(__name__)
MAX_DAG_DIFF_BYTES = 100_000


# =============================================================================
# Project CRUD
# =============================================================================


def list_projects(db: Session, skip: int = 0, limit: int = 100) -> list[Project]:
    """List all projects with pagination."""
    stmt = select(Project).offset(skip).limit(limit).order_by(Project.updated_at.desc())
    return list(db.execute(stmt).scalars().all())


def get_project(db: Session, project_id: str) -> Project | None:
    """Get a project by ID."""
    return db.get(Project, project_id)


def get_project_by_name(db: Session, name: str) -> Project | None:
    """Get a project by name."""
    stmt = select(Project).where(Project.name == name)
    return db.execute(stmt).scalar_one_or_none()


def create_project(
    db: Session,
    name: str,
    description: str | None = None,
    dag_definition: DAGDefinition | None = None,
) -> Project:
    """Create a new project, optionally with an initial DAG version."""
    project = Project(name=name, description=description)
    db.add(project)
    db.flush()  # Get the project ID

    if dag_definition is not None:
        create_version(db, project.id, dag_definition, set_current=True)

    db.commit()
    db.refresh(project)
    return project


def update_project(
    db: Session,
    project: Project,
    name: str | None = None,
    description: str | None = None,
) -> Project:
    """Update project metadata."""
    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    """Delete a project and all its versions (cascade)."""
    db.delete(project)
    db.commit()


# =============================================================================
# DAG Version CRUD
# =============================================================================


def list_versions(db: Session, project_id: str) -> list[DAGVersion]:
    """List all versions for a project."""
    stmt = (
        select(DAGVersion)
        .where(DAGVersion.project_id == project_id)
        .order_by(DAGVersion.version_number.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_version(db: Session, version_id: str) -> DAGVersion | None:
    """Get a version by ID."""
    return db.get(DAGVersion, version_id)


def get_version_by_share_token(db: Session, share_token: str) -> DAGVersion | None:
    """Get a public DAG version by share token."""
    stmt = select(DAGVersion).where(DAGVersion.share_token == share_token)
    return db.execute(stmt).scalar_one_or_none()


def get_current_version(db: Session, project_id: str) -> DAGVersion | None:
    """Get the current version for a project."""
    stmt = (
        select(DAGVersion).where(DAGVersion.project_id == project_id, DAGVersion.is_current == True)  # noqa: E712
    )
    return db.execute(stmt).scalar_one_or_none()


def get_latest_version_number(db: Session, project_id: str) -> int:
    """Get the latest version number for a project."""
    stmt = (
        select(DAGVersion.version_number)
        .where(DAGVersion.project_id == project_id)
        .order_by(DAGVersion.version_number.desc())
        .limit(1)
    )
    result = db.execute(stmt).scalar_one_or_none()
    return result if result is not None else 0


def create_version(
    db: Session,
    project_id: str,
    dag_definition: DAGDefinition,
    name: str | None = None,
    description: str | None = None,
    set_current: bool = True,
) -> DAGVersion:
    """Create a new DAG version for a project."""
    # Get next version number
    latest = get_latest_version_number(db, project_id)
    next_version = latest + 1

    parent_version = get_current_version(db, project_id)

    # If setting as current, unset current flag from other versions
    if set_current:
        _unset_current_versions(db, project_id)
        db.flush()  # Flush to ensure is_current=False is persisted before creating new current

    # Serialize DAGDefinition to dict
    dag_dict: dict[str, Any] = dag_definition.model_dump(mode="json")

    dag_diff = None
    parent_version_id = None
    if parent_version:
        parent_version_id = parent_version.id
        dag_diff = _build_dag_diff(parent_version.dag_definition, dag_dict)

    version = DAGVersion(
        project_id=project_id,
        version_number=next_version,
        name=name,
        description=description,
        parent_version_id=parent_version_id,
        dag_definition=dag_dict,
        dag_diff=dag_diff,
        is_current=set_current,
    )
    db.add(version)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ValueError("Concurrent save conflict; please retry") from error
    db.refresh(version)
    return version


def update_version(
    db: Session,
    version: DAGVersion,
    dag_definition: DAGDefinition,
    name: str | None = None,
    description: str | None = None,
) -> DAGVersion:
    """Update an existing DAG version in place.

    Note: `parent_version_id` is intentionally immutable. `dag_diff` always
    represents delta from the original parent to the latest state.
    """
    dag_dict: dict[str, Any] = dag_definition.model_dump(mode="json")

    version.dag_definition = dag_dict
    if name is not None:
        version.name = name
    if description is not None:
        version.description = description

    if version.parent_version_id:
        parent = db.get(DAGVersion, version.parent_version_id)
        if parent:
            version.dag_diff = _build_dag_diff(parent.dag_definition, dag_dict)
        else:
            logger.warning(
                "Missing parent version while updating DAG version",
                extra={"version_id": version.id, "parent_version_id": version.parent_version_id},
            )
            version.dag_diff = None
    else:
        version.dag_diff = None

    db.commit()
    db.refresh(version)
    return version


def set_current_version(db: Session, version: DAGVersion) -> DAGVersion:
    """Set a version as the current version."""
    # Unset current flag from other versions
    _unset_current_versions(db, version.project_id)
    db.flush()  # Flush to ensure is_current=False is persisted before setting new current

    version.is_current = True
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ValueError("Concurrent save conflict; please retry") from error
    db.refresh(version)
    return version


def set_version_public(db: Session, version: DAGVersion, is_public: bool) -> DAGVersion:
    """Enable or disable public sharing for a version."""
    version.is_public = is_public
    if is_public:
        if not version.share_token:
            version.share_token = _generate_unique_share_token(db)
    else:
        version.share_token = None

    db.commit()
    db.refresh(version)
    return version


def _unset_current_versions(db: Session, project_id: str) -> None:
    """Unset is_current flag for all versions of a project."""
    stmt = (
        select(DAGVersion).where(DAGVersion.project_id == project_id, DAGVersion.is_current == True)  # noqa: E712
    )
    for version in db.execute(stmt).scalars().all():
        version.is_current = False


def _generate_unique_share_token(db: Session) -> str:
    """Generate a unique URL-safe share token."""
    while True:
        token = secrets.token_urlsafe(24)
        existing = get_version_by_share_token(db, token)
        if existing is None:
            return token


def _build_dag_diff(previous_dag: dict[str, Any], current_dag: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Build a JSON patch diff and cap its size to avoid oversized DB payloads."""
    try:
        patch_ops = jsonpatch.JsonPatch.from_diff(previous_dag, current_dag).patch
    except Exception:
        logger.exception("Failed computing DAG diff")
        return None

    try:
        patch_size = len(json.dumps(patch_ops, separators=(",", ":")).encode("utf-8"))
    except Exception:
        logger.exception("Failed measuring DAG diff size")
        return None

    if patch_size > MAX_DAG_DIFF_BYTES:
        logger.warning(
            "Skipping oversized DAG diff",
            extra={"diff_bytes": patch_size, "max_bytes": MAX_DAG_DIFF_BYTES},
        )
        return None

    return patch_ops


# =============================================================================
# Uploaded Source CRUD
# =============================================================================


def create_uploaded_source(
    db: Session,
    *,
    project_id: str,
    filename: str,
    format: str,
    size_bytes: int,
    storage_uri: str,
    schema_json: list[dict[str, Any]],
    upload_fingerprint: str,
    created_by: str,
) -> UploadedSource:
    source = UploadedSource(
        project_id=project_id,
        filename=filename,
        format=format,
        size_bytes=size_bytes,
        storage_uri=storage_uri,
        schema_json=schema_json,
        upload_fingerprint=upload_fingerprint,
        created_by=created_by,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def get_uploaded_source(db: Session, source_id: str) -> UploadedSource | None:
    return db.get(UploadedSource, source_id)


def list_uploaded_sources(
    db: Session,
    *,
    project_id: str,
    created_by: str | None = None,
) -> list[UploadedSource]:
    stmt = select(UploadedSource).where(UploadedSource.project_id == project_id)
    if created_by:
        stmt = stmt.where(UploadedSource.created_by == created_by)
    stmt = stmt.order_by(UploadedSource.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def delete_uploaded_source(db: Session, source: UploadedSource) -> None:
    db.delete(source)
    db.commit()


# =============================================================================
# UX Event CRUD
# =============================================================================


def create_ux_events(
    db: Session,
    *,
    user_id: str,
    events: list[dict[str, Any]],
) -> int:
    rows: list[UXEvent] = []
    for event in events:
        rows.append(
            UXEvent(
                user_id=user_id,
                event_type=str(event.get("event_type", "unknown")),
                path_id=event.get("path_id"),
                stage=event.get("stage"),
                action=event.get("action"),
                latency_ms=event.get("latency_ms"),
                event_metadata=event.get("metadata") or {},
            )
        )
    db.add_all(rows)
    db.commit()
    return len(rows)


def list_ux_events(
    db: Session,
    *,
    user_id: str,
    since_dt: Any,
) -> list[UXEvent]:
    stmt = (
        select(UXEvent)
        .where(UXEvent.user_id == user_id, UXEvent.created_at >= since_dt)
        .order_by(UXEvent.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())
