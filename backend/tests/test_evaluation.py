"""
Tests for /api/dag/evaluate endpoint and evaluation statistics.

These tests verify the evaluation endpoint which computes:
- Column statistics (numeric and categorical)
- Correlation matrices
- Constraint validation pass rates
- Constraint failure details

Tests are written TDD-style, expecting endpoint to be implemented in Fase 9.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.dag import (
    Constraint,
    DAGDefinition,
    DAGEdge,
    DistributionConfig,
    GenerationMetadata,
    NodeConfig,
    PostProcessing,
)

client = TestClient(app)


# =============================================================================
# Test Fixtures
# =============================================================================


def make_dag(
    nodes: list[NodeConfig],
    edges: list[DAGEdge] | None = None,
    constraints: list[Constraint] | None = None,
    context: dict | None = None,
    sample_size: int = 100,
    seed: int = 42,
) -> dict:
    """Helper to create a DAG definition as dict for API calls."""
    dag = DAGDefinition(
        nodes=nodes,
        edges=edges or [],
        constraints=constraints or [],
        context=context or {},
        metadata=GenerationMetadata(sample_size=sample_size, seed=seed),
    )
    return dag.model_dump()


# =============================================================================
# Column Statistics - Numeric
# =============================================================================


@pytest.mark.skip(reason="Evaluation endpoint not implemented yet")
class TestNumericColumnStatistics:
    """Test numeric column statistics computation."""

    def test_numeric_stats_mean_std_computed(self):
        """Test that mean and std are computed for numeric columns."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 15.0},
                    ),
                ),
            ],
            sample_size=1000,
            seed=42,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        assert response.status_code == 200

        result = response.json()
        assert "column_stats" in result
        assert len(result["column_stats"]) == 1

        stats = result["column_stats"][0]
        assert stats["node_id"] == "x"
        assert stats["dtype"] == "float"

        # Check numeric stats are present
        assert "mean" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats
        assert "median" in stats

        # Mean should be close to 100 (with tolerance for random sampling)
        assert 95 < stats["mean"] < 105
        # Std should be close to 15
        assert 12 < stats["std"] < 18

    def test_numeric_stats_min_max_median(self):
        """Test that min, max, and median are computed correctly."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="uniform",
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
            sample_size=1000,
            seed=42,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        stats = result["column_stats"][0]

        # Min should be close to 0
        assert 0 <= stats["min"] < 5
        # Max should be close to 100
        assert 95 < stats["max"] < 100
        # Median should be around 50
        assert 40 < stats["median"] < 60

    def test_numeric_stats_multiple_columns(self):
        """Test statistics for multiple numeric columns."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 50.0, "sigma": 10.0},
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
                        params={"mu": 200.0, "sigma": 30.0},
                    ),
                ),
            ],
            sample_size=500,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        assert len(result["column_stats"]) == 2

        # Find stats for each column
        x_stats = next(s for s in result["column_stats"] if s["node_id"] == "x")
        y_stats = next(s for s in result["column_stats"] if s["node_id"] == "y")

        # Check both have numeric stats
        assert 45 < x_stats["mean"] < 55
        assert 190 < y_stats["mean"] < 210

    def test_numeric_stats_deterministic_column(self):
        """Test statistics for deterministic (formula) columns."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 50.0, "sigma": 5.0},
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
            sample_size=500,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        x_stats = next(s for s in result["column_stats"] if s["node_id"] == "x")
        y_stats = next(s for s in result["column_stats"] if s["node_id"] == "y")

        # y should have mean approximately 2x of x
        assert abs(y_stats["mean"] - x_stats["mean"] * 2) < 5

    def test_numeric_stats_integer_column(self):
        """Test statistics for integer columns."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="count",
                    name="Count",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="poisson",
                        params={"lambda": 5.0},
                    ),
                ),
            ],
            sample_size=500,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        stats = result["column_stats"][0]
        assert stats["dtype"] == "int"
        assert "mean" in stats
        assert stats["mean"] > 0


# =============================================================================
# Column Statistics - Null Values
# =============================================================================


