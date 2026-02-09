"""Shared dataframe schema inference utilities."""

from __future__ import annotations

from typing import Any

import pandas as pd


def infer_schema_from_df(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Infer a normalized schema from a pandas DataFrame."""
    schema: list[dict[str, Any]] = []
    for col in df.columns:
        dtype = df[col].dtype

        if pd.api.types.is_integer_dtype(dtype):
            type_name = "int"
        elif pd.api.types.is_float_dtype(dtype):
            type_name = "float"
        elif pd.api.types.is_bool_dtype(dtype):
            type_name = "bool"
        elif isinstance(dtype, pd.CategoricalDtype):
            type_name = "category"
        elif pd.api.types.is_object_dtype(dtype):
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
