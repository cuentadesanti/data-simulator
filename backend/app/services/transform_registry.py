"""Transform registry for pipeline step operations.

This module provides a registry of available transforms that can be applied
as pipeline steps to derive new columns from existing data.
"""

from __future__ import annotations

import ast
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np
import pandas as pd


# =============================================================================
# Transform Protocol
# =============================================================================


@dataclass
class TransformParameter:
    """Definition of a transform parameter."""
    
    name: str
    display_name: str
    type: str  # "string", "number", "column", "columns"
    required: bool = True
    default: Any = None
    description: str = ""


class Transform(ABC):
    """Base class for all transforms."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the transform."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for the transform."""
        pass
    
    @property
    def description(self) -> str:
        """Description of what the transform does."""
        return ""
    
    @property
    @abstractmethod
    def parameters(self) -> list[TransformParameter]:
        """List of parameters the transform accepts."""
        pass
    
    @abstractmethod
    def required_columns(self, params: dict[str, Any]) -> list[str]:
        """Get list of input column names required by this transform.
        
        Args:
            params: Transform parameters
            
        Returns:
            List of column names that must exist in the input schema
        """
        pass
    
    @abstractmethod
    def infer_dtype(
        self, 
        input_schema: list[dict[str, Any]], 
        params: dict[str, Any]
    ) -> str:
        """Infer the output dtype of this transform.
        
        Args:
            input_schema: Current schema as list of {name, dtype}
            params: Transform parameters
            
        Returns:
            Dtype string for the output column
        """
        pass
    
    @abstractmethod
    def apply(
        self, 
        df: pd.DataFrame, 
        params: dict[str, Any]
    ) -> tuple[pd.Series, dict[str, Any]]:
        """Apply the transform to create a new column.
        
        Args:
            df: Input DataFrame
            params: Transform parameters
            
        Returns:
            Tuple of:
                - Series with the derived values
                - Metadata dict (e.g., {"warnings_count": 0})
        """
        pass


# =============================================================================
# Transform Implementations
# =============================================================================


class FormulaTransform(Transform):
    """Transform that evaluates a safe formula expression."""
    
    @property
    def name(self) -> str:
        return "formula"
    
    @property
    def display_name(self) -> str:
        return "Formula"
    
    @property
    def description(self) -> str:
        return "Evaluate a mathematical expression using column values"
    
    @property
    def parameters(self) -> list[TransformParameter]:
        return [
            TransformParameter(
                name="expression",
                display_name="Expression",
                type="string",
                required=True,
                description="Formula expression (e.g., 'log(income) + age * 2')",
            ),
        ]
    
    def required_columns(self, params: dict[str, Any]) -> list[str]:
        """Parse expression to find referenced column names."""
        expression = params.get("expression", "")
        return _extract_names_from_expression(expression)
    
    def infer_dtype(
        self, 
        input_schema: list[dict[str, Any]], 
        params: dict[str, Any]
    ) -> str:
        # Formula results are typically float
        return "float"
    
    def apply(
        self, 
        df: pd.DataFrame, 
        params: dict[str, Any]
    ) -> tuple[pd.Series, dict[str, Any]]:
        expression = params.get("expression", "")
        
        # Validate the expression first
        validate_safe_expression(expression, list(df.columns))
        
        # Build evaluation context
        context = _build_eval_context(df)
        
        # Compile and evaluate
        try:
            code = compile(expression, "<formula>", "eval")
            result = eval(code, {"__builtins__": {}}, context)
            
            # Ensure result is a Series
            if isinstance(result, (int, float)):
                result = pd.Series([result] * len(df), index=df.index)
            elif isinstance(result, np.ndarray):
                result = pd.Series(result, index=df.index)
            elif not isinstance(result, pd.Series):
                result = pd.Series(result, index=df.index)
            
            return result, {"warnings_count": 0}
            
        except Exception as e:
            raise ValueError(f"Formula evaluation failed: {e}")


class LogTransform(Transform):
    """Natural logarithm transform."""
    
    @property
    def name(self) -> str:
        return "log"
    
    @property
    def display_name(self) -> str:
        return "Natural Log"
    
    @property
    def description(self) -> str:
        return "Compute natural logarithm (values <= 0 become null)"
    
    @property
    def parameters(self) -> list[TransformParameter]:
        return [
            TransformParameter(
                name="column",
                display_name="Column",
                type="column",
                required=True,
                description="Column to transform",
            ),
        ]
    
    def required_columns(self, params: dict[str, Any]) -> list[str]:
        col = params.get("column")
        return [col] if col else []
    
    def infer_dtype(
        self, 
        input_schema: list[dict[str, Any]], 
        params: dict[str, Any]
    ) -> str:
        return "float"
    
    def apply(
        self, 
        df: pd.DataFrame, 
        params: dict[str, Any]
    ) -> tuple[pd.Series, dict[str, Any]]:
        column = params.get("column")
        values = df[column].astype(float)
        
        # Handle invalid domain (x <= 0)
        warnings_count = int((values <= 0).sum())
        result = np.where(values > 0, np.log(values), np.nan)
        
        return pd.Series(result, index=df.index), {"warnings_count": warnings_count}


