"""Sampler service - core data generation pipeline.

This module ties together all the components to generate synthetic data:
- Validates DAG definitions
- Determines topological order for generation
- Samples stochastic nodes using distributions
- Evaluates deterministic nodes using formulas
- Applies post-processing (clipping, rounding, missing values)
- Computes statistics for preview and evaluation
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.core import SampleError, ValidationError
from app.core.exceptions import DistributionError
from app.models.dag import DAGDefinition, NodeConfig, PostProcessing
from app.models.generation import ColumnStats, GenerationResult, PreviewResponse
from app.services.distribution_registry import get_distribution_registry
from app.services.formula_parser import resolve_param_value
from app.services.validator import validate_dag
from app.utils.topological_sort import topological_sort


def generate_preview(dag: DAGDefinition) -> PreviewResponse:
    """Generate a preview of the data with a small sample.

    This function validates the DAG and generates a preview with the configured
    number of preview rows (default from metadata.preview_rows).

    Args:
        dag: DAG definition containing nodes, edges, and metadata

    Returns:
        PreviewResponse containing preview data, columns, stats, and warnings

    Raises:
        ValidationError: If DAG validation fails
        SampleError: If data generation fails
    """
    # Step 1: Validate DAG
    validation_result = validate_dag(dag)
    if not validation_result.valid:
        raise ValidationError(
            message=f"DAG validation failed: {'; '.join(validation_result.errors)}",
            details={"errors": validation_result.errors},
        )

    # Step 2: Determine preview size
    preview_rows = dag.metadata.preview_rows

    # Step 3: Generate data
    df, seed_used, warnings = _generate_data(
        dag=dag, sample_size=preview_rows, seed=dag.metadata.seed
    )

    # Step 4: Compute statistics
    column_stats = _compute_column_stats(df, dag)

    # Step 5: Convert DataFrame to list of dicts for JSON response
    data_records = df.to_dict(orient="records")

    # Step 6: Add validation warnings to generation warnings
    all_warnings = list(validation_result.warnings) + warnings

    return PreviewResponse(
        data=data_records,
        columns=list(df.columns),
        rows=len(df),
        seed=seed_used,
        column_stats=column_stats,
        warnings=all_warnings,
        sanitized_dag=dag,
    )


def generate_data(dag: DAGDefinition) -> GenerationResult:
    """Generate full dataset according to DAG specification.

    For MVP, this always generates data synchronously. In production, large
    datasets (> sync_threshold) would be queued for async generation.

    Args:
        dag: DAG definition containing nodes, edges, and metadata

    Returns:
        GenerationResult with metadata and status

    Raises:
        ValidationError: If DAG validation fails
        SampleError: If data generation fails
    """
    # Step 1: Validate DAG
    validation_result = validate_dag(dag)
    if not validation_result.valid:
        raise ValidationError(
            message=f"DAG validation failed: {'; '.join(validation_result.errors)}",
            details={"errors": validation_result.errors},
        )

    # Step 2: Generate data
    df, seed_used, warnings = _generate_data(
        dag=dag, sample_size=dag.metadata.sample_size, seed=dag.metadata.seed
    )

    # Step 3: For MVP, return completed result
    # In production, this would check if sample_size > settings.sync_threshold
    # and queue async job if needed

    # Add validation warnings
    all_warnings = list(validation_result.warnings) + warnings

    return GenerationResult(
        status="completed",
        rows=len(df),
        columns=list(df.columns),
        seed=seed_used,
        format="csv",  # Default format for MVP
        schema_version=dag.schema_version,
        warnings=all_warnings,
    )


def generate_data_with_df(
    dag: DAGDefinition,
) -> tuple[pd.DataFrame, GenerationResult]:
    """Generate full dataset and return both DataFrame and metadata.

    This is the function used by the API endpoint to get actual data.

    Args:
        dag: DAG definition containing nodes, edges, and metadata

    Returns:
        Tuple of (DataFrame with generated data, GenerationResult metadata)

    Raises:
        ValidationError: If DAG validation fails
        SampleError: If data generation fails
    """
    # Step 1: Validate DAG
    validation_result = validate_dag(dag)
    if not validation_result.valid:
        raise ValidationError(
            message=f"DAG validation failed: {'; '.join(validation_result.errors)}",
            details={"errors": validation_result.errors},
        )

    # Step 2: Generate data
    df, seed_used, warnings = _generate_data(
        dag=dag, sample_size=dag.metadata.sample_size, seed=dag.metadata.seed
    )

    # Add validation warnings
    all_warnings = list(validation_result.warnings) + warnings

    result = GenerationResult(
        status="completed",
        rows=len(df),
        columns=list(df.columns),
        seed=seed_used,
        format="csv",
        schema_version=dag.schema_version,
        warnings=all_warnings,
    )

    return df, result


def _generate_data(
    dag: DAGDefinition, sample_size: int, seed: int | None
) -> tuple[pd.DataFrame, int, list[str]]:
    """Core data generation logic.

    This function orchestrates the entire generation process:
    1. Initialize random number generator with seed
    2. Get topological order of nodes
    3. Generate each node in order (parents before children)
    4. Apply post-processing to each node
    5. Collect warnings during generation

    NOTE: Output columns use var_names (not node IDs) for user-friendly naming.
    Formulas reference parent nodes by their var_names.

    Args:
        dag: DAG definition
        sample_size: Number of rows to generate
        seed: Random seed (None = generate random seed)

    Returns:
        Tuple of (dataframe, seed_used, warnings)

    Raises:
        SampleError: If generation fails for any node
    """
    warnings: list[str] = []

    # Step 1: Initialize random number generator
    if seed is None:
        seed = np.random.randint(0, 2**31 - 1)
    rng = np.random.default_rng(seed)

    # Step 2: Get topological order (already validated, so this should succeed)
    try:
        node_order = topological_sort(dag.nodes, dag.edges)
    except Exception as e:
        raise SampleError(
            message=f"Failed to determine node ordering: {str(e)}",
            details={"error": str(e)},
        ) from e

    # Step 3: Create node lookup for easy access
    node_map = {node.id: node for node in dag.nodes}

    # Step 4: Build mappings for var_names
    # node_id -> var_name (for translating edges to var_names)
    id_to_var_name = {node.id: node.effective_var_name for node in dag.nodes}

    # Step 5: Build parent map from edges (node_id -> set of parent VAR_NAMES)
    # Note: We store var_names because formulas use var_names
    parent_var_names: dict[str, set[str]] = {node.id: set() for node in dag.nodes}
    for edge in dag.edges:
        parent_var = id_to_var_name.get(edge.source)
        if parent_var:
            parent_var_names[edge.target].add(parent_var)

    # Step 6: Initialize empty DataFrame
    df = pd.DataFrame()

    # Step 7: Generate each node in topological order
    for node_id in node_order:
        node = node_map[node_id]
        parent_vars = parent_var_names[node_id]
        var_name = id_to_var_name[node_id]

        try:
            # Generate values for this node (only exposing parent columns by var_name)
            values = _sample_node(
                node, df, dag.context, rng, sample_size, parent_vars, id_to_var_name
            )

            # Apply post-processing
            values = _apply_post_processing(
                values=values,
                pp=node.post_processing,
                dtype=node.dtype,
                rng=rng,
            )

            # Add to DataFrame using var_name as column name
            df[var_name] = values

        except DistributionError as e:
            # Re-raise with node context
            raise DistributionError(
                distribution_type=e.details.get("distribution_type", "unknown"),
                error_msg=str(e.message),
                node_id=node_id,
            ) from e
        except Exception as e:
            # Wrap unexpected errors
            raise SampleError(
                message=f"Failed to generate node '{node.name}': {str(e)}",
                node_id=node_id,
                details={"error": str(e), "error_type": type(e).__name__},
            ) from e

    return df, seed, warnings


def _sample_node(
    node: NodeConfig,
    df: pd.DataFrame,
    context: dict[str, Any],
    rng: np.random.Generator,
    sample_size: int,
    parent_var_names: set[str] | None = None,
    id_to_var_name: dict[str, str] | None = None,
) -> np.ndarray:
    """Generate values for a single node.

    Handles both stochastic (distribution-based) and deterministic (formula-based)
    nodes. Respects node scope (row, global, group).

    Args:
        node: Node configuration
        df: Current DataFrame with already-generated parent nodes (columns are var_names)
        context: Global context (lookup tables, constants)
        rng: Random number generator
        sample_size: Number of rows to generate
        parent_var_names: Set of parent var_names (from edges). If provided, only these
                 columns are exposed in the namespace. If None, all columns
                 are exposed (for backwards compatibility).
        id_to_var_name: Mapping from node ID to var_name (for group_by lookup)

    Returns:
        NumPy array of generated values

    Raises:
        DistributionError: If distribution sampling fails
        SampleError: If formula evaluation or other generation fails
    """
    # Convert DataFrame to dict of arrays for easier row access
    # Only include parent columns (from edges) in the namespace
    # Note: df columns are var_names, and parent_var_names are also var_names
    if parent_var_names is not None:
        # Filter to only include parent columns that exist in df
        available_parents = parent_var_names & set(df.columns)
        row_data_dict = {col: df[col].values for col in available_parents}
    else:
        # Backwards compatibility: expose all columns
        row_data_dict = {col: df[col].values for col in df.columns}

    if node.kind == "stochastic":
        return _sample_stochastic_node(
            node, row_data_dict, context, rng, sample_size, id_to_var_name
        )
    else:  # deterministic
        return _sample_deterministic_node(
            node, row_data_dict, context, sample_size, id_to_var_name
        )


def _sample_stochastic_node(
    node: NodeConfig,
    row_data_dict: dict[str, np.ndarray],
    context: dict[str, Any],
    rng: np.random.Generator,
    sample_size: int,
    id_to_var_name: dict[str, str] | None = None,
) -> np.ndarray:
    """Generate values for a stochastic node using distributions.

    Handles different scopes:
    - row: Generate sample_size independent values
    - global: Generate 1 value and broadcast to all rows
    - group: (MVP: basic implementation or skip)

    Handles dynamic parameters that reference other nodes.

    Args:
        node: Node configuration (must be stochastic)
        row_data_dict: Dictionary of var_name -> array of values
        context: Global context
        rng: Random number generator
        sample_size: Number of rows
        id_to_var_name: Mapping from node ID to var_name (for group_by lookup)

    Returns:
        Array of sampled values

    Raises:
        DistributionError: If distribution not found or sampling fails
    """
    if not node.distribution:
        raise SampleError(
            message=f"Stochastic node '{node.name}' missing distribution",
            node_id=node.id,
        )

    # Get distribution from registry
    registry = get_distribution_registry()
    distribution = registry.get_distribution(node.distribution.type)

    # Check if any params are dynamic (reference other nodes)
    has_dynamic_params = _has_dynamic_params(node.distribution.params, row_data_dict)

    if node.scope == "row":
        if has_dynamic_params:
            # Per-row sampling with dynamic params
            return _sample_per_row_dynamic(
                node, distribution, row_data_dict, context, rng, sample_size, id_to_var_name
            )
        else:
            # Vectorized sampling with static params
            resolved_params = _resolve_params_static(
                node.distribution.params, context, id_to_var_name
            )
            size = sample_size
            return distribution.sample(resolved_params, size, rng)

    elif node.scope == "global":
        # Generate 1 value and broadcast to all rows
        # For global scope, we use first row for parameter resolution
        first_row_data = {
            col: vals[0] if len(vals) > 0 else None for col, vals in row_data_dict.items()
        }
        resolved_params = _resolve_params_for_row(
            node.distribution.params, first_row_data, context, id_to_var_name
        )
        single_value = distribution.sample(resolved_params, 1, rng)[0]
        return np.full(sample_size, single_value)

    else:  # group scope
        # Full implementation: sample one value per unique category, map to rows
        return _sample_group_scope(
            node, distribution, row_data_dict, context, rng, sample_size, id_to_var_name
        )


def _sample_deterministic_node(
    node: NodeConfig,
    row_data_dict: dict[str, np.ndarray],
    context: dict[str, Any],
    sample_size: int,
    id_to_var_name: dict[str, str] | None = None,
) -> np.ndarray:
    """Generate values for a deterministic node using formulas.

    Evaluates the formula for each row using available parent node values.
    Optimized to expand formula once and reuse evaluator across rows.

    Args:
        node: Node configuration (must be deterministic)
        row_data_dict: Dictionary of column_name -> array of values
        context: Global context
        sample_size: Number of rows
        id_to_var_name: Mapping from node ID to var_name for canonical expansion

    Returns:
        Array of computed values

    Raises:
        SampleError: If formula evaluation fails
    """
    if not node.formula:
        raise SampleError(
            message=f"Deterministic node '{node.id}' missing formula",
            node_id=node.id,
        )

    # Import here to avoid circular dependencies
    from simpleeval import EvalWithCompoundTypes

    from app.services.formula_parser import (
        ALLOWED_FUNCTIONS,
        NameResolver,
        expand_canonical_references,
    )

    # Optimize: Expand canonical references once before the loop
    expanded_formula = expand_canonical_references(node.formula, id_to_var_name)

    # Optimize: Create evaluator once and reuse
    evaluator = EvalWithCompoundTypes()
    evaluator.functions = ALLOWED_FUNCTIONS

    # Pre-allocate result array
    if node.dtype in ("string", "category"):
        values = np.empty(sample_size, dtype=object)
    else:
        values = np.zeros(sample_size)

    # Evaluate formula for each row
    for i in range(sample_size):
        # Build row data dict for this row
        row_data = {col: vals[i] for col, vals in row_data_dict.items()}

        # Update name resolver (reuses same evaluator)
        evaluator.names = NameResolver(row_data, context)

        try:
            values[i] = evaluator.eval(expanded_formula)

        except Exception as e:
            # Wrap ALL errors in SampleError to maintain consistent API
            # This matches the original behavior before optimization
            raise SampleError(
                message=f"Formula evaluation failed for node '{node.id}' at row {i}: {str(e)}",
                node_id=node.id,
                details={
                    "formula": node.formula,
                    "row": i,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            ) from e

    return values


def _is_lookup_value(value: Any) -> bool:
    """Check if value is a LookupValue (Pydantic model or dict)."""
    from app.models.dag import LookupValue

    if isinstance(value, LookupValue):
        return True
    if isinstance(value, dict) and "lookup" in value and "key" in value:
        return True
    return False


def _is_mapping_value(value: Any) -> bool:
    """Check if value is a MappingValue (Pydantic model or dict)."""
    from app.models.dag import MappingValue

    if isinstance(value, MappingValue):
        return True
    if isinstance(value, dict) and "mapping" in value and "key" in value:
        return True
    return False


def _has_dynamic_params(params: dict[str, Any], row_data_dict: dict[str, np.ndarray]) -> bool:
    """Check if any parameters reference other nodes (are dynamic).

    A parameter is dynamic if it's a string (formula) that references a column,
    or if it's a LookupValue/MappingValue.

    Args:
        params: Distribution parameters
        row_data_dict: Available column names

    Returns:
        True if any param is dynamic
    """
    for value in params.values():
        # LookupValue and MappingValue are always dynamic
        if _is_lookup_value(value) or _is_mapping_value(value):
            return True
        # String formulas might reference columns
        if isinstance(value, str):
            # Simple heuristic: check if any column name appears in formula
            for col_name in row_data_dict.keys():
                if col_name in value:
                    return True
    return False


# Params that should NOT be evaluated as formulas (e.g., categorical distribution)
_PASSTHROUGH_PARAMS = {"categories", "probs"}


def _resolve_params_static(
    params: dict[str, Any],
    context: dict[str, Any],
    id_to_var_name: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve parameters that don't depend on row data.

    Used for vectorized sampling when all params are static.

    Args:
        params: Distribution parameters
        context: Global context
        id_to_var_name: Mapping from node ID to var_name for canonical expansion

    Returns:
        Dictionary of resolved parameter values
    """
    resolved = {}
    for key, value in params.items():
        # Skip formula evaluation for categorical params (categories, probs)
        if key in _PASSTHROUGH_PARAMS:
            resolved[key] = value
        elif isinstance(value, (int, float)):
            resolved[key] = value
        elif isinstance(value, str):
            # Evaluate formula with empty row data
            resolved[key] = resolve_param_value(value, {}, context, id_to_var_name)
        else:
            # For lists, pass through
            resolved[key] = value
    return resolved


