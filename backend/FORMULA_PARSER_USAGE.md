# Formula Parser Usage Guide

## Overview

The `formula_parser.py` module provides safe formula evaluation and parameter resolution for the data simulator. It uses the `simpleeval` library for secure expression evaluation.

## Key Features

1. **Safe Expression Evaluation**: Only allowed functions and operators
2. **Variable Access**: Access row data and context values
3. **Lookup Syntax**: Support for `base[zona]` style lookups
4. **Multiple Parameter Types**: Literals, formulas, lookup values, and mappings

## Allowed Functions

### Basic Math
- `abs`, `min`, `max`, `round`, `floor`, `ceil`

### Advanced Math
- `sqrt`, `log`, `log10`, `exp`, `pow`

### Trigonometry
- `sin`, `cos`, `tan`

### Custom Functions
- `clamp(x, min, max)` - Clamp value between min and max
- `if_else(condition, then_val, else_val)` - Conditional expression

## Allowed Operators

- **Arithmetic**: `+`, `-`, `*`, `/`, `//`, `%`, `**`
- **Comparison**: `==`, `!=`, `<`, `<=`, `>`, `>=`
- **Logical**: `and`, `or`, `not`
- **Bitwise**: `&`, `|`, `^`, `~`, `<<`, `>>`

## Reserved Constants

- `PI` - π (3.14159...)
- `E` - Euler's number (2.71828...)
- `TRUE` - Boolean true
- `FALSE` - Boolean false

## Usage Examples

### 1. Simple Formulas

```python
from app.services.formula_parser import parse_formula

row_data = {'x': 10, 'y': 5}
context = {}

# Basic arithmetic
result = parse_formula('x + y', row_data, context)
# Result: 15.0

# Using functions
result = parse_formula('sqrt(x) + abs(y)', {'x': 16, 'y': -3}, {})
# Result: 7.0

# Using constants
result = parse_formula('PI * 2', {}, {})
# Result: 6.283...
```

### 2. Lookup Syntax

```python
row_data = {'zona': 'norte', 'salario_padres': 50000}
context = {
    'base_salario': {
        'norte': 8000,
        'sur': 12000
    }
}

# Simple lookup
result = parse_formula('base_salario[zona]', row_data, context)
# Result: 8000.0 (looks up context['base_salario']['norte'])

# Complex formula with lookup
result = parse_formula('base_salario[zona] + salario_padres * 0.1', row_data, context)
# Result: 13000.0
```

### 3. Multiple Lookups

```python
row_data = {'zona': 'norte', 'nivel': 'senior'}
context = {
    'base_salario': {'norte': 8000, 'sur': 12000},
    'multiplicador': {'junior': 1.0, 'senior': 1.5}
}

result = parse_formula('base_salario[zona] * multiplicador[nivel]', row_data, context)
# Result: 12000.0 (8000 * 1.5)
```

### 4. Parameter Resolution

```python
from app.services.formula_parser import resolve_param_value
from app.models.dag import LookupValue, MappingValue

# Literal values
resolve_param_value(42, {}, {})  # Returns: 42.0
resolve_param_value(3.14, {}, {})  # Returns: 3.14

# Formula string
resolve_param_value('x + y', {'x': 10, 'y': 5}, {})  # Returns: 15.0

# LookupValue
lookup = LookupValue(lookup='base_salario', key='zona', default=10000)
row = {'zona': 'norte'}
context = {'base_salario': {'norte': 8000, 'sur': 12000}}
resolve_param_value(lookup, row, context)  # Returns: 8000.0

# MappingValue
mapping = MappingValue(mapping={'A': 100, 'B': 200}, key='grade', default=0)
row = {'grade': 'A'}
resolve_param_value(mapping, row, {})  # Returns: 100.0
```

### 5. Conditional Logic

```python
# Using if_else for conditional expressions
row_data = {'edad': 20, 'salario': 30000}

# Age-based logic
result = parse_formula('if_else(edad >= 18, salario, 0)', row_data, {})
# Result: 30000.0 (edad is 20, which is >= 18)

# Nested conditions
formula = 'if_else(edad < 18, 0, if_else(edad < 65, salario, salario * 0.8))'
result = parse_formula(formula, row_data, {})
# Result: 30000.0
```

### 6. Clamping Values

```python
# Clamp values within a range
row_data = {'score': 150}

result = parse_formula('clamp(score, 0, 100)', row_data, {})
# Result: 100.0 (clamped to maximum)

result = parse_formula('clamp(score, 50, 100)', {'score': 30}, {})
# Result: 50.0 (clamped to minimum)
```

## How Lookup Syntax Works

When simpleeval evaluates `base_salario[zona]`:

1. **Resolve 'base_salario'**: The NameResolver returns a LookupProxy wrapping `context['base_salario']`
2. **Evaluate 'zona'**: Simpleeval evaluates 'zona' to get `row_data['zona']` (e.g., "norte")
3. **Index operation**: Simpleeval calls `LookupProxy['norte']`, which returns `context['base_salario']['norte']`

This design enables clean, readable formulas while maintaining type safety.

## Error Handling

The formula parser raises specific exceptions:

- **FormulaParseError**: Syntax errors or invalid expressions
- **UnknownVariableError**: Variable not found in row_data or context
- **LookupKeyMissingError**: Key not found in lookup table

Example:
```python
try:
    result = parse_formula('unknown_var + 10', {'x': 5}, {})
except UnknownVariableError as e:
    print(f"Error: {e.message}")
    print(f"Available: {e.details['available_vars']}")
```

## Best Practices

1. **Use meaningful variable names**: Makes formulas self-documenting
2. **Leverage lookup tables**: For category-based values
3. **Use if_else for logic**: Instead of complex boolean expressions
4. **Test with edge cases**: Verify behavior at boundaries
5. **Document complex formulas**: Add comments explaining business logic

## Security

- Only whitelisted functions are allowed
- No arbitrary code execution
- No file system or network access
- Safe evaluation sandbox provided by simpleeval