class SqrtTransform(Transform):
    """Square root transform."""
    
    @property
    def name(self) -> str:
        return "sqrt"
    
    @property
    def display_name(self) -> str:
        return "Square Root"
    
    @property
    def description(self) -> str:
        return "Compute square root (negative values become null)"
    
    @property
    def parameters(self) -> list[TransformParameter]:
        return [
            TransformParameter(
                name="column",
                display_name="Column",
                type="column",
                required=True,
                description="Column to transform",
            ),
        ]
    
    def required_columns(self, params: dict[str, Any]) -> list[str]:
        col = params.get("column")
        return [col] if col else []
    
    def infer_dtype(
        self, 
        input_schema: list[dict[str, Any]], 
        params: dict[str, Any]
    ) -> str:
        return "float"
    
    def apply(
        self, 
        df: pd.DataFrame, 
        params: dict[str, Any]
    ) -> tuple[pd.Series, dict[str, Any]]:
        column = params.get("column")
        values = df[column].astype(float)
        
        # Handle invalid domain (x < 0)
        warnings_count = int((values < 0).sum())
        result = np.where(values >= 0, np.sqrt(values), np.nan)
        
        return pd.Series(result, index=df.index), {"warnings_count": warnings_count}


class ExpTransform(Transform):
    """Exponential transform."""
    
    @property
    def name(self) -> str:
        return "exp"
    
    @property
    def display_name(self) -> str:
        return "Exponential"
    
    @property
    def description(self) -> str:
        return "Compute e^x (exponential function)"
    
    @property
    def parameters(self) -> list[TransformParameter]:
        return [
            TransformParameter(
                name="column",
                display_name="Column",
                type="column",
                required=True,
                description="Column to transform",
            ),
        ]
    
    def required_columns(self, params: dict[str, Any]) -> list[str]:
        col = params.get("column")
        return [col] if col else []
    
    def infer_dtype(
        self, 
        input_schema: list[dict[str, Any]], 
        params: dict[str, Any]
    ) -> str:
        return "float"
    
    def apply(
        self, 
        df: pd.DataFrame, 
        params: dict[str, Any]
    ) -> tuple[pd.Series, dict[str, Any]]:
        column = params.get("column")
        values = df[column].astype(float)
        
        # Handle overflow by clipping large values
        MAX_EXP = 700  # Approximate limit before overflow
        warnings_count = int((values > MAX_EXP).sum())
        clipped = np.clip(values, -MAX_EXP, MAX_EXP)
        result = np.exp(clipped)
        
        return pd.Series(result, index=df.index), {"warnings_count": warnings_count}


class BinTransform(Transform):
    """Binning/discretization transform."""
    
    @property
    def name(self) -> str:
        return "bin"
    
    @property
    def display_name(self) -> str:
        return "Bin/Discretize"
    
    @property
    def description(self) -> str:
        return "Discretize a continuous column into bins"
    
    @property
    def parameters(self) -> list[TransformParameter]:
        return [
            TransformParameter(
                name="column",
                display_name="Column",
                type="column",
                required=True,
                description="Column to bin",
            ),
            TransformParameter(
                name="bins",
                display_name="Number of Bins",
                type="number",
                required=True,
                default=5,
                description="Number of equal-width bins",
            ),
            TransformParameter(
                name="labels",
                display_name="Labels",
                type="string",
                required=False,
                description="Comma-separated labels for bins (optional)",
            ),
        ]
    
    def required_columns(self, params: dict[str, Any]) -> list[str]:
        col = params.get("column")
        return [col] if col else []
    
    def infer_dtype(
        self, 
        input_schema: list[dict[str, Any]], 
        params: dict[str, Any]
    ) -> str:
        labels = params.get("labels")
        return "category" if labels else "int"
    
    def apply(
        self, 
        df: pd.DataFrame, 
        params: dict[str, Any]
    ) -> tuple[pd.Series, dict[str, Any]]:
        column = params.get("column")
        bins = int(params.get("bins", 5))
        labels_str = params.get("labels")
        
        values = df[column].astype(float)
        
        if labels_str:
            labels = [l.strip() for l in labels_str.split(",")]
            if len(labels) != bins:
                raise ValueError(f"Number of labels ({len(labels)}) must match number of bins ({bins})")
            result = pd.cut(values, bins=bins, labels=labels)
        else:
            result = pd.cut(values, bins=bins, labels=False)
        
        return result, {"warnings_count": 0}


# =============================================================================
# Safe Expression Evaluation Helpers
# =============================================================================


# AST nodes that are allowed in safe expressions
ALLOWED_AST_NODES = {
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Compare,
    ast.BoolOp,
    ast.IfExp,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    # Operators
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    # Comparison
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    # Boolean
    ast.And,
    ast.Or,
    ast.Not,
}

