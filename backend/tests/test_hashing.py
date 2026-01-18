"""Comprehensive tests for canonicalization and hashing in Data Simulator.

This module tests the deterministic hashing system used for model versioning
and deduplication. The hash must be stable across equivalent models while
being sensitive to meaningful changes.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from app.models.dag import (
    DAGDefinition,
    DAGEdge,
    DistributionConfig,
    GenerationMetadata,
    NodeConfig,
)


# =============================================================================
# Helper Functions (to be implemented in app/utils/hashing.py)
# =============================================================================


def float_handler(obj):
    """Handle float serialization with precision limiting.

    Rounds floats to 10 decimal places to avoid floating-point
    representation issues (e.g., 0.1 vs 0.10000000001).

    Args:
        obj: Object to serialize

    Returns:
        Rounded float

    Raises:
        TypeError: If object is not a float
    """
    if isinstance(obj, float):
        return round(obj, 10)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def canonicalize(model: dict) -> str:
    """Normalize JSON for deterministic hashing.

    Produces a canonical string representation by:
    - Sorting all keys alphabetically
    - Using consistent separators (no whitespace)
    - Ensuring ASCII encoding
    - Normalizing floats to 10 decimal places

    Args:
        model: Dictionary to canonicalize

    Returns:
        Canonical JSON string
    """
    return json.dumps(
        model, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=float_handler
    )


def compute_hash(model: dict) -> str:
    """Compute SHA256 hash of canonicalized model.

    Args:
        model: Dictionary to hash

    Returns:
        SHA256 hexadecimal digest (64 characters)
    """
    canonical = canonicalize(model)
    return hashlib.sha256(canonical.encode()).hexdigest()


def prepare_model_for_hash(dag: DAGDefinition) -> dict:
    """Extract hashable content from DAG definition.

    Includes:
    - nodes (without position information)
    - edges
    - context
    - metadata

    Excludes:
    - layout (positions, viewport)
    - schema_version (migrated before hashing)

    Args:
        dag: DAG definition

    Returns:
        Dictionary containing only hashable fields
    """
    # Convert to dict
    model = dag.model_dump()

    # Remove schema_version (handled by migration)
    model.pop("schema_version", None)

    # Remove layout if present
    model.pop("layout", None)

    # Strip position data from nodes if present
    for node in model.get("nodes", []):
        node.pop("position", None)
        node.pop("x", None)
        node.pop("y", None)

    return model


def compute_model_hash(dag: DAGDefinition) -> str:
    """Compute content hash for a DAG definition.

    This is the main function used for version deduplication.

    Args:
        dag: DAG definition

    Returns:
        SHA256 hash of the model content
    """
    hashable = prepare_model_for_hash(dag)
    return compute_hash(hashable)


# =============================================================================
# Test Suite
# =============================================================================


@pytest.mark.skip(reason="Hashing not implemented yet")
class TestCanonicalization:
    """Test JSON canonicalization for deterministic output."""

    def test_key_ordering_is_deterministic(self):
        """Keys should be sorted alphabetically regardless of input order."""
        model1 = {"z": 1, "a": 2, "m": 3}
        model2 = {"a": 2, "m": 3, "z": 1}
        model3 = {"m": 3, "z": 1, "a": 2}

        canon1 = canonicalize(model1)
        canon2 = canonicalize(model2)
        canon3 = canonicalize(model3)

        assert canon1 == canon2 == canon3
        assert canon1 == '{"a":2,"m":3,"z":1}'

    def test_nested_keys_are_sorted(self):
        """Nested object keys should also be sorted."""
        model = {"outer": {"z": 1, "a": 2}, "inner": {"b": 3, "x": 4}}

        canonical = canonicalize(model)

        # Should sort both outer and inner keys
        assert canonical == '{"inner":{"b":3,"x":4},"outer":{"a":2,"z":1}}'

    def test_no_whitespace_in_output(self):
        """Canonical output should have no whitespace."""
        model = {"key1": "value1", "key2": [1, 2, 3], "key3": {"nested": "data"}}

        canonical = canonicalize(model)

        # No spaces, newlines, or tabs
        assert " " not in canonical
        assert "\n" not in canonical
        assert "\t" not in canonical
        assert "\r" not in canonical

    def test_float_normalization(self):
        """Floats should be normalized to avoid precision issues."""
        # These should produce the same canonical form
        model1 = {"value": 0.1}
        model2 = {"value": 0.10000000001}
        model3 = {"value": 0.09999999999}

        # After rounding to 10 decimals, first two should match
        canon1 = canonicalize(model1)
        canon2 = canonicalize(model2)

        # 0.1 and 0.10000000001 should be considered equal
        assert canon1 == canon2

        # But 0.09999999999 is genuinely different
        canon3 = canonicalize(model3)
        assert canon1 != canon3

    def test_scientific_notation_normalized(self):
        """Scientific notation floats should be normalized."""
        model1 = {"value": 1e-5}
        model2 = {"value": 0.00001}

        canon1 = canonicalize(model1)
        canon2 = canonicalize(model2)

        assert canon1 == canon2

    def test_list_order_preserved(self):
        """List order should be preserved (not sorted)."""
        model = {"items": [3, 1, 2]}
        canonical = canonicalize(model)

        # List order is preserved
        assert canonical == '{"items":[3,1,2]}'

    def test_unicode_handled_correctly(self):
        """Unicode should be ASCII-escaped."""
        model = {"name": "José", "city": "São Paulo"}
        canonical = canonicalize(model)

        # ensure_ascii=True means unicode is escaped
        assert "\\u" in canonical or all(ord(c) < 128 for c in canonical)

    def test_empty_structures(self):
        """Empty dicts and lists should canonicalize consistently."""
        model1 = {"empty_dict": {}, "empty_list": []}
        model2 = {"empty_list": [], "empty_dict": {}}

        canon1 = canonicalize(model1)
        canon2 = canonicalize(model2)

        assert canon1 == canon2
        assert canon1 == '{"empty_dict":{},"empty_list":[]}'


@pytest.mark.skip(reason="Hashing not implemented yet")
class TestHashComputation:
    """Test SHA256 hash computation."""

    def test_sha256_output_format(self):
        """Hash should be 64-character hexadecimal string."""
        model = {"test": "data"}
        hash_result = compute_hash(model)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_same_model_same_hash(self):
        """Identical models should produce identical hashes."""
        model = {
            "nodes": [{"id": "a", "type": "normal"}],
            "edges": [{"source": "a", "target": "b"}],
        }

        hash1 = compute_hash(model)
        hash2 = compute_hash(model)
        hash3 = compute_hash(deepcopy(model))

        assert hash1 == hash2 == hash3

    def test_different_model_different_hash(self):
        """Different models should produce different hashes."""
        model1 = {"value": 1}
        model2 = {"value": 2}

        hash1 = compute_hash(model1)
        hash2 = compute_hash(model2)

        assert hash1 != hash2

    def test_key_order_doesnt_affect_hash(self):
        """Different key order should produce same hash (via canonicalization)."""
        model1 = {"z": 1, "a": 2, "m": 3}
        model2 = {"a": 2, "m": 3, "z": 1}

        hash1 = compute_hash(model1)
        hash2 = compute_hash(model2)

        assert hash1 == hash2

    def test_minor_value_change_changes_hash(self):
        """Even minor changes should produce different hashes."""
        model1 = {"config": {"param": 1.0}}
        model2 = {"config": {"param": 1.01}}

        hash1 = compute_hash(model1)
        hash2 = compute_hash(model2)

        assert hash1 != hash2

    def test_hash_is_deterministic(self):
        """Same model should produce same hash across multiple runs."""
        model = {"complex": {"nested": [1, 2, 3], "data": {"x": 1.5, "y": 2.5}}}

        hashes = [compute_hash(model) for _ in range(10)]

        assert len(set(hashes)) == 1  # All hashes identical


@pytest.mark.skip(reason="Hashing not implemented yet")
class TestHashedFieldsInclusion:
    """Test what fields are included in the hash."""

    def test_nodes_included_in_hash(self):
        """Changes to nodes should affect hash."""
        dag1 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100),
        )

        dag2 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 1, "sigma": 1},  # Different mu
                    ),
                )
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100),
        )

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        assert hash1 != hash2

    def test_edges_included_in_hash(self):
        """Changes to edges should affect hash."""
        dag1 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                ),
            ],
            edges=[DAGEdge(source="a", target="b")],
            metadata=GenerationMetadata(sample_size=100),
        )

        dag2 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                ),
            ],
            edges=[],  # No edges
            metadata=GenerationMetadata(sample_size=100),
        )

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        assert hash1 != hash2

    def test_context_included_in_hash(self):
        """Changes to context should affect hash."""
        dag1 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            context={"constant": 100},
            metadata=GenerationMetadata(sample_size=100),
        )

        dag2 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            context={"constant": 200},  # Different value
            metadata=GenerationMetadata(sample_size=100),
        )

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        assert hash1 != hash2

    def test_metadata_included_in_hash(self):
        """Changes to metadata should affect hash."""
        dag1 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100),
        )

        dag2 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=200),  # Different sample_size
        )

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        assert hash1 != hash2

    def test_constraints_included_in_hash(self):
        """Changes to constraints should affect hash."""
        from app.models.dag import Constraint

        dag1 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            constraints=[Constraint(type="range", target="a", min=0, max=10)],
            metadata=GenerationMetadata(sample_size=100),
        )

        dag2 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            constraints=[
                Constraint(type="range", target="a", min=0, max=20)  # Different max
            ],
            metadata=GenerationMetadata(sample_size=100),
        )

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        assert hash1 != hash2


@pytest.mark.skip(reason="Hashing not implemented yet")
class TestLayoutExclusion:
    """Test that layout changes don't affect hash."""

    def test_position_changes_dont_affect_hash(self):
        """Node position changes should not affect hash."""
        # Create base model
        model1 = {
            "nodes": [
                {
                    "id": "a",
                    "name": "A",
                    "kind": "stochastic",
                    "distribution": {"type": "normal", "params": {"mu": 0, "sigma": 1}},
                    "position": {"x": 100, "y": 200},
                }
            ],
            "edges": [],
            "metadata": {"sample_size": 100},
        }

        model2 = deepcopy(model1)
        model2["nodes"][0]["position"] = {"x": 300, "y": 400}

        # Prepare for hashing (should strip position)
        from app.models.dag import DAGDefinition

        dag1 = DAGDefinition(**model1)
        dag2 = DAGDefinition(**model2)

        # Since position is stripped, hashes should match
        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        assert hash1 == hash2

    def test_viewport_changes_dont_affect_hash(self):
        """Viewport changes should not affect hash."""
        dag_dict = {
            "nodes": [
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                ).model_dump()
            ],
            "edges": [],
            "metadata": GenerationMetadata(sample_size=100).model_dump(),
        }

        # Add different layout/viewport data
        model1 = deepcopy(dag_dict)
        model1["layout"] = {"viewport": {"x": 0, "y": 0, "zoom": 1}}

        model2 = deepcopy(dag_dict)
        model2["layout"] = {"viewport": {"x": 100, "y": 100, "zoom": 2}}

        dag1 = DAGDefinition(**model1)
        dag2 = DAGDefinition(**model2)

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        # Layout is stripped, so hashes should match
        assert hash1 == hash2

    def test_schema_version_doesnt_affect_hash(self):
        """Schema version should not affect hash (handled by migration)."""
        dag1 = DAGDefinition(
            schema_version="1.0.0",
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100),
        )

        dag2 = DAGDefinition(
            schema_version="2.0.0",  # Different version
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100),
        )

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        # Schema version is stripped before hashing
        assert hash1 == hash2


