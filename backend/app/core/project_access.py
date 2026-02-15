from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import Project


def raise_not_found() -> NoReturn:
    """Raise the canonical not-found response for inaccessible resources."""
    raise HTTPException(status_code=404, detail="Not found")


def require_project_read(db: Session, project_id: str, user_id: str) -> Project:
    """Return project if current user can read it, else raise not found."""
    project = db.get(Project, project_id)
    if not project:
        raise_not_found()
    if project.owner_user_id == user_id or project.visibility == "public":
        return project
    raise_not_found()


def require_project_owner(db: Session, project_id: str, user_id: str) -> Project:
    """Return project if current user owns it, else raise not found."""
    project = db.get(Project, project_id)
    if not project:
        raise_not_found()
    if project.owner_user_id == user_id:
        return project
    raise_not_found()
