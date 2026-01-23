"""Transforms API routes for listing available transforms."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.transform_registry import get_transform_registry

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================


class TransformParameter(BaseModel):
    """Parameter definition for a transform."""
    
    name: str
    display_name: str
    type: str
    required: bool
    default: Any | None
    description: str


class TransformInfo(BaseModel):
    """Information about a transform."""
    
    name: str
    display_name: str
    description: str
    parameters: list[TransformParameter]


class TransformsListResponse(BaseModel):
    """Response schema for listing transforms."""
    
    transforms: list[TransformInfo]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=TransformsListResponse)
def list_transforms() -> TransformsListResponse:
    """List all available transforms.
    
    Returns metadata about each transform including name, description,
    and parameter definitions for UI rendering.
    """
    registry = get_transform_registry()
    transforms_data = registry.list_all()
    
    transforms = [
        TransformInfo(
            name=t["name"],
            display_name=t["display_name"],
            description=t["description"],
            parameters=[TransformParameter(**p) for p in t["parameters"]],
        )
        for t in transforms_data
    ]
    
    return TransformsListResponse(transforms=transforms)
