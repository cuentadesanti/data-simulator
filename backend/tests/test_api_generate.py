"""
Tests for /api/dag/generate endpoint.

These tests verify that the endpoint returns actual data, not just metadata.
This catches the bug where /generate returned only GenerationResult metadata
instead of streaming the actual CSV/JSON/Parquet data.
"""

import csv
import io
import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# Test DAG fixture
TEST_DAG = {
    "nodes": [
        {
            "id": "x",
            "name": "X",
            "kind": "stochastic",
            "dtype": "float",
            "scope": "row",
            "distribution": {"type": "normal", "params": {"mu": 100, "sigma": 10}},
        },
        {
            "id": "y",
            "name": "Y",
            "kind": "deterministic",
            "dtype": "float",
            "scope": "row",
            "formula": "x * 2",
        },
    ],
    "edges": [{"source": "x", "target": "y"}],
    "metadata": {"sample_size": 50, "seed": 42},
}


class TestGenerateEndpointReturnsData:
    """Tests that /generate returns actual data, not just metadata."""

    def test_generate_csv_returns_csv_content(self):
        """
        BUG TEST: /generate should return actual CSV data, not just metadata.

        Previously, the endpoint returned:
            {"status": "completed", "rows": 50, "columns": ["x", "y"], ...}

        It should return actual CSV content:
            x,y
            98.123,196.246
            ...
        """
        response = client.post("/api/dag/generate?format=csv", json=TEST_DAG)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

        # Parse the CSV content
        content = response.text
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

        # Should have actual data rows
        assert len(rows) == 50, f"Expected 50 rows of data, got {len(rows)}"

        # Should have correct columns
        assert "x" in rows[0], "CSV should have column 'x'"
        assert "y" in rows[0], "CSV should have column 'y'"

        # Values should be numeric, not metadata
        x_val = float(rows[0]["x"])
        y_val = float(rows[0]["y"])
        assert 50 < x_val < 150, f"x value {x_val} seems wrong for Normal(100, 10)"
        assert abs(y_val - x_val * 2) < 0.001, "y should be x * 2"

    def test_generate_csv_not_metadata_json(self):
        """
        BUG TEST: Ensure response is not JSON metadata.

        If this test fails, the endpoint is returning metadata instead of data.
        """
        response = client.post("/api/dag/generate?format=csv", json=TEST_DAG)

        # Should NOT be parseable as the old metadata format
        try:
            data = json.loads(response.text)
            # If we get here, it's JSON. Check it's not the metadata format
            assert "status" not in data, "Response should not be metadata JSON"
            assert "job_id" not in data, "Response should not be metadata JSON"
            assert "rows" not in data or isinstance(data.get("data"), list), (
                "Response should not be metadata JSON"
            )
        except json.JSONDecodeError:
            # Good - CSV is not valid JSON
            pass

    def test_generate_json_returns_data_array(self):
        """
        BUG TEST: /generate?format=json should return data array, not just metadata.
        """
        response = client.post("/api/dag/generate?format=json", json=TEST_DAG)

        assert response.status_code == 200
        data = response.json()

        # Should have actual data array
        assert "data" in data, "Response should contain 'data' field"
        assert isinstance(data["data"], list), "'data' should be a list"
        assert len(data["data"]) == 50, f"Expected 50 rows, got {len(data['data'])}"

        # Each row should have actual values
        first_row = data["data"][0]
        assert "x" in first_row, "Row should have 'x' column"
        assert "y" in first_row, "Row should have 'y' column"
        assert isinstance(first_row["x"], (int, float)), "x should be numeric"

    def test_generate_json_includes_metadata(self):
        """JSON format should include both data and metadata."""
        response = client.post("/api/dag/generate?format=json", json=TEST_DAG)
        data = response.json()

        assert "metadata" in data, "Response should include metadata"
        assert data["metadata"]["rows"] == 50
        assert data["metadata"]["seed"] == 42
        assert "x" in data["metadata"]["columns"]
        assert "y" in data["metadata"]["columns"]

    def test_generate_parquet_returns_binary(self):
        """
        BUG TEST: /generate?format=parquet should return binary Parquet data.
        """
        response = client.post("/api/dag/generate?format=parquet", json=TEST_DAG)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"

        # Parquet files start with "PAR1" magic bytes
        content = response.content
        assert content[:4] == b"PAR1", "Response should be valid Parquet (starts with PAR1)"

        # Should be substantial size (not just metadata JSON)
        assert len(content) > 100, "Parquet file should have actual data"

    def test_generate_parquet_is_readable(self):
        """Parquet output should be readable by pandas."""
        from io import BytesIO

        import pandas as pd

        response = client.post("/api/dag/generate?format=parquet", json=TEST_DAG)

        df = pd.read_parquet(BytesIO(response.content))

        assert len(df) == 50, f"Expected 50 rows, got {len(df)}"
        assert "x" in df.columns
        assert "y" in df.columns

    def test_generate_csv_headers_contain_metadata(self):
        """CSV response should include metadata in headers."""
        response = client.post("/api/dag/generate?format=csv", json=TEST_DAG)

        assert "X-Seed" in response.headers, "Should have X-Seed header"
        assert "X-Rows" in response.headers, "Should have X-Rows header"
        assert "X-Columns" in response.headers, "Should have X-Columns header"

        assert response.headers["X-Seed"] == "42"
        assert response.headers["X-Rows"] == "50"
        assert "x" in response.headers["X-Columns"]
        assert "y" in response.headers["X-Columns"]

    def test_generate_csv_content_disposition(self):
        """CSV response should have Content-Disposition for download."""
        response = client.post("/api/dag/generate?format=csv", json=TEST_DAG)

        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["Content-Disposition"]
        assert "dataset_42.csv" in response.headers["Content-Disposition"]


