"""Pipeline service for managing versioned transform pipelines.

This module provides the core business logic for creating pipelines,
adding transform steps, and materializing data.
"""

from __future__ import annotations

import copy
import uuid
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.db import crud
from app.db.models import Pipeline, PipelineVersion
from app.services.hashing import fingerprint_source, hash_steps
from app.services.pipeline_source import (
    load_source,
    load_simulation_source,
)
from app.services.transform_registry import get_transform_registry


class PipelineDependencyConflictError(ValueError):
    """Raised when a step mutation would violate transform dependencies."""

    def __init__(
        self,
        message: str,
        *,
        affected_step_ids: list[str] | None = None,
        affected_columns: list[str] | None = None,
    ):
        super().__init__(message)
        self.affected_step_ids = affected_step_ids or []
        self.affected_columns = affected_columns or []


# =============================================================================
# Pipeline Creation
# =============================================================================


def create_pipeline(
    db: Session,
    project_id: str,
    name: str,
    source_type: str,
    dag_version_id: str | None = None,
    seed: int | None = None,
    sample_size: int | None = None,
    upload_source_id: str | None = None,
) -> dict[str, Any]:
    """Create a new pipeline from a simulation source.
    
    This creates a Pipeline and its first PipelineVersion with:
    - Empty steps
    - Input schema inferred from the source data
    - Output schema initially equal to input schema
    
    Args:
        db: Database session
        project_id: ID of the project this pipeline belongs to
        name: Name for the pipeline
        source_type: Type of source ("simulation" or "upload")
        dag_version_id: ID of the DAG version to use as source
        seed: Random seed for reproducibility
        sample_size: Number of rows to generate
        
    Returns:
        Dict with pipeline_id, version_id, and schema
    """
    # Load source data to infer schema
    if source_type == "upload":
        if not upload_source_id:
            raise ValueError("upload source requires source_id")

        upload_source = crud.get_uploaded_source(db, upload_source_id)
        if not upload_source:
            raise ValueError(f"Uploaded source '{upload_source_id}' not found")
        if upload_source.project_id != project_id:
            raise ValueError("Uploaded source does not belong to this project")

        input_schema = upload_source.schema_json
        source_fp = upload_source.upload_fingerprint
    else:
        if not dag_version_id or seed is None or sample_size is None:
            raise ValueError("simulation source requires dag_version_id, seed, sample_size")
        _, input_schema = load_simulation_source(db, dag_version_id, seed, sample_size)
        # Compute source fingerprint
        source_fp = fingerprint_source(dag_version_id, seed, sample_size)
    
    # Compute steps hash (empty list)
    empty_steps_hash = hash_steps([])
    
    # Create the pipeline
    pipeline = Pipeline(
        project_id=project_id,
        name=name,
        source_type=source_type,
    )
    db.add(pipeline)
    db.flush()  # Get the pipeline ID
    
    # Create the first version
    version = PipelineVersion(
        pipeline_id=pipeline.id,
        version_number=1,
        steps=[],
        input_schema=input_schema,
        output_schema=input_schema.copy(),  # Initially same as input
        lineage=[],
        source_dag_version_id=dag_version_id,
        source_upload_id=upload_source_id,
        source_seed=seed,
        source_sample_size=sample_size,
        source_fingerprint=source_fp,
        steps_hash=empty_steps_hash,
    )
    db.add(version)
    db.flush()
    
    # Set as current version
    pipeline.current_version_id = version.id
    
    db.commit()
    db.refresh(pipeline)
    db.refresh(version)
    
    return {
        "pipeline_id": pipeline.id,
        "version_id": version.id,
        "schema": version.output_schema,
    }


# =============================================================================
# Pipeline Step Operations
# =============================================================================