@pytest.mark.skip(reason="Evaluation endpoint not implemented yet")
class TestNullValueStatistics:
    """Test null value counting and rate computation."""

    def test_null_count_with_missing_rate(self):
        """Test null_count and null_rate with missing_rate post-processing."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                    post_processing=PostProcessing(missing_rate=0.2),
                ),
            ],
            sample_size=1000,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        stats = result["column_stats"][0]

        # Should have null_count and null_rate
        assert "null_count" in stats
        assert "null_rate" in stats

        # With missing_rate=0.2, expect ~200 nulls out of 1000
        assert 150 < stats["null_count"] < 250
        # null_rate should be ~0.2
        assert 0.15 < stats["null_rate"] < 0.25

    def test_null_count_zero_when_no_missing(self):
        """Test null_count is 0 when no missing values."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                    # No post_processing = no missing values
                ),
            ],
            sample_size=100,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        stats = result["column_stats"][0]

        assert stats["null_count"] == 0
        assert stats["null_rate"] == 0.0

    def test_null_count_all_nulls(self):
        """Test null_count when all values are null."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                    post_processing=PostProcessing(missing_rate=1.0),
                ),
            ],
            sample_size=100,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        stats = result["column_stats"][0]

        assert stats["null_count"] == 100
        assert stats["null_rate"] == 1.0

        # Numeric stats should be None when all nulls
        assert stats["mean"] is None
        assert stats["std"] is None
        assert stats["min"] is None
        assert stats["max"] is None
        assert stats["median"] is None


# =============================================================================
# Column Statistics - Categorical
# =============================================================================


@pytest.mark.skip(reason="Evaluation endpoint not implemented yet")
class TestCategoricalColumnStatistics:
    """Test categorical column statistics computation."""

    def test_categorical_stats_category_counts(self):
        """Test that category counts are computed correctly."""
        dag = make_dag(
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
                            "probs": [0.5, 0.3, 0.2],
                        },
                    ),
                ),
            ],
            sample_size=1000,
            seed=42,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        stats = result["column_stats"][0]
        assert stats["node_id"] == "category"
        assert stats["dtype"] == "category"

        # Should have categories and category_rates
        assert "categories" in stats
        assert "category_rates" in stats
        assert stats["categories"] is not None
        assert stats["category_rates"] is not None

        # Check all categories are present
        categories = stats["categories"]
        assert "A" in categories
        assert "B" in categories
        assert "C" in categories

        # Total should equal sample_size
        total = sum(categories.values())
        assert total == 1000

        # A should be most common (~500)
        assert 450 < categories["A"] < 550

    def test_categorical_stats_category_rates(self):
        """Test that category rates (proportions) are computed correctly."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="status",
                    name="Status",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": ["active", "inactive"],
                            "probs": [0.8, 0.2],
                        },
                    ),
                ),
            ],
            sample_size=500,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        stats = result["column_stats"][0]
        rates = stats["category_rates"]

        # Rates should sum to 1.0
        total_rate = sum(rates.values())
        assert abs(total_rate - 1.0) < 0.001

        # Active should be ~0.8
        assert 0.75 < rates["active"] < 0.85
        # Inactive should be ~0.2
        assert 0.15 < rates["inactive"] < 0.25

    def test_categorical_stats_single_category(self):
        """Test categorical stats with only one category."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="constant",
                    name="Constant",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": ["ONLY"],
                            "probs": [1.0],
                        },
                    ),
                ),
            ],
            sample_size=100,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        stats = result["column_stats"][0]

        # Should have only one category
        assert len(stats["categories"]) == 1
        assert stats["categories"]["ONLY"] == 100
        assert stats["category_rates"]["ONLY"] == 1.0

    def test_categorical_stats_many_categories(self):
        """Test categorical stats with many categories."""
        categories = [f"cat_{i}" for i in range(20)]
        probs = [1.0 / 20] * 20  # Uniform distribution

        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="many_cats",
                    name="Many Categories",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": categories,
                            "probs": probs,
                        },
                    ),
                ),
            ],
            sample_size=1000,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        stats = result["column_stats"][0]

        # Should have 20 categories
        assert len(stats["categories"]) == 20
        # Each should have roughly equal count (~50)
        for count in stats["categories"].values():
            assert 30 < count < 70

    def test_categorical_stats_no_numeric_stats(self):
        """Test that categorical columns don't have numeric stats."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="cat",
                    name="Cat",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": ["X", "Y"],
                            "probs": [0.5, 0.5],
                        },
                    ),
                ),
            ],
            sample_size=100,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        stats = result["column_stats"][0]

        # Categorical columns should not have numeric stats
        assert stats["mean"] is None
        assert stats["std"] is None
        assert stats["min"] is None
        assert stats["max"] is None
        assert stats["median"] is None


