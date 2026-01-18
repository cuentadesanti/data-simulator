"""DAG validation service.

This module provides comprehensive validation for DAG definitions including:
- Limit checks (max nodes, edges, rows)
- Reserved keyword validation
- Cycle detection via topological sort
- Edge and node reference validation
- Group-by ancestor validation
- Edge semantic validation (references must have corresponding edges)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set

from app.core import (
    RESERVED_CONTEXT,
    RESERVED_FUNCTIONS,
    CycleDetectedError,
    InvalidNodeError,
    LimitError,
    MissingParentError,
    ReservedKeywordError,
    settings,
)
from app.core.exceptions import FormulaParseError
from app.models.dag import (
    DAGDefinition,
    DAGEdge,
    EdgeValidation,
    NodeConfig,
    ValidationResult,
)
from app.services.formula_parser import parse_formula
from app.utils.topological_sort import topological_sort

# Regex to extract variable names from formulas
# Matches valid Python identifiers that are not followed by '(' (to exclude function calls)
_VARIABLE_PATTERN = re.compile(r"\b([a-z_][a-z0-9_]*)\b(?!\s*\()", re.IGNORECASE)
# Canonical format: node("id")
_CANONICAL_NODE_PATTERN = re.compile(r'node\("([^"]+)"\)')

# Params that contain node references but shouldn't be parsed as formulas
_PASSTHROUGH_PARAMS = {"categories", "probs"}


def validate_dag(dag: DAGDefinition) -> ValidationResult:
    """Validate a DAG definition.

    Performs comprehensive validation including:
    1. Limit checks (max nodes, edges, rows)
    2. Reserved keyword validation (node IDs and context keys)
    3. Formula syntax validation (for deterministic nodes)
    4. Cycle detection via topological sort
    5. Edge validation (references existing nodes)
    6. Group-by validation (references existing ancestor nodes)
    7. Edge semantic validation (references must have corresponding edges)

    Args:
        dag: The DAG definition to validate

    Returns:
        ValidationResult with validation status, errors, warnings,
        topological order, edge statuses, and missing edges

    Example:
        >>> dag = DAGDefinition(
        ...     nodes=[...],
        ...     edges=[...],
        ...     metadata=GenerationMetadata(sample_size=1000)
        ... )
        >>> result = validate_dag(dag)
        >>> if result.valid:
        ...     print(f"Valid DAG with order: {result.topological_order}")
        ... else:
        ...     print(f"Errors: {result.errors}")
    """
    errors: List[str] = []
    warnings: List[str] = []
    edge_statuses: List[EdgeValidation] = []
    missing_edges: List[dict[str, str]] = []

    # Step 1: Check limits
    try:
        _validate_limits(dag, errors)
    except Exception as e:
        errors.append(str(e))

    # Step 2: Check reserved keywords
    try:
        _validate_reserved_keywords(dag, errors)
    except Exception as e:
        errors.append(str(e))

    # Step 2.5: Validate formula syntax
    try:
        _validate_formula_syntax(dag, errors)
    except Exception as e:
        errors.append(str(e))

    # If we already have critical errors, return early
    if errors:
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    # Step 3: Build node ID set for reference validation
    node_ids = {node.id for node in dag.nodes}
    context_keys = set(dag.context.keys()) | set(RESERVED_CONTEXT.keys())

    # Step 4: Validate edges reference existing nodes
    try:
        _validate_edges(dag.edges, node_ids, errors)
    except Exception as e:
        errors.append(str(e))

    # Step 5: Run topological sort (detects cycles)
    topological_order: List[str] | None = None
    try:
        topological_order = topological_sort(dag.nodes, dag.edges)
    except CycleDetectedError as e:
        errors.append(e.message)
    except Exception as e:
        errors.append(f"Error during topological sort: {str(e)}")

    # Step 6: Validate group_by references (must be ancestors in DAG)
    if topological_order:
        try:
            _validate_group_by_references(dag.nodes, dag.edges, node_ids, errors)
        except Exception as e:
            errors.append(str(e))

    # Step 7: Validate edge semantics (references must have corresponding edges)
    # and compute edge statuses
    try:
        edge_statuses, missing_edges = _validate_edge_semantics(
            dag.nodes, dag.edges, node_ids, context_keys, errors
        )
    except Exception as e:
        errors.append(f"Error validating edge semantics: {str(e)}")

    # Step 8: Generate warnings for common issues
    _generate_warnings(dag, warnings)

    # Determine if validation passed
    valid = len(errors) == 0

    return ValidationResult(
        valid=valid,
        errors=errors,
        warnings=warnings,
        topological_order=topological_order if valid else None,
        edge_statuses=edge_statuses,
        missing_edges=missing_edges,
    )


def _validate_limits(dag: DAGDefinition, errors: List[str]) -> None:
    """Validate DAG doesn't exceed configured limits.

    Args:
        dag: The DAG definition to validate
        errors: List to append error messages to
    """
    # Check node count
    node_count = len(dag.nodes)
    if node_count > settings.max_nodes:
        error = LimitError("max_nodes", node_count, settings.max_nodes)
        errors.append(error.message)

    # Check edge count
    edge_count = len(dag.edges)
    if edge_count > settings.max_edges:
        error = LimitError("max_edges", edge_count, settings.max_edges)
        errors.append(error.message)

    # Check sample size
    sample_size = dag.metadata.sample_size
    if sample_size > settings.max_rows_hard:
        error = LimitError("max_rows_hard", sample_size, settings.max_rows_hard)
        errors.append(error.message)

    # Check formula lengths
    for node in dag.nodes:
        if node.formula and len(node.formula) > settings.max_formula_length:
            error = InvalidNodeError(
                node.id,
                f"Formula length {len(node.formula)} exceeds maximum {settings.max_formula_length}",
            )
            errors.append(error.message)


def _validate_reserved_keywords(dag: DAGDefinition, errors: List[str]) -> None:
    """Validate node IDs and context keys don't use reserved keywords.

    Args:
        dag: The DAG definition to validate
        errors: List to append error messages to
    """
    # Check node IDs against reserved functions
    for node in dag.nodes:
        if node.id in RESERVED_FUNCTIONS:
            error = ReservedKeywordError(node.id, "function name")
            errors.append(error.message)

    # Check context keys against reserved context
    for key in dag.context.keys():
        if key in RESERVED_CONTEXT:
            error = ReservedKeywordError(key, "context key")
            errors.append(error.message)


def _validate_formula_syntax(dag: DAGDefinition, errors: List[str]) -> None:
    """Validate formula syntax for deterministic nodes.

    Uses the formula parser to pre-validate formulas with a test environment,
    catching syntax errors before data generation.

    IMPORTANT: Formulas use var_names (not node IDs). Only parent nodes (from edges)
    are included in test_row_data, matching the actual generation behavior.

    Args:
        dag: The DAG definition to validate
        errors: List to append error messages to
    """
    # Build mappings for var_name resolution
    # node_id -> var_name
    id_to_var_name = {node.id: node.effective_var_name for node in dag.nodes}
    # var_name -> node_id (for reverse lookup)
    var_name_to_id = {node.effective_var_name: node.id for node in dag.nodes}

    # Build parent map: node_id -> set of parent var_names (from edges)
    # This matches what generation does - only expose parent columns by var_name
    parent_var_names: Dict[str, Set[str]] = {node.id: set() for node in dag.nodes}
    for edge in dag.edges:
        if edge.target in parent_var_names and edge.source in id_to_var_name:
            # Store the var_name of the parent, not the ID
            parent_var_names[edge.target].add(id_to_var_name[edge.source])

    # Create test context with numeric values for all keys
    test_context = {}
    for key, value in dag.context.items():
        if isinstance(value, dict):
            # For lookup tables, create a test version with numeric values
            test_context[key] = {k: 1.0 for k in value.keys()}
        else:
            test_context[key] = 1.0

    # Validate each node's formula
    for node in dag.nodes:
        # Deterministic nodes MUST have a formula
        if node.kind == "deterministic":
            if not node.formula or not node.formula.strip():
                error = InvalidNodeError(
                    node.id,
                    "Deterministic node must have a formula",
                )
                errors.append(error.message)
                continue

        if node.formula:
            # Create test row_data with ONLY parent var_names (from edges)
            # This matches generation behavior exactly
            parent_vars = parent_var_names.get(node.id, set())
            test_row_data = {var_name: 1.0 for var_name in parent_vars}

            try:
                # Try to parse the formula with test data
                parse_formula(node.formula, test_row_data, test_context)
            except FormulaParseError as e:
                error = InvalidNodeError(
                    node.id,
                    f"Syntax error in formula: {e.details.get('error', str(e))}",
                )
                errors.append(error.message)
            except Exception as e:
                # Catch any other unexpected parsing errors (including UnknownVariableError)
                error = InvalidNodeError(
                    node.id,
                    f"Formula error: {str(e)}",
                )
                errors.append(error.message)


def _validate_edges(
    edges: List[DAGEdge],
    node_ids: Set[str],
    errors: List[str],
) -> None:
    """Validate all edges reference existing nodes.

    Args:
        edges: List of edges to validate
        node_ids: Set of valid node IDs
        errors: List to append error messages to
    """
    for edge in edges:
        if edge.source not in node_ids:
            error = InvalidNodeError(
                edge.target,
                f"Edge source '{edge.source}' does not exist",
            )
            errors.append(error.message)

        if edge.target not in node_ids:
            error = InvalidNodeError(
                edge.source,
                f"Edge target '{edge.target}' does not exist",
            )
            errors.append(error.message)


def _validate_group_by_references(
    nodes: List[NodeConfig],
    edges: List[DAGEdge],
    node_ids: Set[str],
    errors: List[str],
) -> None:
    """Validate group_by references point to existing ancestor nodes.

    A node with scope='group' must have a group_by that references an
    ancestor node (a node that appears before it in the DAG).

    Additional scope rules enforced:
    - group_by must reference a categorical node (dtype='category')
    - group_by must reference a row-scoped node (for v1)

    Args:
        nodes: List of node configurations
        edges: List of edges (for building ancestor relationships)
        node_ids: Set of valid node IDs
        errors: List to append error messages to
    """
    # Build ancestor map (which nodes can reach which other nodes)
    ancestors = _build_ancestor_map(nodes, edges)

    # Build a node lookup for checking dtype/scope
    node_lookup = {n.id: n for n in nodes}

    for node in nodes:
        if node.group_by:
            # Check group_by references an existing node
            if node.group_by not in node_ids:
                error = MissingParentError(node.id, node.group_by)
                errors.append(error.message)
                continue

            # Check group_by is an ancestor (or the node itself for edge cases)
            if node.id != node.group_by and node.group_by not in ancestors.get(node.id, set()):
                error = InvalidNodeError(
                    node.id,
                    f"group_by '{node.group_by}' must be an ancestor node in the DAG",
                )
                errors.append(error.message)
                continue

            # Get the referenced node for scope/dtype validation
            ref_node = node_lookup.get(node.group_by)
            if ref_node:
                # Check group_by references a categorical node
                if ref_node.dtype != "category":
                    error = InvalidNodeError(
                        node.id,
                        f"group_by '{node.group_by}' must be a categorical node "
                        f"(dtype='category'), but it has dtype='{ref_node.dtype}'",
                    )
                    errors.append(error.message)

                # Check group_by references a row-scoped node (v1 restriction)
                if ref_node.scope != "row":
                    error = InvalidNodeError(
                        node.id,
                        f"group_by '{node.group_by}' must be row-scoped, "
                        f"but it has scope='{ref_node.scope}'",
                    )
                    errors.append(error.message)


def _build_ancestor_map(
    nodes: List[NodeConfig],
    edges: List[DAGEdge],
) -> Dict[str, Set[str]]:
    """Build a map of node -> all its ancestors.

    Uses DFS to find all nodes reachable via incoming edges.

    Args:
        nodes: List of node configurations
        edges: List of directed edges

    Returns:
        Dictionary mapping each node ID to the set of all its ancestor node IDs
    """
    # Build reverse adjacency list (child -> parents)
    parents: Dict[str, List[str]] = {node.id: [] for node in nodes}
    for edge in edges:
        parents[edge.target].append(edge.source)

    # For each node, find all ancestors via DFS
    ancestors: Dict[str, Set[str]] = {}

    def find_ancestors(node_id: str, visited: Set[str]) -> Set[str]:
        """Recursively find all ancestors of a node."""
        if node_id in ancestors:
            return ancestors[node_id]

        # Prevent infinite loops in case of cycles (shouldn't happen after validation)
        if node_id in visited:
            return set()

        visited.add(node_id)
        result: Set[str] = set()

        for parent in parents[node_id]:
            result.add(parent)
            result.update(find_ancestors(parent, visited))

        ancestors[node_id] = result
        return result

    for node in nodes:
        find_ancestors(node.id, set())

    return ancestors


def _generate_warnings(dag: DAGDefinition, warnings: List[str]) -> None:
    """Generate warnings for common issues that aren't errors.

    Args:
        dag: The DAG definition to check
        warnings: List to append warning messages to
    """
    # Warn about isolated nodes (no edges)
    if dag.edges:
        node_ids_in_edges = set()
        for edge in dag.edges:
            node_ids_in_edges.add(edge.source)
            node_ids_in_edges.add(edge.target)

        isolated_nodes = [node.id for node in dag.nodes if node.id not in node_ids_in_edges]
        if isolated_nodes:
            warnings.append(
                f"Isolated nodes (not connected to any edges): {', '.join(isolated_nodes)}"
            )

    # Warn about high sample sizes
    if dag.metadata.sample_size > 1_000_000:
        warnings.append(
            f"Large sample size ({dag.metadata.sample_size:,} rows) may take "
            "significant time to generate"
        )

    # Warn about complex DAGs
    if len(dag.nodes) > 100:
        warnings.append(
            f"Large DAG with {len(dag.nodes)} nodes may have slower validation and generation times"
        )

    # Warn if no seed specified for reproducibility
    if dag.metadata.seed is None:
        warnings.append("No random seed specified - results will not be reproducible")


def _extract_references_from_formula(formula: str) -> Set[str]:
    """Extract variable references from a formula string.

    Handles both plain variable names (e.g., 'base_salary') and canonical
    format (e.g., 'node("node_123")').

    Args:
        formula: Formula expression string

    Returns:
        Set of variable names/IDs referenced in the formula
    """
    if not formula:
        return set()

    references = set()

    # Extract canonical node("id") references first
    canonical_matches = _CANONICAL_NODE_PATTERN.findall(formula)
    references.update(canonical_matches)

    # Find all potential plain variable names
    matches = _VARIABLE_PATTERN.findall(formula)

    # Filter out reserved functions and keywords
    for match in matches:
        if match.lower() not in RESERVED_FUNCTIONS and match not in {"True", "False", "None"}:
            references.add(match)

    return references


def _extract_references_from_params(params: Dict[str, Any], node_ids: Set[str]) -> Set[str]:
    """Extract node references from distribution parameters.

    Args:
        params: Distribution parameters dict
        node_ids: Set of valid node IDs (to distinguish from literals)

    Returns:
        Set of node IDs referenced in the parameters
    """
    references: Set[str] = set()

    for key, value in params.items():
        # Skip passthrough params (categories, probs) - they don't reference nodes
        if key in _PASSTHROUGH_PARAMS:
            continue

        if isinstance(value, str):
            # Formula expression - extract variables
            refs = _extract_references_from_formula(value)
            # Only include references that are actual node IDs
            references.update(refs & node_ids)

        elif isinstance(value, dict):
            # LookupValue or MappingValue
            if "key" in value:
                # The 'key' field references a node
                key_ref = value["key"]
                if key_ref in node_ids:
                    references.add(key_ref)

    return references


def _get_node_references(node: NodeConfig, allowed_identifiers: Set[str]) -> Set[str]:
    """Get all node references for a given node.

    Args:
        node: Node configuration
        allowed_identifiers: Set of valid node IDs or variable names to filter against

    Returns:
        Set of node IDs/names that this node references
    """
    references: Set[str] = set()

    # Check formula (for deterministic nodes)
    if node.formula:
        formula_refs = _extract_references_from_formula(node.formula)
        # Filter against valid identifiers (could be IDs or var_names)
        references.update(formula_refs & allowed_identifiers)

    # Check distribution params (for stochastic nodes)
    if node.distribution and node.distribution.params:
        param_refs = _extract_references_from_params(node.distribution.params, allowed_identifiers)
        references.update(param_refs)

    # Check group_by (must use node ID)
    if node.group_by and node.group_by in allowed_identifiers:
        references.add(node.group_by)

    return references


def _validate_edge_semantics(
    nodes: List[NodeConfig],
    edges: List[DAGEdge],
    node_ids: Set[str],
    context_keys: Set[str],
    errors: List[str],
) -> tuple[List[EdgeValidation], List[dict[str, str]]]:
    """Validate that node references have corresponding edges.

    For each node, checks that all referenced nodes are direct parents (have
    an incoming edge). Also computes edge status (used/unused).

    NOTE: Formulas use var_names, but edges use node_ids. This function
    translates between the two to check semantic correctness.

    Args:
        nodes: List of node configurations
        edges: List of edges
        node_ids: Set of valid node IDs
        context_keys: Set of valid context keys
        errors: List to append error messages to

    Returns:
        Tuple of (edge_statuses, missing_edges)
    """
    # Build mappings for var_name resolution
    id_to_var_name = {node.id: node.effective_var_name for node in nodes}
    var_name_to_id = {node.effective_var_name: node.id for node in nodes}
    var_names = set(var_name_to_id.keys())

    # Build parent map: node_id -> set of direct parent identifiers (IDs and var_names)
    parent_identifiers: Dict[str, Set[str]] = {node.id: set() for node in nodes}
    for edge in edges:
        if edge.target in parent_identifiers and edge.source in id_to_var_name:
            parent_identifiers[edge.target].add(edge.source)
            parent_identifiers[edge.target].add(id_to_var_name[edge.source])

    # Track which edges are used (by node_id pairs)
    used_edges: Set[tuple[str, str]] = set()
    missing_edges: List[dict[str, str]] = []

    # Check each node's references (which can be IDs or var_names)
    for node in nodes:
        # Get references - can be node IDs or var_names
        references = _get_node_references(node, node_ids | var_names)
        direct_parent_idents = parent_identifiers.get(node.id, set())

        for ref_ident in references:
            if ref_ident in direct_parent_idents:
                # Edge exists and is used - translate ident (ID or var_name) back to source source_id
                source_id = ref_ident if ref_ident in node_ids else var_name_to_id.get(ref_ident)
                if source_id:
                    used_edges.add((source_id, node.id))
            elif ref_ident in context_keys:
                # Reference to context key - valid, no edge needed
                pass
            elif ref_ident in (node_ids | var_names):
                # Reference to a node without an edge - error!
                source_id = ref_ident if ref_ident in node_ids else var_name_to_id.get(ref_ident)
                errors.append(
                    f"Node '{node.name}' references '{ref_ident}' but there is no edge. "
                    f"Add an edge to make this dependency explicit."
                )
                if source_id:
                    missing_edges.append({"source": source_id, "target": node.id})

    # Build edge statuses
    edge_statuses: List[EdgeValidation] = []
    for edge in edges:
        edge_tuple = (edge.source, edge.target)
        if edge_tuple in used_edges:
            edge_statuses.append(
                EdgeValidation(
                    source=edge.source,
                    target=edge.target,
                    status="used",
                )
            )
        else:
            source_var = id_to_var_name.get(edge.source, edge.source)
            target_node = next((n for n in nodes if n.id == edge.target), None)
            target_name = target_node.name if target_node else edge.target
            edge_statuses.append(
                EdgeValidation(
                    source=edge.source,
                    target=edge.target,
                    status="unused",
                    reason=f"Node '{target_name}' does not reference '{source_var}'",
                )
            )

    return edge_statuses, missing_edges
