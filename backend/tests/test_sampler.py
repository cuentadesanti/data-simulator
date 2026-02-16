"""Tests for the sampler service."""

from __future__ import annotations

import pytest

from app.models.dag import (
    DAGDefinition,
    DAGEdge,
    DistributionConfig,
    GenerationMetadata,
    NodeConfig,
)
from app.services.sampler import generate_data, generate_preview


def make_simple_dag(
    nodes: list[NodeConfig],
    edges: list[DAGEdge] = None,
    context: dict = None,
    sample_size: int = 100,
    seed: int = 42,
) -> DAGDefinition:
    """Helper to create a DAG definition."""
    return DAGDefinition(
        nodes=nodes,
        edges=edges or [],
        context=context or {},
        metadata=GenerationMetadata(
            sample_size=sample_size,
            seed=seed,
            preview_rows=min(sample_size, 10),
        ),
    )


class TestBasicSampling:
    """Test basic sampling functionality."""

    def test_single_normal_node(self):
        """Test sampling a single normal distribution node."""
        dag = make_simple_dag(
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
        )

        result = generate_preview(dag)

        assert result.rows == 10
        assert result.columns == ["x"]
        assert len(result.data) == 10

        # Check all values are present
        for row in result.data:
            assert "x" in row
            assert isinstance(row["x"], float)

    def test_single_categorical_node(self):
        """Test sampling a single categorical distribution node."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="cat",
                    name="Category",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": ["A", "B", "C"],
                            "probs": [0.5, 0.3, 0.2],
                        },
                    ),
                ),
            ],
        )

        result = generate_preview(dag)

        assert result.columns == ["cat"]
        for row in result.data:
            assert row["cat"] in ["A", "B", "C"]

    def test_single_uniform_node(self):
        """Test sampling a single uniform distribution node."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="u",
                    name="Uniform",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0.0, "high": 100.0},
                    ),
                ),
            ],
        )

        result = generate_preview(dag)

        for row in result.data:
            assert 0.0 <= row["u"] < 100.0

    def test_single_bernoulli_node(self):
        """Test sampling a single Bernoulli distribution node."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="b",
                    name="Binary",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="bernoulli",
                        params={"p": 0.7},
                    ),
                ),
            ],
        )

        result = generate_preview(dag)

        for row in result.data:
            assert row["b"] in [0, 1]


class TestDeterministicNodes:
    """Test deterministic (formula-based) nodes."""

    def test_simple_formula(self):
        """Test a simple formula node."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 10.0, "sigma": 0.0},  # Always 10
                    ),
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
        )

        result = generate_preview(dag)

        assert result.columns == ["x", "y"]
        for row in result.data:
            assert row["y"] == row["x"] * 2

    def test_formula_with_context(self):
        """Test formula using context variables."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="base",
                    name="Base",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 1000.0, "sigma": 0.0},  # Always 1000
                    ),
                ),
                NodeConfig(
                    id="with_tax",
                    name="With Tax",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="base * (1 + TAX_RATE)",
                ),
            ],
            edges=[DAGEdge(source="base", target="with_tax")],
            context={"TAX_RATE": 0.16},
        )

        result = generate_preview(dag)

        for row in result.data:
            expected = row["base"] * 1.16
            assert abs(row["with_tax"] - expected) < 0.01


class TestDependencies:
    """Test DAG with dependencies between nodes."""

    def test_chain_dependency(self):
        """Test chain: a -> b -> c."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 1.0, "high": 2.0},
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
                    formula="b + 1",
                ),
            ],
            edges=[
                DAGEdge(source="a", target="b"),
                DAGEdge(source="b", target="c"),
            ],
        )

        result = generate_preview(dag)

        for row in result.data:
            assert row["b"] == row["a"] * 2
            assert row["c"] == row["b"] + 1

    def test_diamond_dependency(self):
        """Test diamond: a -> b, a -> c, b -> d, c -> d."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 10.0, "high": 20.0},
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
                    formula="a / 2",
                ),
                NodeConfig(
                    id="d",
                    name="D",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="b + c",
                ),
            ],
            edges=[
                DAGEdge(source="a", target="b"),
                DAGEdge(source="a", target="c"),
                DAGEdge(source="b", target="d"),
                DAGEdge(source="c", target="d"),
            ],
        )

        result = generate_preview(dag)

        for row in result.data:
            assert row["b"] == row["a"] * 2
            assert row["c"] == row["a"] / 2
            assert abs(row["d"] - (row["b"] + row["c"])) < 0.0001


class TestLookupParameters:
    """Test distribution parameters using lookups."""

    def test_lookup_for_mu(self):
        """Test using lookup for distribution mean parameter."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="zona",
                    name="Zona",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": ["norte", "sur"],
                            "probs": [0.5, 0.5],
                        },
                    ),
                ),
                NodeConfig(
                    id="salario",
                    name="Salario",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={
                            "mu": {"lookup": "base_por_zona", "key": "zona", "default": 10000},
                            "sigma": 100,  # Small sigma to keep values close to mu
                        },
                    ),
                ),
            ],
            edges=[DAGEdge(source="zona", target="salario")],
            context={
                "base_por_zona": {"norte": 8000, "sur": 12000},
            },
            sample_size=100,
        )

        result = generate_preview(dag)

        # Verify salaries are roughly centered around zone means
        for row in result.data:
            if row["zona"] == "norte":
                # Should be around 8000 +/- some variance
                assert 7500 < row["salario"] < 8500
            else:  # sur
                assert 11500 < row["salario"] < 12500

    def test_mapping_for_parameter(self):
        """Test using inline mapping for distribution parameter."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="tipo",
                    name="Tipo",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": ["A", "B"],
                            "probs": [0.5, 0.5],
                        },
                    ),
                ),
                NodeConfig(
                    id="valor",
                    name="Valor",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={
                            "mu": {"mapping": {"A": 100, "B": 200}, "key": "tipo", "default": 150},
                            "sigma": 1,  # Very small for predictable values
                        },
                    ),
                ),
            ],
            edges=[DAGEdge(source="tipo", target="valor")],
            sample_size=100,
        )

        result = generate_preview(dag)

        for row in result.data:
            if row["tipo"] == "A":
                assert 95 < row["valor"] < 105
            else:  # B
                assert 195 < row["valor"] < 205


class TestComplexDAG:
    """Test complex real-world DAG scenarios."""

    def test_salary_model(self):
        """Test a realistic salary generation model."""
        dag = make_simple_dag(
            nodes=[
                # Zone (categorical)
                NodeConfig(
                    id="zona",
                    name="Zona",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": ["norte", "sur", "centro"],
                            "probs": [0.3, 0.4, 0.3],
                        },
                    ),
                ),
                # Base salary with zone-dependent mean
                NodeConfig(
                    id="salario_base",
                    name="Salario Base",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={
                            "mu": {"lookup": "base_por_zona", "key": "zona", "default": 10000},
                            "sigma": 2000,
                        },
                    ),
                ),
                # Net salary after tax
                NodeConfig(
                    id="salario_neto",
                    name="Salario Neto",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="salario_base * (1 - TAX_RATE)",
                ),
            ],
            edges=[
                DAGEdge(source="zona", target="salario_base"),
                DAGEdge(source="salario_base", target="salario_neto"),
            ],
            context={
                "base_por_zona": {"norte": 8000, "sur": 12000, "centro": 10000},
                "TAX_RATE": 0.16,
            },
            sample_size=1000,
        )

        result = generate_preview(dag)

        assert result.columns == ["zona", "salario_base", "salario_neto"]

        for row in result.data:
            # Net salary should be 84% of base
            expected_net = row["salario_base"] * 0.84
            assert abs(row["salario_neto"] - expected_net) < 0.01


class TestReproducibility:
    """Test that sampling is reproducible with same seed."""

    def test_same_seed_same_results(self):
        """Test that same seed produces identical results."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0.0, "sigma": 1.0},
                    ),
                ),
            ],
            seed=42,
        )

        result1 = generate_preview(dag)
        result2 = generate_preview(dag)

        # Results should be identical
        for r1, r2 in zip(result1.data, result2.data, strict=True):
            assert r1["x"] == r2["x"]

    def test_different_seeds_different_results(self):
        """Test that different seeds produce different results."""
        node = NodeConfig(
            id="x",
            name="X",
            kind="stochastic",
            dtype="float",
            scope="row",
            distribution=DistributionConfig(
                type="normal",
                params={"mu": 0.0, "sigma": 1.0},
            ),
        )

        dag1 = make_simple_dag(nodes=[node], seed=42)
        dag2 = make_simple_dag(nodes=[node], seed=123)

        result1 = generate_preview(dag1)
        result2 = generate_preview(dag2)

        # Results should be different
        different = False
        for r1, r2 in zip(result1.data, result2.data, strict=True):
            if r1["x"] != r2["x"]:
                different = True
                break
        assert different


