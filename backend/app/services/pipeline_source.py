"""Pipeline source loader for loading simulation data.

This module provides functions to load source data for pipelines,
primarily from simulation runs (DAG + seed + sample_size).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.db import crud
from app.models.dag import DAGDefinition
from app.services.sampler import _generate_data


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


def infer_schema_from_df(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Infer schema from a pandas DataFrame.
    
    Maps pandas dtypes to standardized type names.
    
    Args:
        df: DataFrame to infer schema from
        
    Returns:
        List of {name: str, dtype: str} for each column
    """
    schema = []
    for col in df.columns:
        dtype = df[col].dtype
        
        # Map numpy/pandas dtype to our standard type names
        if pd.api.types.is_integer_dtype(dtype):
            type_name = "int"
        elif pd.api.types.is_float_dtype(dtype):
            type_name = "float"
        elif pd.api.types.is_bool_dtype(dtype):
            type_name = "bool"
        elif pd.api.types.is_categorical_dtype(dtype):
            type_name = "category"
        elif pd.api.types.is_object_dtype(dtype):
            # Check if it's likely a string column
            sample = df[col].dropna().head(10)
            if len(sample) > 0 and all(isinstance(v, str) for v in sample):
                type_name = "string"
            else:
                type_name = "object"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            type_name = "datetime"
        else:
            type_name = str(dtype)
        
        schema.append({"name": col, "dtype": type_name})
    
    return schema


def get_column_names_from_schema(schema: list[dict[str, Any]]) -> list[str]:
    """Extract column names from a schema.
    
    Args:
        schema: List of {name, dtype} column definitions
        
    Returns:
        List of column names
    """
    return [col["name"] for col in schema]
