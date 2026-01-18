"""Golden hash determinism tests for Data Simulator.

This module tests the core determinism invariant:
    same DAG (canonicalized) + same seed + same sample_size => byte-identical output

These tests use ACTUAL hash values (SHA256) that serve as regression tests.
If any test fails, it means determinism has been broken and the change is backward-incompatible.

How to regenerate golden hashes:
1. Run: pytest tests/test_determinism_golden.py -v
2. Look at the assertion errors showing expected vs actual hashes
3. If the change is intentional, update the GOLDEN_HASHES dictionary with the new values
4. Re-run tests to verify they pass
"""

from __future__ import annotations

import hashlib
import io
import json
import random

import pandas as pd
import pytest

from app.models.dag import (
    DAGDefinition,
    DAGEdge,
    DistributionConfig,
    GenerationMetadata,
    LookupValue,
    MappingValue,
    NodeConfig,
    PostProcessing,
)
from app.services.sampler import _generate_data, generate_data_with_df


def compute_csv_hash(df: pd.DataFrame) -> str:
    """Compute SHA256 hash of DataFrame serialized to CSV.

    This ensures byte-identical output by using deterministic CSV formatting:
    - No index column
    - UTF-8 encoding
    - Unix line endings
    - Deterministic column order (sorted by name)

    Args:
        df: DataFrame to hash

    Returns:
        Hexadecimal SHA256 hash string
    """
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


def compute_json_hash(data: list[dict]) -> str:
    """Compute SHA256 hash of data serialized to JSON.

    Args:
        data: List of dictionaries to hash

    Returns:
        Hexadecimal SHA256 hash string
    """
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