class TestGenerateData:
    """Test full data generation (not just preview)."""

    def test_generate_specified_rows(self):
        """Test generating specified number of rows."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0.0, "sigma": 1.0},
                    ),
                ),
            ],
            sample_size=500,
        )

        result = generate_data(dag)

        # GenerationResult doesn't include data (that's in PreviewResponse)
        # It just returns metadata about the generation
        assert result.rows == 500
        assert result.columns == ["x"]
        assert result.status == "completed"


class TestTopoInvarianceE2E:
    """End-to-end test that shuffled node order produces identical output (P0 regression)."""

    def test_shuffled_dag_nodes_identical_output(self):
        """Test that reordering nodes in DAG JSON produces identical output with same seed."""
        import hashlib
        import json

        def make_dag_with_node_order(node_order):
            """Create DAG with nodes in specified order."""
            node_configs = {
                "zona": NodeConfig(
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
                "base": NodeConfig(
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
                "neto": NodeConfig(
                    id="neto",
                    name="Neto",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="base * 0.84",
                ),
            }
            return make_simple_dag(
                nodes=[node_configs[n] for n in node_order],
                edges=[
                    DAGEdge(source="zona", target="base"),
                    DAGEdge(source="base", target="neto"),
                ],
                context={"salarios": {"norte": 8000, "sur": 12000}},
                sample_size=100,
                seed=42,
            )

        # Test with different node orderings
        orderings = [
            ["zona", "base", "neto"],
            ["neto", "base", "zona"],
            ["base", "zona", "neto"],
            ["neto", "zona", "base"],
        ]

        results = []
        for order in orderings:
            dag = make_dag_with_node_order(order)
            result = generate_preview(dag)
            # Hash the output data for comparison
            data_hash = hashlib.sha256(json.dumps(result.data, sort_keys=True).encode()).hexdigest()
            results.append((order, data_hash, result.data))

        # All results should have identical hash
        first_hash = results[0][1]
        for order, data_hash, _data in results:
            assert data_hash == first_hash, (
                f"Output differs for node order {order}. "
                f"Expected hash {first_hash}, got {data_hash}"
            )


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_row(self):
        """Test generating a single row."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0.0, "sigma": 1.0},
                    ),
                ),
            ],
            sample_size=1,
        )

        # Use preview since generate_data doesn't return data
        result = generate_preview(dag)

        assert result.rows == 1
        assert len(result.data) == 1

    def test_many_nodes(self):
        """Test DAG with many nodes."""
        nodes = []
        edges = []

        # Create a chain of 20 nodes
        for i in range(20):
            if i == 0:
                node = NodeConfig(
                    id=f"n{i}",
                    name=f"Node {i}",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0.0, "high": 1.0},
                    ),
                )
            else:
                node = NodeConfig(
                    id=f"n{i}",
                    name=f"Node {i}",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula=f"n{i - 1} + 1",
                )
                edges.append(DAGEdge(source=f"n{i - 1}", target=f"n{i}"))
            nodes.append(node)

        dag = make_simple_dag(nodes=nodes, edges=edges)

        result = generate_preview(dag)

        assert len(result.columns) == 20

        # Verify the chain calculation
        for row in result.data:
            for i in range(1, 20):
                expected = row[f"n{i - 1}"] + 1
                assert abs(row[f"n{i}"] - expected) < 0.0001


