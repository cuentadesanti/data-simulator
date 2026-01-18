"""Tests for topological sort."""

from __future__ import annotations

import pytest

from app.models.dag import (
    DAGDefinition,
    DAGEdge,
    DistributionConfig,
    GenerationMetadata,
    NodeConfig,
)
from app.utils.topological_sort import topological_sort


def make_simple_node(node_id: str) -> NodeConfig:
    """Create a simple stochastic node for testing."""
    return NodeConfig(
        id=node_id,
        name=node_id.upper(),
        kind="stochastic",
        dtype="float",
        scope="row",
        distribution=DistributionConfig(
            type="normal",
            params={"mu": 0, "sigma": 1},
        ),
    )


class TestTopologicalSort:
    """Test topological sort implementation.

    Note: topological_sort returns List[str] (node IDs), not List[NodeConfig].
    """

    def test_single_node(self):
        """Test sorting a single node."""
        nodes = [make_simple_node("a")]
        edges = []

        result = topological_sort(nodes, edges)

        assert len(result) == 1
        assert result[0] == "a"

    def test_two_nodes_with_edge(self):
        """Test sorting two nodes with dependency."""
        nodes = [make_simple_node("a"), make_simple_node("b")]
        edges = [DAGEdge(source="a", target="b")]

        result = topological_sort(nodes, edges)

        assert len(result) == 2
        # a must come before b
        assert result.index("a") < result.index("b")

    def test_chain_a_b_c(self):
        """Test sorting a chain: a -> b -> c."""
        nodes = [make_simple_node("a"), make_simple_node("b"), make_simple_node("c")]
        edges = [
            DAGEdge(source="a", target="b"),
            DAGEdge(source="b", target="c"),
        ]

        result = topological_sort(nodes, edges)

        assert len(result) == 3
        # Order must be a, b, c
        assert result.index("a") < result.index("b") < result.index("c")

    def test_diamond_shape(self):
        """Test sorting diamond shape: a -> b, a -> c, b -> d, c -> d."""
        nodes = [
            make_simple_node("a"),
            make_simple_node("b"),
            make_simple_node("c"),
            make_simple_node("d"),
        ]
        edges = [
            DAGEdge(source="a", target="b"),
            DAGEdge(source="a", target="c"),
            DAGEdge(source="b", target="d"),
            DAGEdge(source="c", target="d"),
        ]

        result = topological_sort(nodes, edges)

        assert len(result) == 4

        # a must be first
        assert result.index("a") == 0
        # d must be last
        assert result.index("d") == 3
        # b and c must be between a and d
        assert result.index("a") < result.index("b") < result.index("d")
        assert result.index("a") < result.index("c") < result.index("d")

    def test_independent_nodes(self):
        """Test sorting independent nodes (no edges)."""
        nodes = [make_simple_node("a"), make_simple_node("b"), make_simple_node("c")]
        edges = []

        result = topological_sort(nodes, edges)

        assert len(result) == 3
        # All nodes should be present
        assert set(result) == {"a", "b", "c"}

    def test_multiple_roots(self):
        """Test sorting DAG with multiple root nodes."""
        nodes = [
            make_simple_node("a"),
            make_simple_node("b"),
            make_simple_node("c"),
            make_simple_node("d"),
        ]
        # Two independent chains: a -> c and b -> d
        edges = [
            DAGEdge(source="a", target="c"),
            DAGEdge(source="b", target="d"),
        ]

        result = topological_sort(nodes, edges)

        assert len(result) == 4

        # a must come before c
        assert result.index("a") < result.index("c")
        # b must come before d
        assert result.index("b") < result.index("d")

    def test_complex_dag(self):
        """Test sorting a more complex DAG."""
        #     a
        #    / \
        #   b   c
        #    \ / \
        #     d   e
        #      \ /
        #       f
        nodes = [
            make_simple_node("a"),
            make_simple_node("b"),
            make_simple_node("c"),
            make_simple_node("d"),
            make_simple_node("e"),
            make_simple_node("f"),
        ]
        edges = [
            DAGEdge(source="a", target="b"),
            DAGEdge(source="a", target="c"),
            DAGEdge(source="b", target="d"),
            DAGEdge(source="c", target="d"),
            DAGEdge(source="c", target="e"),
            DAGEdge(source="d", target="f"),
            DAGEdge(source="e", target="f"),
        ]

        result = topological_sort(nodes, edges)

        assert len(result) == 6

        # Verify all dependencies are respected
        assert result.index("a") < result.index("b")
        assert result.index("a") < result.index("c")
        assert result.index("b") < result.index("d")
        assert result.index("c") < result.index("d")
        assert result.index("c") < result.index("e")
        assert result.index("d") < result.index("f")
        assert result.index("e") < result.index("f")

    def test_empty_graph(self):
        """Test sorting empty graph."""
        nodes = []
        edges = []

        result = topological_sort(nodes, edges)

        assert result == []

    def test_returns_node_ids(self):
        """Test that sorting returns node IDs (strings), not NodeConfig objects."""
        nodes = [make_simple_node("a"), make_simple_node("b")]
        edges = [DAGEdge(source="a", target="b")]

        result = topological_sort(nodes, edges)

        # Should be strings, not NodeConfig objects
        assert all(isinstance(node_id, str) for node_id in result)
        assert result == ["a", "b"]


