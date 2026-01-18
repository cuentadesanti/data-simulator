"""CRUD operations for database models."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DAGVersion, Project
from app.models.dag import DAGDefinition


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
    set_current: bool = True,
) -> DAGVersion:
    """Create a new DAG version for a project."""
    # Get next version number
    latest = get_latest_version_number(db, project_id)
    next_version = latest + 1

    # If setting as current, unset current flag from other versions
    if set_current:
        _unset_current_versions(db, project_id)

    # Serialize DAGDefinition to dict
    dag_dict: dict[str, Any] = dag_definition.model_dump(mode="json")

    version = DAGVersion(
        project_id=project_id,
        version_number=next_version,
        dag_definition=dag_dict,
        is_current=set_current,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def set_current_version(db: Session, version: DAGVersion) -> DAGVersion:
    """Set a version as the current version."""
    # Unset current flag from other versions
    _unset_current_versions(db, version.project_id)

    version.is_current = True
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
