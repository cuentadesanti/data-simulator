"""
Comprehensive tests for scope handling (global, row, group).

Fase 4: Scopes global/row (MVP) + group scope (extended)
"""

import numpy as np
import pytest
from app.models.dag import (
    DAGDefinition,
    DAGEdge,
    DistributionConfig,
    GenerationMetadata,
    NodeConfig,
)
from app.services.sampler import _generate_data
from app.services.validator import validate_dag


class TestRowScope:
    """Row scope: N independent samples for N rows."""

    def test_row_scope_generates_n_values(self):
        """Each row gets an independent sample."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="x",
                    name="X",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="uniform", params={"low": 0, "high": 100}),
                ),
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=1000, seed=42),
        )

        df, _, _ = _generate_data(dag, 1000, seed=42)

        # Should have 1000 rows
        assert len(df) == 1000

        # Values should vary (not all the same)
        unique_values = df["x"].nunique()
        assert unique_values > 100  # High variance expected

    def test_row_scope_with_dependencies(self):
        """Row scope respects dependencies between nodes."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="base",
                    name="Base",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="uniform", params={"low": 100, "high": 200}
                    ),
                ),
                NodeConfig(
                    id="derived",
                    name="Derived",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="base * 2",
                ),
            ],
            edges=[DAGEdge(source="base", target="derived")],
            metadata=GenerationMetadata(sample_size=100, seed=42),
        )

        df, _, _ = _generate_data(dag, 100, seed=42)

        # derived should be exactly base * 2
        assert np.allclose(df["derived"], df["base"] * 2)


class TestGlobalScope:
    """Global scope: 1 sample broadcast to all N rows."""

    def test_global_scope_broadcasts_single_value(self):
        """All rows have the same value for global scope."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="global_factor",
                    name="Global Factor",
                    kind="stochastic",
                    dtype="float",
                    scope="global",
                    distribution=DistributionConfig(
                        type="uniform", params={"low": 0.9, "high": 1.1}
                    ),
                ),
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=1000, seed=42),
        )

        df, _, _ = _generate_data(dag, 1000, seed=42)

        # All 1000 rows should have the exact same value
        unique_values = df["global_factor"].unique()
        assert len(unique_values) == 1

    def test_global_scope_is_deterministic(self):
        """Same seed produces same global value."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="global_rate",
                    name="Rate",
                    kind="stochastic",
                    dtype="float",
                    scope="global",
                    distribution=DistributionConfig(
                        type="normal", params={"mu": 0.1, "sigma": 0.01}
                    ),
                ),
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100, seed=42),
        )

        df1, _, _ = _generate_data(dag, 100, seed=42)
        df2, _, _ = _generate_data(dag, 100, seed=42)

        # Column name is "global_rate" (canonical ID)
        assert df1["global_rate"].iloc[0] == df2["global_rate"].iloc[0]

    def test_global_scope_with_different_sample_sizes(self):
        """Global value is the same regardless of sample size."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="constant",
                    name="Constant",
                    kind="stochastic",
                    dtype="float",
                    scope="global",
                    distribution=DistributionConfig(type="normal", params={"mu": 100, "sigma": 5}),
                ),
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100, seed=42),
        )

        df_100, _, _ = _generate_data(dag, 100, seed=42)
        df_1000, _, _ = _generate_data(dag, 1000, seed=42)

        # Same seed should produce same global value
        assert df_100["constant"].iloc[0] == df_1000["constant"].iloc[0]

    def test_global_scope_used_in_formulas(self):
        """Global values can be used in row-level formulas."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="inflation",
                    name="Inflation Rate",
                    kind="stochastic",
                    dtype="float",
                    scope="global",
                    distribution=DistributionConfig(
                        type="uniform", params={"low": 0.02, "high": 0.05}
                    ),
                ),
                NodeConfig(
                    id="salary",
                    name="Base Salary",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal", params={"mu": 50000, "sigma": 10000}
                    ),
                ),
                NodeConfig(
                    id="adjusted_salary",
                    name="Adjusted Salary",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="salary * (1 + inflation)",
                ),
            ],
            edges=[
                DAGEdge(source="inflation", target="adjusted_salary"),
                DAGEdge(source="salary", target="adjusted_salary"),
            ],
            metadata=GenerationMetadata(sample_size=100, seed=42),
        )

        df, _, _ = _generate_data(dag, 100, seed=42)

        # inflation should be same for all rows
        assert df["inflation"].nunique() == 1

        # adjusted_salary should use the global inflation
        inflation = df["inflation"].iloc[0]
        expected = df["salary"] * (1 + inflation)
        assert np.allclose(df["adjusted_salary"], expected)


