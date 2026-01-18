"""DAG data models - core schema definitions."""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.config import CURRENT_SCHEMA_VERSION

# Valid Python identifier pattern for node IDs
NODE_ID_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")


# =============================================================================
# ParamValue Types - Explicit types to avoid heuristics
# =============================================================================


class LookupValue(BaseModel):
    """Lookup value in context[lookup][row[key]].

    Example:
        lookup: "base_salario"
        key: "zona"
        default: 10000

    This will lookup context["base_salario"][row["zona"]], falling back to default.
    """

    lookup: str = Field(..., description="Name of the table in context")
    key: str = Field(..., description="Node ID from which to take the category value")
    default: float = Field(0, description="Default value if key not found")


class MappingValue(BaseModel):
    """Inline mapping (small, doesn't need context).

    Example:
        mapping: {"norte": 8000, "sur": 12000}
        key: "zona"
        default: 10000
    """

    mapping: dict[str, float] = Field(..., description="Inline category-to-value mapping")
    key: str = Field(..., description="Node ID from which to take the category value")
    default: float = Field(0, description="Default value if key not found")


# ParamValue: strict typing without ambiguity
ParamValue = Annotated[
    Union[float, int, str, LookupValue, MappingValue],
    Field(
        description=(
            "Parameter value: literal number, expression string, LookupValue, or MappingValue"
        )
    ),
]


# =============================================================================
# Distribution Configuration
# =============================================================================


class DistributionConfig(BaseModel):
    """Distribution configuration for stochastic nodes."""

    type: str = Field(..., description='Distribution type: "normal", "categorical", etc.')
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Distribution parameters (can include ParamValue types)",
    )


# =============================================================================
# Post-Processing Configuration
# =============================================================================


class PostProcessing(BaseModel):
    """Post-processing configuration for realism."""

    round_decimals: int | None = Field(None, ge=0, le=10, description="Round to N decimals")
    clip_min: float | None = Field(None, description="Minimum clipping value")
    clip_max: float | None = Field(None, description="Maximum clipping value")
    missing_rate: float | None = Field(None, ge=0, le=1, description="Missing value rate (MCAR)")

    @model_validator(mode="after")
    def validate_clip_range(self) -> "PostProcessing":
        """Ensure clip_min <= clip_max if both are set."""
        if self.clip_min is not None and self.clip_max is not None:
            if self.clip_min > self.clip_max:
                raise ValueError("clip_min must be <= clip_max")
        return self


# =============================================================================
# Node Configuration
# =============================================================================

NodeKind = Literal["stochastic", "deterministic"]
NodeDtype = Literal["float", "int", "category", "bool", "string"]
NodeScope = Literal["global", "group", "row"]


def to_snake_case(name: str) -> str:
    """Convert a name to snake_case for use as variable name.

    Examples:
        "My Variable" -> "my_variable"
        "Income (USD)" -> "income_usd"
        "customer-age" -> "customer_age"
    """
    # Replace common separators with spaces
    result = re.sub(r"[-\s]+", " ", name)
    # Remove non-alphanumeric characters (except spaces)
    result = re.sub(r"[^a-zA-Z0-9\s]", "", result)
    # Split into words and join with underscores
    words = result.strip().lower().split()
    result = "_".join(words)
    # Ensure it starts with a letter or underscore
    if result and result[0].isdigit():
        result = "_" + result
    # If empty, return a default
    return result if result else "var"


class NodeConfig(BaseModel):
    """Configuration for a single node in the DAG."""

    id: str = Field(..., description="Unique identifier (internal, auto-generated)")
    name: str = Field(..., description="Display name (UI only)")
    var_name: str | None = Field(
        None,
        description="Variable name for formulas and output columns (defaults to snake_case of name)",
    )
    kind: NodeKind = Field(..., description="Node type: stochastic or deterministic")
    dtype: NodeDtype | None = Field(None, description="Data type (optional, inferrable)")
    scope: NodeScope = Field("row", description="Scope: global, group, or row")
    group_by: str | None = Field(
        None, description="Node var_name to group by (only for scope=group)"
    )

    # MECE: only one of these should be set based on kind
    distribution: DistributionConfig | None = Field(
        None, description="Distribution config (for stochastic nodes)"
    )
    formula: str | None = Field(None, description="Formula expression (for deterministic nodes)")

    # Post-processing
    post_processing: PostProcessing | None = Field(None, description="Post-processing config")

    @field_validator("var_name")
    @classmethod
    def validate_var_name(cls, v: str | None) -> str | None:
        """Validate var_name is a valid Python identifier if provided."""
        if v is not None and not NODE_ID_PATTERN.match(v):
            raise ValueError(
                f"Variable name '{v}' must be a valid identifier (lowercase, underscores, "
                "starting with letter or underscore)"
            )
        return v

    @property
    def effective_var_name(self) -> str:
        """Get the effective variable name (explicit or derived from name)."""
        if self.var_name:
            return self.var_name
        return to_snake_case(self.name)

    @model_validator(mode="after")
    def validate_mece(self) -> "NodeConfig":
        """Ensure MECE: stochastic has distribution, deterministic has formula."""
        if self.kind == "stochastic":
            if self.distribution is None:
                raise ValueError("Stochastic nodes must have a distribution")
            if self.formula is not None:
                raise ValueError("Stochastic nodes cannot have a formula")
        elif self.kind == "deterministic":
            if self.formula is None:
                raise ValueError("Deterministic nodes must have a formula")
            if self.distribution is not None:
                raise ValueError("Deterministic nodes cannot have a distribution")
        return self

    @model_validator(mode="after")
    def validate_group_by(self) -> "NodeConfig":
        """Validate group_by is only set for group scope."""
        if self.scope == "group" and self.group_by is None:
            raise ValueError("Nodes with scope='group' must specify group_by")
        if self.scope != "group" and self.group_by is not None:
            raise ValueError("group_by can only be set when scope='group'")
        return self


