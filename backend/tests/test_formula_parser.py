"""Tests for formula parser and param resolver."""

from __future__ import annotations

import math

import pytest

from app.core.exceptions import (
    FormulaParseError,
    LookupKeyMissingError,
    UnknownVariableError,
)
from app.models.dag import LookupValue, MappingValue
from app.services.formula_parser import parse_formula, resolve_param_value


class TestParseFormula:
    """Test formula parsing and evaluation."""

    def test_simple_arithmetic(self):
        """Test simple arithmetic expressions."""
        assert parse_formula("2 + 2", {}, {}) == 4.0
        assert parse_formula("10 - 3", {}, {}) == 7.0
        assert parse_formula("5 * 4", {}, {}) == 20.0
        assert parse_formula("20 / 4", {}, {}) == 5.0
        assert parse_formula("7 // 2", {}, {}) == 3.0
        assert parse_formula("7 % 3", {}, {}) == 1.0
        assert parse_formula("2 ** 3", {}, {}) == 8.0

    def test_complex_arithmetic(self):
        """Test complex arithmetic expressions."""
        assert parse_formula("(2 + 3) * 4", {}, {}) == 20.0
        assert parse_formula("2 + 3 * 4", {}, {}) == 14.0  # Precedence
        assert parse_formula("100 / 10 / 2", {}, {}) == 5.0

    def test_variable_access(self):
        """Test accessing variables from row_data."""
        row_data = {"x": 10, "y": 5}
        assert parse_formula("x", row_data, {}) == 10.0
        assert parse_formula("y", row_data, {}) == 5.0
        assert parse_formula("x + y", row_data, {}) == 15.0
        assert parse_formula("x * y", row_data, {}) == 50.0

    def test_context_access(self):
        """Test accessing values from context."""
        context = {"RATE": 0.15, "BASE": 1000}
        assert parse_formula("RATE", {}, context) == 0.15
        assert parse_formula("BASE", {}, context) == 1000.0
        assert parse_formula("BASE * RATE", {}, context) == 150.0

    def test_row_data_takes_precedence(self):
        """Test that row_data takes precedence over context."""
        row_data = {"x": 100}
        context = {"x": 50}  # Same name, different value
        assert parse_formula("x", row_data, context) == 100.0

    def test_reserved_constants(self):
        """Test reserved constants like PI and E."""
        assert abs(parse_formula("PI", {}, {}) - math.pi) < 0.0001
        assert abs(parse_formula("E", {}, {}) - math.e) < 0.0001

    def test_lookup_syntax(self):
        """Test lookup syntax: base[zona]."""
        row_data = {"zona": "norte"}
        context = {"base": {"norte": 8000, "sur": 12000}}

        result = parse_formula("base[zona]", row_data, context)
        assert result == 8000.0

    def test_lookup_with_different_keys(self):
        """Test lookup with different category values."""
        context = {"salarios": {"junior": 3000, "senior": 6000, "lead": 10000}}

        assert parse_formula("salarios[nivel]", {"nivel": "junior"}, context) == 3000.0
        assert parse_formula("salarios[nivel]", {"nivel": "senior"}, context) == 6000.0
        assert parse_formula("salarios[nivel]", {"nivel": "lead"}, context) == 10000.0

    def test_lookup_in_expression(self):
        """Test lookup as part of larger expression."""
        row_data = {"zona": "sur", "factor": 1.5}
        context = {"base": {"norte": 8000, "sur": 12000}}

        result = parse_formula("base[zona] * factor", row_data, context)
        assert result == 18000.0

    def test_allowed_functions_basic_math(self):
        """Test basic math functions."""
        assert parse_formula("abs(-5)", {}, {}) == 5.0
        assert parse_formula("min(3, 7)", {}, {}) == 3.0
        assert parse_formula("max(3, 7)", {}, {}) == 7.0
        assert parse_formula("round(3.7)", {}, {}) == 4.0
        assert parse_formula("floor(3.7)", {}, {}) == 3.0
        assert parse_formula("ceil(3.2)", {}, {}) == 4.0

    def test_allowed_functions_advanced_math(self):
        """Test advanced math functions."""
        assert parse_formula("sqrt(16)", {}, {}) == 4.0
        assert abs(parse_formula("log(E)", {}, {}) - 1.0) < 0.0001
        assert abs(parse_formula("log10(100)", {}, {}) - 2.0) < 0.0001
        assert abs(parse_formula("exp(0)", {}, {}) - 1.0) < 0.0001
        assert parse_formula("pow(2, 3)", {}, {}) == 8.0

    def test_allowed_functions_trigonometry(self):
        """Test trigonometry functions."""
        assert abs(parse_formula("sin(0)", {}, {})) < 0.0001
        assert abs(parse_formula("cos(0)", {}, {}) - 1.0) < 0.0001
        assert abs(parse_formula("tan(0)", {}, {})) < 0.0001

    def test_custom_clamp_function(self):
        """Test custom clamp function."""
        assert parse_formula("clamp(5, 0, 10)", {}, {}) == 5.0
        assert parse_formula("clamp(-5, 0, 10)", {}, {}) == 0.0
        assert parse_formula("clamp(15, 0, 10)", {}, {}) == 10.0

    def test_custom_if_else_function(self):
        """Test custom if_else function."""
        assert parse_formula("if_else(1 > 0, 10, 20)", {}, {}) == 10.0
        assert parse_formula("if_else(1 < 0, 10, 20)", {}, {}) == 20.0

        row_data = {"x": 5}
        assert parse_formula("if_else(x > 3, 100, 0)", row_data, {}) == 100.0
        assert parse_formula("if_else(x < 3, 100, 0)", row_data, {}) == 0.0

    def test_comparison_operators(self):
        """Test comparison operators."""
        assert parse_formula("5 > 3", {}, {}) == 1.0  # True as float
        assert parse_formula("5 < 3", {}, {}) == 0.0  # False as float
        assert parse_formula("5 == 5", {}, {}) == 1.0
        assert parse_formula("5 != 3", {}, {}) == 1.0
        assert parse_formula("5 >= 5", {}, {}) == 1.0
        assert parse_formula("5 <= 5", {}, {}) == 1.0

    def test_logical_operators(self):
        """Test logical operators."""
        assert parse_formula("1 and 1", {}, {}) == 1.0
        assert parse_formula("1 and 0", {}, {}) == 0.0
        assert parse_formula("0 or 1", {}, {}) == 1.0
        assert parse_formula("not 0", {}, {}) == 1.0