def add_step(
    db: Session,
    pipeline_id: str,
    version_id: str,
    step_spec: dict[str, Any],
    preview_limit: int = 200,
) -> dict[str, Any]:
    """Add a transform step to a pipeline, creating a new version.
    
    Args:
        db: Database session
        pipeline_id: ID of the pipeline
        version_id: ID of the current version to add step to
        step_spec: Step specification with:
            - type: Transform type name
            - output_column: Name for the new column
            - params: Transform parameters
            - allow_overwrite: Whether to allow overwriting existing columns
        preview_limit: Number of rows to preview
        
    Returns:
        Dict with new_version_id, schema, added_columns, preview_rows, warnings
        
    Raises:
        ValueError: If step is invalid or columns missing
    """
    # Get current version
    version = db.get(PipelineVersion, version_id)
    if not version or version.pipeline_id != pipeline_id:
        raise ValueError(f"Version {version_id} not found in pipeline {pipeline_id}")
    
    pipeline = db.get(Pipeline, pipeline_id)
    if not pipeline:
        raise ValueError(f"Pipeline {pipeline_id} not found")
    
    # Extract step spec fields
    step_type = step_spec.get("type")
    output_column = step_spec.get("output_column")
    params = step_spec.get("params", {})
    allow_overwrite = step_spec.get("allow_overwrite", False)
    
    if not step_type or not output_column:
        raise ValueError("Step must have 'type' and 'output_column'")
    
    # Get the transform
    registry = get_transform_registry()
    transform = registry.get(step_type)
    if not transform:
        raise ValueError(f"Unknown transform type: {step_type}")
    
    # Check output column doesn't exist (unless allow_overwrite)
    current_columns = {col["name"] for col in version.output_schema}
    if output_column in current_columns and not allow_overwrite:
        raise ValueError(
            f"Column '{output_column}' already exists. Set allow_overwrite=true to replace."
        )
    
    # Check required input columns exist
    required_cols = transform.required_columns(params)
    for col in required_cols:
        if col not in current_columns:
            raise ValueError(f"Required column '{col}' not found in schema")
    
    # Load source and apply existing steps to get current state
    df = _materialize_to_df(db, version)
    
    # Apply the new transform
    result_series, metadata = transform.apply(df, params)
    df[output_column] = result_series
    
    # Infer the new column's dtype
    new_dtype = transform.infer_dtype(version.output_schema, params)
    
    # Build new output schema
    if allow_overwrite and output_column in current_columns:
        # Update existing column dtype
        new_output_schema = [
            {"name": c["name"], "dtype": new_dtype if c["name"] == output_column else c["dtype"]}
            for c in version.output_schema
        ]
    else:
        # Add new column
        new_output_schema = version.output_schema + [{"name": output_column, "dtype": new_dtype}]
    
    # Create the step record
    step_id = str(uuid.uuid4())
    new_step = {
        "step_id": step_id,
        "type": step_type,
        "output_column": output_column,
        "params": params,
        "order": len(version.steps) + 1,
        "created_at": datetime.now(UTC).isoformat(),
    }
    
    # Build lineage entry
    lineage_entry = {
        "output_col": output_column,
        "inputs": required_cols,
        "step_id": step_id,
        "transform_name": step_type,
    }
    
    # Create new version
    new_steps = version.steps + [new_step]
    new_lineage = version.lineage + [lineage_entry]
    
    new_version = PipelineVersion(
        pipeline_id=pipeline_id,
        version_number=version.version_number + 1,
        steps=new_steps,
        input_schema=version.input_schema,
        output_schema=new_output_schema,
        lineage=new_lineage,
        source_dag_version_id=version.source_dag_version_id,
        source_upload_id=version.source_upload_id,
        source_seed=version.source_seed,
        source_sample_size=version.source_sample_size,
        source_fingerprint=version.source_fingerprint,
        steps_hash=hash_steps(new_steps),
    )
    db.add(new_version)
    db.flush()
    
    # Update pipeline's current version
    pipeline.current_version_id = new_version.id
    
    db.commit()
    db.refresh(new_version)
    
    # Generate preview
    preview_df = df.head(preview_limit)
    preview_rows = preview_df.to_dict(orient="records")
    
    return {
        "new_version_id": new_version.id,
        "schema": new_output_schema,
        "added_columns": [output_column],
        "preview_rows": preview_rows,
        "warnings": metadata.get("warnings_count", 0),
    }