# =============================================================================
# Golden Hash Fixtures
# =============================================================================
# NOTE: These hashes are PLACEHOLDER values. To regenerate:
# 1. Run the tests and capture the actual hashes from assertion failures
# 2. Update these values with the actual hashes
# 3. Commit the updated values as the new golden standard
# =============================================================================

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
        "csv_hash": "79c131a0d4d6f2e3ba5c4575575e917ea05c272199aec60fd4511e2e77230ff9",
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
        "csv_hash": "cf205ef445f641ad2d2b75728677a57c7fbf0d66a8976bed95410f65eaf65061",
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
        "csv_hash": "7ce2ec7584ceffd633ce71c355895a17c97ee7b310972e430d27aa1aab1977b0",
    },
    "comprehensive_features": {
        "description": "Comprehensive DAG with all features: categorical root, lookup params, formulas, global scope, group scope, post-processing",
        "dag_config": {
            "nodes": [
                # Categorical root node
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
                # Global scope node
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
                # Group scope node with lookup parameters
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
                # Row-level stochastic with mapping parameter
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
                # Deterministic formula node
                {
                    "id": "base_salary",
                    "name": "Base Salary",
                    "kind": "deterministic",
                    "dtype": "float",
                    "scope": "row",
                    "formula": "regional_base_salary + (experience_years * SALARY_INCREMENT)",
                },
                # Another deterministic with global dependency
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
                # Stochastic with post-processing (missing values)
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
        "csv_hash": "270c52607f965ddc7822af1514a418ccb65a157b0f0cf28dfc8dfdce33acd38e",
    },
}


def make_dag_from_config(config: dict, seed: int, rows: int) -> DAGDefinition:
    """Create a DAGDefinition from a config dictionary.

    Args:
        config: Dictionary containing nodes, edges, and context
        seed: Random seed
        rows: Number of rows to generate

    Returns:
        DAGDefinition instance
    """
    return DAGDefinition(
        nodes=[NodeConfig(**node) for node in config["nodes"]],
        edges=[DAGEdge(**edge) for edge in config["edges"]],
        context=config["context"],
        metadata=GenerationMetadata(sample_size=rows, seed=seed),
    )


# =============================================================================
# Test Classes
# =============================================================================


class TestGoldenHashes:
    """Test that specific DAG configurations produce expected hash values."""

    def test_simple_normal_golden_hash(self):
        """Test simple normal distribution produces expected hash."""
        fixture = GOLDEN_HASHES["simple_normal"]
        dag = make_dag_from_config(fixture["dag_config"], fixture["seed"], fixture["rows"])

        df, *_ = _generate_data(dag, fixture["rows"], fixture["seed"])
        actual_hash = compute_csv_hash(df)

        # If this fails, it means determinism has been broken
        assert actual_hash == fixture["csv_hash"], (
            f"Hash mismatch for '{fixture['description']}'!\n"
            f"Expected: {fixture['csv_hash']}\n"
            f"Actual:   {actual_hash}\n"
            f"This indicates a backward-incompatible change in generation logic."
        )

    def test_simple_categorical_golden_hash(self):
        """Test simple categorical distribution produces expected hash."""
        fixture = GOLDEN_HASHES["simple_categorical"]
        dag = make_dag_from_config(fixture["dag_config"], fixture["seed"], fixture["rows"])

        df, *_ = _generate_data(dag, fixture["rows"], fixture["seed"])
        actual_hash = compute_csv_hash(df)

        assert actual_hash == fixture["csv_hash"], (
            f"Hash mismatch for '{fixture['description']}'!\n"
            f"Expected: {fixture['csv_hash']}\n"
            f"Actual:   {actual_hash}\n"
            f"This indicates a backward-incompatible change in generation logic."
        )

    def test_complex_with_lookups_golden_hash(self):
        """Test complex DAG with lookups produces expected hash."""
        fixture = GOLDEN_HASHES["complex_with_lookups"]
        dag = make_dag_from_config(fixture["dag_config"], fixture["seed"], fixture["rows"])

        df, *_ = _generate_data(dag, fixture["rows"], fixture["seed"])
        actual_hash = compute_csv_hash(df)

        assert actual_hash == fixture["csv_hash"], (
            f"Hash mismatch for '{fixture['description']}'!\n"
            f"Expected: {fixture['csv_hash']}\n"
            f"Actual:   {actual_hash}\n"
            f"This indicates a backward-incompatible change in generation logic."
        )

    def test_comprehensive_features_golden_hash(self):
        """Test comprehensive DAG with all features produces expected hash."""
        fixture = GOLDEN_HASHES["comprehensive_features"]
        dag = make_dag_from_config(fixture["dag_config"], fixture["seed"], fixture["rows"])

        df, *_ = _generate_data(dag, fixture["rows"], fixture["seed"])
        actual_hash = compute_csv_hash(df)

        assert actual_hash == fixture["csv_hash"], (
            f"Hash mismatch for '{fixture['description']}'!\n"
            f"Expected: {fixture['csv_hash']}\n"
            f"Actual:   {actual_hash}\n"
            f"This indicates a backward-incompatible change in generation logic."
        )


class TestCrossRunDeterminism:
    """Test that generating the same DAG multiple times produces identical results."""

    def test_simple_dag_cross_run_determinism(self):
        """Generate twice with same seed => identical hash."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 10.0, "sigma": 2.0},
                    ),
                ),
            ],
            edges=[],
            context={},
            metadata=GenerationMetadata(sample_size=1000, seed=42),
        )

        # Generate twice
        df1, *_ = _generate_data(dag, 1000, seed=42)
        df2, *_ = _generate_data(dag, 1000, seed=42)

        # Hashes should be identical
        hash1 = compute_csv_hash(df1)
        hash2 = compute_csv_hash(df2)

        assert hash1 == hash2, (
            "Same DAG with same seed produced different outputs!\n"
            f"Run 1 hash: {hash1}\n"
            f"Run 2 hash: {hash2}"
        )

        # DataFrames should be byte-identical
        assert df1.equals(df2), "DataFrames are not identical"

    def test_complex_dag_cross_run_determinism(self):
        """Complex DAG generates identically across multiple runs."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="category",
                    name="Category",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={"categories": ["A", "B", "C"], "probs": [0.5, 0.3, 0.2]},
                    ),
                ),
                NodeConfig(
                    id="value",
                    name="Value",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={
                            "mu": {
                                "mapping": {"A": 100, "B": 200, "C": 300},
                                "key": "category",
                                "default": 150,
                            },
                            "sigma": 10,
                        },
                    ),
                ),
                NodeConfig(
                    id="doubled",
                    name="Doubled",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="value * 2",
                ),
            ],
            edges=[
                DAGEdge(source="category", target="value"),
                DAGEdge(source="value", target="doubled"),
            ],
            context={},
            metadata=GenerationMetadata(sample_size=500, seed=123),
        )

        # Generate 3 times
        hashes = []
        for i in range(3):
            df, *_ = _generate_data(dag, 500, seed=123)
            hashes.append(compute_csv_hash(df))

        # All hashes should be identical
        assert len(set(hashes)) == 1, f"Cross-run hashes differ!\nUnique hashes: {set(hashes)}"

    def test_all_scopes_cross_run_determinism(self):
        """DAG with global, group, and row scopes is deterministic."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="global_factor",
                    name="Global Factor",
                    kind="stochastic",
                    dtype="float",
                    scope="global",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0.9, "high": 1.1},
                    ),
                ),
                NodeConfig(
                    id="region",
                    name="Region",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={"categories": ["A", "B", "C"], "probs": [0.4, 0.35, 0.25]},
                    ),
                ),
                NodeConfig(
                    id="regional_base",
                    name="Regional Base",
                    kind="stochastic",
                    dtype="float",
                    scope="group",
                    group_by="region",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 1000, "sigma": 100},
                    ),
                ),
                NodeConfig(
                    id="individual_value",
                    name="Individual Value",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100, "sigma": 20},
                    ),
                ),
                NodeConfig(
                    id="final",
                    name="Final",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="(regional_base + individual_value) * global_factor",
                ),
            ],
            edges=[
                DAGEdge(source="region", target="regional_base"),
                DAGEdge(source="global_factor", target="final"),
                DAGEdge(source="regional_base", target="final"),
                DAGEdge(source="individual_value", target="final"),
            ],
            context={},
            metadata=GenerationMetadata(sample_size=300, seed=42),
        )

        # Generate twice
        df1, *_ = _generate_data(dag, 300, seed=42)
        df2, *_ = _generate_data(dag, 300, seed=42)

        hash1 = compute_csv_hash(df1)
        hash2 = compute_csv_hash(df2)

        assert hash1 == hash2, (
            f"Mixed scope DAG produced different outputs!\nHash 1: {hash1}\nHash 2: {hash2}"
        )


class TestTopoOrderInvariance:
    """Test that node order in DAG definition doesn't affect output."""

    def test_shuffled_nodes_identical_output(self):
        """Reordering nodes in DAG JSON produces identical output."""
        # Define node configs
        node_configs = [
            NodeConfig(
                id="zona",
                name="Zona",
                kind="stochastic",
                dtype="category",
                scope="row",
                distribution=DistributionConfig(
                    type="categorical",
                    params={"categories": ["norte", "sur"], "probs": [0.5, 0.5]},
                ),
            ),
            NodeConfig(
                id="base",
                name="Base",
                kind="stochastic",
                dtype="float",
                scope="row",
                distribution=DistributionConfig(
                    type="normal",
                    params={
                        "mu": {"lookup": "salarios", "key": "zona", "default": 1000},
                        "sigma": 100,
                    },
                ),
            ),
            NodeConfig(
                id="neto",
                name="Neto",
                kind="deterministic",
                dtype="float",
                scope="row",
                formula="base * 0.84",
            ),
        ]

        edges = [
            DAGEdge(source="zona", target="base"),
            DAGEdge(source="base", target="neto"),
        ]

        context = {"salarios": {"norte": 8000, "sur": 12000}}

        # Generate with different node orderings
        orderings = [
            [0, 1, 2],  # zona, base, neto
            [2, 1, 0],  # neto, base, zona
            [1, 0, 2],  # base, zona, neto
            [2, 0, 1],  # neto, zona, base
            [1, 2, 0],  # base, neto, zona
        ]

        hashes = []
        for ordering in orderings:
            nodes_ordered = [node_configs[i] for i in ordering]
            dag = DAGDefinition(
                nodes=nodes_ordered,
                edges=edges,
                context=context,
                metadata=GenerationMetadata(sample_size=100, seed=42),
            )

            df, *_ = _generate_data(dag, 100, seed=42)
            hashes.append(compute_csv_hash(df))

        # All hashes should be identical
        assert len(set(hashes)) == 1, (
            f"Node ordering affected output!\nUnique hashes: {len(set(hashes))}\nHashes: {hashes}"
        )

    def test_random_node_shuffling(self):
        """Random shuffling of nodes produces identical output."""
        # Create a larger DAG with many nodes
        nodes = [
            NodeConfig(
                id="a",
                name="A",
                kind="stochastic",
                dtype="float",
                scope="row",
                distribution=DistributionConfig(
                    type="uniform",
                    params={"low": 0, "high": 10},
                ),
            ),
            NodeConfig(
                id="b",
                name="B",
                kind="deterministic",
                dtype="float",
                scope="row",
                formula="a * 2",
            ),
            NodeConfig(
                id="c",
                name="C",
                kind="deterministic",
                dtype="float",
                scope="row",
                formula="a + 5",
            ),
            NodeConfig(
                id="d",
                name="D",
                kind="deterministic",
                dtype="float",
                scope="row",
                formula="b + c",
            ),
            NodeConfig(
                id="e",
                name="E",
                kind="deterministic",
                dtype="float",
                scope="row",
                formula="d * 0.5",
            ),
        ]

        edges = [
            DAGEdge(source="a", target="b"),
            DAGEdge(source="a", target="c"),
            DAGEdge(source="b", target="d"),
            DAGEdge(source="c", target="d"),
            DAGEdge(source="d", target="e"),
        ]

        # Generate with original order
        dag_original = DAGDefinition(
            nodes=nodes,
            edges=edges,
            context={},
            metadata=GenerationMetadata(sample_size=200, seed=999),
        )
        df_original, *_ = _generate_data(dag_original, 200, seed=999)
        hash_original = compute_csv_hash(df_original)

        # Generate with 5 random shuffles
        for i in range(5):
            shuffled_nodes = nodes.copy()
            random.seed(i)  # Deterministic shuffle for reproducibility
            random.shuffle(shuffled_nodes)

            dag_shuffled = DAGDefinition(
                nodes=shuffled_nodes,
                edges=edges,
                context={},
                metadata=GenerationMetadata(sample_size=200, seed=999),
            )
            df_shuffled, *_ = _generate_data(dag_shuffled, 200, seed=999)
            hash_shuffled = compute_csv_hash(df_shuffled)

            assert hash_shuffled == hash_original, (
                f"Shuffle {i} produced different output!\n"
                f"Original hash: {hash_original}\n"
                f"Shuffled hash: {hash_shuffled}"
            )


