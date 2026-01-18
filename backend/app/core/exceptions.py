"""Custom exceptions for the data simulator."""

from __future__ import annotations

from typing import Any


class DataSimulatorError(Exception):
    """Base exception for all data simulator errors."""

    code: str = "UNKNOWN_ERROR"
    phase: str = "unknown"

    def __init__(
        self,
        message: str,
        node_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.node_id = node_id
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert to error response dict."""
        error = {
            "code": self.code,
            "message": self.message,
            "phase": self.phase,
        }
        if self.node_id:
            error["node_id"] = self.node_id
        if self.details:
            error["details"] = self.details
        return {"error": error}


class ValidationError(DataSimulatorError):
    """DAG validation errors (cycles, params, etc.)."""

    code = "VALIDATION_ERROR"
    phase = "validate"


class CycleDetectedError(ValidationError):
    """Cycle detected in DAG."""

    code = "CYCLE_DETECTED"

    def __init__(self, cycle_nodes: list[str]):
        super().__init__(
            message=f"Cycle detected in DAG involving nodes: {cycle_nodes}",
            details={"cycle_nodes": cycle_nodes},
        )


class ReservedKeywordError(ValidationError):
    """Node ID or context key uses reserved keyword."""

    code = "RESERVED_KEYWORD"

    def __init__(self, keyword: str, keyword_type: str):
        super().__init__(
            message=f"'{keyword}' is a reserved {keyword_type} and cannot be used",
            details={"keyword": keyword, "type": keyword_type},
        )


class InvalidNodeError(ValidationError):
    """Node configuration is invalid."""

    code = "INVALID_NODE"

    def __init__(self, node_id: str, reason: str):
        super().__init__(
            message=f"Invalid node '{node_id}': {reason}",
            node_id=node_id,
            details={"reason": reason},
        )


class MissingParentError(ValidationError):
    """Node references a parent that doesn't exist."""

    code = "MISSING_PARENT"

    def __init__(self, node_id: str, parent_id: str):
        super().__init__(
            message=f"Node '{node_id}' references non-existent parent '{parent_id}'",
            node_id=node_id,
            details={"missing_parent": parent_id},
        )


class ResolveError(DataSimulatorError):
    """Error resolving ParamValue."""

    code = "RESOLVE_ERROR"
    phase = "resolve"


class FormulaParseError(ResolveError):
    """Error parsing formula expression."""

    code = "FORMULA_PARSE_ERROR"

    def __init__(self, formula: str, error_msg: str, position: int | None = None):
        details: dict[str, Any] = {"formula": formula, "error": error_msg}
        if position is not None:
            details["position"] = position
        super().__init__(
            message=f"Syntax error in formula: {error_msg}",
            details=details,
        )


class UnknownVariableError(ResolveError):
    """Variable not found in row or context."""

    code = "UNKNOWN_VARIABLE"

    def __init__(self, variable: str, available_vars: list[str]):
        super().__init__(
            message=f"Variable '{variable}' not found",
            details={"variable": variable, "available_vars": available_vars},
        )


class LookupKeyMissingError(ResolveError):
    """Lookup key not found in context table."""

    code = "LOOKUP_KEY_MISSING"

    def __init__(self, key_value: str, lookup_table: str, available_keys: list[str]):
        super().__init__(
            message=f"Key '{key_value}' not found in context['{lookup_table}']",
            details={
                "key_value": key_value,
                "lookup_table": lookup_table,
                "available_keys": available_keys,
            },
        )


class SampleError(DataSimulatorError):
    """Error during sampling."""

    code = "SAMPLE_ERROR"
    phase = "sample"


class DistributionError(SampleError):
    """Error with distribution configuration or sampling."""

    code = "DISTRIBUTION_ERROR"

    def __init__(self, distribution_type: str, error_msg: str, node_id: str | None = None):
        super().__init__(
            message=f"Distribution '{distribution_type}' error: {error_msg}",
            node_id=node_id,
            details={"distribution_type": distribution_type, "error": error_msg},
        )


class WriteError(DataSimulatorError):
    """Error writing output."""

    code = "WRITE_ERROR"
    phase = "write"


class TimeoutError(DataSimulatorError):
    """Generation exceeded time limit."""

    code = "TIMEOUT_ERROR"
    phase = "any"


class LimitError(ValidationError):
    """Exceeded configured limits."""

    code = "LIMIT_ERROR"

    def __init__(self, limit_name: str, value: int, max_value: int):
        super().__init__(
            message=f"Exceeded {limit_name} limit: {value} > {max_value}",
            details={"limit": limit_name, "value": value, "max": max_value},
        )
