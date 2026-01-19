"""Formula parser and parameter resolver for data generation.

This module provides safe formula evaluation using simpleeval, supporting:
- Mathematical expressions with allowed functions and operators
- Variable access from row data and context
- Lookup syntax for context tables: base[zona]
- Parameter resolution for different value types (literal, formula, lookup, mapping)
- Canonical node reference format: node("id") -> var_name
"""

from __future__ import annotations

import math
import re
from typing import Any

from simpleeval import EvalWithCompoundTypes, NameNotDefined

from app.core.config import RESERVED_CONTEXT
from app.core.exceptions import (
    FormulaParseError,
    LookupKeyMissingError,
    UnknownVariableError,
)
from app.models.dag import LookupValue, MappingValue


# =============================================================================
# Custom Functions
# =============================================================================


def clamp(x: float, min_val: float, max_val: float) -> float:
    """Clamp value x between min_val and max_val.

    Args:
        x: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Clamped value
    """
    return max(min_val, min(max_val, x))


def if_else(condition: bool, then_val: Any, else_val: Any) -> Any:
    """Conditional expression: return then_val if condition else else_val.

    Args:
        condition: Boolean condition
        then_val: Value to return if condition is True
        else_val: Value to return if condition is False

    Returns:
        then_val or else_val based on condition
    """
    return then_val if condition else else_val


# =============================================================================
# Allowed Functions and Operators
# =============================================================================

# Allowed functions available in formulas
ALLOWED_FUNCTIONS = {
    # Basic math
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    # Advanced math
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pow": pow,
    # Trigonometry
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    # Custom functions
    "clamp": clamp,
    "if_else": if_else,
}

# Allowed operators (all arithmetic, comparison, logical)
ALLOWED_OPERATORS = {
    # Arithmetic
    "+",
    "-",
    "*",
    "/",
    "//",
    "%",
    "**",
    # Comparison
    "==",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    # Logical
    "and",
    "or",
    "not",
    # Bitwise
    "&",
    "|",
    "^",
    "~",
    "<<",
    ">>",
}


# =============================================================================
# Canonical Format Processing
# =============================================================================

# Regex to match node("id") canonical format
CANONICAL_NODE_PATTERN = re.compile(r'node\("([^"]+)"\)')


def expand_canonical_references(
    formula: str,
    id_to_var_name: dict[str, str] | None = None,
) -> str:
    """Expand canonical node("id") references to var_names.

    The frontend stores formulas in canonical format using node IDs for stability.
    This function converts them to var_names for evaluation.

    Args:
        formula: Formula potentially containing node("id") references
        id_to_var_name: Mapping from node ID to var_name

    Returns:
        Formula with node("id") expanded to var_names

    Example:
        Input:  'node("node_123") * 2 + node("node_456")'
        Output: 'base_salary * 2 + tax_rate'
    """
    if not formula or not id_to_var_name:
        return formula

    def replacer(match: re.Match) -> str:
        node_id = match.group(1)
        # Look up var_name, fall back to node_id if not found
        return id_to_var_name.get(node_id, node_id)

    return CANONICAL_NODE_PATTERN.sub(replacer, formula)


# =============================================================================
# Custom Name Resolver for Lookup Syntax
# =============================================================================


