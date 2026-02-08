"""Generation-related models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.dag import DAGDefinition


class ColumnStats(BaseModel):
    """Statistics for a single column."""

    node_id: str = Field(..., description="Node ID (stable identifier)")
    var_name: str = Field(..., description="Variable/column name (display name)")
    dtype: str = Field(..., description="Data type")

    # Numeric stats
    mean: float | None = Field(None, description="Mean value")
    std: float | None = Field(None, description="Standard deviation")
    min: float | None = Field(None, description="Minimum value")
    max: float | None = Field(None, description="Maximum value")
    median: float | None = Field(None, description="Median value")

    # Null stats
    null_count: int = Field(0, description="Number of null values")
    null_rate: float = Field(0, description="Rate of null values")

    # Categorical stats
    categories: dict[str, int] | None = Field(None, description="Category counts")
    category_rates: dict[str, float] | None = Field(None, description="Category rates")


class ConstraintFailure(BaseModel):
    """Information about constraint failures."""

    type: str = Field(..., description="Constraint type")
    target: str = Field(..., description="Target node ID")
    failures: int = Field(..., description="Number of failures")


class GenerationResult(BaseModel):
    """Result of data generation."""

    job_id: str | None = Field(None, description="Job ID (for async generation)")
    status: Literal["completed", "pending", "running", "failed"] = Field(
        ..., description="Generation status"
    )

    # Metadata
    rows: int = Field(..., description="Number of rows generated")
    columns: list[str] = Field(..., description="Column names (node IDs)")
    seed: int = Field(..., description="Random seed used")
    format: Literal["csv", "parquet", "json"] = Field(..., description="Output format")
    size_bytes: int | None = Field(None, description="Output file size in bytes")
    schema_version: str = Field("1.0", description="Schema version")

    # Validation
    warnings: list[str] = Field(default_factory=list, description="Generation warnings")
    constraint_pass_rate: float | None = Field(None, description="Constraint pass rate")
    constraint_failures: list[ConstraintFailure] = Field(
        default_factory=list, description="Constraint failure details"
    )

    # Download
    download_url: str | None = Field(None, description="Download URL (for async)")


class PreviewResponse(BaseModel):
    """Response for preview endpoint."""

    data: list[dict[str, Any]] = Field(..., description="Preview data rows")
    columns: list[str] = Field(..., description="Column names")
    rows: int = Field(..., description="Number of rows in preview")
    seed: int = Field(..., description="Random seed used")
    column_stats: list[ColumnStats] = Field(..., description="Per-column statistics")
    warnings: list[str] = Field(default_factory=list, description="Generation warnings")
    sanitized_dag: DAGDefinition | None = Field(
        None, description="The DAG definition after automatic migration/sanitization"
    )


class EvaluationResult(BaseModel):
    """Result of DAG evaluation."""

    column_stats: list[ColumnStats] = Field(..., description="Per-column statistics")
    correlation_matrix: dict[str, dict[str, float]] = Field(..., description="Correlation matrix")
    constraint_pass_rate: float = Field(..., description="Constraint pass rate (0-1)")
    constraint_failures: list[ConstraintFailure] = Field(
        default_factory=list, description="Constraint failure details"
    )
