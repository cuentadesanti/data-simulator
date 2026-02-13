"""Utilities for uploaded data sources."""

from __future__ import annotations

import hashlib
import os
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import settings
from app.services.schema_inference import infer_schema_from_df


def ensure_upload_dir() -> Path:
    path = Path(settings.upload_storage_path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_storage_path(storage_uri: str) -> Path:
    """Ensure storage_uri is inside the configured upload directory."""
    upload_dir = Path(settings.upload_storage_path).resolve()
    target = Path(storage_uri).resolve()
    if not str(target).startswith(str(upload_dir) + os.sep) and target != upload_dir:
        raise ValueError("Invalid storage path")
    return target


def compute_upload_fingerprint(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def parse_upload(
    *,
    file_bytes: bytes,
    filename: str,
    format_hint: str | None = None,
) -> tuple[pd.DataFrame, list[dict[str, Any]], str]:
    lower = filename.lower()
    fmt = (format_hint or "").strip().lower()

    if not fmt:
        if lower.endswith(".csv"):
            fmt = "csv"
        elif lower.endswith(".parquet"):
            fmt = "parquet"

    if fmt not in {"csv", "parquet"}:
        raise ValueError("Unsupported file format. Only CSV and Parquet are allowed.")

    bio = BytesIO(file_bytes)
    if fmt == "csv":
        df = pd.read_csv(bio)
    else:
        df = pd.read_parquet(bio)

    if df.empty:
        raise ValueError("Uploaded dataset is empty.")

    schema = infer_schema_from_df(df)
    return df, schema, fmt


def persist_upload_bytes(source_id: str, fmt: str, file_bytes: bytes) -> str:
    upload_dir = ensure_upload_dir()
    filename = f"{source_id}.{fmt}"
    target = upload_dir / filename
    with open(target, "wb") as f:
        f.write(file_bytes)
    return str(target.resolve())


def load_upload_dataframe(storage_uri: str, fmt: str) -> pd.DataFrame:
    validate_storage_path(storage_uri)
    if not os.path.exists(storage_uri):
        raise ValueError("Source file no longer exists")
    if fmt == "csv":
        return pd.read_csv(storage_uri)
    if fmt == "parquet":
        return pd.read_parquet(storage_uri)
    raise ValueError("Unsupported stored source format")