def _resolve_params_for_row(
    params: dict[str, Any],
    row_data: dict[str, Any],
    context: dict[str, Any],
    id_to_var_name: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve parameters for a specific row.

    Args:
        params: Distribution parameters
        row_data: Current row data
        context: Global context
        id_to_var_name: Mapping from node ID to var_name for canonical expansion

    Returns:
        Dictionary of resolved parameter values
    """
    resolved = {}
    for key, value in params.items():
        # Skip formula evaluation for categorical params (categories, probs)
        if key in _PASSTHROUGH_PARAMS:
            resolved[key] = value
        elif isinstance(value, (int, float, str)):
            resolved[key] = resolve_param_value(value, row_data, context, id_to_var_name)
        else:
            # For complex types (LookupValue, MappingValue, lists), resolve
            try:
                resolved[key] = resolve_param_value(value, row_data, context, id_to_var_name)
            except (TypeError, ValueError, KeyError):
                # If resolve fails, pass through (e.g., for lists)
                resolved[key] = value
    return resolved


def _sample_per_row_dynamic(
    node: NodeConfig,
    distribution: Any,
    row_data_dict: dict[str, np.ndarray],
    context: dict[str, Any],
    rng: np.random.Generator,
    sample_size: int,
    id_to_var_name: dict[str, str] | None = None,
) -> np.ndarray:
    """Sample with dynamic parameters that change per row.

    This is slower as it samples one value at a time, resolving params for each row.

    Args:
        node: Node configuration
        distribution: Distribution instance
        row_data_dict: Dictionary of column_name -> array
        context: Global context
        rng: Random number generator
        sample_size: Number of rows
        id_to_var_name: Mapping from node ID to var_name for canonical expansion

    Returns:
        Array of sampled values
    """
    values = np.zeros(sample_size)

    for i in range(sample_size):
        # Build row data dict for this row
        row_data = {col: vals[i] for col, vals in row_data_dict.items()}

        # Resolve params for this row
        resolved_params = _resolve_params_for_row(
            node.distribution.params, row_data, context, id_to_var_name
        )

        # Sample 1 value
        values[i] = distribution.sample(resolved_params, 1, rng)[0]

    return values


def _sample_group_scope(
    node: NodeConfig,
    distribution: Any,
    row_data_dict: dict[str, np.ndarray],
    context: dict[str, Any],
    rng: np.random.Generator,
    sample_size: int,
    id_to_var_name: dict[str, str] | None = None,
) -> np.ndarray:
    """Sample with group scope: one value per unique category, mapped to rows.

    This function:
    1. Gets the group_by column from already-generated data
    2. Finds unique categories in that column
    3. Samples ONE value for each unique category
    4. Creates a mapping from category -> sampled value
    5. Maps each row to the appropriate value based on its category

    Args:
        node: Node configuration (must have group_by set)
        distribution: Distribution instance
        row_data_dict: Dictionary of var_name -> array (columns are var_names)
        context: Global context
        rng: Random number generator
        sample_size: Number of rows
        id_to_var_name: Mapping from node ID to var_name (for group_by lookup)

    Returns:
        Array of sampled values (one per row, but same value for same category)

    Raises:
        SampleError: If group_by column not found or other generation error
    """
    if not node.group_by:
        raise SampleError(
            message=f"Group scope node '{node.id}' missing group_by",
            node_id=node.id,
        )

    # Translate group_by (node ID) to var_name for column lookup
    # node.group_by always stores a node ID, but row_data_dict uses var_names as keys
    if not id_to_var_name or node.group_by not in id_to_var_name:
        raise SampleError(
            message=f"Cannot resolve group_by node ID '{node.group_by}' to var_name",
            node_id=node.id,
            details={"group_by": node.group_by},
        )
    group_by_var_name = id_to_var_name[node.group_by]

    # Get the group_by column values
    if group_by_var_name not in row_data_dict:
        raise SampleError(
            message=f"Group-by column '{group_by_var_name}' not found for node '{node.id}'",
            node_id=node.id,
            details={
                "group_by": node.group_by,
                "group_by_var_name": group_by_var_name,
                "available_columns": list(row_data_dict.keys()),
            },
        )

    group_column = row_data_dict[group_by_var_name]

    # Find unique categories
    unique_categories = np.unique(group_column)

    # Sample one value per unique category
    category_to_value: dict[Any, Any] = {}
    for category in unique_categories:
        # Build row data for this category (use first row with this category for param resolution)
        category_indices = np.where(group_column == category)[0]
        first_idx = category_indices[0]
        row_data = {col: vals[first_idx] for col, vals in row_data_dict.items()}

        # Resolve params for this category
        resolved_params = _resolve_params_for_row(
            node.distribution.params, row_data, context, id_to_var_name
        )

        # Sample 1 value for this category
        sampled_value = distribution.sample(resolved_params, 1, rng)[0]
        category_to_value[category] = sampled_value

    # Map values back to all rows based on their category
    values = np.zeros(sample_size)
    for i in range(sample_size):
        category = group_column[i]
        values[i] = category_to_value[category]

    return values


def _apply_post_processing(
    values: np.ndarray,
    pp: PostProcessing | None,
    dtype: str | None,
    rng: np.random.Generator,
) -> np.ndarray:
    """Apply post-processing transformations to generated values.

    Applies in order:
    1. Clipping (min/max) - only for numeric types
    2. Rounding (decimals) - only for numeric types
    3. Missing values (MCAR)
    4. Type casting

    Args:
        values: Array of values to process
        pp: Post-processing configuration (optional)
        dtype: Target data type (optional)
        rng: Random number generator for missing value generation

    Returns:
        Processed array
    """
    # Make a copy to avoid modifying input
    result = values.copy()

    # Check if values are numeric (can apply numeric operations)
    is_numeric = np.issubdtype(result.dtype, np.number)

    if pp:
        # Step 1: Clipping (only for numeric types)
        if is_numeric and (pp.clip_min is not None or pp.clip_max is not None):
            result = np.clip(
                result,
                a_min=pp.clip_min if pp.clip_min is not None else -np.inf,
                a_max=pp.clip_max if pp.clip_max is not None else np.inf,
            )

        # Step 2: Rounding (only for numeric types)
        if is_numeric and pp.round_decimals is not None:
            result = np.round(result, decimals=pp.round_decimals)

        # Step 3: Missing values (MCAR - Missing Completely At Random)
        if pp.missing_rate is not None and pp.missing_rate > 0:
            # Generate random mask
            missing_mask = rng.uniform(0, 1, size=len(result)) < pp.missing_rate
            if is_numeric:
                result = result.astype(float)  # Ensure float to support NaN
                result[missing_mask] = np.nan
            else:
                # For non-numeric types (strings, categories), use None
                result = result.astype(object)
                result[missing_mask] = None

    # Step 4: Type casting
    if dtype:
        result = _cast_to_dtype(result, dtype)

    return result


def _cast_to_dtype(values: np.ndarray, dtype: str) -> np.ndarray:
    """Cast array to specified dtype.

    Args:
        values: Array to cast
        dtype: Target dtype string ("int", "float", "bool", "category", "string")

    Returns:
        Cast array
    """
    # Check if array is numeric (safe to use np.isnan)
    is_numeric = np.issubdtype(values.dtype, np.number)

    if dtype == "int":
        # Handle NaN values before casting to int
        if is_numeric and np.any(np.isnan(values)):
            # Keep as float to preserve NaN
            return values
        elif not is_numeric:
            # Non-numeric, keep as-is
            return values
        return values.astype(np.int64)

    elif dtype == "float":
        if is_numeric:
            return values.astype(np.float64)
        # Non-numeric cannot be cast to float, return as-is
        return values

    elif dtype == "bool":
        if is_numeric:
            # Convert to boolean (non-zero = True)
            return values.astype(bool)
        # For non-numeric, return as-is
        return values

    elif dtype == "category":
        # Keep as object/string for categorical
        return values.astype(object)

    elif dtype == "string":
        return values.astype(str)

    else:
        # Unknown dtype, return as-is
        return values


def _compute_column_stats(df: pd.DataFrame, dag: DAGDefinition) -> list[ColumnStats]:
    """Compute statistics for each column in the DataFrame.

    Args:
        df: DataFrame with generated data (columns are var_names)
        dag: DAG definition to map var_names back to node IDs

    Returns:
        List of ColumnStats objects with both node_id and var_name
    """
    # Build mapping from var_name to node_id
    var_name_to_node = {node.effective_var_name: node.id for node in dag.nodes}

    stats_list = []

    for col in df.columns:
        series = df[col]

        # Map column name (var_name) back to node ID
        node_id = var_name_to_node.get(col, col)  # Fallback to col if not found

        # Detect dtype
        if pd.api.types.is_numeric_dtype(series):
            dtype = "float" if pd.api.types.is_float_dtype(series) else "int"
        elif pd.api.types.is_bool_dtype(series):
            dtype = "bool"
        elif pd.api.types.is_object_dtype(series):
            dtype = "category"
        else:
            dtype = "string"

        # Null stats
        null_count = int(series.isna().sum())
        null_rate = null_count / len(series) if len(series) > 0 else 0

        # Initialize stats
        mean = std = min_val = max_val = median = None
        categories = category_rates = None

        # Numeric stats
        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            try:
                mean = float(series.mean()) if not series.isna().all() else None
                std = float(series.std()) if not series.isna().all() else None
                min_val = float(series.min()) if not series.isna().all() else None
                max_val = float(series.max()) if not series.isna().all() else None
                median = float(series.median()) if not series.isna().all() else None
            except Exception:
                pass  # Skip if computation fails

        # Categorical stats
        elif pd.api.types.is_object_dtype(series) or pd.api.types.is_bool_dtype(series):
            try:
                value_counts = series.value_counts()
                categories = {str(k): int(v) for k, v in value_counts.items()}
                total = series.notna().sum()
                if total > 0:
                    category_rates = {str(k): float(v) / total for k, v in value_counts.items()}
            except Exception:
                pass  # Skip if computation fails

        stats_list.append(
            ColumnStats(
                node_id=node_id,
                var_name=col,
                dtype=dtype,
                mean=mean,
                std=std,
                min=min_val,
                max=max_val,
                median=median,
                null_count=null_count,
                null_rate=null_rate,
                categories=categories,
                category_rates=category_rates,
            )
        )

    return stats_list
