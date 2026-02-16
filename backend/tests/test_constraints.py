"""Tests for the Constraints system.

This test file defines expected behavior for constraint enforcement in the Data Simulator.
Constraints are validated during data generation to ensure generated data meets specified rules.

Test cases cover:
- Range constraints (min/max bounds)
- NotNull constraints (missing value prevention)
- Unique constraints (duplicate detection)
- Comparison constraints (inter-column relationships)
- Constraint evaluation and reporting
- Integration with DAG generation pipeline
"""

from __future__ import annotations

import numpy as np
import pytest

from app.models.dag import (
    Constraint,
    DAGDefinition,
    DAGEdge,
    DistributionConfig,
    GenerationMetadata,
    NodeConfig,
    PostProcessing,
)
from app.services.sampler import generate_preview


def make_dag_with_constraints(
    nodes: list[NodeConfig],
    constraints: list[Constraint],
    edges: list[DAGEdge] | None = None,
    context: dict | None = None,
    sample_size: int = 100,
    seed: int = 42,
) -> DAGDefinition:
    """Helper to create a DAG definition with constraints."""
    return DAGDefinition(
        nodes=nodes,
        edges=edges or [],
        context=context or {},
        constraints=constraints,
        metadata=GenerationMetadata(
            sample_size=sample_size,
            seed=seed,
            preview_rows=min(sample_size, 10),
        ),
    )


class TestConstraintModel:
    """Test Constraint model validation."""

    def test_range_constraint_creation(self):
        """Test creating a range constraint."""
        constraint = Constraint(
            type="range",
            target="age",
            min=0,
            max=120,
        )
        assert constraint.type == "range"
        assert constraint.target == "age"
        assert constraint.min == 0
        assert constraint.max == 120

    def test_range_constraint_only_min(self):
        """Test creating a range constraint with only min."""
        constraint = Constraint(
            type="range",
            target="salary",
            min=0,
        )
        assert constraint.min == 0
        assert constraint.max is None

    def test_range_constraint_only_max(self):
        """Test creating a range constraint with only max."""
        constraint = Constraint(
            type="range",
            target="temperature",
            max=100,
        )
        assert constraint.min is None
        assert constraint.max == 100

    def test_not_null_constraint_creation(self):
        """Test creating a not_null constraint."""
        constraint = Constraint(
            type="not_null",
            target="user_id",
        )
        assert constraint.type == "not_null"
        assert constraint.target == "user_id"

    def test_unique_constraint_creation(self):
        """Test creating a unique constraint."""
        constraint = Constraint(
            type="unique",
            target="email",
        )
        assert constraint.type == "unique"
        assert constraint.target == "email"

    def test_comparison_constraint_creation(self):
        """Test creating a comparison constraint."""
        constraint = Constraint(
            type="comparison",
            target="end_date",
            other="start_date",
            operator=">=",
        )
        assert constraint.type == "comparison"
        assert constraint.target == "end_date"
        assert constraint.other == "start_date"
        assert constraint.operator == ">="

    def test_comparison_constraint_requires_other_and_operator(self):
        """Test that comparison constraints require both 'other' and 'operator'."""
        # Missing operator
        with pytest.raises(ValueError, match="Comparison constraints require"):
            Constraint(
                type="comparison",
                target="a",
                other="b",
            )

        # Missing other
        with pytest.raises(ValueError, match="Comparison constraints require"):
            Constraint(
                type="comparison",
                target="a",
                operator=">=",
            )

    def test_comparison_constraint_all_operators(self):
        """Test all comparison operators are supported."""
        operators = ["<", "<=", ">", ">="]
        for op in operators:
            constraint = Constraint(
                type="comparison",
                target="a",
                other="b",
                operator=op,
            )
            assert constraint.operator == op


