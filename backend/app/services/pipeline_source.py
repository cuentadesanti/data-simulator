"""Pipeline source loader for loading source data.

This module provides functions to load source data for pipelines,
primarily from simulation runs (DAG + seed + sample_size).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.db import crud
from app.models.dag import DAGDefinition
from app.services.schema_inference import infer_schema_from_df
from app.services.sampler import _generate_data
from app.services.upload_source import load_upload_dataframe


def load_simulation_source(
    db: Session,
    dag_version_id: str,
    seed: int,
    sample_size: int,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Load source data by running a simulation with specified parameters.
    
    This function reproduces data from a DAG version using the exact seed
    and sample size, ensuring reproducibility.
    
    Args:
        db: Database session
        dag_version_id: ID of the DAG version to use for generation
        seed: Random seed for reproducibility
        sample_size: Number of rows to generate
        
    Returns:
        Tuple of:
            - DataFrame with generated data
            - Schema list: [{name: str, dtype: str}, ...]
            
    Raises:
        ValueError: If DAG version not found
        SampleError: If data generation fails
    """
    # Get the DAG version from the database
    dag_version = crud.get_version(db, dag_version_id)
    if not dag_version:
        raise ValueError(f"DAG version '{dag_version_id}' not found")
    
    # Parse the DAG definition
    dag_dict = dag_version.dag_definition
    
    # Override metadata with our specific seed and sample_size
    dag_dict = {**dag_dict}  # Shallow copy
    dag_dict["metadata"] = {
        **dag_dict.get("metadata", {}),
        "seed": seed,
        "sample_size": sample_size,
        "preview_rows": sample_size,  # For compatibility with generate_preview
    }
    
    dag = DAGDefinition.model_validate(dag_dict)
    
    # Generate the data using the internal _generate_data function
    # This gives us the raw DataFrame without validation overhead
    df, seed_used, warnings = _generate_data(dag, sample_size, seed)
    
    # Infer schema from DataFrame
    schema = infer_schema_from_df(df)
    
    return df, schema


def load_upload_source(
    db: Session,
    source_id: str,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    source = crud.get_uploaded_source(db, source_id)
    if not source:
        raise ValueError(f"Uploaded source '{source_id}' not found")
    df = load_upload_dataframe(source.storage_uri, source.format)
    schema = infer_schema_from_df(df)
    return df, schema


def load_source(
    db: Session,
    *,
    source_dag_version_id: str | None,
    source_upload_id: str | None,
    source_seed: int | None,
    source_sample_size: int | None,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    if source_upload_id:
        return load_upload_source(db, source_upload_id)

    if not source_dag_version_id or source_seed is None or source_sample_size is None:
        raise ValueError("Invalid simulation source metadata")

    return load_simulation_source(
        db,
        source_dag_version_id,
        source_seed,
        source_sample_size,
    )

def get_column_names_from_schema(schema: list[dict[str, Any]]) -> list[str]:
    """Extract column names from a schema.
    
    Args:
        schema: List of {name, dtype} column definitions
        
    Returns:
        List of column names
    """
    return [col["name"] for col in schema]