# =============================================================================
# Edge Configuration
# =============================================================================


class DAGEdge(BaseModel):
    """Edge in the DAG representing a dependency."""

    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")


# =============================================================================
# Constraint Configuration
# =============================================================================

ConstraintType = Literal["range", "not_null", "unique", "comparison"]
ComparisonOperator = Literal["<", "<=", ">", ">="]


class Constraint(BaseModel):
    """Constraint for validating generated rows."""

    type: ConstraintType = Field(..., description="Constraint type")
    target: str = Field(..., description="Target node ID")

    # For type="range"
    min: float | None = Field(None, description="Minimum value (for range)")
    max: float | None = Field(None, description="Maximum value (for range)")

    # For type="comparison"
    other: str | None = Field(None, description="Other node ID (for comparison)")
    operator: ComparisonOperator | None = Field(None, description="Comparison operator")

    @model_validator(mode="after")
    def validate_constraint_params(self) -> "Constraint":
        """Validate constraint has required params for its type."""
        if self.type == "comparison":
            if self.other is None or self.operator is None:
                raise ValueError("Comparison constraints require 'other' and 'operator'")
        return self


# =============================================================================
# Generation Metadata
# =============================================================================


class GenerationMetadata(BaseModel):
    """Metadata for data generation."""

    sample_size: int = Field(..., gt=0, description="Number of rows to generate")
    seed: int | None = Field(None, description="Random seed for reproducibility")
    preview_rows: int = Field(500, gt=0, le=10000, description="Rows for preview")


# =============================================================================
# DAG Definition (Top-level)
# =============================================================================


class DAGDefinition(BaseModel):
    """Complete DAG definition for data generation."""

    schema_version: str = Field(CURRENT_SCHEMA_VERSION, description="Schema version")
    nodes: list[NodeConfig] = Field(..., min_length=1, description="List of nodes")
    edges: list[DAGEdge] = Field(default_factory=list, description="List of edges")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Context: mappings, constants, mini-tables",
    )
    constraints: list[Constraint] = Field(default_factory=list, description="Row constraints")
    metadata: GenerationMetadata = Field(..., description="Generation metadata")

    @field_validator("nodes")
    @classmethod
    def validate_unique_node_ids(cls, v: list[NodeConfig]) -> list[NodeConfig]:
        """Ensure all node IDs are unique."""
        ids = [node.id for node in v]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate node IDs: {set(duplicates)}")
        return v

    @model_validator(mode="after")
    def validate_unique_var_names(self) -> "DAGDefinition":
        """Ensure all effective var_names are unique."""
        var_names = [node.effective_var_name for node in self.nodes]
        if len(var_names) != len(set(var_names)):
            duplicates = [vn for vn in var_names if var_names.count(vn) > 1]
            raise ValueError(
                f"Duplicate variable names: {set(duplicates)}. "
                "Each node must have a unique var_name."
            )
        return self


# =============================================================================
# Validation Result
# =============================================================================

EdgeStatus = Literal["used", "unused", "invalid"]


class EdgeValidation(BaseModel):
    """Validation status for a single edge."""

    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    status: EdgeStatus = Field(..., description="Edge status: used, unused, or invalid")
    reason: str | None = Field(None, description="Reason for status (if not 'used')")


class ValidationResult(BaseModel):
    """Result of DAG validation."""

    valid: bool = Field(..., description="Whether the DAG is valid")
    errors: list[str] = Field(default_factory=list, description="List of validation errors")
    warnings: list[str] = Field(default_factory=list, description="List of warnings")
    topological_order: list[str] | None = Field(
        None, description="Node IDs in topological order (if valid)"
    )
    edge_statuses: list[EdgeValidation] = Field(
        default_factory=list, description="Status of each edge (used/unused/invalid)"
    )
    missing_edges: list[dict[str, str]] = Field(
        default_factory=list,
        description="Edges that should be added (node references without edges)",
    )
