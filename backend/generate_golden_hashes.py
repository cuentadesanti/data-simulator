#!/usr/bin/env python3
"""Helper script to generate golden hash values for determinism tests.

Run this script to generate actual hash values, then copy them into
tests/test_determinism_golden.py in the GOLDEN_HASHES dictionary.
"""

import hashlib
import io
import sys

import pandas as pd

from app.models.dag import (
    DAGDefinition,
    DAGEdge,
    GenerationMetadata,
    NodeConfig,
)
from app.services.sampler import _generate_data


def compute_csv_hash(df: pd.DataFrame) -> str:
    """Compute SHA256 hash of DataFrame serialized to CSV."""
    # Sort columns by name for deterministic ordering
    df_sorted = df[sorted(df.columns)]

    # Serialize to CSV with deterministic settings
    csv_buffer = io.StringIO()
    df_sorted.to_csv(
        csv_buffer,
        index=False,
        lineterminator="\n",  # Unix line endings
        encoding="utf-8",
    )
    csv_bytes = csv_buffer.getvalue().encode("utf-8")

    # Compute SHA256 hash
    return hashlib.sha256(csv_bytes).hexdigest()


def make_dag_from_config(config: dict, seed: int, rows: int) -> DAGDefinition:
    """Create a DAGDefinition from a config dictionary."""
    return DAGDefinition(
        nodes=[NodeConfig(**node) for node in config["nodes"]],
        edges=[DAGEdge(**edge) for edge in config["edges"]],
        context=config["context"],
        metadata=GenerationMetadata(sample_size=rows, seed=seed),
    )