class TestNamespaceRestriction:
    """Test that formulas can only access parent nodes (from edges)."""

    def test_formula_cannot_access_non_parent(self):
        """Test that formula cannot access node without edge, even if computed earlier."""
        # Node 'a' is computed first (it's a root)
        # Node 'b' is also a root
        # Node 'c' tries to access 'a' but has no edge from 'a'
        # Even though 'a' is computed before 'c', 'c' should not see 'a'
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100, "sigma": 1},
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
                        params={"mu": 200, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="c",
                    name="C",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="a + b",  # References both but only edge from b
                ),
            ],
            edges=[
                # Only edge from b to c, NOT from a to c
                DAGEdge(source="b", target="c"),
            ],
        )

        # This should raise an error because 'a' is not a parent of 'c'
        with pytest.raises(Exception) as exc_info:
            generate_preview(dag)

        assert "a" in str(exc_info.value).lower() or "variable" in str(exc_info.value).lower()

    def test_formula_can_access_parent(self):
        """Test that formula can access parent node with edge."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100, "sigma": 1},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="a * 2",  # References 'a' with proper edge
                ),
            ],
            edges=[
                DAGEdge(source="a", target="b"),
            ],
        )

        result = generate_preview(dag)
        assert result.rows > 0

        for row in result.data:
            expected = row["a"] * 2
            assert abs(row["b"] - expected) < 0.001

    def test_param_cannot_reference_non_parent(self):
        """Test that distribution params cannot reference non-parent nodes."""
        dag = make_simple_dag(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100, "sigma": 1},
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
                        params={"mu": "a", "sigma": 1},  # References 'a' but no edge
                    ),
                ),
            ],
            edges=[],  # No edges!
        )

        # This should raise an error because 'a' is not a parent of 'b'
        with pytest.raises(Exception) as exc_info:
            generate_preview(dag)

        # Error should mention missing variable
        assert "a" in str(exc_info.value).lower() or "variable" in str(exc_info.value).lower()
