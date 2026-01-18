"""Distribution-related models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ParameterInfo(BaseModel):
    """Information about a distribution parameter."""

    name: str = Field(..., description="Parameter name")
    description: str = Field(..., description="Parameter description")
    type: Literal["float", "int", "list", "dict"] = Field(..., description="Parameter type")
    required: bool = Field(True, description="Whether the parameter is required")
    default: float | int | list | dict | None = Field(None, description="Default value")
    min_value: float | None = Field(None, description="Minimum value (if applicable)")
    max_value: float | None = Field(None, description="Maximum value (if applicable)")


class DistributionInfo(BaseModel):
    """Information about an available distribution."""

    name: str = Field(..., description="Distribution name (e.g., 'normal')")
    display_name: str = Field(..., description="Display name (e.g., 'Normal')")
    description: str = Field(..., description="Distribution description")
    category: Literal["continuous", "discrete", "categorical"] = Field(
        ..., description="Distribution category"
    )
    parameters: list[ParameterInfo] = Field(..., description="List of parameters")
    default_dtype: Literal["float", "int", "category", "bool"] = Field(
        ..., description="Default output dtype"
    )