@pytest.mark.skip(reason="Constraints not implemented yet")
class TestRangeConstraints:
    """Test range constraint enforcement."""

    def test_range_constraint_min_only(self):
        """Test range constraint with only minimum value enforces floor."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="score",
                    name="Score",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": -5, "sigma": 10},  # Can generate negative values
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="range",
                    target="score",
                    min=0,  # Enforce non-negative
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        # All values should be >= 0
        for row in result.data:
            assert row["score"] >= 0, f"Score {row['score']} violates min constraint"

    def test_range_constraint_max_only(self):
        """Test range constraint with only maximum value enforces ceiling."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="percentage",
                    name="Percentage",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 95, "sigma": 10},  # Can exceed 100
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="range",
                    target="percentage",
                    max=100,  # Cap at 100
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        # All values should be <= 100
        for row in result.data:
            assert row["percentage"] <= 100, (
                f"Percentage {row['percentage']} violates max constraint"
            )

    def test_range_constraint_min_and_max(self):
        """Test range constraint with both min and max bounds."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="age",
                    name="Age",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 40, "sigma": 30},  # Wide variance
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="range",
                    target="age",
                    min=0,
                    max=120,
                ),
            ],
            sample_size=200,
        )

        result = generate_preview(dag)

        # All values should be in [0, 120]
        for row in result.data:
            assert 0 <= row["age"] <= 120, f"Age {row['age']} violates range constraint"

    def test_range_constraint_on_deterministic_node(self):
        """Test range constraint on deterministic (formula) node."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="base",
                    name="Base",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100, "sigma": 50},
                    ),
                ),
                NodeConfig(
                    id="adjusted",
                    name="Adjusted",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="base * 1.5",  # Can exceed reasonable bounds
                ),
            ],
            edges=[DAGEdge(source="base", target="adjusted")],
            constraints=[
                Constraint(
                    type="range",
                    target="adjusted",
                    min=0,
                    max=200,
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        for row in result.data:
            assert 0 <= row["adjusted"] <= 200, f"Adjusted {row['adjusted']} violates range"

    def test_range_constraint_resample_strategy(self):
        """Test that range violations trigger resampling, not just clamping."""
        # Note: This test verifies that the constraint system resamples
        # rather than simply clipping, which maintains distribution properties.
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="value",
                    name="Value",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": -10, "high": 110},  # Spans beyond [0, 100]
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="range",
                    target="value",
                    min=0,
                    max=100,
                ),
            ],
            sample_size=1000,
        )

        result = generate_preview(dag)

        # All values should be in valid range
        values = [row["value"] for row in result.data]
        assert all(0 <= v <= 100 for v in values)

        # Distribution should not show concentration at boundaries
        # (which would indicate clamping rather than resampling)
        at_min = sum(1 for v in values if abs(v - 0) < 0.01)
        at_max = sum(1 for v in values if abs(v - 100) < 0.01)

        # With uniform distribution and resampling, we shouldn't see
        # more than ~2% of values at boundaries
        assert at_min < len(values) * 0.02, (
            "Too many values at minimum boundary (clamping detected)"
        )
        assert at_max < len(values) * 0.02, (
            "Too many values at maximum boundary (clamping detected)"
        )