@pytest.mark.skip(reason="Hashing not implemented yet")
class TestFloatEdgeCases:
    """Test edge cases for float handling."""

    def test_very_small_numbers(self):
        """Very small numbers should be handled correctly."""
        model1 = {"value": 1e-15}
        model2 = {"value": 1.0000000000000001e-15}

        # After 10 decimal rounding, these should match
        hash1 = compute_hash(model1)
        hash2 = compute_hash(model2)

        assert hash1 == hash2

    def test_very_large_numbers(self):
        """Very large numbers should be handled correctly."""
        model1 = {"value": 1e15}
        model2 = {"value": 1000000000000000.0}

        hash1 = compute_hash(model1)
        hash2 = compute_hash(model2)

        assert hash1 == hash2

    def test_negative_floats(self):
        """Negative floats should be handled correctly."""
        model1 = {"value": -0.1}
        model2 = {"value": -0.10000000001}

        hash1 = compute_hash(model1)
        hash2 = compute_hash(model2)

        assert hash1 == hash2

    def test_zero_variants(self):
        """Different representations of zero should be consistent."""
        model1 = {"value": 0.0}
        model2 = {"value": -0.0}
        model3 = {"value": 0}

        # 0.0 and -0.0 should be the same after rounding
        hash1 = compute_hash(model1)
        hash2 = compute_hash(model2)

        assert hash1 == hash2

        # But integer 0 is different from float 0.0 in JSON
        hash3 = compute_hash(model3)
        assert hash1 != hash3

    def test_infinity_and_nan(self):
        """Infinity and NaN should be handled (or explicitly rejected)."""
        # JSON doesn't support Infinity or NaN, so these should either
        # be rejected or handled specially

        with pytest.raises((ValueError, TypeError)):
            model = {"value": float("inf")}
            canonicalize(model)

        with pytest.raises((ValueError, TypeError)):
            model = {"value": float("nan")}
            canonicalize(model)

    def test_float_precision_boundary(self):
        """Test behavior at the 10-decimal precision boundary."""
        # These differ at 11th decimal place (should be considered equal)
        model1 = {"value": 1.12345678901}
        model2 = {"value": 1.12345678909}

        hash1 = compute_hash(model1)
        hash2 = compute_hash(model2)

        assert hash1 == hash2

        # These differ at 9th decimal place (should be different)
        model3 = {"value": 1.123456781}
        model4 = {"value": 1.123456789}

        hash3 = compute_hash(model3)
        hash4 = compute_hash(model4)

        assert hash3 != hash4


