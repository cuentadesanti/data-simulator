"""Pipeline service for managing versioned transform pipelines.

This module provides the core business logic for creating pipelines,
adding transform steps, and materializing data.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import Pipeline, PipelineVersion
from app.services.hashing import fingerprint_source, hash_steps
from app.services.pipeline_source import (
    infer_schema_from_df,
    load_simulation_source,
)
from app.services.transform_registry import get_transform_registry


# =============================================================================
# Pipeline Creation
# =============================================================================


def create_pipeline(
    db: Session,
    project_id: str,
    name: str,
    source_type: str,
    dag_version_id: str,
    seed: int,
    sample_size: int,
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
    df, input_schema = load_simulation_source(db, dag_version_id, seed, sample_size)
    
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
        "created_at": datetime.utcnow().isoformat(),
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
    df, _ = load_simulation_source(
        db,
        version.source_dag_version_id,
        version.source_seed,
        version.source_sample_size,
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