class TestGroupScope:
    """Group scope: 1 sample per unique category, mapped back to rows.

    Note: Group scope may be MVP/basic - tests verify expected behavior.
    """

    def test_group_scope_generates_value_per_category(self):
        """Each unique category gets one value."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="region",
                    name="Region",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": ["north", "south", "east"],
                            "probs": [0.4, 0.4, 0.2],
                        },
                    ),
                ),
                NodeConfig(
                    id="regional_bonus",
                    name="Regional Bonus",
                    kind="stochastic",
                    dtype="float",
                    scope="group",
                    group_by="region",
                    distribution=DistributionConfig(
                        type="normal", params={"mu": 1000, "sigma": 100}
                    ),
                ),
            ],
            edges=[DAGEdge(source="region", target="regional_bonus")],
            metadata=GenerationMetadata(sample_size=1000, seed=42),
        )

        df, _, _ = _generate_data(dag, 1000, seed=42)

        # regional_bonus should have exactly 3 unique values (one per region)
        unique_bonuses = df["regional_bonus"].nunique()
        assert unique_bonuses == 3

        # All rows with same region should have same bonus
        for region in ["north", "south", "east"]:
            region_rows = df[df["region"] == region]
            if len(region_rows) > 0:
                assert region_rows["regional_bonus"].nunique() == 1

    def test_group_scope_mapping_consistency(self):
        """Same category always maps to same value within a generation."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="team",
                    name="Team",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": ["alpha", "beta", "gamma"],
                            "probs": [0.33, 0.33, 0.34],
                        },
                    ),
                ),
                NodeConfig(
                    id="team_budget",
                    name="Team Budget",
                    kind="stochastic",
                    dtype="float",
                    scope="group",
                    group_by="team",
                    distribution=DistributionConfig(
                        type="uniform", params={"low": 10000, "high": 50000}
                    ),
                ),
            ],
            edges=[DAGEdge(source="team", target="team_budget")],
            metadata=GenerationMetadata(sample_size=500, seed=42),
        )

        df, _, _ = _generate_data(dag, 500, seed=42)

        # Build mapping from team to budget
        team_to_budget = {}
        for _, row in df.iterrows():
            team = row["team"]
            budget = row["team_budget"]
            if team in team_to_budget:
                assert team_to_budget[team] == budget, f"Inconsistent budget for {team}"
            else:
                team_to_budget[team] = budget

    def test_group_scope_determinism(self):
        """Same seed produces same group values."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="dept",
                    name="Department",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={
                            "categories": ["eng", "sales", "hr"],
                            "probs": [0.5, 0.3, 0.2],
                        },
                    ),
                ),
                NodeConfig(
                    id="dept_modifier",
                    name="Dept Modifier",
                    kind="stochastic",
                    dtype="float",
                    scope="group",
                    group_by="dept",
                    distribution=DistributionConfig(
                        type="normal", params={"mu": 1.0, "sigma": 0.1}
                    ),
                ),
            ],
            edges=[DAGEdge(source="dept", target="dept_modifier")],
            metadata=GenerationMetadata(sample_size=300, seed=123),
        )

        df1, _, _ = _generate_data(dag, 300, seed=123)
        df2, _, _ = _generate_data(dag, 300, seed=123)

        # Same seed should produce identical results
        assert df1["dept_modifier"].equals(df2["dept_modifier"])


class TestScopeValidation:
    """Validation rules for scopes."""

    def test_group_scope_requires_group_by(self):
        """scope='group' without group_by should fail validation."""
        with pytest.raises(ValueError, match="group_by"):
            NodeConfig(
                id="bad",
                name="Bad",
                kind="stochastic",
                dtype="float",
                scope="group",
                # Missing group_by!
                distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
            )

    def test_group_by_requires_group_scope(self):
        """group_by set with scope != 'group' should fail."""
        with pytest.raises(ValueError, match="scope"):
            NodeConfig(
                id="bad",
                name="Bad",
                kind="stochastic",
                dtype="float",
                scope="row",  # Not 'group'
                group_by="some_node",  # group_by set incorrectly
                distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
            )

    def test_group_by_must_be_ancestor(self):
        """group_by must reference an ancestor node."""
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
                    group_by="c",  # 'c' is not an ancestor of 'b'
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                ),
                NodeConfig(
                    id="c",
                    name="C",
                    kind="stochastic",
                    dtype="category",
                    scope="row",
                    distribution=DistributionConfig(
                        type="categorical",
                        params={"categories": ["x", "y"], "probs": [0.5, 0.5]},
                    ),
                ),
            ],
            edges=[],  # No edges - 'c' is NOT an ancestor of 'b'
            metadata=GenerationMetadata(sample_size=100, seed=42),
        )

        result = validate_dag(dag)
        assert not result.valid
        assert any("ancestor" in err.lower() for err in result.errors)

    def test_group_by_nonexistent_node(self):
        """group_by referencing non-existent node should fail."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="bad_group",
                    name="Bad Group",
                    kind="stochastic",
                    dtype="float",
                    scope="group",
                    group_by="nonexistent",
                    distribution=DistributionConfig(type="normal", params={"mu": 0, "sigma": 1}),
                ),
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=100, seed=42),
        )

        result = validate_dag(dag)
        assert not result.valid