def delete_step(
    db: Session,
    pipeline_id: str,
    version_id: str,
    step_id: str,
    *,
    cascade: bool = False,
    preview_limit: int = 200,
) -> dict[str, Any]:
    """Delete a transform step, optionally cascading to dependent downstream steps.

    Always creates a new pipeline version when successful.
    """
    version = db.get(PipelineVersion, version_id)
    if not version or version.pipeline_id != pipeline_id:
        raise ValueError(f"Version {version_id} not found in pipeline {pipeline_id}")

    pipeline = db.get(Pipeline, pipeline_id)
    if not pipeline:
        raise ValueError(f"Pipeline {pipeline_id} not found")

    steps = _normalize_step_orders(version.steps)
    step_ids = {step["step_id"] for step in steps}
    if step_id not in step_ids:
        raise ValueError(f"Step '{step_id}' not found in version '{version_id}'")

    dependency_map = _build_step_dependency_map(steps)
    downstream_ids = _collect_downstream_step_ids(step_id, dependency_map)

    if downstream_ids and not cascade:
        affected_columns = [
            step["output_column"] for step in steps if step["step_id"] in downstream_ids
        ]
        raise PipelineDependencyConflictError(
            "Deleting this step would break dependent downstream steps",
            affected_step_ids=sorted(downstream_ids),
            affected_columns=sorted(set(affected_columns)),
        )

    removed_step_ids = {step_id}
    if cascade:
        removed_step_ids.update(downstream_ids)

    remaining_steps = [
        step for step in steps if step["step_id"] not in removed_step_ids
    ]
    rebuild = _rebuild_version_from_steps(db, version, remaining_steps)
    mutation = _create_mutated_version(
        db,
        pipeline,
        version,
        rebuild,
        preview_limit=preview_limit,
    )

    removed_columns = [
        step["output_column"] for step in steps if step["step_id"] in removed_step_ids
    ]
    mutation["removed_step_ids"] = sorted(removed_step_ids)
    mutation["affected_columns"] = sorted(set(removed_columns))
    return mutation


def reorder_steps(
    db: Session,
    pipeline_id: str,
    version_id: str,
    step_ids: list[str],
    *,
    preview_limit: int = 200,
) -> dict[str, Any]:
    """Reorder pipeline transform steps and create a new version."""
    version = db.get(PipelineVersion, version_id)
    if not version or version.pipeline_id != pipeline_id:
        raise ValueError(f"Version {version_id} not found in pipeline {pipeline_id}")

    pipeline = db.get(Pipeline, pipeline_id)
    if not pipeline:
        raise ValueError(f"Pipeline {pipeline_id} not found")

    current_steps = _normalize_step_orders(version.steps)
    current_ids = [step["step_id"] for step in current_steps]

    if len(step_ids) != len(current_ids):
        raise ValueError("Step reorder list must include all current steps exactly once")
    if len(set(step_ids)) != len(step_ids):
        raise ValueError("Step reorder list contains duplicate step IDs")
    if set(step_ids) != set(current_ids):
        raise ValueError("Step reorder list must be a permutation of current step IDs")

    step_by_id = {step["step_id"]: step for step in current_steps}
    reordered_steps: list[dict[str, Any]] = []
    for index, step_id in enumerate(step_ids, start=1):
        step = copy.deepcopy(step_by_id[step_id])
        step["order"] = index
        reordered_steps.append(step)

    rebuild = _rebuild_version_from_steps(db, version, reordered_steps)
    return _create_mutated_version(
        db,
        pipeline,
        version,
        rebuild,
        preview_limit=preview_limit,
    )


# =============================================================================
# Materialization
# =============================================================================