# =============================================================================
# Correlation Matrix
# =============================================================================


@pytest.mark.skip(reason="Evaluation endpoint not implemented yet")
class TestCorrelationMatrix:
    """Test correlation matrix computation."""

    def test_correlation_matrix_structure(self):
        """Test that correlation matrix has correct structure."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
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
                        params={"mu": 200.0, "sigma": 20.0},
                    ),
                ),
            ],
            sample_size=500,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        assert "correlation_matrix" in result
        corr_matrix = result["correlation_matrix"]

        # Should be a dict of dicts
        assert isinstance(corr_matrix, dict)

        # Should have entries for both x and y
        assert "x" in corr_matrix
        assert "y" in corr_matrix

        # Each row should have entries for both columns
        assert "x" in corr_matrix["x"]
        assert "y" in corr_matrix["x"]
        assert "x" in corr_matrix["y"]
        assert "y" in corr_matrix["y"]

    def test_correlation_matrix_diagonal_is_one(self):
        """Test that diagonal elements (self-correlation) are 1.0."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0.0, "high": 100.0},
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
                        params={"low": 0.0, "high": 100.0},
                    ),
                ),
            ],
            sample_size=500,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        corr_matrix = result["correlation_matrix"]

        # Diagonal should be 1.0
        assert abs(corr_matrix["a"]["a"] - 1.0) < 0.001
        assert abs(corr_matrix["b"]["b"] - 1.0) < 0.001

    def test_correlation_matrix_symmetric(self):
        """Test that correlation matrix is symmetric."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 50.0, "sigma": 10.0},
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
                        params={"mu": 100.0, "sigma": 20.0},
                    ),
                ),
            ],
            sample_size=500,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        corr_matrix = result["correlation_matrix"]

        # Should be symmetric: corr(x, y) == corr(y, x)
        assert abs(corr_matrix["x"]["y"] - corr_matrix["y"]["x"]) < 0.001

    def test_correlation_matrix_perfect_correlation(self):
        """Test correlation with perfectly correlated variables."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
                NodeConfig(
                    id="y",
                    name="Y",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="x * 2 + 10",  # Perfectly correlated
                ),
            ],
            edges=[DAGEdge(source="x", target="y")],
            sample_size=500,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        corr_matrix = result["correlation_matrix"]

        # Correlation should be very close to 1.0 (perfect positive)
        assert corr_matrix["x"]["y"] > 0.99

    def test_correlation_matrix_negative_correlation(self):
        """Test correlation with negatively correlated variables."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
                NodeConfig(
                    id="y",
                    name="Y",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="-x + 200",  # Perfectly negatively correlated
                ),
            ],
            edges=[DAGEdge(source="x", target="y")],
            sample_size=500,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        corr_matrix = result["correlation_matrix"]

        # Correlation should be very close to -1.0 (perfect negative)
        assert corr_matrix["x"]["y"] < -0.99

    def test_correlation_matrix_only_numeric_columns(self):
        """Test that correlation matrix only includes numeric columns."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="numeric",
                    name="Numeric",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
                NodeConfig(
                    id="category",
                    name="Category",
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
            ],
            sample_size=500,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        corr_matrix = result["correlation_matrix"]

        # Correlation matrix should only have numeric column
        assert "numeric" in corr_matrix
        assert "category" not in corr_matrix

    def test_correlation_matrix_three_variables(self):
        """Test correlation matrix with three variables."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="a",
                    name="A",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 50.0, "sigma": 10.0},
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
                        params={"mu": 100.0, "sigma": 15.0},
                    ),
                ),
                NodeConfig(
                    id="c",
                    name="C",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="a + b",
                ),
            ],
            edges=[
                DAGEdge(source="a", target="c"),
                DAGEdge(source="b", target="c"),
            ],
            sample_size=500,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        corr_matrix = result["correlation_matrix"]

        # Should have 3x3 matrix
        assert len(corr_matrix) == 3
        assert "a" in corr_matrix
        assert "b" in corr_matrix
        assert "c" in corr_matrix

        # c should be highly correlated with both a and b
        assert corr_matrix["a"]["c"] > 0.5
        assert corr_matrix["b"]["c"] > 0.5


# =============================================================================
# Constraint Evaluation
# =============================================================================


@pytest.mark.skip(reason="Evaluation endpoint not implemented yet")
class TestConstraintEvaluation:
    """Test constraint validation pass rate and failure reporting."""

    def test_constraint_pass_rate_all_pass(self):
        """Test constraint_pass_rate when all rows pass."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 10.0, "high": 90.0},
                    ),
                ),
            ],
            constraints=[
                Constraint(type="range", target="x", min=0.0, max=100.0),
            ],
            sample_size=100,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        assert "constraint_pass_rate" in result
        # All values should be in [10, 90], which is within [0, 100]
        assert result["constraint_pass_rate"] == 1.0

        # Should have no failures
        assert "constraint_failures" in result
        assert len(result["constraint_failures"]) == 0

    def test_constraint_pass_rate_some_fail(self):
        """Test constraint_pass_rate when some rows fail."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 20.0},
                    ),
                ),
            ],
            constraints=[
                # This constraint will fail for values outside [90, 110]
                Constraint(type="range", target="x", min=90.0, max=110.0),
            ],
            sample_size=1000,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        # Some rows should fail (values in tails of normal distribution)
        pass_rate = result["constraint_pass_rate"]
        assert 0.0 < pass_rate < 1.0

        # Should have failure details
        assert len(result["constraint_failures"]) > 0

    def test_constraint_pass_rate_all_fail(self):
        """Test constraint_pass_rate when all rows fail."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 50.0, "high": 150.0},
                    ),
                ),
            ],
            constraints=[
                # Impossible constraint: all values are > 50
                Constraint(type="range", target="x", min=0.0, max=40.0),
            ],
            sample_size=100,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        # All rows should fail
        assert result["constraint_pass_rate"] == 0.0

    def test_constraint_failures_list_format(self):
        """Test that constraint_failures has correct format."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 30.0},
                    ),
                ),
            ],
            constraints=[
                Constraint(type="range", target="x", min=80.0, max=120.0),
            ],
            sample_size=1000,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        failures = result["constraint_failures"]

        if len(failures) > 0:
            failure = failures[0]

            # Check structure
            assert "type" in failure
            assert "target" in failure
            assert "failures" in failure

            assert failure["type"] == "range"
            assert failure["target"] == "x"
            assert isinstance(failure["failures"], int)
            assert failure["failures"] > 0

    def test_constraint_failures_multiple_constraints(self):
        """Test constraint failures with multiple constraints."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0.0, "high": 200.0},
                    ),
                ),
                NodeConfig(
                    id="y",
                    name="Y",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0.0, "high": 200.0},
                    ),
                ),
            ],
            constraints=[
                Constraint(type="range", target="x", min=50.0, max=150.0),
                Constraint(type="range", target="y", min=50.0, max=150.0),
            ],
            sample_size=1000,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        failures = result["constraint_failures"]

        # Should have failures for both constraints
        x_failure = next((f for f in failures if f["target"] == "x"), None)
        y_failure = next((f for f in failures if f["target"] == "y"), None)

        assert x_failure is not None
        assert y_failure is not None

    def test_constraint_not_null_evaluation(self):
        """Test evaluation of not_null constraint."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                    post_processing=PostProcessing(missing_rate=0.1),
                ),
            ],
            constraints=[
                Constraint(type="not_null", target="x"),
            ],
            sample_size=1000,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        # Pass rate should be ~0.9 (10% nulls)
        assert 0.85 < result["constraint_pass_rate"] < 0.95

        # Should have not_null failure
        failures = result["constraint_failures"]
        not_null_failure = next((f for f in failures if f["type"] == "not_null"), None)
        assert not_null_failure is not None
        assert 50 < not_null_failure["failures"] < 150  # ~100 failures

    def test_constraint_comparison_evaluation(self):
        """Test evaluation of comparison constraint."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="start",
                    name="Start",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0.0, "high": 100.0},
                    ),
                ),
                NodeConfig(
                    id="end",
                    name="End",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform",
                        params={"low": 0.0, "high": 100.0},
                    ),
                ),
            ],
            constraints=[
                # start < end (will fail ~50% of the time randomly)
                Constraint(type="comparison", target="end", other="start", operator="<"),
            ],
            sample_size=1000,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        # Pass rate should be around 0.5 (random uniform distributions)
        assert 0.4 < result["constraint_pass_rate"] < 0.6

    def test_constraint_pass_rate_no_constraints(self):
        """Test that constraint_pass_rate is 1.0 when no constraints."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
            ],
            constraints=[],  # No constraints
            sample_size=100,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        # Should be 1.0 when no constraints
        assert result["constraint_pass_rate"] == 1.0
        assert len(result["constraint_failures"]) == 0


# =============================================================================
# API Endpoint Tests
# =============================================================================


@pytest.mark.skip(reason="Evaluation endpoint not implemented yet")
class TestEvaluateEndpoint:
    """Test the /api/dag/evaluate endpoint itself."""

    def test_evaluate_endpoint_exists(self):
        """Test that POST /api/dag/evaluate endpoint exists."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
            ],
            sample_size=100,
        )

        response = client.post("/api/dag/evaluate", json=dag)

        # Endpoint should exist (not 404)
        assert response.status_code != 404

    def test_evaluate_endpoint_accepts_dag(self):
        """Test that endpoint accepts DAG definition."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
            ],
            sample_size=100,
        )

        response = client.post("/api/dag/evaluate", json=dag)

        assert response.status_code == 200

    def test_evaluate_endpoint_returns_evaluation_result(self):
        """Test that endpoint returns EvaluationResult structure."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
            ],
            sample_size=100,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        # Should have all required fields
        assert "column_stats" in result
        assert "correlation_matrix" in result
        assert "constraint_pass_rate" in result
        assert "constraint_failures" in result

        # Types should be correct
        assert isinstance(result["column_stats"], list)
        assert isinstance(result["correlation_matrix"], dict)
        assert isinstance(result["constraint_pass_rate"], (int, float))
        assert isinstance(result["constraint_failures"], list)

    def test_evaluate_endpoint_uses_sample_size(self):
        """Test that endpoint respects sample_size from metadata."""
        dag_small = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
            ],
            sample_size=50,
        )

        dag_large = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
            ],
            sample_size=500,
        )

        response_small = client.post("/api/dag/evaluate", json=dag_small)
        response_large = client.post("/api/dag/evaluate", json=dag_large)

        # Both should succeed
        assert response_small.status_code == 200
        assert response_large.status_code == 200

        # Statistics should differ due to different sample sizes
        stats_small = response_small.json()["column_stats"][0]
        stats_large = response_large.json()["column_stats"][0]

        # Larger sample should generally have more stable statistics
        # (This is a soft check - we just verify endpoint respects sample_size)
        assert stats_small["mean"] is not None
        assert stats_large["mean"] is not None

    def test_evaluate_endpoint_invalid_dag_returns_error(self):
        """Test that endpoint returns error for invalid DAG."""
        invalid_dag = {
            "nodes": [
                {
                    "id": "x",
                    "name": "X",
                    "kind": "stochastic",
                    "scope": "row",
                    # Missing distribution
                },
            ],
            "edges": [],
            "metadata": {"sample_size": 100},
        }

        response = client.post("/api/dag/evaluate", json=invalid_dag)

        # Should return error status
        assert response.status_code in [400, 422]

    def test_evaluate_endpoint_with_seed(self):
        """Test that endpoint produces deterministic results with seed."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
            ],
            sample_size=100,
            seed=42,
        )

        response1 = client.post("/api/dag/evaluate", json=dag)
        response2 = client.post("/api/dag/evaluate", json=dag)

        result1 = response1.json()
        result2 = response2.json()

        # Statistics should be identical with same seed
        assert result1["column_stats"][0]["mean"] == result2["column_stats"][0]["mean"]


# =============================================================================
# Edge Cases
# =============================================================================


@pytest.mark.skip(reason="Evaluation endpoint not implemented yet")
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_edge_case_all_nulls_in_column(self):
        """Test evaluation with all null values in a column."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                    post_processing=PostProcessing(missing_rate=1.0),
                ),
            ],
            sample_size=100,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        stats = result["column_stats"][0]

        # All numeric stats should be None
        assert stats["mean"] is None
        assert stats["std"] is None
        assert stats["min"] is None
        assert stats["max"] is None
        assert stats["median"] is None

        # Null stats should reflect all nulls
        assert stats["null_count"] == 100
        assert stats["null_rate"] == 1.0

    def test_edge_case_zero_variance_column(self):
        """Test evaluation with zero variance (constant) column."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="constant",
                    name="Constant",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 0.0},  # Zero variance
                    ),
                ),
            ],
            sample_size=100,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        stats = result["column_stats"][0]

        # Mean should be 100
        assert stats["mean"] == 100.0
        # Std should be 0
        assert stats["std"] == 0.0
        # All values should be 100
        assert stats["min"] == 100.0
        assert stats["max"] == 100.0
        assert stats["median"] == 100.0

    def test_edge_case_single_row(self):
        """Test evaluation with only one row."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
            ],
            sample_size=1,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        # Should still return statistics
        assert response.status_code == 200
        stats = result["column_stats"][0]

        # Stats should be defined
        assert stats["mean"] is not None
        # Std might be 0 or undefined for single value
        assert stats["min"] is not None
        assert stats["max"] is not None
        # Min should equal max for single value
        assert stats["min"] == stats["max"]

    def test_edge_case_mixed_types_in_dag(self):
        """Test evaluation with mixed numeric and categorical columns."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="numeric",
                    name="Numeric",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
                NodeConfig(
                    id="category",
                    name="Category",
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
                    id="integer",
                    name="Integer",
                    kind="stochastic",
                    dtype="int",
                    scope="row",
                    distribution=DistributionConfig(
                        type="poisson",
                        params={"lambda": 5.0},
                    ),
                ),
            ],
            sample_size=500,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        # Should have stats for all three columns
        assert len(result["column_stats"]) == 3

        # Numeric columns should have numeric stats
        numeric_stats = next(s for s in result["column_stats"] if s["node_id"] == "numeric")
        assert numeric_stats["mean"] is not None

        integer_stats = next(s for s in result["column_stats"] if s["node_id"] == "integer")
        assert integer_stats["mean"] is not None

        # Categorical column should have category stats
        cat_stats = next(s for s in result["column_stats"] if s["node_id"] == "category")
        assert cat_stats["categories"] is not None
        assert cat_stats["mean"] is None

        # Correlation matrix should only have numeric columns
        corr_matrix = result["correlation_matrix"]
        assert "numeric" in corr_matrix
        assert "integer" in corr_matrix
        assert "category" not in corr_matrix

    def test_edge_case_large_sample_size(self):
        """Test evaluation with large sample size."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
            ],
            sample_size=10000,
        )

        response = client.post("/api/dag/evaluate", json=dag)

        # Should succeed even with large sample
        assert response.status_code == 200

        result = response.json()
        stats = result["column_stats"][0]

        # With large sample, mean should be very close to 100
        assert 99 < stats["mean"] < 101

    def test_edge_case_no_edges_independent_nodes(self):
        """Test evaluation with independent nodes (no edges)."""
        dag = make_dag(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal",
                        params={"mu": 50.0, "sigma": 10.0},
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
                        params={"mu": 100.0, "sigma": 10.0},
                    ),
                ),
            ],
            edges=[],  # No edges - independent
            sample_size=500,
        )

        response = client.post("/api/dag/evaluate", json=dag)
        result = response.json()

        # Should compute statistics for both
        assert len(result["column_stats"]) == 2

        # Correlation should be close to 0 (independent)
        corr_matrix = result["correlation_matrix"]
        assert abs(corr_matrix["x"]["y"]) < 0.2  # Small correlation due to randomness
