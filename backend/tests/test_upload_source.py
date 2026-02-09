from __future__ import annotations

import pytest

from app.services.upload_source import compute_upload_fingerprint, parse_upload


def test_compute_upload_fingerprint_is_deterministic():
    data = b"col\n1\n2\n"
    first = compute_upload_fingerprint(data)
    second = compute_upload_fingerprint(data)
    assert first == second


def test_parse_csv_upload_infers_schema():
    df, schema, fmt = parse_upload(file_bytes=b"a,b\n1,2\n3,4\n", filename="sample.csv")
    assert fmt == "csv"
    assert len(df) == 2
    assert [col["name"] for col in schema] == ["a", "b"]


def test_parse_upload_rejects_unsupported_format():
    with pytest.raises(ValueError, match="Unsupported file format"):
        parse_upload(file_bytes=b"{}", filename="sample.json")


def test_parse_upload_rejects_empty_dataset():
    with pytest.raises(ValueError, match="empty"):
        parse_upload(file_bytes=b"a,b\n", filename="sample.csv")