class TestPostProcessingDeterminism:
    """Test that post-processing operations are deterministic."""

    def test_clipping_determinism(self):
        """Clipping produces deterministic results."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100, "sigma": 50},
                    ),
                    post_processing=PostProcessing(
                        clip_min=50,
                        clip_max=150,
                    ),
                ),
            ],
            edges=[],
            context={},
            metadata=GenerationMetadata(sample_size=1000, seed=42),
        )

        df1, *_ = _generate_data(dag, 1000, seed=42)
        df2, *_ = _generate_data(dag, 1000, seed=42)

        assert compute_csv_hash(df1) == compute_csv_hash(df2)

    def test_rounding_determinism(self):
        """Rounding produces deterministic results."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="salary",
                    name="Salary",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 50000.123456, "sigma": 10000.987654},
                    ),
                    post_processing=PostProcessing(
                        round_decimals=2,
                    ),
                ),
            ],
            edges=[],
            context={},
            metadata=GenerationMetadata(sample_size=500, seed=123),
        )

        df1, *_ = _generate_data(dag, 500, seed=123)
        df2, *_ = _generate_data(dag, 500, seed=123)

        assert compute_csv_hash(df1) == compute_csv_hash(df2)

    def test_missing_values_determinism(self):
        """Missing value generation is deterministic."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="incomplete_data",
                    name="Incomplete Data",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0, "high": 100},
                    ),
                    post_processing=PostProcessing(
                        missing_rate=0.2,
                    ),
                ),
            ],
            edges=[],
            context={},
            metadata=GenerationMetadata(sample_size=1000, seed=777),
        )

        df1, *_ = _generate_data(dag, 1000, seed=777)
        df2, *_ = _generate_data(dag, 1000, seed=777)

        # Check that missing value placement is identical
        assert df1["incomplete_data"].isna().sum() == df2["incomplete_data"].isna().sum()
        assert (df1["incomplete_data"].isna() == df2["incomplete_data"].isna()).all()

        # Check full determinism
        hash1 = compute_csv_hash(df1)
        hash2 = compute_csv_hash(df2)
        assert hash1 == hash2

    def test_combined_post_processing_determinism(self):
        """Combined post-processing operations are deterministic."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="processed",
                    name="Processed",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 75.5, "sigma": 25.7},
                    ),
                    post_processing=PostProcessing(
                        clip_min=0,
                        clip_max=100,
                        round_decimals=1,
                        missing_rate=0.15,
                    ),
                ),
            ],
            edges=[],
            context={},
            metadata=GenerationMetadata(sample_size=800, seed=555),
        )

        df1, *_ = _generate_data(dag, 800, seed=555)
        df2, *_ = _generate_data(dag, 800, seed=555)

        assert compute_csv_hash(df1) == compute_csv_hash(df2)