class TestParseFormulaErrors:
    """Test formula parsing error handling."""

    def test_unknown_variable(self):
        """Test error for unknown variable."""
        with pytest.raises(UnknownVariableError):
            parse_formula("unknown_var", {}, {})

    def test_syntax_error(self):
        """Test error for syntax errors."""
        with pytest.raises(FormulaParseError):
            parse_formula("2 +", {}, {})

        with pytest.raises(FormulaParseError):
            parse_formula("(2 + 3", {}, {})

    def test_lookup_key_missing(self):
        """Test error for missing lookup key."""
        row_data = {"zona": "unknown_zone"}
        context = {"base": {"norte": 8000, "sur": 12000}}

        with pytest.raises(LookupKeyMissingError):
            parse_formula("base[zona]", row_data, context)

    def test_blocked_builtins(self):
        """Test that dangerous builtins are blocked."""
        blocked_calls = [
            "open('file.txt')",
            "__import__('os')",
            "eval('1+1')",
            "exec('print(1)')",
        ]

        for expr in blocked_calls:
            with pytest.raises((FormulaParseError, UnknownVariableError)):
                parse_formula(expr, {}, {})

    def test_division_by_zero(self):
        """Test division by zero handling."""
        # Direct division by zero
        with pytest.raises(FormulaParseError):
            parse_formula("1 / 0", {}, {})

        # Division by zero via variable
        with pytest.raises(FormulaParseError):
            parse_formula("x / y", {"x": 10, "y": 0}, {})

        # Integer division by zero
        with pytest.raises(FormulaParseError):
            parse_formula("10 // 0", {}, {})

        # Modulo by zero
        with pytest.raises(FormulaParseError):
            parse_formula("10 % 0", {}, {})


