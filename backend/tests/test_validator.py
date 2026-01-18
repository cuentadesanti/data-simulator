"""Tests for DAG validator."""

from __future__ import annotations

import pytest

from app.core.exceptions import CycleDetectedError, ValidationError
from app.models.dag import (
    DAGDefinition,
    DAGEdge,
    DistributionConfig,
    GenerationMetadata,
    NodeConfig,
)
from app.services.validator import validate_dag


class TestCycleDetection:
    """Test DAG cycle detection."""

    def test_valid_dag_no_cycles(self):
        """Test that valid DAG with no cycles passes validation."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": "a", "sigma": 1},
                    ),
                ),
            ],
            edges=[DAGEdge(source="a", target="b")],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_simple_cycle_detected(self):
        """Test that a simple A->B->A cycle is detected."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": "b", "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": "a", "sigma": 1},
                    ),
                ),
            ],
            edges=[
                DAGEdge(source="a", target="b"),
                DAGEdge(source="b", target="a"),
            ],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any("cycle" in error.lower() for error in result.errors)

    def test_self_loop_detected(self):
        """Test that a self-loop A->A is detected."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
            ],
            edges=[DAGEdge(source="a", target="a")],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any("cycle" in error.lower() for error in result.errors)

    def test_complex_cycle_detected(self):
        """Test that a complex A->B->C->A cycle is detected."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="c",
                    name="C",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
            ],
            edges=[
                DAGEdge(source="a", target="b"),
                DAGEdge(source="b", target="c"),
                DAGEdge(source="c", target="a"),
            ],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any("cycle" in error.lower() for error in result.errors)


class TestReservedKeywords:
    """Test reserved keyword validation."""

    def test_node_id_cannot_be_reserved_function(self):
        """Test that node ID cannot be a reserved function name."""
        reserved_functions = ["abs", "min", "max", "round", "sqrt", "log", "sin", "cos"]

        for func_name in reserved_functions:
            dag = DAGDefinition(
                nodes=[
                    NodeConfig(
                        id=func_name,  # Reserved!
                        name="Test",
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
                metadata=GenerationMetadata(sample_size=100),
            )

            result = validate_dag(dag)
            assert result.valid is False
            assert any("reserved" in error.lower() for error in result.errors)

    def test_context_key_cannot_be_reserved(self):
        """Test that context keys cannot be reserved constants."""
        reserved_constants = ["PI", "E", "TRUE", "FALSE"]

        for const_name in reserved_constants:
            dag = DAGDefinition(
                nodes=[
                    NodeConfig(
                        id="a",
                        name="A",
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
                context={const_name: 123},  # Reserved!
                metadata=GenerationMetadata(sample_size=100),
            )

            result = validate_dag(dag)
            assert result.valid is False
            assert any("reserved" in error.lower() for error in result.errors)

    def test_valid_node_id_not_reserved(self):
        """Test that non-reserved node IDs pass."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="my_variable",
                    name="My Variable",
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
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is True


class TestEdgeValidation:
    """Test edge validation."""

    def test_edge_with_nonexistent_source_fails(self):
        """Test that edge with non-existent source node fails."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
            ],
            edges=[DAGEdge(source="nonexistent", target="a")],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any(
            "nonexistent" in error.lower() or "source" in error.lower() for error in result.errors
        )

    def test_edge_with_nonexistent_target_fails(self):
        """Test that edge with non-existent target node fails."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
            ],
            edges=[DAGEdge(source="a", target="nonexistent")],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any(
            "nonexistent" in error.lower() or "target" in error.lower() for error in result.errors
        )


class TestLimits:
    """Test validation limits."""

    def test_sample_size_exceeds_max_fails(self):
        """Test that sample size exceeding max fails."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
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
            metadata=GenerationMetadata(sample_size=100_000_000),  # Very large
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any("limit" in error.lower() or "max" in error.lower() for error in result.errors)


class TestTopologicalOrder:
    """Test topological order in validation result."""

    def test_valid_dag_has_topological_order(self):
        """Test that valid DAG has topological order in result."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
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
            ],
            edges=[DAGEdge(source="a", target="b")],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is True
        assert result.topological_order is not None
        assert result.topological_order == ["a", "b"]

    def test_invalid_dag_has_no_topological_order(self):
        """Test that invalid DAG has no topological order."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="abs",  # Reserved!
                    name="A",
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
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert result.topological_order is None


class TestWarnings:
    """Test validation warnings."""

    def test_warning_for_no_seed(self):
        """Test warning when no seed specified."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
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
            metadata=GenerationMetadata(sample_size=100, seed=None),
        )

        result = validate_dag(dag)
        assert result.valid is True
        assert any("seed" in warning.lower() for warning in result.warnings)

    def test_no_warning_when_seed_provided(self):
        """Test no seed warning when seed is provided."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
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
            metadata=GenerationMetadata(sample_size=100, seed=42),
        )

        result = validate_dag(dag)
        assert result.valid is True
        assert not any("seed" in warning.lower() for warning in result.warnings)


class TestGroupByValidation:
    """Test group_by ancestor validation."""

    def test_group_by_must_be_ancestor(self):
        """Test that group_by must reference an ancestor node."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={"categories": ["x", "y"], "probs": [0.5, 0.5]},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="float",
                    scope="group",
                    group_by="c",  # c is NOT an ancestor of b
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="c",
                    name="C",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={"categories": ["p", "q"], "probs": [0.5, 0.5]},
                    ),
                ),
            ],
            edges=[
                DAGEdge(source="a", target="b"),
                # No edge from c to b, so c is not an ancestor
            ],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any(
            "ancestor" in error.lower() or "group_by" in error.lower() for error in result.errors
        )

    def test_group_by_nonexistent_node_fails(self):
        """Test that group_by referencing non-existent node fails."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="group",
                    group_by="nonexistent",  # Doesn't exist
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any(
            "nonexistent" in error.lower() or "parent" in error.lower() for error in result.errors
        )

    def test_valid_group_by_ancestor(self):
        """Test that valid group_by with proper ancestor passes."""
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
                        params={"categories": ["norte", "sur"], "probs": [0.5, 0.5]},
                    ),
                ),
                NodeConfig(
                    id="efecto_zona",
                    name="Efecto Zona",
                    kind="stochastic",
                    dtype="float",
                    scope="group",
                    group_by="zona",  # zona IS an ancestor
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
            ],
            edges=[
                DAGEdge(source="zona", target="efecto_zona"),
            ],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is True

    def test_group_by_must_be_categorical(self):
        """Test that group_by must reference a categorical node."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",  # NOT categorical!
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="y",
                    name="Y",
                    kind="stochastic",
                    dtype="float",
                    scope="group",
                    group_by="x",  # x is NOT categorical
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
            ],
            edges=[
                DAGEdge(source="x", target="y"),
            ],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any("categorical" in error.lower() for error in result.errors)

    def test_group_by_must_be_row_scoped(self):
        """Test that group_by must reference a row-scoped node."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="global_cat",
                    name="Global Category",
                    kind="stochastic",
                    dtype="category",
                    scope="global",  # NOT row-scoped!
                    distribution=DistributionConfig(
                        type="categorical",
                        params={"categories": ["A", "B"], "probs": [0.5, 0.5]},
                    ),
                ),
                NodeConfig(
                    id="y",
                    name="Y",
                    kind="stochastic",
                    dtype="float",
                    scope="group",
                    group_by="global_cat",  # global_cat is NOT row-scoped
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
            ],
            edges=[
                DAGEdge(source="global_cat", target="y"),
            ],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any(
            "row-scoped" in error.lower() or "row" in error.lower() for error in result.errors
        )