# Allowed function names in expressions
ALLOWED_FUNCTIONS = {
    "log", "exp", "sqrt", "abs", "min", "max", "clip", 
    "where", "isnan", "isnull", "coalesce", 
    "sin", "cos", "tan", "floor", "ceil", "round",
}

# Maximum limits for expression safety
MAX_EXPRESSION_LENGTH = 500
MAX_AST_NODES = 200


def validate_safe_expression(expression: str, available_columns: list[str]) -> None:
    """Validate that an expression is safe to evaluate.
    
    Checks:
    - Expression length
    - AST node whitelist
    - Only allowed functions
    - Column names exist
    
    Args:
        expression: Formula expression string
        available_columns: List of available column names
        
    Raises:
        ValueError: If expression is unsafe or invalid
    """
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError(f"Expression too long (max {MAX_EXPRESSION_LENGTH} chars)")
    
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Invalid expression syntax: {e}")
    
    # Count and validate nodes
    node_count = 0
    for node in ast.walk(tree):
        node_count += 1
        if node_count > MAX_AST_NODES:
            raise ValueError(f"Expression too complex (max {MAX_AST_NODES} nodes)")
        
        # Check node type is allowed
        if type(node) not in ALLOWED_AST_NODES:
            raise ValueError(f"Disallowed expression element: {type(node).__name__}")
        
        # Check function calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id not in ALLOWED_FUNCTIONS:
                    raise ValueError(f"Function not allowed: {node.func.id}")
            else:
                raise ValueError("Only simple function calls are allowed")
    
    # Validate column references exist
    referenced = _extract_names_from_expression(expression)
    available_set = set(available_columns)
    for name in referenced:
        if name not in available_set and name not in ALLOWED_FUNCTIONS:
            raise ValueError(f"Unknown column: {name}")


def _extract_names_from_expression(expression: str) -> list[str]:
    """Extract variable names referenced in an expression.
    
    Args:
        expression: Formula expression string
        
    Returns:
        List of referenced variable/column names
    """
    if not expression:
        return []
    
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return []
    
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            # Exclude function names
            if node.id not in ALLOWED_FUNCTIONS:
                names.append(node.id)
    
    return list(set(names))


def _build_eval_context(df: pd.DataFrame) -> dict[str, Any]:
    """Build the evaluation context for formula evaluation.
    
    Provides columns as variables and allowed functions.
    
    Args:
        df: DataFrame with column data
        
    Returns:
        Context dict for eval()
    """
    context = {}
    
    # Add columns
    for col in df.columns:
        context[col] = df[col].values
    
    # Add allowed functions
    context["log"] = np.log
    context["exp"] = np.exp
    context["sqrt"] = np.sqrt
    context["abs"] = np.abs
    context["min"] = np.minimum
    context["max"] = np.maximum
    context["clip"] = np.clip
    context["where"] = np.where
    context["isnan"] = np.isnan
    context["isnull"] = pd.isna
    context["coalesce"] = lambda a, b: np.where(pd.isna(a), b, a)
    context["sin"] = np.sin
    context["cos"] = np.cos
    context["tan"] = np.tan
    context["floor"] = np.floor
    context["ceil"] = np.ceil
    context["round"] = np.round
    
    return context


# =============================================================================
# Transform Registry
# =============================================================================


class TransformRegistry:
    """Registry of available transforms."""
    
    _instance: "TransformRegistry | None" = None
    
    def __init__(self):
        self._transforms: dict[str, Transform] = {}
    
    @classmethod
    def get_instance(cls) -> "TransformRegistry":
        """Get the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._register_defaults()
        return cls._instance
    
    def _register_defaults(self) -> None:
        """Register the default transforms."""
        self.register(FormulaTransform())
        self.register(LogTransform())
        self.register(SqrtTransform())
        self.register(ExpTransform())
        self.register(BinTransform())
    
    def register(self, transform: Transform) -> None:
        """Register a transform.
        
        Args:
            transform: Transform instance to register
        """
        self._transforms[transform.name] = transform
    
    def get(self, name: str) -> Transform | None:
        """Get a transform by name.
        
        Args:
            name: Transform name
            
        Returns:
            Transform instance or None if not found
        """
        return self._transforms.get(name)
    
    def list_all(self) -> list[dict[str, Any]]:
        """List all registered transforms with their metadata.
        
        Returns:
            List of transform info dicts
        """
        result = []
        for transform in self._transforms.values():
            params = [
                {
                    "name": p.name,
                    "display_name": p.display_name,
                    "type": p.type,
                    "required": p.required,
                    "default": p.default,
                    "description": p.description,
                }
                for p in transform.parameters
            ]
            result.append({
                "name": transform.name,
                "display_name": transform.display_name,
                "description": transform.description,
                "parameters": params,
            })
        return result


def get_transform_registry() -> TransformRegistry:
    """Get the global transform registry.
    
    Returns:
        The singleton TransformRegistry instance
    """
    return TransformRegistry.get_instance()