class NameResolver:
    """Custom name resolver that supports lookup syntax: base[zona].

    This class intercepts variable access and enables:
    - Direct variable access: salario_padres -> row_data["salario_padres"]
    - Lookup syntax: base[zona] -> context["base"][row_data["zona"]]

    How it works when simpleeval evaluates base[zona]:
    1. Resolves 'base' -> returns LookupProxy(context["base"])
    2. Evaluates 'zona' -> returns row_data["zona"] (e.g., "norte")
    3. Calls LookupProxy["norte"] -> returns context["base"]["norte"]
    """

    def __init__(self, row_data: dict[str, Any], context: dict[str, Any]):
        """Initialize name resolver.

        Args:
            row_data: Current row data (generated node values)
            context: Global context (lookup tables, constants)
        """
        self.row_data = row_data
        self.context = context
        # Merge context constants (like PI, E) with context tables
        self.all_names = {**context, **RESERVED_CONTEXT}

    def __getitem__(self, name: str) -> Any:
        """Resolve a name to its value.

        Args:
            name: Variable name to resolve

        Returns:
            Value from row_data, context, or LookupProxy for context tables

        Raises:
            NameNotDefined: If name not found in row_data or context
        """
        # First check row_data (generated values have precedence)
        if name in self.row_data:
            return self.row_data[name]

        # Then check context (includes RESERVED_CONTEXT constants)
        if name in self.all_names:
            value = self.all_names[name]
            # If it's a dict, wrap it in a LookupProxy to enable base[zona] syntax
            if isinstance(value, dict):
                return LookupProxy(value, name)
            return value

        # Name not found - collect available names for error message
        available = sorted(list(self.row_data.keys()) + list(self.all_names.keys()))
        raise NameNotDefined(name, self)

    def __contains__(self, name: str) -> bool:
        """Check if name exists in row_data or context."""
        return name in self.row_data or name in self.all_names


class LookupProxy:
    """Proxy object that enables lookup syntax: base[zona].

    When simpleeval evaluates base[zona], it:
    1. First evaluates 'zona' in the names dict to get 'norte'
    2. Then calls LookupProxy.__getitem__('norte')
    3. We look up 'norte' in the context table

    So the key we receive is already the evaluated value, not the variable name.
    """

    def __init__(self, lookup_table: dict[str, Any], table_name: str):
        """Initialize lookup proxy.

        Args:
            lookup_table: The context table to look up values in
            table_name: Name of the lookup table (for error messages)
        """
        self.lookup_table = lookup_table
        self.table_name = table_name

    def __getitem__(self, key: Any) -> Any:
        """Resolve lookup: base[zona] -> context["base"][evaluated_zona].

        simpleeval already evaluates the key expression (zona -> 'norte'),
        so we just need to look it up in the table.

        Args:
            key: Already-evaluated key value (e.g., 'norte', not 'zona')

        Returns:
            Value from lookup table

        Raises:
            LookupKeyMissingError: If key not found in lookup table
        """
        # Convert key to string for lookup
        key_str = str(key)

        # Lookup the key in the context table
        if key_str not in self.lookup_table:
            available = sorted(self.lookup_table.keys())
            raise LookupKeyMissingError(key_str, self.table_name, available)

        return self.lookup_table[key_str]


# =============================================================================
# Parameter Resolution
# =============================================================================


