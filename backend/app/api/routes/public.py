"""Public sharing routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import crud, get_db

router = APIRouter()


class PublicDAGResponse(BaseModel):
    """Response schema for a publicly shared DAG version."""

    project_id: str
    project_name: str
    version_id: str
    version_number: int
    shared_at: datetime
    dag_definition: dict[str, Any]


@router.get("/dags/{share_token}", response_model=PublicDAGResponse)
def get_public_dag(
    share_token: str,
    db: Session = Depends(get_db),
) -> PublicDAGResponse:
    """Fetch a publicly shared DAG version by token."""
    version = crud.get_version_by_share_token(db, share_token)
    if not version or not version.is_public:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared DAG not found",
        )

    project = crud.get_project(db, version.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared DAG not found",
        )

    return PublicDAGResponse(
        project_id=project.id,
        project_name=project.name,
        version_id=version.id,
        version_number=version.version_number,
        shared_at=version.created_at,
        dag_definition=version.dag_definition,
    )