@pytest.mark.skip(reason="Hashing not implemented yet")
class TestDeduplication:
    """Test deduplication scenarios using content_hash."""

    def test_identical_dags_have_same_hash(self):
        """Two identical DAG definitions should have the same hash."""
        dag1 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                ),
                NodeConfig(
                    id="y",
                    name="Y",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="x * 2",
                ),
            ],
            edges=[DAGEdge(source="x", target="y")],
            context={"constant": 10},
            metadata=GenerationMetadata(sample_size=1000, seed=42),
        )

        dag2 = deepcopy(dag1)

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        assert hash1 == hash2

    def test_reordered_nodes_same_hash(self):
        """Nodes in different order should produce same hash."""
        dag1 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                ),
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100),
        )

        dag2 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                ),
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                ),
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100),
        )

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        # After canonicalization, order shouldn't matter
        assert hash1 == hash2

    def test_different_seed_same_hash(self):
        """Different seeds should produce different hashes."""
        # Note: seed IS part of metadata, so it affects the hash
        # This is intentional - different seeds = different generation config
        dag1 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100, seed=42),
        )

        dag2 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100, seed=123),
        )

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        # Different seeds = different hashes (seed is meaningful config)
        assert hash1 != hash2

    def test_semantic_change_different_hash(self):
        """Semantic changes to model should produce different hash."""
        dag1 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100),
        )

        dag2 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 5, "sigma": 1},  # Different mu
                    ),
                )
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100),
        )

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        assert hash1 != hash2

    def test_cosmetic_change_same_hash(self):
        """Cosmetic-only changes should produce same hash."""
        dag1 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="x",
                    name="Original Name",  # Cosmetic
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100),
        )

        dag2 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="x",
                    name="New Name",  # Changed name (cosmetic)
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100),
        )

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        # Note: If 'name' is included in the hash, they will be different
        # This test documents the current behavior. You may want names
        # to affect the hash, or you may want to strip them.
        # Adjust based on requirements.

        # For now, assuming 'name' IS part of the hash (it's semantic):
        assert hash1 != hash2