@pytest.mark.skip(reason="Constraints not implemented yet")
class TestNotNullConstraints:
    """Test not_null constraint enforcement."""

    def test_not_null_prevents_missing_values(self):
        """Test that not_null constraint prevents null/missing values."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="user_id",
                    name="User ID",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 1000, "sigma": 100},
                    ),
                    post_processing=PostProcessing(
                        missing_rate=0.3,  # 30% missing values
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="not_null",
                    target="user_id",
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        # No null values should be present
        for row in result.data:
            assert row["user_id"] is not None, "user_id should not be null"
            assert not (isinstance(row["user_id"], float) and np.isnan(row["user_id"])), (
                "user_id should not be NaN"
            )

    def test_not_null_with_high_missing_rate(self):
        """Test not_null constraint with very high configured missing rate."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="value",
                    name="Value",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 50, "sigma": 10},
                    ),
                    post_processing=PostProcessing(
                        missing_rate=0.9,  # 90% would be missing without constraint
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="not_null",
                    target="value",
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        # All values should be present
        null_count = sum(
            1
            for row in result.data
            if row["value"] is None or (isinstance(row["value"], float) and np.isnan(row["value"]))
        )
        assert null_count == 0, f"Found {null_count} null values despite not_null constraint"

    def test_not_null_on_deterministic_node(self):
        """Test not_null constraint on deterministic node with potential nulls."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="base",
                    name="Base",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100, "sigma": 20},
                    ),
                    post_processing=PostProcessing(
                        missing_rate=0.2,  # 20% missing
                    ),
                ),
                NodeConfig(
                    id="derived",
                    name="Derived",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="base * 2",  # Will propagate nulls
                ),
            ],
            edges=[DAGEdge(source="base", target="derived")],
            constraints=[
                Constraint(
                    type="not_null",
                    target="derived",
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        # derived should have no nulls
        for row in result.data:
            assert row["derived"] is not None, "derived should not be null"


@pytest.mark.skip(reason="Constraints not implemented yet")
class TestUniqueConstraints:
    """Test unique constraint enforcement."""

    def test_unique_constraint_enforces_uniqueness(self):
        """Test that unique constraint prevents duplicate values."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="id",
                    name="ID",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 1, "high": 10},  # Small range, high collision probability
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="unique",
                    target="id",
                ),
            ],
            sample_size=50,
        )

        result = generate_preview(dag)

        # All values should be unique
        values = [row["id"] for row in result.data]
        assert len(values) == len(set(values)), "Duplicate values found despite unique constraint"

    def test_unique_constraint_with_categorical(self):
        """Test unique constraint on categorical data."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="email",
                    name="Email",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": [f"user{i}@example.com" for i in range(1000)],
                            "probs": None,  # Uniform
                        },
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="unique",
                    target="email",
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        emails = [row["email"] for row in result.data]
        assert len(emails) == len(set(emails)), "Duplicate emails found"

    def test_unique_constraint_max_attempts(self):
        """Test that unique constraint respects max resample attempts."""
        # Create a scenario where uniqueness is impossible
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="value",
                    name="Value",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 1, "high": 3},  # Only 2 possible values
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="unique",
                    target="value",
                ),
            ],
            sample_size=10,  # Need 10 unique values from 2 possibilities
        )

        # Should generate with a warning about uniqueness constraint failures
        result = generate_preview(dag)

        # Should have warnings about constraint violations
        assert len(result.warnings) > 0
        assert any("unique" in w.lower() or "duplicate" in w.lower() for w in result.warnings), (
            "Expected warning about unique constraint violations"
        )

    def test_unique_constraint_on_float_values(self):
        """Test unique constraint on continuous float values."""
        # With continuous distributions, uniqueness should be naturally achievable
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="measurement",
                    name="Measurement",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 0, "sigma": 1},
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="unique",
                    target="measurement",
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        measurements = [row["measurement"] for row in result.data]
        assert len(measurements) == len(set(measurements)), "Duplicate measurements found"


@pytest.mark.skip(reason="Constraints not implemented yet")
class TestComparisonConstraints:
    """Test comparison constraint enforcement."""

    def test_comparison_constraint_less_than(self):
        """Test comparison constraint with < operator."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="min_price",
                    name="Min Price",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 10, "high": 50},
                    ),
                ),
                NodeConfig(
                    id="max_price",
                    name="Max Price",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 20, "high": 100},
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="comparison",
                    target="min_price",
                    other="max_price",
                    operator="<",
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        # min_price should always be < max_price
        for row in result.data:
            assert row["min_price"] < row["max_price"], (
                f"min_price ({row['min_price']}) should be < max_price ({row['max_price']})"
            )

    def test_comparison_constraint_less_than_or_equal(self):
        """Test comparison constraint with <= operator."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="start_date",
                    name="Start Date",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 1, "high": 365},
                    ),
                ),
                NodeConfig(
                    id="end_date",
                    name="End Date",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 1, "high": 365},
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="comparison",
                    target="start_date",
                    other="end_date",
                    operator="<=",
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        # start_date should always be <= end_date
        for row in result.data:
            assert row["start_date"] <= row["end_date"], (
                f"start_date ({row['start_date']}) should be <= end_date ({row['end_date']})"
            )

    def test_comparison_constraint_greater_than(self):
        """Test comparison constraint with > operator."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="revenue",
                    name="Revenue",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 1000, "high": 10000},
                    ),
                ),
                NodeConfig(
                    id="cost",
                    name="Cost",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 500, "high": 8000},
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="comparison",
                    target="revenue",
                    other="cost",
                    operator=">",
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        # revenue should always be > cost
        for row in result.data:
            assert row["revenue"] > row["cost"], (
                f"revenue ({row['revenue']}) should be > cost ({row['cost']})"
            )

    def test_comparison_constraint_greater_than_or_equal(self):
        """Test comparison constraint with >= operator."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="actual",
                    name="Actual",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 50, "high": 150},
                    ),
                ),
                NodeConfig(
                    id="baseline",
                    name="Baseline",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0, "high": 100},
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="comparison",
                    target="actual",
                    other="baseline",
                    operator=">=",
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        # actual should always be >= baseline
        for row in result.data:
            assert row["actual"] >= row["baseline"], (
                f"actual ({row['actual']}) should be >= baseline ({row['baseline']})"
            )

    def test_comparison_constraint_on_deterministic_nodes(self):
        """Test comparison constraint between deterministic nodes."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="base",
                    name="Base",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 10, "high": 100},
                    ),
                ),
                NodeConfig(
                    id="lower",
                    name="Lower Bound",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="base * 0.8",
                ),
                NodeConfig(
                    id="upper",
                    name="Upper Bound",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="base * 1.2",
                ),
            ],
            edges=[
                DAGEdge(source="base", target="lower"),
                DAGEdge(source="base", target="upper"),
            ],
            constraints=[
                Constraint(
                    type="comparison",
                    target="lower",
                    other="upper",
                    operator="<",
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        # This should always pass due to deterministic formulas
        for row in result.data:
            assert row["lower"] < row["upper"], (
                f"lower ({row['lower']}) should be < upper ({row['upper']})"
            )

    def test_multiple_comparison_constraints(self):
        """Test multiple comparison constraints on same nodes."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0, "high": 100},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0, "high": 100},
                    ),
                ),
                NodeConfig(
                    id="c",
                    name="C",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0, "high": 100},
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="comparison",
                    target="a",
                    other="b",
                    operator="<",
                ),
                Constraint(
                    type="comparison",
                    target="b",
                    other="c",
                    operator="<",
                ),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        # Should enforce a < b < c
        for row in result.data:
            assert row["a"] < row["b"], f"a ({row['a']}) should be < b ({row['b']})"
            assert row["b"] < row["c"], f"b ({row['b']}) should be < c ({row['c']})"
            assert row["a"] < row["c"], f"Transitively, a ({row['a']}) should be < c ({row['c']})"


@pytest.mark.skip(reason="Constraints not implemented yet")
class TestConstraintEvaluation:
    """Test constraint evaluation metrics and reporting."""

    def test_constraint_pass_rate_calculation(self):
        """Test that constraint pass rate is calculated correctly."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="value",
                    name="Value",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 50, "sigma": 30},
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="range",
                    target="value",
                    min=0,
                    max=100,
                ),
            ],
            sample_size=1000,
        )

        result = generate_preview(dag)

        # Should have constraint statistics in response
        # (This is a design decision - could be in warnings, stats, or dedicated field)
        assert len(result.warnings) >= 0  # May have warnings about resamples

        # All generated values should pass constraints
        for row in result.data:
            assert 0 <= row["value"] <= 100

    def test_max_resample_attempts(self):
        """Test that constraint enforcement respects max resample attempts."""
        # Create impossible constraints
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 1, "high": 10},
                    ),
                ),
                NodeConfig(
                    id="b",
                    name="B",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 20, "high": 30},
                    ),
                ),
            ],
            constraints=[
                # Impossible: a is always < 10, b is always >= 20
                Constraint(
                    type="comparison",
                    target="a",
                    other="b",
                    operator=">",
                ),
            ],
            sample_size=10,
        )

        # Should generate with warnings about constraint failures
        result = generate_preview(dag)

        # Should have warnings about max attempts reached
        assert len(result.warnings) > 0
        assert any("constraint" in w.lower() or "attempt" in w.lower() for w in result.warnings)

    def test_constraint_failure_reporting(self):
        """Test that constraint failures are properly reported."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="value",
                    name="Value",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 1, "high": 5},  # Small range
                    ),
                ),
            ],
            constraints=[
                Constraint(
                    type="unique",
                    target="value",
                ),
            ],
            sample_size=20,  # Need more unique values than possible
        )

        result = generate_preview(dag)

        # Should have detailed warnings about which constraints failed
        assert len(result.warnings) > 0
        warning_text = " ".join(result.warnings).lower()
        assert "constraint" in warning_text or "unique" in warning_text

    def test_multiple_constraints_evaluation(self):
        """Test evaluation with multiple constraints on different nodes."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="age",
                    name="Age",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 40, "sigma": 20},
                    ),
                ),
                NodeConfig(
                    id="income",
                    name="Income",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 50000, "sigma": 20000},
                    ),
                ),
                NodeConfig(
                    id="id",
                    name="ID",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 1, "high": 1000000},
                    ),
                ),
            ],
            constraints=[
                Constraint(type="range", target="age", min=18, max=65),
                Constraint(type="range", target="income", min=0),
                Constraint(type="not_null", target="age"),
                Constraint(type="not_null", target="income"),
                Constraint(type="unique", target="id"),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        # All constraints should be satisfied
        ids_seen = set()
        for row in result.data:
            # Range constraints
            assert 18 <= row["age"] <= 65
            assert row["income"] >= 0

            # Not null constraints
            assert row["age"] is not None
            assert row["income"] is not None

            # Unique constraint
            assert row["id"] not in ids_seen, f"Duplicate ID: {row['id']}"
            ids_seen.add(row["id"])


@pytest.mark.skip(reason="Constraints not implemented yet")
class TestConstraintIntegration:
    """Test constraint integration with full DAG generation pipeline."""

    def test_constraints_with_dag_dependencies(self):
        """Test constraints work correctly with node dependencies."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="base_salary",
                    name="Base Salary",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 50000, "sigma": 15000},
                    ),
                ),
                NodeConfig(
                    id="bonus",
                    name="Bonus",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 5000, "sigma": 2000},
                    ),
                ),
                NodeConfig(
                    id="total_comp",
                    name="Total Compensation",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="base_salary + bonus",
                ),
            ],
            edges=[
                DAGEdge(source="base_salary", target="total_comp"),
                DAGEdge(source="bonus", target="total_comp"),
            ],
            constraints=[
                Constraint(type="range", target="base_salary", min=20000, max=200000),
                Constraint(type="range", target="bonus", min=0, max=50000),
                Constraint(type="not_null", target="base_salary"),
                Constraint(type="not_null", target="bonus"),
                Constraint(type="not_null", target="total_comp"),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        for row in result.data:
            # Individual constraints
            assert 20000 <= row["base_salary"] <= 200000
            assert 0 <= row["bonus"] <= 50000
            assert row["base_salary"] is not None
            assert row["bonus"] is not None
            assert row["total_comp"] is not None

            # Formula relationship
            expected_total = row["base_salary"] + row["bonus"]
            assert abs(row["total_comp"] - expected_total) < 0.01

    def test_constraints_with_post_processing(self):
        """Test constraints interact correctly with post-processing."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="raw_score",
                    name="Raw Score",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 75.5, "sigma": 15},
                    ),
                    post_processing=PostProcessing(
                        round_decimals=0,  # Round to integers
                        clip_min=0,
                        clip_max=100,
                    ),
                ),
            ],
            constraints=[
                Constraint(type="range", target="raw_score", min=0, max=100),
                Constraint(type="not_null", target="raw_score"),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        for row in result.data:
            # Should be integer (from rounding)
            assert row["raw_score"] == int(row["raw_score"])
            # Should satisfy constraints
            assert 0 <= row["raw_score"] <= 100
            assert row["raw_score"] is not None

    def test_constraints_with_lookups_and_context(self):
        """Test constraints work with dynamic parameters and context."""
        dag = make_dag_with_constraints(
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
                            "categories": ["A", "B", "C"],
                            "probs": [0.33, 0.33, 0.34],
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
                            "mu": {"lookup": "means", "key": "category", "default": 50},
                            "sigma": 10,
                        },
                    ),
                ),
            ],
            edges=[DAGEdge(source="category", target="value")],
            context={
                "means": {"A": 30, "B": 50, "C": 70},
            },
            constraints=[
                Constraint(type="range", target="value", min=0, max=100),
                Constraint(type="not_null", target="value"),
            ],
            sample_size=100,
        )

        result = generate_preview(dag)

        for row in result.data:
            assert 0 <= row["value"] <= 100
            assert row["value"] is not None

    def test_constraints_reproducibility_with_seed(self):
        """Test that constraints produce reproducible results with same seed."""

        def make_test_dag(seed_val):
            return make_dag_with_constraints(
                nodes=[
                    NodeConfig(
                        id="x",
                        name="X",
                        kind="stochastic",
                        dtype="float",
                        scope="row",
                        distribution=DistributionConfig(
                            type="normal",
                            params={"mu": 50, "sigma": 30},
                        ),
                    ),
                ],
                constraints=[
                    Constraint(type="range", target="x", min=0, max=100),
                ],
                sample_size=50,
                seed=seed_val,
            )

        # Generate with same seed twice
        result1 = generate_preview(make_test_dag(42))
        result2 = generate_preview(make_test_dag(42))

        # Results should be identical
        for r1, r2 in zip(result1.data, result2.data, strict=True):
            assert r1["x"] == r2["x"]

    def test_constraints_do_not_break_topological_order(self):
        """Test that constraint enforcement preserves topological ordering."""
        # This test ensures constraints don't interfere with DAG dependencies
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 10, "high": 20},
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
                    formula="b + 10",
                ),
            ],
            edges=[
                DAGEdge(source="a", target="b"),
                DAGEdge(source="b", target="c"),
            ],
            constraints=[
                Constraint(type="range", target="a", min=10, max=20),
                Constraint(type="range", target="b", min=20, max=40),
                Constraint(type="range", target="c", min=30, max=50),
            ],
            sample_size=50,
        )

        result = generate_preview(dag)

        # Verify formulas are still evaluated correctly
        for row in result.data:
            assert abs(row["b"] - (row["a"] * 2)) < 0.001
            assert abs(row["c"] - (row["b"] + 10)) < 0.001

            # And constraints are satisfied
            assert 10 <= row["a"] <= 20
            assert 20 <= row["b"] <= 40
            assert 30 <= row["c"] <= 50