def materialize(
    db: Session,
    pipeline_id: str,
    version_id: str,
    limit: int = 1000,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Materialize a pipeline version to data.
    
    Args:
        db: Database session
        pipeline_id: ID of the pipeline
        version_id: ID of the version to materialize
        limit: Maximum rows to return
        columns: Optional list of columns to include (None = all)
        
    Returns:
        Dict with schema and rows
    """
    version = db.get(PipelineVersion, version_id)
    if not version or version.pipeline_id != pipeline_id:
        raise ValueError(f"Version {version_id} not found in pipeline {pipeline_id}")
    
    # Materialize full dataset
    df = _materialize_to_df(db, version)
    
    # Select columns if specified
    if columns:
        available = set(df.columns)
        missing = [c for c in columns if c not in available]
        if missing:
            raise ValueError(f"Columns not found: {missing}")
        df = df[columns]
    
    # Apply limit
    df = df.head(limit)
    
    # Get schema for selected columns
    full_schema_map = {col["name"]: col for col in version.output_schema}
    schema = [full_schema_map[col] for col in df.columns if col in full_schema_map]
    
    return {
        "schema": schema,
        "rows": df.to_dict(orient="records"),
    }


def _materialize_to_df(db: Session, version: PipelineVersion) -> pd.DataFrame:
    """Internal: materialize a version to a DataFrame.
    
    Loads source data and applies all steps in order.
    """
    # Load source data
    df, _ = load_source(
        db,
        source_dag_version_id=version.source_dag_version_id,
        source_upload_id=version.source_upload_id,
        source_seed=version.source_seed,
        source_sample_size=version.source_sample_size,
    )
    
    # Apply steps in order
    registry = get_transform_registry()
    sorted_steps = sorted(version.steps, key=lambda s: s.get("order", 0))
    
    for step in sorted_steps:
        transform = registry.get(step["type"])
        if not transform:
            raise ValueError(f"Unknown transform type: {step['type']}")
        
        result_series, _ = transform.apply(df, step["params"])
        df[step["output_column"]] = result_series
    
    return df


def _normalize_step_orders(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a copy of steps sorted and renumbered with sequential order values."""
    ordered = sorted(
        [copy.deepcopy(step) for step in steps],
        key=lambda s: (int(s.get("order", 0)), s.get("created_at", ""), s.get("step_id", "")),
    )
    for index, step in enumerate(ordered, start=1):
        step["order"] = index
    return ordered


def _build_step_dependency_map(
    ordered_steps: list[dict[str, Any]]
) -> dict[str, set[str]]:
    """Build direct dependencies map using required input columns per step."""
    registry = get_transform_registry()
    produced_by_col: dict[str, str] = {}
    dependency_map: dict[str, set[str]] = {}

    for step in ordered_steps:
        step_id = step["step_id"]
        transform = registry.get(step["type"])
        params = step.get("params", {})
        required_cols = transform.required_columns(params) if transform else []
        deps = {
            produced_by_col[col]
            for col in required_cols
            if col in produced_by_col
        }
        dependency_map[step_id] = deps
        produced_by_col[step["output_column"]] = step_id
    return dependency_map


def _collect_downstream_step_ids(
    root_step_id: str, dependency_map: dict[str, set[str]]
) -> set[str]:
    """Collect all transitive downstream step IDs that depend on root_step_id."""
    reverse_map: dict[str, set[str]] = {}
    for step_id, deps in dependency_map.items():
        for dep_id in deps:
            reverse_map.setdefault(dep_id, set()).add(step_id)

    seen: set[str] = set()
    stack = list(reverse_map.get(root_step_id, set()))
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(reverse_map.get(current, set()))
    return seen


def _rebuild_version_from_steps(
    db: Session,
    source_version: PipelineVersion,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Rebuild schema/lineage/dataframe by replaying steps over the source."""
    ordered_steps = _normalize_step_orders(steps)
    registry = get_transform_registry()
    df, inferred_input_schema = load_simulation_source(
        db=db,
        dag_version_id=source_version.source_dag_version_id,
        seed=source_version.source_seed,
        sample_size=source_version.source_sample_size,
    )
    input_schema = source_version.input_schema or inferred_input_schema
    output_schema = [dict(col) for col in input_schema]
    lineage: list[dict[str, Any]] = []
    warnings_count = 0

    for step in ordered_steps:
        transform = registry.get(step["type"])
        if not transform:
            raise ValueError(f"Unknown transform type: {step['type']}")

        params = step.get("params", {})
        output_column = step["output_column"]
        required_cols = transform.required_columns(params)
        current_columns = {col["name"] for col in output_schema}
        missing = [col for col in required_cols if col not in current_columns]
        if missing:
            raise PipelineDependencyConflictError(
                (
                    f"Step '{step['step_id']}' requires missing columns: "
                    f"{', '.join(sorted(missing))}"
                ),
                affected_step_ids=[step["step_id"]],
                affected_columns=sorted(missing),
            )

        result_series, metadata = transform.apply(df, params)
        df[output_column] = result_series
        inferred_dtype = transform.infer_dtype(output_schema, params)
        if output_column in current_columns:
            output_schema = [
                {
                    "name": col["name"],
                    "dtype": inferred_dtype if col["name"] == output_column else col["dtype"],
                }
                for col in output_schema
            ]
        else:
            output_schema.append({"name": output_column, "dtype": inferred_dtype})

        lineage.append(
            {
                "output_col": output_column,
                "inputs": required_cols,
                "step_id": step["step_id"],
                "transform_name": step["type"],
            }
        )
        warnings_count += int((metadata or {}).get("warnings_count", 0))

    return {
        "steps": ordered_steps,
        "input_schema": input_schema,
        "output_schema": output_schema,
        "lineage": lineage,
        "dataframe": df,
        "warnings": warnings_count,
    }


def _create_mutated_version(
    db: Session,
    pipeline: Pipeline,
    source_version: PipelineVersion,
    rebuild: dict[str, Any],
    *,
    preview_limit: int,
) -> dict[str, Any]:
    """Persist a rebuilt step mutation as a new version and return API payload."""
    steps = rebuild["steps"]
    output_schema = rebuild["output_schema"]
    input_schema = rebuild["input_schema"]
    lineage = rebuild["lineage"]
    df = rebuild["dataframe"]
    warnings = rebuild["warnings"]

    new_version = PipelineVersion(
        pipeline_id=pipeline.id,
        version_number=source_version.version_number + 1,
        steps=steps,
        input_schema=input_schema,
        output_schema=output_schema,
        lineage=lineage,
        source_dag_version_id=source_version.source_dag_version_id,
        source_seed=source_version.source_seed,
        source_sample_size=source_version.source_sample_size,
        source_fingerprint=source_version.source_fingerprint,
        steps_hash=hash_steps(steps),
    )
    db.add(new_version)
    db.flush()
    pipeline.current_version_id = new_version.id
    db.commit()
    db.refresh(new_version)

    preview_rows = df.head(preview_limit).to_dict(orient="records")
    return {
        "new_version_id": new_version.id,
        "schema": output_schema,
        "preview_rows": preview_rows,
        "warnings": warnings,
        "steps": steps,
        "lineage": lineage,
    }


# =============================================================================
# Resimulation
# =============================================================================


def resimulate(
    db: Session,
    pipeline_id: str,
    version_id: str,
    seed: int,
    sample_size: int,
) -> dict[str, Any]:
    """Create a new pipeline with different seed/sample_size but same steps.
    
    This creates a copy of the pipeline with the same transform steps
    but using a different source configuration.
    
    Args:
        db: Database session
        pipeline_id: Source pipeline ID
        version_id: Source version ID to copy steps from
        seed: New random seed
        sample_size: New sample size
        
    Returns:
        Dict with new_pipeline_id and version_id
    """
    version = db.get(PipelineVersion, version_id)
    if not version or version.pipeline_id != pipeline_id:
        raise ValueError(f"Version {version_id} not found in pipeline {pipeline_id}")
    
    pipeline = db.get(Pipeline, pipeline_id)
    if not pipeline:
        raise ValueError(f"Pipeline {pipeline_id} not found")
    if version.source_upload_id:
        raise ValueError("Resimulate is only supported for simulation-backed pipelines")
    
    # Load new source to get schema
    df, input_schema = load_simulation_source(
        db, version.source_dag_version_id, seed, sample_size
    )
    
    # Compute new source fingerprint
    source_fp = fingerprint_source(version.source_dag_version_id, seed, sample_size)
    
    # Apply steps to compute output schema
    registry = get_transform_registry()
    output_schema = input_schema.copy()
    
    for step in sorted(version.steps, key=lambda s: s.get("order", 0)):
        transform = registry.get(step["type"])
        if transform:
            new_dtype = transform.infer_dtype(output_schema, step["params"])
            # Add or update column in schema
            col_names = {col["name"] for col in output_schema}
            if step["output_column"] not in col_names:
                output_schema.append({"name": step["output_column"], "dtype": new_dtype})
    
    # Create new pipeline
    new_pipeline = Pipeline(
        project_id=pipeline.project_id,
        name=f"{pipeline.name} (resimulated)",
        source_type=pipeline.source_type,
    )
    db.add(new_pipeline)
    db.flush()
    
    # Create version 1 with copied steps
    new_version = PipelineVersion(
        pipeline_id=new_pipeline.id,
        version_number=1,
        steps=version.steps,  # Copy steps
        input_schema=input_schema,
        output_schema=output_schema,
        lineage=version.lineage,  # Copy lineage
        source_dag_version_id=version.source_dag_version_id,
        source_upload_id=None,
        source_seed=seed,
        source_sample_size=sample_size,
        source_fingerprint=source_fp,
        steps_hash=version.steps_hash,  # Same because steps are the same
    )
    db.add(new_version)
    db.flush()
    
    # Set as current version
    new_pipeline.current_version_id = new_version.id
    
    db.commit()
    db.refresh(new_pipeline)
    db.refresh(new_version)
    
    return {
        "new_pipeline_id": new_pipeline.id,
        "version_id": new_version.id,
    }


# =============================================================================
# Pipeline Queries
# =============================================================================


def get_pipeline(db: Session, pipeline_id: str) -> dict[str, Any] | None:
    """Get pipeline details.
    
    Args:
        db: Database session
        pipeline_id: Pipeline ID
        
    Returns:
        Pipeline details or None if not found
    """
    pipeline = db.get(Pipeline, pipeline_id)
    if not pipeline:
        return None
    
    current_version = pipeline.current_version
    
    versions_summary = [
        {
            "id": v.id,
            "version_number": v.version_number,
            "steps_count": len(v.steps),
            "created_at": v.created_at.isoformat(),
        }
        for v in pipeline.versions
    ]
    
    return {
        "pipeline": {
            "id": pipeline.id,
            "project_id": pipeline.project_id,
            "name": pipeline.name,
            "source_type": pipeline.source_type,
            "created_at": pipeline.created_at.isoformat(),
        },
        "current_version": {
            "id": current_version.id,
            "version_number": current_version.version_number,
            "steps": current_version.steps,
            "input_schema": current_version.input_schema,
            "output_schema": current_version.output_schema,
            "lineage": current_version.lineage,
        } if current_version else None,
        "versions_summary": versions_summary,
    }


def list_pipelines(db: Session, project_id: str) -> list[dict[str, Any]]:
    """List all pipelines for a project.
    
    Args:
        db: Database session
        project_id: Project ID
        
    Returns:
        List of pipeline summaries
    """
    from sqlalchemy import select
    
    stmt = select(Pipeline).where(Pipeline.project_id == project_id)
    pipelines = db.execute(stmt).scalars().all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "source_type": p.source_type,
            "current_version_id": p.current_version_id,
            "versions_count": len(p.versions),
            "created_at": p.created_at.isoformat(),
        }
        for p in pipelines
    ]