class TestContextDeterminism:
    """Test that context (lookups, mappings) doesn't affect determinism."""

    def test_lookup_value_determinism(self):
        """LookupValue produces deterministic results."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="category",
                    name="Category",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": ["alpha", "beta", "gamma"],
                            "probs": [0.4, 0.35, 0.25],
                        },
                    ),
                ),
                NodeConfig(
                    id="value",
                    name="Value",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={
                            "mu": {"lookup": "means", "key": "category", "default": 100},
                            "sigma": 10,
                        },
                    ),
                ),
            ],
            edges=[DAGEdge(source="category", target="value")],
            context={"means": {"alpha": 50, "beta": 100, "gamma": 150}},
            metadata=GenerationMetadata(sample_size=600, seed=888),
        )

        df1, *_ = _generate_data(dag, 600, seed=888)
        df2, *_ = _generate_data(dag, 600, seed=888)

        assert compute_csv_hash(df1) == compute_csv_hash(df2)

    def test_mapping_value_determinism(self):
        """MappingValue produces deterministic results."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="type",
                    name="Type",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": ["small", "medium", "large"],
                            "probs": [0.3, 0.5, 0.2],
                        },
                    ),
                ),
                NodeConfig(
                    id="size_value",
                    name="Size Value",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={
                            "low": {
                                "mapping": {"small": 0, "medium": 10, "large": 20},
                                "key": "type",
                                "default": 5,
                            },
                            "high": {
                                "mapping": {"small": 10, "medium": 20, "large": 30},
                                "key": "type",
                                "default": 15,
                            },
                        },
                    ),
                ),
            ],
            edges=[DAGEdge(source="type", target="size_value")],
            context={},
            metadata=GenerationMetadata(sample_size=400, seed=222),
        )

        df1, *_ = _generate_data(dag, 400, seed=222)
        df2, *_ = _generate_data(dag, 400, seed=222)

        assert compute_csv_hash(df1) == compute_csv_hash(df2)