class TestEdgeSemantics:
    """Test edge semantic validation - references must have corresponding edges."""

    def test_reference_without_edge_fails(self):
        """Test that referencing a node without an edge fails validation."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": "a", "sigma": 1},  # References 'a' but no edge!
                    ),
                ),
            ],
            edges=[],  # No edges!
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert len(result.missing_edges) == 1
        assert result.missing_edges[0]["source"] == "a"
        assert result.missing_edges[0]["target"] == "b"
        assert any("no edge" in error.lower() for error in result.errors)

    def test_formula_reference_without_edge_fails(self):
        """Test that referencing a node in formula without an edge fails."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="a * 2",  # References 'a' but no edge!
                ),
            ],
            edges=[],  # No edges!
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        # Formula validation catches this early with a clear error message
        # The error mentions the missing variable 'a'
        assert any("Variable 'a' not found" in error for error in result.errors)

    def test_unused_edge_flagged(self):
        """Test that edge without reference is flagged as unused."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 5, "sigma": 2},  # Does NOT reference 'a'
                    ),
                ),
            ],
            edges=[DAGEdge(source="a", target="b")],  # Edge exists but unused
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is True  # Unused edge is a warning, not error
        assert len(result.edge_statuses) == 1
        assert result.edge_statuses[0].source == "a"
        assert result.edge_statuses[0].target == "b"
        assert result.edge_statuses[0].status == "unused"
        assert result.edge_statuses[0].reason is not None

    def test_used_edge_flagged(self):
        """Test that edge with reference is flagged as used."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": "a", "sigma": 1},  # References 'a'
                    ),
                ),
            ],
            edges=[DAGEdge(source="a", target="b")],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is True
        assert len(result.edge_statuses) == 1
        assert result.edge_statuses[0].source == "a"
        assert result.edge_statuses[0].target == "b"
        assert result.edge_statuses[0].status == "used"

    def test_context_reference_no_edge_needed(self):
        """Test that context references don't require edges."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="MY_CONST * 2",  # References context, not a node
                ),
            ],
            edges=[],
            context={"MY_CONST": 10},
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is True
        assert len(result.missing_edges) == 0

    def test_multiple_references_multiple_edges(self):
        """Test that multiple references need multiple edges."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="c",
                    name="C",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="a + b",  # References both a and b
                ),
            ],
            edges=[
                DAGEdge(source="a", target="c"),
                # Missing edge from b to c!
            ],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        # Formula validation catches this early with a clear error message
        # The error mentions the missing variable 'b' (edge from 'a' exists, but not from 'b')
        assert any("Variable 'b' not found" in error for error in result.errors)