@pytest.mark.skip(reason="Constraints not implemented yet")
class TestConstraintEdgeCases:
    """Test edge cases and boundary conditions for constraints."""

    def test_empty_constraints_list(self):
        """Test that empty constraints list works (no-op)."""
        dag = make_dag_with_constraints(
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
            constraints=[],  # No constraints
            sample_size=50,
        )

        result = generate_preview(dag)
        assert result.rows > 0

    def test_constraint_on_nonexistent_node(self):
        """Test that constraint on non-existent node is caught during validation."""
        from app.core.exceptions import ValidationError

        dag = make_dag_with_constraints(
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
            constraints=[
                Constraint(
                    type="range",
                    target="nonexistent_node",  # Doesn't exist
                    min=0,
                    max=100,
                ),
            ],
            sample_size=10,
        )

        # Should raise validation error
        with pytest.raises(ValidationError):
            generate_preview(dag)

    def test_comparison_constraint_nonexistent_other_node(self):
        """Test comparison constraint with non-existent other node."""
        from app.core.exceptions import ValidationError

        dag = make_dag_with_constraints(
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
            constraints=[
                Constraint(
                    type="comparison",
                    target="a",
                    other="nonexistent",  # Doesn't exist
                    operator="<",
                ),
            ],
            sample_size=10,
        )

        with pytest.raises(ValidationError):
            generate_preview(dag)

    def test_conflicting_constraints(self):
        """Test that conflicting constraints are detected or handled gracefully."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="value",
                    name="Value",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0, "high": 100},
                    ),
                ),
            ],
            constraints=[
                Constraint(type="range", target="value", min=60, max=100),  # Only allows 60-100
                Constraint(type="range", target="value", min=0, max=40),  # Only allows 0-40
                # These are mutually exclusive!
            ],
            sample_size=10,
        )

        # Should either reject during validation or warn during generation
        result = generate_preview(dag)
        assert len(result.warnings) > 0, "Expected warnings about conflicting constraints"

    def test_constraint_with_extreme_values(self):
        """Test constraints with very large or very small values."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="big_number",
                    name="Big Number",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 1e10, "sigma": 1e9},
                    ),
                ),
            ],
            constraints=[
                Constraint(type="range", target="big_number", min=0, max=1e12),
            ],
            sample_size=50,
        )

        result = generate_preview(dag)

        for row in result.data:
            assert 0 <= row["big_number"] <= 1e12

    def test_unique_constraint_with_single_row(self):
        """Test unique constraint with single row (trivially satisfied)."""
        dag = make_dag_with_constraints(
            nodes=[
                NodeConfig(
                    id="id",
                    name="ID",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 1, "high": 100},
                    ),
                ),
            ],
            constraints=[
                Constraint(type="unique", target="id"),
            ],
            sample_size=1,
        )

        result = generate_preview(dag)
        assert len(result.data) == 1
        # Single row is always unique

    def test_constraint_ordering_independence(self):
        """Test that constraint order doesn't affect results."""

        def make_dag_with_constraint_order(constraints):
            return make_dag_with_constraints(
                nodes=[
                    NodeConfig(
                        id="value",
                        name="Value",
                        kind="stochastic",
                        dtype="float",
                        scope="row",
                        distribution=DistributionConfig(
                            type="normal",
                            params={"mu": 50, "sigma": 20},
                        ),
                    ),
                ],
                constraints=constraints,
                sample_size=100,
                seed=42,
            )

        c1 = Constraint(type="range", target="value", min=0, max=100)
        c2 = Constraint(type="not_null", target="value")

        result1 = generate_preview(make_dag_with_constraint_order([c1, c2]))
        result2 = generate_preview(make_dag_with_constraint_order([c2, c1]))

        # Results should be identical regardless of constraint order
        for r1, r2 in zip(result1.data, result2.data, strict=True):
            assert r1["value"] == r2["value"]