class TestEdgeCasesDeterminism:
    """Test determinism in edge cases."""

    def test_single_row_determinism(self):
        """Single row generation is deterministic."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
            ],
            edges=[],
            context={},
            metadata=GenerationMetadata(sample_size=1, seed=42),
        )

        df1, *_ = _generate_data(dag, 1, seed=42)
        df2, *_ = _generate_data(dag, 1, seed=42)

        assert compute_csv_hash(df1) == compute_csv_hash(df2)

    def test_large_dataset_determinism(self):
        """Large dataset generation is deterministic."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="data",
                    name="Data",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
            ],
            edges=[],
            context={},
            metadata=GenerationMetadata(sample_size=10000, seed=42),
        )

        df1, *_ = _generate_data(dag, 10000, seed=42)
        df2, *_ = _generate_data(dag, 10000, seed=42)

        assert compute_csv_hash(df1) == compute_csv_hash(df2)

    def test_many_nodes_determinism(self):
        """DAG with many nodes is deterministic."""
        # Create a chain of 30 nodes
        nodes = []
        edges = []

        # First node is stochastic
        nodes.append(
            NodeConfig(
                id="n0",
                name="Node 0",
                kind="stochastic",
                dtype="float",
                scope="row",
                distribution=DistributionConfig(
                    type="uniform",
                    params={"low": 0, "high": 1},
                ),
            )
        )

        # Rest are deterministic
        for i in range(1, 30):
            nodes.append(
                NodeConfig(
                    id=f"n{i}",
                    name=f"Node {i}",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula=f"node_{i - 1} + 0.1",
                )
            )
            edges.append(DAGEdge(source=f"n{i - 1}", target=f"n{i}"))

        dag = DAGDefinition(
            nodes=nodes,
            edges=edges,
            context={},
            metadata=GenerationMetadata(sample_size=100, seed=42),
        )

        df1, *_ = _generate_data(dag, 100, seed=42)
        df2, *_ = _generate_data(dag, 100, seed=42)

        assert compute_csv_hash(df1) == compute_csv_hash(df2)


