"""Tests for context_meta roundtrip on DAGDefinition.

Verifies that:
1. DAGDefinition without context_meta defaults to {}
2. DAGDefinition with populated context_meta roundtrips correctly
3. model_dump always includes context_meta
"""

from __future__ import annotations

from app.models.dag import ContextVariableMeta, DAGDefinition


def _minimal_dag(**overrides) -> dict:
    """Build a minimal valid DAG dict for testing."""
    base = {
        "nodes": [
            {
                "id": "node_a",
                "name": "Node A",
                "kind": "stochastic",
                "scope": "row",
                "distribution": {"type": "normal", "params": {"mu": 0, "sigma": 1}},
            }
        ],
        "edges": [],
        "context": {},
        "metadata": {"sample_size": 100},
    }
    base.update(overrides)
    return base


class TestContextMetaRoundtrip:
    """Tests for context_meta field on DAGDefinition."""

    def test_missing_context_meta_defaults_to_empty(self):
        """Legacy DAGs without context_meta should default to {}."""
        dag_dict = _minimal_dag()
        assert "context_meta" not in dag_dict

        dag = DAGDefinition.model_validate(dag_dict)
        assert dag.context_meta == {}

    def test_empty_context_meta_roundtrips(self):
        """Empty context_meta should be present in model_dump output."""
        dag = DAGDefinition.model_validate(_minimal_dag())
        dumped = dag.model_dump(mode="json")

        assert "context_meta" in dumped
        assert dumped["context_meta"] == {}

    def test_populated_context_meta_roundtrips(self):
        """Populated context_meta should survive validate -> dump."""
        meta = {
            "tax_rate": {"type": "number"},
            "is_active": {"type": "boolean"},
            "salary_table": {"type": "dict"},
            "weights": {"type": "array"},
            "weird_thing": {"type": "unsupported"},
        }
        dag_dict = _minimal_dag(context_meta=meta)
        dag = DAGDefinition.model_validate(dag_dict)

        assert len(dag.context_meta) == 5
        assert dag.context_meta["tax_rate"].type == "number"
        assert dag.context_meta["is_active"].type == "boolean"
        assert dag.context_meta["salary_table"].type == "dict"
        assert dag.context_meta["weights"].type == "array"
        assert dag.context_meta["weird_thing"].type == "unsupported"

        # Roundtrip via dump
        dumped = dag.model_dump(mode="json")
        assert dumped["context_meta"] == meta

    def test_context_meta_model(self):
        """ContextVariableMeta validates type field."""
        m = ContextVariableMeta(type="number")
        assert m.type == "number"

        m2 = ContextVariableMeta(type="unsupported")
        assert m2.type == "unsupported"