def resolve_param_value(
    param_value: int | float | str | LookupValue | MappingValue,
    row_data: dict[str, Any],
    context: dict[str, Any],
    id_to_var_name: dict[str, str] | None = None,
) -> float:
    """Resolve a parameter value to a float.

    This function handles all parameter types:
    - int/float: Return directly
    - str (formula): Parse and evaluate
    - LookupValue: Lookup context[lookup][row[key]] with default
    - MappingValue: Lookup mapping[row[key]] with default

    Args:
        param_value: Parameter value to resolve
        row_data: Current row data (generated node values)
        context: Global context (lookup tables, constants)
        id_to_var_name: Optional mapping from node ID to var_name for canonical expansion

    Returns:
        Resolved float value

    Raises:
        FormulaParseError: If formula parsing fails
        UnknownVariableError: If variable not found
        LookupKeyMissingError: If lookup key not found
    """
    # Case 1: Literal number
    if isinstance(param_value, (int, float)):
        return float(param_value)

    # Case 2: Formula string
    if isinstance(param_value, str):
        return parse_formula(param_value, row_data, context, id_to_var_name)

    # Case 3: LookupValue - lookup context[lookup][row[key]]
    # Handle both Pydantic model and dict-style
    is_lookup = isinstance(param_value, LookupValue) or (
        isinstance(param_value, dict) and "lookup" in param_value and "key" in param_value
    )
    if is_lookup:
        # Extract fields (works for both Pydantic model and dict)
        if isinstance(param_value, dict):
            lookup_name = param_value["lookup"]
            key_name = param_value["key"]
            default = param_value.get("default", 0)
        else:
            lookup_name = param_value.lookup
            key_name = param_value.key
            default = param_value.default

        # Get the key value from row_data
        if key_name not in row_data:
            available = sorted(row_data.keys())
            raise UnknownVariableError(key_name, available)

        key_value = str(row_data[key_name])

        # Get the lookup table from context
        if lookup_name not in context:
            available = sorted(context.keys())
            raise UnknownVariableError(lookup_name, available)

        lookup_table = context[lookup_name]
        if not isinstance(lookup_table, dict):
            raise FormulaParseError(
                formula=f"lookup:{lookup_name}",
                error_msg=f"Context['{lookup_name}'] is not a lookup table (dict)",
            )

        # Lookup with default
        return float(lookup_table.get(key_value, default))

    # Case 4: MappingValue - lookup mapping[row[key]]
    # Handle both Pydantic model and dict-style
    is_mapping = isinstance(param_value, MappingValue) or (
        isinstance(param_value, dict) and "mapping" in param_value and "key" in param_value
    )
    if is_mapping:
        # Extract fields (works for both Pydantic model and dict)
        if isinstance(param_value, dict):
            mapping = param_value["mapping"]
            key_name = param_value["key"]
            default = param_value.get("default", 0)
        else:
            mapping = param_value.mapping
            key_name = param_value.key
            default = param_value.default

        # Get the key value from row_data
        if key_name not in row_data:
            available = sorted(row_data.keys())
            raise UnknownVariableError(key_name, available)

        key_value = str(row_data[key_name])

        # Lookup with default
        return float(mapping.get(key_value, default))

    # Should never reach here due to type hints, but handle gracefully
    raise FormulaParseError(
        formula=str(param_value), error_msg=f"Unknown parameter type: {type(param_value)}"
    )


# =============================================================================
# Formula Parsing
# =============================================================================


def parse_formula(
    formula: str,
    row_data: dict[str, Any],
    context: dict[str, Any],
    id_to_var_name: dict[str, str] | None = None,
) -> float:
    """Parse and evaluate a formula expression.

    This function uses simpleeval for safe expression evaluation with:
    - Allowed functions (math, custom functions)
    - Variable access from row_data and context
    - Lookup syntax support: base[zona]
    - Canonical node reference expansion: node("id") -> var_name

    Args:
        formula: Formula expression to evaluate (may contain canonical node("id") refs)
        row_data: Current row data (generated node values, keyed by var_name)
        context: Global context (lookup tables, constants)
        id_to_var_name: Optional mapping from node ID to var_name for canonical expansion

    Returns:
        Evaluated float value

    Raises:
        FormulaParseError: If formula has syntax errors
        UnknownVariableError: If variable not found
        LookupKeyMissingError: If lookup key not found
    """
    try:
        # Step 1: Expand canonical node("id") references to var_names
        expanded_formula = expand_canonical_references(formula, id_to_var_name)

        # Create evaluator with compound types (supports indexing: base[zona])
        evaluator = EvalWithCompoundTypes()

        # Set allowed functions
        evaluator.functions = ALLOWED_FUNCTIONS

        # Set names using custom resolver for lookup syntax
        evaluator.names = NameResolver(row_data, context)

        # Evaluate the formula
        result = evaluator.eval(expanded_formula)

        # Return result as-is (allow strings, bools, etc.)
        return result

    except NameNotDefined as e:
        # Variable not found in row_data or context
        name_resolver = evaluator.names
        if isinstance(name_resolver, NameResolver):
            available = sorted(
                list(name_resolver.row_data.keys()) + list(name_resolver.all_names.keys())
            )
        else:
            available = []
        raise UnknownVariableError(str(e.name), available)

    except (LookupKeyMissingError, UnknownVariableError):
        # Re-raise our custom errors as-is
        raise

    except (SyntaxError, ValueError, TypeError, AttributeError, KeyError) as e:
        # Syntax or evaluation error
        raise FormulaParseError(
            formula=formula,
            error_msg=str(e),
        )

    except Exception as e:
        # Catch-all for unexpected errors
        raise FormulaParseError(
            formula=formula,
            error_msg=f"Unexpected error: {type(e).__name__}: {e}",
        )
