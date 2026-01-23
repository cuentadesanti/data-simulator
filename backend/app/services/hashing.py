"""Canonical hashing utilities for pipeline reproducibility.

This module provides functions for creating deterministic hashes of pipeline
source configurations and transform steps, enabling reproducibility verification.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_dumps(obj: Any) -> str:
    """Serialize object to JSON with stable, deterministic ordering.
    
    Uses sorted keys and consistent separators to ensure the same object
    always produces the same JSON string regardless of dict ordering.
    
    Args:
        obj: Python object to serialize
        
    Returns:
        Canonical JSON string
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256_str(text: str) -> str:
    """Compute SHA-256 hash of a string.
    
    Args:
        text: String to hash
        
    Returns:
        Hexadecimal SHA-256 hash (64 characters)
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fingerprint_source(
    dag_version_id: str,
    seed: int,
    sample_size: int,
    sampler_version: str = "1.0",
    registry_version: str = "1.0",
) -> str:
    """Compute fingerprint for a simulation source configuration.
    
    The fingerprint uniquely identifies the source data based on:
    - DAG version ID (what nodes/edges define the generation)
    - Seed (controls random number generation)
    - Sample size (number of rows)
    - Sampler/registry versions (for future compatibility)
    
    Args:
        dag_version_id: ID of the DAG version used for generation
        seed: Random seed for reproducibility
        sample_size: Number of rows to generate
        sampler_version: Version of the sampler (for future compatibility)
        registry_version: Version of the distribution registry
        
    Returns:
        SHA-256 fingerprint hex string
    """
    source_spec = {
        "dag_version_id": dag_version_id,
        "seed": seed,
        "sample_size": sample_size,
        "sampler_version": sampler_version,
        "registry_version": registry_version,
    }
    return sha256_str(canonical_json_dumps(source_spec))


def hash_steps(steps: list[dict[str, Any]]) -> str:
    """Compute hash of transform steps for version comparison.
    
    Creates a deterministic hash of the step definitions that can be used
    to detect whether two pipeline versions have equivalent transforms.
    
    Args:
        steps: List of step dictionaries, each containing:
            - step_id: Unique identifier
            - type: Transform type (e.g., "formula", "log")
            - output_column: Name of derived column
            - params: Transform parameters
            - order: Execution order
            
    Returns:
        SHA-256 hash hex string
    """
    # Normalize steps for hashing - we hash only the semantic content,
    # not metadata like created_at or step_id (which are identity, not content)
    normalized_steps = []
    for step in steps:
        normalized_step = {
            "type": step.get("type"),
            "output_column": step.get("output_column"),
            "params": step.get("params", {}),
            "order": step.get("order"),
        }
        normalized_steps.append(normalized_step)
    
    return sha256_str(canonical_json_dumps(normalized_steps))


def hash_schema(schema: list[dict[str, Any]]) -> str:
    """Compute hash of a schema definition.
    
    Args:
        schema: List of {name, dtype} column definitions
        
    Returns:
        SHA-256 hash hex string
    """
    return sha256_str(canonical_json_dumps(schema))