class TestStableSorting:
    """Test that topological sort is stable (deterministic)."""

    def test_same_input_same_output(self):
        """Test that same input always produces same output."""
        nodes = [
            make_simple_node("a"),
            make_simple_node("b"),
            make_simple_node("c"),
            make_simple_node("d"),
        ]
        edges = [
            DAGEdge(source="a", target="c"),
            DAGEdge(source="b", target="d"),
        ]

        result1 = topological_sort(nodes, edges)
        result2 = topological_sort(nodes, edges)

        assert result1 == result2

    def test_deterministic_across_runs(self):
        """Test that sort is deterministic across multiple runs."""
        nodes = [
            make_simple_node("x"),
            make_simple_node("y"),
            make_simple_node("z"),
        ]
        edges = []  # No edges, so any order is valid

        results = []
        for _ in range(10):
            # Create new copies of nodes each time
            result = topological_sort(nodes.copy(), edges)
            results.append(result)

        # All results should be identical
        assert all(r == results[0] for r in results)


class TestTopoInvariance:
    """Test that topological sort is invariant to input node order (P0 regression)."""

    def test_shuffled_nodes_same_output(self):
        """Test that shuffling input nodes produces identical topological order."""
        import random

        # Create nodes in original order
        nodes_original = [
            make_simple_node("a"),
            make_simple_node("b"),
            make_simple_node("c"),
            make_simple_node("d"),
            make_simple_node("e"),
        ]
        edges = [
            DAGEdge(source="a", target="c"),
            DAGEdge(source="b", target="c"),
            DAGEdge(source="c", target="d"),
            DAGEdge(source="c", target="e"),
        ]

        # Get result with original order
        result_original = topological_sort(nodes_original, edges)

        # Test with multiple shuffled orders
        for seed in [42, 123, 456, 789, 1000]:
            nodes_shuffled = nodes_original.copy()
            random.seed(seed)
            random.shuffle(nodes_shuffled)

            result_shuffled = topological_sort(nodes_shuffled, edges)

            assert result_shuffled == result_original, (
                f"Topo sort not invariant to input order. "
                f"Original: {result_original}, Shuffled (seed={seed}): {result_shuffled}"
            )

    def test_reversed_nodes_same_output(self):
        """Test that reversing input nodes produces identical topological order."""
        nodes = [
            make_simple_node("x"),
            make_simple_node("y"),
            make_simple_node("z"),
        ]
        edges = [
            DAGEdge(source="x", target="y"),
            DAGEdge(source="y", target="z"),
        ]

        result_forward = topological_sort(nodes, edges)
        result_reversed = topological_sort(list(reversed(nodes)), edges)

        assert result_forward == result_reversed

    def test_independent_nodes_sorted_by_id(self):
        """Test that independent nodes (no edges) are sorted lexicographically by ID."""
        # Create nodes in non-alphabetical order
        nodes = [
            make_simple_node("zebra"),
            make_simple_node("alpha"),
            make_simple_node("mike"),
            make_simple_node("bravo"),
        ]
        edges = []

        result = topological_sort(nodes, edges)

        # Should be sorted alphabetically by node ID
        assert result == ["alpha", "bravo", "mike", "zebra"]

    def test_diamond_invariance(self):
        """Test diamond DAG produces same output regardless of node order."""

        #     a
        #    / \
        #   b   c
        #    \ /
        #     d
        def make_diamond_nodes(order):
            node_map = {
                "a": make_simple_node("a"),
                "b": make_simple_node("b"),
                "c": make_simple_node("c"),
                "d": make_simple_node("d"),
            }
            return [node_map[n] for n in order]

        edges = [
            DAGEdge(source="a", target="b"),
            DAGEdge(source="a", target="c"),
            DAGEdge(source="b", target="d"),
            DAGEdge(source="c", target="d"),
        ]

        # Test various input orders
        orders = [
            ["a", "b", "c", "d"],
            ["d", "c", "b", "a"],
            ["b", "d", "a", "c"],
            ["c", "a", "d", "b"],
        ]

        results = [topological_sort(make_diamond_nodes(order), edges) for order in orders]

        # All results should be identical
        assert all(r == results[0] for r in results)
        # And should respect the DAG constraints with deterministic tie-breaking
        assert results[0].index("a") < results[0].index("b")
        assert results[0].index("a") < results[0].index("c")
        assert results[0].index("b") < results[0].index("d")
        assert results[0].index("c") < results[0].index("d")