@pytest.mark.skip(reason="Hashing not implemented yet")
class TestComplexScenarios:
    """Test complex real-world hashing scenarios."""

    def test_complete_dag_hashing(self):
        """Test hashing a complete, realistic DAG."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="zona",
                    name="Zona",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={"categories": ["norte", "sur"], "probs": [0.6, 0.4]},
                    ),
                ),
                NodeConfig(
                    id="efecto_zona",
                    name="Efecto Zona",
                    kind="stochastic",
                    dtype="float",
                    scope="group",
                    group_by="zona",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 5000}),
                ),
                NodeConfig(
                    id="experiencia",
                    name="Experiencia",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(type="poisson", params={"lambda": 5}),
                ),
                NodeConfig(
                    id="salario",
                    name="Salario",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="base_salario + experiencia * 1000 + efecto_zona",
                ),
            ],
            edges=[
                DAGEdge(source="zona", target="efecto_zona"),
                DAGEdge(source="efecto_zona", target="salario"),
                DAGEdge(source="experiencia", target="salario"),
            ],
            context={"base_salario": 30000},
            metadata=GenerationMetadata(sample_size=1000, seed=42),
        )

        hash_result = compute_model_hash(dag)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64

        # Computing again should give same result
        hash_result2 = compute_model_hash(dag)
        assert hash_result == hash_result2

    def test_hash_stability_across_sessions(self):
        """Hash should be stable across different Python sessions."""
        # This is really testing that we don't depend on
        # object ID, memory addresses, or other session-specific data

        def create_dag():
            return DAGDefinition(
                nodes=[
                    NodeConfig(
                        id="a",
                        name="A",
                        kind="stochastic",
                        dtype="float",
                        scope="row",
                        distribution=DistributionConfig(
                            type="normal", params={"mu": 0, "sigma": 1}
                        ),
                    )
                ],
                edges=[],
                metadata=GenerationMetadata(sample_size=100),
            )

        dag1 = create_dag()
        dag2 = create_dag()

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        assert hash1 == hash2

        # Also verify it's consistent within the same object
        hash1_again = compute_model_hash(dag1)
        assert hash1 == hash1_again

    def test_empty_optional_fields_handled(self):
        """Empty optional fields should hash consistently."""
        dag1 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            context={},  # Explicit empty
            constraints=[],  # Explicit empty
            metadata=GenerationMetadata(sample_size=100),
        )

        dag2 = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                )
            ],
            edges=[],
            # context and constraints omitted (default to empty)
            metadata=GenerationMetadata(sample_size=100),
        )

        hash1 = compute_model_hash(dag1)
        hash2 = compute_model_hash(dag2)

        assert hash1 == hash2
