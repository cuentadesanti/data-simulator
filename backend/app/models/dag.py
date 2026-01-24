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

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Ensure node ID follows snake_case naming conventions."""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError("Node ID must be snake_case (e.g., income_y)")
        return v

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

    @property
    def effective_var_name(self) -> str:
        """Get the effective variable name (canonical node ID)."""
        return self.id

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert a name to snake_case variable format."""
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
        return result or "unnamed"

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
# Layout Configuration
# =============================================================================


# Position bounds to prevent issues with extremely large values
POSITION_MIN = -100000.0
POSITION_MAX = 100000.0


class NodePosition(BaseModel):
    """Position of a node in the visual editor."""

    x: float = Field(..., ge=POSITION_MIN, le=POSITION_MAX, description="X coordinate")
    y: float = Field(..., ge=POSITION_MIN, le=POSITION_MAX, description="Y coordinate")



class Viewport(BaseModel):
    """Viewport state (pan position and zoom level)."""

    x: float = Field(..., description="Viewport value x")
    y: float = Field(..., description="Viewport value y")
    zoom: float = Field(..., description="Zoom level")


class Layout(BaseModel):
    """Visual layout information for the DAG editor."""

    positions: dict[str, NodePosition] = Field(
        default_factory=dict,
        description="Node positions keyed by node ID"
    )
    viewport: Viewport | None = Field(None, description="Viewport state (x, y, zoom)")


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
    layout: Layout | None = Field(None, description="Visual layout for the editor")
    was_migrated: bool = Field(False, description="Internal flag: was this DAG migrated from legacy IDs?")

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_ids(cls, data: Any) -> Any:
        """Automatically sanitize legacy node IDs and update all references.
        
        This enables existing DAGs with legacy IDs (e.g., 'Node 1') to work 
        seamlessly by migrating them to canonical snake_case during load.
        """
        if not isinstance(data, dict) or "nodes" not in data:
            return data
            
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        
        # 1. Identify nodes with invalid IDs and generate mapping
        id_map = {} # old_id -> new_id
        used_new_ids = set()
        
        # Helper to get field value regardless of whether it's a dict or object
        def get_val(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # First pass: collect already valid IDs to avoid collisions
        for node in nodes:
            node_id = get_val(node, "id")
            if node_id and NODE_ID_PATTERN.match(node_id):
                used_new_ids.add(node_id)
        
        # Second pass: generate new IDs for invalid ones
        for node in nodes:
            old_id = get_val(node, "id")
            if old_id and not NODE_ID_PATTERN.match(old_id):
                new_id = to_snake_case(old_id)
                # Ensure uniqueness
                base_id = new_id
                counter = 1
                while new_id in used_new_ids:
                    new_id = f"{base_id}_{counter}"
                    counter += 1
                
                id_map[old_id] = new_id
                used_new_ids.add(new_id)
        
        if not id_map:
            return data
            
        # 2. Update nodes
        new_nodes = []
        for node in nodes:
            # Create a dict copy for modification
            if isinstance(node, dict):
                new_node = {**node}
            else:
                # If it's a NodeConfig object, convert to dict first
                new_node = node.model_dump() if hasattr(node, "model_dump") else vars(node).copy()

            old_id = new_node.get("id")
            if old_id in id_map:
                new_node["id"] = id_map[old_id]
            
            # Update formula node() references
            formula = new_node.get("formula")
            if formula:
                for old_id_ref, new_id_ref in id_map.items():
                    formula = formula.replace(f'node("{old_id_ref}")', f'node("{new_id_ref}")')
                new_node["formula"] = formula
            
            # Update group_by
            group_by = new_node.get("group_by")
            if group_by in id_map:
                new_node["group_by"] = id_map[group_by]
                
            new_nodes.append(new_node)
            
        # 3. Update edges
        new_edges = []
        for edge in edges:
            if isinstance(edge, dict):
                new_edge = {**edge}
            else:
                new_edge = edge.model_dump() if hasattr(edge, "model_dump") else vars(edge).copy()

            source = new_edge.get("source")
            target = new_edge.get("target")
            if source in id_map:
                new_edge["source"] = id_map[source]
            if target in id_map:
                new_edge["target"] = id_map[target]
            new_edges.append(new_edge)
            
        # 4. Update constraints
        constraints = data.get("constraints", [])
        new_constraints = []
        for c in constraints:
            if isinstance(c, dict):
                new_c = {**c}
            else:
                new_c = c.model_dump() if hasattr(c, "model_dump") else vars(c).copy()

            target = new_c.get("target")
            other = new_c.get("other")
            if target in id_map:
                new_c["target"] = id_map[target]
            if other in id_map:
                new_c["other"] = id_map[other]
            new_constraints.append(new_c)
            
        # 5. Update layout positions
        layout = data.get("layout")
        new_layout = layout
        if layout and isinstance(layout, dict) and "positions" in layout:
            positions = layout.get("positions", {})
            new_positions = {}
            for old_id, pos in positions.items():
                new_id = id_map.get(old_id, old_id)
                new_positions[new_id] = pos
            new_layout = {**layout, "positions": new_positions}
            
        return {
            **data,
            "nodes": new_nodes,
            "edges": new_edges,
            "constraints": new_constraints,
            "layout": new_layout,
            "was_migrated": True
        }

    @field_validator("nodes")
    @classmethod
    def validate_unique_node_ids(cls, v: list[NodeConfig]) -> list[NodeConfig]:
        """Ensure all node IDs are unique."""
        ids = [node.id for node in v]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate node IDs: {set(duplicates)}")
        return v


# =============================================================================
# Validation Result
# =============================================================================

EdgeStatus = Literal["used", "unused", "invalid"]
ErrorCode = Literal[
    "CYCLE_DETECTED",
    "MISSING_EDGE",
    "INVALID_EDGE",
    "UNKNOWN_VARIABLE",
    "SYNTAX_ERROR",
    "RESERVED_KEYWORD",
    "INVALID_GROUP_BY",
    "LIMIT_EXCEEDED",
    "MISSING_DISTRIBUTION",
    "MISSING_FORMULA",
    "INVALID_DTYPE",
    "DUPLICATE_NODE_ID",
    "DUPLICATE_VAR_NAME",
    "ISOLATED_NODE",
    "GENERAL_ERROR",
]
ErrorSeverity = Literal["error", "warning"]


class ValidationError(BaseModel):
    """Structured validation error with actionable information."""

    code: ErrorCode = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    severity: ErrorSeverity = Field("error", description="Error severity level")
    node_id: str | None = Field(None, description="ID of the affected node (if applicable)")
    node_name: str | None = Field(None, description="Name of the affected node (if applicable)")
    suggestion: str | None = Field(None, description="Actionable suggestion to fix the error")
    context: dict[str, Any] | None = Field(
        None, description="Additional context (e.g., expected vs actual values)"
    )


class EdgeValidation(BaseModel):
    """Validation status for a single edge."""

    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    status: EdgeStatus = Field(..., description="Edge status: used, unused, or invalid")
    reason: str | None = Field(None, description="Reason for status (if not 'used')")


class ValidationResult(BaseModel):
    """Result of DAG validation."""

    valid: bool = Field(..., description="Whether the DAG is valid")
    errors: list[str] = Field(default_factory=list, description="List of validation errors (legacy)")
    warnings: list[str] = Field(default_factory=list, description="List of warnings (legacy)")
    structured_errors: list[ValidationError] = Field(
        default_factory=list, description="Structured validation errors with codes and suggestions"
    )
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
    sanitized_dag: DAGDefinition | None = Field(
        None, description="The DAG definition after automatic migration/sanitization"
    )