class TestMixedScopes:
    """Tests combining different scopes in one DAG."""

    def test_global_row_combination(self):
        """Global and row scopes work together."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="tax_rate",
                    name="Tax Rate",
                    kind="stochastic",
                    dtype="float",
                    scope="global",
                    distribution=DistributionConfig(
                        type="uniform", params={"low": 0.15, "high": 0.25}
                    ),
                ),
                NodeConfig(
                    id="income",
                    name="Income",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(
                        type="normal", params={"mu": 50000, "sigma": 15000}
                    ),
                ),
                NodeConfig(
                    id="net_income",
                    name="Net Income",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="income * (1 - tax_rate)",
                ),
            ],
            edges=[
                DAGEdge(source="tax_rate", target="net_income"),
                DAGEdge(source="income", target="net_income"),
            ],
            metadata=GenerationMetadata(sample_size=100, seed=42),
        )

        df, _, _ = _generate_data(dag, 100, seed=42)

        # tax_rate: 1 unique value
        assert df["tax_rate"].nunique() == 1

        # income: many unique values
        assert df["income"].nunique() > 50

        # net_income calculated correctly
        tax_rate = df["tax_rate"].iloc[0]
        expected_net = df["income"] * (1 - tax_rate)
        assert np.allclose(df["net_income"], expected_net)

    def test_all_three_scopes_together(self):
        """Global, group, and row scopes in one DAG."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="year_factor",
                    name="Year Factor",
                    kind="stochastic",
                    dtype="float",
                    scope="global",
                    distribution=DistributionConfig(
                        type="uniform", params={"low": 0.95, "high": 1.05}
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
                        params={
                            "categories": ["A", "B", "C"],
                            "probs": [0.4, 0.35, 0.25],
                        },
                    ),
                ),
                NodeConfig(
                    id="region_base",
                    name="Region Base",
                    kind="stochastic",
                    dtype="float",
                    scope="group",
                    group_by="region",
                    distribution=DistributionConfig(
                        type="normal", params={"mu": 1000, "sigma": 100}
                    ),
                ),
                NodeConfig(
                    id="individual_value",
                    name="Individual Value",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 100, "sigma": 20}),
                ),
                NodeConfig(
                    id="final_value",
                    name="Final Value",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="(region_base + individual_value) * year_factor",
                ),
            ],
            edges=[
                DAGEdge(source="year_factor", target="final_value"),
                DAGEdge(source="region", target="region_base"),
                DAGEdge(source="region_base", target="final_value"),
                DAGEdge(source="individual_value", target="final_value"),
            ],
            metadata=GenerationMetadata(sample_size=300, seed=42),
        )

        df, _, _ = _generate_data(dag, 300, seed=42)

        # Verify scope behaviors
        assert df["year_factor"].nunique() == 1  # global
        assert df["region"].nunique() == 3  # categorical with 3 options
        assert df["region_base"].nunique() == 3  # group by region
        assert df["individual_value"].nunique() > 100  # row level variation

        # Verify formula calculation
        year_factor = df["year_factor"].iloc[0]
        expected = (df["region_base"] + df["individual_value"]) * year_factor
        assert np.allclose(df["final_value"], expected)


class TestScopeDeterminism:
    """Tests that scopes produce deterministic output."""

    def test_global_scope_determinism_across_runs(self):
        """Global scope produces identical value across runs with same seed."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="global_val",
                    name="Global",
                    kind="stochastic",
                    dtype="float",
                    scope="global",
                    distribution=DistributionConfig(type="normal", params={"mu": 100, "sigma": 10}),
                ),
            ],
            edges=[],
            metadata=GenerationMetadata(sample_size=50, seed=999),
        )

        results = []
        for _ in range(5):
            df, _, _ = _generate_data(dag, 50, seed=999)
            results.append(df["global_val"].iloc[0])

        # All runs should produce the same value
        assert all(v == results[0] for v in results)

    def test_mixed_scope_determinism(self):
        """Mixed scope DAG produces identical output with same seed."""
        dag = DAGDefinition(
            nodes=[
                NodeConfig(
                    id="global_mod",
                    name="Global Mod",
                    kind="stochastic",
                    dtype="float",
                    scope="global",
                    distribution=DistributionConfig(
                        type="uniform", params={"low": 1.0, "high": 2.0}
                    ),
                ),
                NodeConfig(
                    id="row_val",
                    name="Row Val",
                    kind="stochastic",
                    dtype="float",
                    scope="row",
                    distribution=DistributionConfig(type="normal", params={"mu": 50, "sigma": 5}),
                ),
                NodeConfig(
                    id="result",
                    name="Result",
                    kind="deterministic",
                    dtype="float",
                    scope="row",
                    formula="row_val * global_mod",
                ),
            ],
            edges=[
                DAGEdge(source="global_mod", target="result"),
                DAGEdge(source="row_val", target="result"),
            ],
            metadata=GenerationMetadata(sample_size=100, seed=42),
        )

        df1, _, _ = _generate_data(dag, 100, seed=42)
        df2, _, _ = _generate_data(dag, 100, seed=42)

        # Should be byte-identical
        assert df1.equals(df2)