class TestGenerateEndpointDeterminism:
    """Tests that /generate produces deterministic output."""

    def test_same_seed_produces_identical_csv(self):
        """Same seed should produce byte-identical CSV output."""
        response1 = client.post("/api/dag/generate?format=csv", json=TEST_DAG)
        response2 = client.post("/api/dag/generate?format=csv", json=TEST_DAG)

        assert response1.text == response2.text, "Same seed should produce identical CSV"

    def test_different_seeds_produce_different_csv(self):
        """Different seeds should produce different output."""
        dag1 = {**TEST_DAG, "metadata": {"sample_size": 50, "seed": 42}}
        dag2 = {**TEST_DAG, "metadata": {"sample_size": 50, "seed": 123}}

        response1 = client.post("/api/dag/generate?format=csv", json=dag1)
        response2 = client.post("/api/dag/generate?format=csv", json=dag2)

        assert response1.text != response2.text, "Different seeds should produce different CSV"


class TestGenerateEndpointEdgeCases:
    """Edge case tests for /generate endpoint."""

    def test_generate_single_row(self):
        """Should handle generating just 1 row."""
        dag = {**TEST_DAG, "metadata": {"sample_size": 1, "seed": 42}}
        response = client.post("/api/dag/generate?format=csv", json=dag)

        reader = csv.DictReader(io.StringIO(response.text))
        rows = list(reader)

        assert len(rows) == 1

    def test_generate_large_dataset(self):
        """Should handle larger datasets."""
        dag = {**TEST_DAG, "metadata": {"sample_size": 10000, "seed": 42}}
        response = client.post("/api/dag/generate?format=csv", json=dag)

        # Count lines (header + 10000 data rows)
        lines = response.text.strip().split("\n")
        assert len(lines) == 10001, f"Expected 10001 lines (header + 10000 rows), got {len(lines)}"

    def test_generate_with_categorical_column(self):
        """Should handle categorical columns correctly."""
        dag = {
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
                },
            ],
            "edges": [],
            "metadata": {"sample_size": 100, "seed": 42},
        }

        response = client.post("/api/dag/generate?format=csv", json=dag)
        reader = csv.DictReader(io.StringIO(response.text))
        rows = list(reader)

        # All values should be one of the categories
        categories = {row["category"] for row in rows}
        assert categories <= {"A", "B", "C"}, f"Unexpected categories: {categories}"

    def test_generate_invalid_dag_returns_error(self):
        """Invalid DAG should return error, not crash."""
        invalid_dag = {
            "nodes": [
                {"id": "a", "name": "A", "kind": "stochastic", "scope": "row"},
                # Missing distribution for stochastic node
            ],
            "edges": [],
            "metadata": {"sample_size": 10},
        }

        response = client.post("/api/dag/generate?format=csv", json=invalid_dag)

        # Should return error status, not 500
        assert response.status_code in [400, 422], (
            f"Invalid DAG should return 4xx, got {response.status_code}"
        )