class TestFormulaSyntaxValidation:
    """Test formula syntax validation during DAG validation."""

    def test_valid_formula_passes(self):
        """Test that valid formula passes validation."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="a * 2 + 10",  # Valid formula
                ),
            ],
            edges=[DAGEdge(source="a", target="b")],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_syntax_error_in_formula_fails(self):
        """Test that syntax error in formula fails validation."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="a * 2 +",  # Syntax error: incomplete expression
                ),
            ],
            edges=[DAGEdge(source="a", target="b")],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any("syntax" in error.lower() for error in result.errors)
        assert any("b" in error for error in result.errors)  # Should mention node 'b'

    def test_invalid_function_in_formula_fails(self):
        """Test that invalid function in formula fails validation."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="invalid_function(10)",  # Invalid function
                ),
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any("a" in error for error in result.errors)

    def test_mismatched_parentheses_fails(self):
        """Test that mismatched parentheses fail validation."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="(a * 2 + 10",  # Missing closing parenthesis
                ),
            ],
            edges=[DAGEdge(source="a", target="b")],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any(
            "syntax" in error.lower() or "formula" in error.lower() for error in result.errors
        )

    def test_complex_valid_formula_passes(self):
        """Test that complex valid formula passes validation."""
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
                NodeConfig(
                    id="y",
                    name="Y",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="z",
                    name="Z",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="sqrt(abs(x)) + max(y, 0) * 2",  # Complex but valid
                ),
            ],
            edges=[
                DAGEdge(source="x", target="z"),
                DAGEdge(source="y", target="z"),
            ],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is True

    def test_formula_with_context_reference_passes(self):
        """Test that formula referencing context passes validation."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="PI * 2",  # References reserved context constant
                ),
            ],
            edges=[],
            context={},
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is True


class TestMoreLimits:
    """Test additional limit validations (MAX_EDGES, MAX_FORMULA_LENGTH)."""

    def test_max_edges_exceeded(self):
        """Test that exceeding MAX_EDGES fails validation."""
        from app.core import settings

        # Create a DAG with more edges than allowed
        nodes = [
            NodeConfig(
                id=f"n{i}",
                name=f"Node {i}",
                kind="stochastic",
                dtype="float",
                scope="row",
                distribution=DistributionConfig(
                    type="normal",
                    params={"mu": 0, "sigma": 1},
                ),
            )
            for i in range(10)
        ]

        # Create more edges than settings.max_edges allows
        # For testing, we'll create a dense graph if max_edges is reasonable
        # If max_edges is very high, skip this test
        if settings.max_edges < 10000:
            edges = []
            edge_count = 0
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    if edge_count >= settings.max_edges + 1:
                        break
                    edges.append(DAGEdge(source=f"n{i}", target=f"n{j}"))
                    edge_count += 1
                if edge_count >= settings.max_edges + 1:
                    break

            if edge_count > settings.max_edges:
                dag = DAGDefinition(
                    nodes=nodes,
                    edges=edges,
                    metadata=GenerationMetadata(sample_size=100),
                )

                result = validate_dag(dag)
                assert result.valid is False
                assert any(
                    "edge" in error.lower() or "limit" in error.lower() for error in result.errors
                )

    def test_max_formula_length_exceeded(self):
        """Test that exceeding MAX_FORMULA_LENGTH fails validation."""
        from app.core import settings

        # Create a formula longer than allowed
        long_formula = "a + " + " + ".join(["1"] * (settings.max_formula_length // 4 + 100))

        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula=long_formula,  # Very long formula
                ),
            ],
            edges=[DAGEdge(source="a", target="b")],
            metadata=GenerationMetadata(sample_size=100),
        )

        result = validate_dag(dag)
        assert result.valid is False
        assert any(
            "formula" in error.lower() or "length" in error.lower() for error in result.errors
        )