class TestSeedSensitivity:
    """Test that different seeds produce different outputs (sanity check)."""

    def test_different_seeds_different_outputs(self):
        """Different seeds should produce different hashes."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
            ],
            edges=[],
            context={},
            metadata=GenerationMetadata(sample_size=1000, seed=42),
        )

        df1, *_ = _generate_data(dag, 1000, seed=42)
        df2, *_ = _generate_data(dag, 1000, seed=123)

        hash1 = compute_csv_hash(df1)
        hash2 = compute_csv_hash(df2)

        # Different seeds should produce different results
        assert hash1 != hash2, (
            "Different seeds produced identical outputs! "
            "This indicates the seed is not being used properly."
        )


# =============================================================================
# Helper Test for Regenerating Golden Hashes
# =============================================================================


@pytest.mark.skip(reason="Helper test for regenerating golden hashes - run manually")
def test_generate_golden_hashes():
    """Helper test to generate actual hash values for GOLDEN_HASHES.

    To use:
    1. Comment out the @pytest.mark.skip decorator
    2. Run: pytest tests/test_determinism_golden.py::test_generate_golden_hashes -v -s
    3. Copy the printed hashes into GOLDEN_HASHES dictionary
    4. Re-enable the skip decorator
    """
    print("\n" + "=" * 80)
    print("GOLDEN HASH REGENERATION")
    print("=" * 80)

    for fixture_name, fixture in GOLDEN_HASHES.items():
        print(f"\n{fixture_name}:")
        print(f"  Description: {fixture['description']}")

        dag = make_dag_from_config(fixture["dag_config"], fixture["seed"], fixture["rows"])
        df, *_ = _generate_data(dag, fixture["rows"], fixture["seed"])
        actual_hash = compute_csv_hash(df)

        print(f"  Seed: {fixture['seed']}")
        print(f"  Rows: {fixture['rows']}")
        print(f"  Hash: {actual_hash}")
        print(f"  Update GOLDEN_HASHES['{fixture_name}']['csv_hash'] = '{actual_hash}'")

    print("\n" + "=" * 80)