# Golden hash fixtures (copied from test file)
GOLDEN_HASHES = {
    "simple_normal": {
        "description": "Single normal distribution node",
        "dag_config": {
            "nodes": [
                {
                    "id": "x",
                    "name": "X",
                    "kind": "stochastic",
                    "dtype": "float",
                    "scope": "row",
                    "distribution": {"type": "normal", "params": {"mu": 0.0, "sigma": 1.0}},
                    "post_processing": {"round_decimals": 6},
                }
            ],
            "edges": [],
            "context": {},
        },
        "seed": 42,
        "rows": 1000,
    },
    "simple_categorical": {
        "description": "Single categorical distribution node",
        "dag_config": {
            "nodes": [
                {
                    "id": "category",
                    "name": "Category",
                    "kind": "stochastic",
                    "dtype": "category",
                    "scope": "row",
                    "distribution": {
                        "type": "categorical",
                        "params": {
                            "categories": ["A", "B", "C"],
                            "probs": [0.5, 0.3, 0.2],
                        },
                    },
                }
            ],
            "edges": [],
            "context": {},
        },
        "seed": 12345,
        "rows": 500,
    },
    "complex_with_lookups": {
        "description": "Complex DAG with lookup parameters",
        "dag_config": {
            "nodes": [
                {
                    "id": "zona",
                    "name": "Zona",
                    "kind": "stochastic",
                    "dtype": "category",
                    "scope": "row",
                    "distribution": {
                        "type": "categorical",
                        "params": {
                            "categories": ["norte", "sur", "centro"],
                            "probs": [0.3, 0.4, 0.3],
                        },
                    },
                },
                {
                    "id": "salario_base",
                    "name": "Salario Base",
                    "kind": "stochastic",
                    "dtype": "float",
                    "scope": "row",
                    "distribution": {
                        "type": "normal",
                        "params": {
                            "mu": {"lookup": "base_por_zona", "key": "zona", "default": 10000},
                            "sigma": 2000,
                        },
                    },
                    "post_processing": {"round_decimals": 4},
                },
                {
                    "id": "salario_neto",
                    "name": "Salario Neto",
                    "kind": "deterministic",
                    "dtype": "float",
                    "scope": "row",
                    "formula": "salario_base * (1 - TAX_RATE)",
                    "post_processing": {"round_decimals": 4},
                },
            ],
            "edges": [
                {"source": "zona", "target": "salario_base"},
                {"source": "salario_base", "target": "salario_neto"},
            ],
            "context": {
                "base_por_zona": {"norte": 8000, "sur": 12000, "centro": 10000},
                "TAX_RATE": 0.16,
            },
        },
        "seed": 999,
        "rows": 2000,
    },
    "comprehensive_features": {
        "description": "Comprehensive DAG with all features",
        "dag_config": {
            "nodes": [
                {
                    "id": "region",
                    "name": "Region",
                    "kind": "stochastic",
                    "dtype": "category",
                    "scope": "row",
                    "distribution": {
                        "type": "categorical",
                        "params": {
                            "categories": ["north", "south", "east", "west"],
                            "probs": [0.25, 0.25, 0.25, 0.25],
                        },
                    },
                },
                {
                    "id": "global_inflation",
                    "name": "Global Inflation",
                    "kind": "stochastic",
                    "dtype": "float",
                    "scope": "global",
                    "distribution": {
                        "type": "uniform",
                        "params": {"low": 0.02, "high": 0.05},
                    },
                },
                {
                    "id": "regional_base_salary",
                    "name": "Regional Base Salary",
                    "kind": "stochastic",
                    "dtype": "float",
                    "scope": "group",
                    "group_by": "region",
                    "distribution": {
                        "type": "normal",
                        "params": {
                            "mu": {"lookup": "salary_by_region", "key": "region", "default": 50000},
                            "sigma": 5000,
                        },
                    },
                },
                {
                    "id": "experience_years",
                    "name": "Experience Years",
                    "kind": "stochastic",
                    "dtype": "int",
                    "scope": "row",
                    "distribution": {
                        "type": "uniform",
                        "params": {"low": 0, "high": 20},
                    },
                    "post_processing": {
                        "round_decimals": 0,
                    },
                },
                {
                    "id": "base_salary",
                    "name": "Base Salary",
                    "kind": "deterministic",
                    "dtype": "float",
                    "scope": "row",
                    "formula": "regional_base_salary + (experience_years * SALARY_INCREMENT)",
                },
                {
                    "id": "adjusted_salary",
                    "name": "Adjusted Salary",
                    "kind": "deterministic",
                    "dtype": "float",
                    "scope": "row",
                    "formula": "base_salary * (1 + global_inflation)",
                    "post_processing": {
                        "round_decimals": 2,
                        "clip_min": 30000,
                        "clip_max": 200000,
                    },
                },
                {
                    "id": "bonus",
                    "name": "Bonus",
                    "kind": "stochastic",
                    "dtype": "float",
                    "scope": "row",
                    "distribution": {
                        "type": "normal",
                        "params": {"mu": 5000, "sigma": 2000},
                    },
                    "post_processing": {
                        "clip_min": 0,
                        "round_decimals": 2,
                        "missing_rate": 0.1,
                    },
                },
            ],
            "edges": [
                {"source": "region", "target": "regional_base_salary"},
                {"source": "regional_base_salary", "target": "base_salary"},
                {"source": "experience_years", "target": "base_salary"},
                {"source": "base_salary", "target": "adjusted_salary"},
                {"source": "global_inflation", "target": "adjusted_salary"},
            ],
            "context": {
                "salary_by_region": {
                    "north": 60000,
                    "south": 50000,
                    "east": 55000,
                    "west": 58000,
                },
                "SALARY_INCREMENT": 2000,
            },
        },
        "seed": 777,
        "rows": 1500,
    },
}


def main():
    """Generate golden hashes for all fixtures."""
    print("=" * 80)
    print("GOLDEN HASH GENERATION")
    print("=" * 80)
    print("\nGenerating hashes for test fixtures...")
    print("Copy these values into tests/test_determinism_golden.py")
    print("=" * 80)

    results = {}

    for fixture_name, fixture in GOLDEN_HASHES.items():
        print(f"\n{fixture_name}:")
        print(f"  Description: {fixture['description']}")

        try:
            dag = make_dag_from_config(fixture["dag_config"], fixture["seed"], fixture["rows"])
            df, seed_used, _ = _generate_data(dag, fixture["rows"], fixture["seed"])
            actual_hash = compute_csv_hash(df)

            print(f"  Seed: {fixture['seed']}")
            print(f"  Rows: {fixture['rows']}")
            print(f"  Columns: {list(df.columns)}")
            print(f"  Hash: {actual_hash}")

            results[fixture_name] = actual_hash

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback

            traceback.print_exc()
            results[fixture_name] = f"ERROR: {e}"

    print("\n" + "=" * 80)
    print("SUMMARY - Copy these into GOLDEN_HASHES:")
    print("=" * 80)

    for fixture_name, hash_value in results.items():
        print(f'    "{fixture_name}": "{hash_value}",')

    print("\n" + "=" * 80)
    print("Done!")
    print("=" * 80)


if __name__ == "__main__":
    main()
