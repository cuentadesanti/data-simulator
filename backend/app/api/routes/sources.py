"""Uploaded data source API routes."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import current_user_context, require_auth, require_user_id
from app.core.project_access import require_project_owner
from app.core.config import settings
from app.db import crud, get_db
from app.services.upload_source import (
    compute_upload_fingerprint,
    parse_upload,
    persist_upload_bytes,
    validate_storage_path,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class UploadSourceResponse(BaseModel):
    source_id: str
    schema: list[dict[str, Any]]
    row_count_sample: int
    warnings: list[str]


class SourceMetadataResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    format: str
    size_bytes: int
    schema: list[dict[str, Any]]
    upload_fingerprint: str
    created_by: str
    created_at: str


class SourceListResponse(BaseModel):
    sources: list[SourceMetadataResponse]



@router.post("/upload", response_model=UploadSourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_source(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_auth),
    current_user: dict[str, str] = Depends(current_user_context),
) -> UploadSourceResponse:
    user_id = require_user_id(user)
    require_project_owner(db, project_id, current_user["user_id"])

    max_size = settings.upload_max_size_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max {settings.upload_max_size_mb}MB",
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    try:
        df, schema, fmt = parse_upload(file_bytes=content, filename=file.filename or "upload")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    fingerprint = compute_upload_fingerprint(content)

    # Persist file first, then create DB row to avoid orphaned rows.
    from app.db.models import generate_uuid

    source_id = generate_uuid()
    storage_uri = persist_upload_bytes(source_id, fmt, content)

    try:
        source = crud.create_uploaded_source(
            db,
            id=source_id,
            project_id=project_id,
            filename=file.filename or f"upload.{fmt}",
            file_format=fmt,
            size_bytes=len(content),
            storage_uri=storage_uri,
            schema_json=schema,
            upload_fingerprint=fingerprint,
            created_by=user_id,
        )
    except Exception:
        try:
            os.remove(storage_uri)
        except OSError:
            pass
        raise

    return UploadSourceResponse(
        source_id=source.id,
        schema=schema,
        row_count_sample=min(len(df), 1000),
        warnings=[],
    )


@router.get("/{source_id}", response_model=SourceMetadataResponse)
def get_source(
    source_id: str,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_auth),
) -> SourceMetadataResponse:
    user_id = require_user_id(user)
    source = crud.get_uploaded_source(db, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    require_project_owner(db, source.project_id, user_id)
    return SourceMetadataResponse(
        id=source.id,
        project_id=source.project_id,
        filename=source.filename,
        format=source.format,
        size_bytes=source.size_bytes,
        schema=source.schema_json,
        upload_fingerprint=source.upload_fingerprint,
        created_by=source.created_by,
        created_at=source.created_at.isoformat(),
    )


@router.get("", response_model=SourceListResponse)
def list_sources(
    project_id: str,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_auth),
) -> SourceListResponse:
    user_id = require_user_id(user)
    require_project_owner(db, project_id, user_id)
    rows = crud.list_uploaded_sources(db, project_id=project_id)
    return SourceListResponse(
        sources=[
            SourceMetadataResponse(
                id=source.id,
                project_id=source.project_id,
                filename=source.filename,
                format=source.format,
                size_bytes=source.size_bytes,
                schema=source.schema_json,
                upload_fingerprint=source.upload_fingerprint,
                created_by=source.created_by,
                created_at=source.created_at.isoformat(),
            )
            for source in rows
        ]
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: str,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_auth),
) -> None:
    user_id = require_user_id(user)
    source = crud.get_uploaded_source(db, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    require_project_owner(db, source.project_id, user_id)

    if source.storage_uri:
        try:
            validated = validate_storage_path(source.storage_uri)
            validated.unlink(missing_ok=True)
        except (OSError, ValueError) as exc:
            logger.warning("Failed to remove source file: %s", exc)

    crud.delete_uploaded_source(db, source)