class TestResolveParamValue:
    """Test param value resolution."""

    def test_literal_int(self):
        """Test resolving literal int."""
        assert resolve_param_value(42, {}, {}) == 42.0

    def test_literal_float(self):
        """Test resolving literal float."""
        assert resolve_param_value(3.14, {}, {}) == 3.14

    def test_formula_string(self):
        """Test resolving formula string."""
        row_data = {"x": 10}
        result = resolve_param_value("x * 2", row_data, {})
        assert result == 20.0

    def test_lookup_value_pydantic(self):
        """Test resolving LookupValue (Pydantic model)."""
        lookup = LookupValue(lookup="salarios", key="nivel", default=0)
        row_data = {"nivel": "senior"}
        context = {"salarios": {"junior": 3000, "senior": 6000}}

        result = resolve_param_value(lookup, row_data, context)
        assert result == 6000.0

    def test_lookup_value_dict(self):
        """Test resolving LookupValue as dict (from JSON)."""
        lookup_dict = {"lookup": "salarios", "key": "nivel", "default": 0}
        row_data = {"nivel": "senior"}
        context = {"salarios": {"junior": 3000, "senior": 6000}}

        result = resolve_param_value(lookup_dict, row_data, context)
        assert result == 6000.0

    def test_lookup_value_default(self):
        """Test LookupValue default when key not found."""
        lookup_dict = {"lookup": "salarios", "key": "nivel", "default": 999}
        row_data = {"nivel": "unknown"}
        context = {"salarios": {"junior": 3000, "senior": 6000}}

        result = resolve_param_value(lookup_dict, row_data, context)
        assert result == 999.0

    def test_mapping_value_pydantic(self):
        """Test resolving MappingValue (Pydantic model)."""
        mapping = MappingValue(
            mapping={"A": 1.0, "B": 2.0, "C": 3.0},
            key="grade",
            default=0,
        )
        row_data = {"grade": "B"}

        result = resolve_param_value(mapping, row_data, {})
        assert result == 2.0

    def test_mapping_value_dict(self):
        """Test resolving MappingValue as dict (from JSON)."""
        mapping_dict = {
            "mapping": {"A": 1.0, "B": 2.0, "C": 3.0},
            "key": "grade",
            "default": 0,
        }
        row_data = {"grade": "B"}

        result = resolve_param_value(mapping_dict, row_data, {})
        assert result == 2.0

    def test_mapping_value_default(self):
        """Test MappingValue default when key not found."""
        mapping_dict = {
            "mapping": {"A": 1.0, "B": 2.0},
            "key": "grade",
            "default": -1,
        }
        row_data = {"grade": "X"}

        result = resolve_param_value(mapping_dict, row_data, {})
        assert result == -1.0


class TestResolveParamValueErrors:
    """Test param value resolution error handling."""

    def test_lookup_key_not_in_row_data(self):
        """Test error when lookup key not in row_data."""
        lookup_dict = {"lookup": "salarios", "key": "nivel", "default": 0}
        row_data = {}  # Missing 'nivel'
        context = {"salarios": {"junior": 3000}}

        with pytest.raises(UnknownVariableError):
            resolve_param_value(lookup_dict, row_data, context)

    def test_lookup_table_not_in_context(self):
        """Test error when lookup table not in context."""
        lookup_dict = {"lookup": "missing_table", "key": "nivel", "default": 0}
        row_data = {"nivel": "junior"}
        context = {}  # Missing 'missing_table'

        with pytest.raises(UnknownVariableError):
            resolve_param_value(lookup_dict, row_data, context)

    def test_lookup_table_not_dict(self):
        """Test error when lookup table is not a dict."""
        lookup_dict = {"lookup": "salarios", "key": "nivel", "default": 0}
        row_data = {"nivel": "junior"}
        context = {"salarios": 12345}  # Not a dict!

        with pytest.raises(FormulaParseError):
            resolve_param_value(lookup_dict, row_data, context)

    def test_mapping_key_not_in_row_data(self):
        """Test error when mapping key not in row_data."""
        mapping_dict = {"mapping": {"A": 1.0}, "key": "grade", "default": 0}
        row_data = {}  # Missing 'grade'

        with pytest.raises(UnknownVariableError):
            resolve_param_value(mapping_dict, row_data, {})


class TestComplexFormulas:
    """Test complex real-world formula scenarios."""

    def test_salary_calculation(self):
        """Test salary with zone lookup and tax formula."""
        row_data = {"zona": "norte", "antiguedad": 5}
        context = {
            "base_por_zona": {"norte": 8000, "sur": 12000, "centro": 10000},
            "TAX_RATE": 0.16,
        }

        # Base salary from lookup
        base = parse_formula("base_por_zona[zona]", row_data, context)
        assert base == 8000.0

        # Net salary after tax
        net = parse_formula("base_por_zona[zona] * (1 - TAX_RATE)", row_data, context)
        assert net == 6720.0

        # Bonus based on seniority
        bonus = parse_formula("base_por_zona[zona] * 0.05 * antiguedad", row_data, context)
        assert bonus == 2000.0

    def test_clamped_probability(self):
        """Test clamped probability calculation."""
        row_data = {"score": 150}

        # Score clamped to [0, 100] then converted to probability
        prob = parse_formula("clamp(score, 0, 100) / 100", row_data, {})
        assert prob == 1.0

    def test_conditional_bonus(self):
        """Test conditional bonus calculation."""
        context = {"BONUS_THRESHOLD": 50000, "BONUS_RATE": 0.1}

        # Above threshold
        row_data = {"salario": 60000}
        bonus = parse_formula(
            "if_else(salario > BONUS_THRESHOLD, salario * BONUS_RATE, 0)",
            row_data,
            context,
        )
        assert bonus == 6000.0

        # Below threshold
        row_data = {"salario": 40000}
        bonus = parse_formula(
            "if_else(salario > BONUS_THRESHOLD, salario * BONUS_RATE, 0)",
            row_data,
            context,
        )
        assert bonus == 0.0
