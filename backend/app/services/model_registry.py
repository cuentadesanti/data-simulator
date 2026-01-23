"""Enhanced model registry for sklearn regression models.

This module provides a registry of available regression models with auto-discovery
of sklearn estimators, full parameter support, UI grouping, and task-specific metrics.
"""

from __future__ import annotations

import inspect
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Type

import numpy as np

# Sklearn imports - Core
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.utils import all_estimators

# Sklearn imports - Metrics
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    explained_variance_score,
    max_error,
    mean_absolute_percentage_error,
    median_absolute_error,
)


# =============================================================================
# Parameter Definitions
# =============================================================================


@dataclass
class ModelParameter:
    """Definition of a model parameter with full metadata."""
    
    name: str
    display_name: str
    type: str  # "number", "integer", "string", "boolean", "choice"
    required: bool = False
    default: Any = None
    description: str = ""
    choices: list[Any] = field(default_factory=list)
    min_value: float | None = None
    max_value: float | None = None
    recommended_min: float | None = None
    recommended_max: float | None = None
    log_scale: bool = False
    ui_group: str = "advanced"  # "core", "advanced", "internal"


def _infer_param_type(default_value: Any) -> str:
    """Infer parameter type from default value."""
    if default_value is None:
        return "string"
    if isinstance(default_value, bool):
        return "boolean"
    if isinstance(default_value, int):
        return "integer"
    if isinstance(default_value, float):
        return "number"
    if isinstance(default_value, str):
        return "string"
    if isinstance(default_value, tuple):
        return "string"  # e.g., hidden_layer_sizes
    return "string"


# =============================================================================
# Parameter Enrichment Maps
# =============================================================================


# Known parameter choices for common sklearn parameters
PARAM_CHOICES = {
    "solver": ["auto", "svd", "cholesky", "lsqr", "sparse_cg", "sag", "saga", "lbfgs"],
    "criterion": ["squared_error", "friedman_mse", "absolute_error", "poisson"],
    "loss": ["squared_error", "absolute_error", "huber", "quantile"],
    "penalty": ["l1", "l2", "elasticnet", None],
    "kernel": ["linear", "poly", "rbf", "sigmoid", "precomputed"],
    "activation": ["identity", "logistic", "tanh", "relu"],
    "max_features": ["sqrt", "log2", None, "auto"],
    "splitter": ["best", "random"],
    "algorithm": ["auto", "ball_tree", "kd_tree", "brute"],
    "weights": ["uniform", "distance"],
    "learning_rate": ["constant", "invscaling", "adaptive"],
}

# Boolean parameters
BOOLEAN_PARAMS = {
    "bootstrap", "oob_score", "warm_start", "fit_intercept", 
    "copy_X", "positive", "shuffle", "verbose",
    "shrinking", "early_stopping", "compute_score",
}

# Core parameters (high impact, always visible)
CORE_PARAMS = {
    "alpha", "C", "n_estimators", "max_depth", "learning_rate",
    "hidden_layer_sizes", "n_neighbors", "kernel", "solver",
    "epsilon", "gamma", "l1_ratio", "n_iter",
}

# Advanced parameters (collapsed by default)
ADVANCED_PARAMS = {
    "tol", "max_iter", "warm_start", "fit_intercept", 
    "min_samples_split", "min_samples_leaf", "max_features",
    "min_weight_fraction_leaf", "max_leaf_nodes", "min_impurity_decrease",
    "ccp_alpha", "subsample", "criterion", "loss", "activation",
    "batch_size", "learning_rate_init", "power_t", "momentum",
    "nesterovs_momentum", "beta_1", "beta_2", "epsilon", "validation_fraction",
    "n_iter_no_change", "max_fun", "degree", "coef0", "shrinking",
    "cache_size", "algorithm", "leaf_size", "p", "metric", "weights",
}

# Internal parameters (hidden by default)
INTERNAL_PARAMS = {
    "verbose", "n_jobs", "random_state", "copy_X", "copy",
    "positive", "compute_score", "precompute",
}

# Numeric parameters with constraints and recommended ranges
NUMERIC_CONSTRAINTS = {
    "n_estimators": {
        "min": 1, "type": "integer",
        "recommended_min": 50, "recommended_max": 500,
    },
    "max_depth": {
        "min": 1, "type": "integer",
        "recommended_min": 2, "recommended_max": 20,
    },
    "min_samples_split": {"min": 2, "type": "integer"},
    "min_samples_leaf": {"min": 1, "type": "integer"},
    "n_neighbors": {
        "min": 1, "type": "integer",
        "recommended_min": 1, "recommended_max": 20,
    },
    "max_iter": {"min": 1, "type": "integer"},
    "n_jobs": {"min": -1, "type": "integer"},
    "C": {
        "min": 1e-5, "log_scale": True, "type": "number",
        "recommended_min": 1e-3, "recommended_max": 1e3,
    },
    "alpha": {
        "min": 1e-10, "log_scale": True, "type": "number",
        "recommended_min": 1e-4, "recommended_max": 10.0,
    },
    "learning_rate_init": {
        "min": 1e-6, "log_scale": True, "type": "number",
        "recommended_min": 1e-4, "recommended_max": 0.1,
    },
    "tol": {"min": 1e-10, "log_scale": True, "type": "number"},
    "subsample": {"min": 0.0, "max": 1.0, "type": "number"},
    "max_samples": {"min": 0.0, "max": 1.0, "type": "number"},
    "epsilon": {
        "min": 0.0, "type": "number",
        "recommended_min": 0.01, "recommended_max": 1.0,
    },
    "gamma": {
        "min": 0.0, "log_scale": True, "type": "number",
        "recommended_min": 1e-4, "recommended_max": 10.0,
    },
    "l1_ratio": {"min": 0.0, "max": 1.0, "type": "number"},
    "validation_fraction": {"min": 0.0, "max": 1.0, "type": "number"},
}

# Parameter descriptions (human-friendly)
PARAM_DESCRIPTIONS = {
    "alpha": "Regularization strength. Higher values mean stronger regularization.",
    "C": "Inverse regularization strength. Lower values mean stronger regularization.",
    "n_estimators": "Number of trees/estimators in the ensemble.",
    "max_depth": "Maximum depth of each tree. None means unlimited.",
    "learning_rate": "Step size shrinkage used in gradient boosting.",
    "hidden_layer_sizes": "Number of neurons in each hidden layer, e.g. (100,) or (100, 50).",
    "n_neighbors": "Number of neighbors to use for k-nearest neighbors.",
    "kernel": "Kernel function for SVM. 'rbf' is a good default.",
    "solver": "Algorithm to use for optimization.",
    "epsilon": "Epsilon in the epsilon-insensitive loss function.",
    "gamma": "Kernel coefficient for 'rbf', 'poly' and 'sigmoid'.",
    "l1_ratio": "The ElasticNet mixing parameter. 0 = L2, 1 = L1.",
    "tol": "Tolerance for stopping criteria.",
    "max_iter": "Maximum number of iterations.",
    "fit_intercept": "Whether to calculate the intercept.",
    "warm_start": "Reuse the solution from previous fit as initialization.",
    "n_jobs": "Number of parallel jobs. -1 means using all processors.",
    "random_state": "Seed for reproducibility.",
    "verbose": "Verbosity level for logging.",
    "min_samples_split": "Minimum samples required to split an internal node.",
    "min_samples_leaf": "Minimum samples required at a leaf node.",
    "max_features": "Number of features to consider for best split.",
    "bootstrap": "Whether bootstrap samples are used when building trees.",
    "oob_score": "Whether to use out-of-bag samples to estimate R^2.",
    "criterion": "Function to measure the quality of a split.",
    "loss": "Loss function to optimize.",
    "subsample": "Fraction of samples used for fitting each base learner.",
    "activation": "Activation function for the hidden layers.",
    "batch_size": "Size of minibatches for stochastic optimizers.",
    "learning_rate_init": "Initial learning rate for weight updates.",
    "early_stopping": "Whether to terminate training when validation score stops improving.",
    "validation_fraction": "Proportion of training data to set aside for early stopping.",
    "n_iter_no_change": "Maximum consecutive epochs without improvement for early stopping.",
    "weights": "Weight function for predictions. 'uniform' or 'distance'.",
    "algorithm": "Algorithm used to compute nearest neighbors.",
    "leaf_size": "Leaf size passed to BallTree or KDTree.",
    "p": "Power parameter for the Minkowski metric.",
    "metric": "Distance metric to use.",
    "degree": "Degree of the polynomial kernel function.",
    "coef0": "Independent term in kernel function.",
    "shrinking": "Whether to use the shrinking heuristic.",
    "cache_size": "Size of the kernel cache (in MB).",
}


def _get_param_ui_group(param_name: str) -> str:
    """Determine the UI group for a parameter."""
    if param_name in INTERNAL_PARAMS:
        return "internal"
    if param_name in CORE_PARAMS:
        return "core"
    if param_name in ADVANCED_PARAMS:
        return "advanced"
    return "advanced"


def _extract_sklearn_params(estimator_class: Type[BaseEstimator]) -> list[ModelParameter]:
    """Extract parameters from a sklearn estimator class with enrichment."""
    params = []
    sig = inspect.signature(estimator_class.__init__)
    
    for param_name, param in sig.parameters.items():
        if param_name in ("self", "args", "kwargs"):
            continue
        
        default = param.default if param.default is not inspect.Parameter.empty else None
        param_type = _infer_param_type(default)
        display_name = param_name.replace("_", " ").title()
        
        # Check for known choices
        choices = PARAM_CHOICES.get(param_name, [])
        
        # Check for boolean params
        if param_name in BOOLEAN_PARAMS:
            param_type = "boolean"
        
        # Check for numeric constraints
        constraints = NUMERIC_CONSTRAINTS.get(param_name, {})
        min_value = constraints.get("min")
        max_value = constraints.get("max")
        recommended_min = constraints.get("recommended_min")
        recommended_max = constraints.get("recommended_max")
        log_scale = constraints.get("log_scale", False)
        if "type" in constraints:
            param_type = constraints["type"]
        
        # Get description
        description = PARAM_DESCRIPTIONS.get(param_name, f"Parameter: {param_name}")
        
        # Get UI group
        ui_group = _get_param_ui_group(param_name)
        
        params.append(ModelParameter(
            name=param_name,
            display_name=display_name,
            type="choice" if choices else param_type,
            required=param.default is inspect.Parameter.empty,
            default=default,
            description=description,
            choices=choices,
            min_value=min_value,
            max_value=max_value,
            recommended_min=recommended_min,
            recommended_max=recommended_max,
            log_scale=log_scale,
            ui_group=ui_group,
        ))
    
    return params


# =============================================================================
# Metrics Computation
# =============================================================================


def compute_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Compute comprehensive regression metrics."""
    metrics = {
        "r2": float(r2_score(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mse": float(mean_squared_error(y_true, y_pred)),
        "explained_variance": float(explained_variance_score(y_true, y_pred)),
        "median_ae": float(median_absolute_error(y_true, y_pred)),
    }
    
    try:
        metrics["max_error"] = float(max_error(y_true, y_pred))
    except Exception:
        pass
    
    # MAPE - handle zero values
    try:
        if np.all(y_true != 0):
            metrics["mape"] = float(mean_absolute_percentage_error(y_true, y_pred))
    except Exception:
        pass
    
    return metrics


# =============================================================================
# Model Type Base Class
# =============================================================================


class ModelType(ABC):
    """Base class for model types."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def task_type(self) -> str:
        """Task type: 'regression'."""
        pass
    
    @property
    def description(self) -> str:
        return ""
    
    @property
    def category(self) -> str:
        return "other"
    
    @property
    @abstractmethod
    def parameters(self) -> list[ModelParameter]:
        pass
    
    @abstractmethod
    def fit(
        self, 
        X: np.ndarray, 
        y: np.ndarray | None, 
        params: dict[str, Any]
    ) -> tuple[Any, dict[str, float], dict[str, Any]]:
        pass
    
    @abstractmethod
    def predict(self, model: Any, X: np.ndarray) -> np.ndarray:
        pass
    
    @abstractmethod
    def coefficients(
        self, 
        model: Any, 
        feature_names: list[str]
    ) -> dict[str, float] | None:
        pass
    
    def diagnostics(
        self, 
        model: Any, 
        X: np.ndarray, 
        y: np.ndarray | None
    ) -> dict[str, Any] | None:
        return None


# =============================================================================
# Sklearn Model Type Implementation
# =============================================================================


class SklearnModelType(ModelType):
    """Model type wrapper for sklearn estimators."""
    
    def __init__(
        self,
        estimator_class: Type[BaseEstimator],
        name: str,
        display_name: str,
        task_type: str,
        description: str = "",
        category: str = "other",
    ):
        self._estimator_class = estimator_class
        self._name = name
        self._display_name = display_name
        self._task_type = task_type
        self._description = description or self._extract_description(estimator_class)
        self._category = category
    
    @staticmethod
    def _extract_description(estimator_class: Type[BaseEstimator]) -> str:
        """Extract a clean description from the estimator's docstring."""
        doc = estimator_class.__doc__ or ""
        # Get first non-empty line
        lines = [line.strip() for line in doc.split("\n") if line.strip()]
        if lines:
            desc = lines[0]
            # Remove trailing period if present and limit length
            desc = desc.rstrip(".")
            return desc[:200]
        return ""
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def display_name(self) -> str:
        return self._display_name
    
    @property
    def task_type(self) -> str:
        return self._task_type
    
    @property
    def description(self) -> str:
        return self._description[:200] if self._description else ""
    
    @property
    def category(self) -> str:
        return self._category
    
    @property
    def parameters(self) -> list[ModelParameter]:
        return _extract_sklearn_params(self._estimator_class)
    
    def _filter_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Filter params to only those accepted by the estimator."""
        sig = inspect.signature(self._estimator_class.__init__)
        valid_params = set(sig.parameters.keys()) - {"self", "args", "kwargs"}
        return {k: v for k, v in params.items() if k in valid_params and v is not None}
    
    def fit(
        self, 
        X: np.ndarray, 
        y: np.ndarray | None, 
        params: dict[str, Any]
    ) -> tuple[Any, dict[str, float], dict[str, Any]]:
        filtered_params = self._filter_params(params)
        
        model = self._estimator_class(**filtered_params)
        
        model.fit(X, y)
        y_pred = model.predict(X)
        metrics = compute_regression_metrics(y, y_pred)
        
        return model, metrics, {}
    
    def predict(self, model: Any, X: np.ndarray) -> np.ndarray:
        return model.predict(X)
    
    def coefficients(
        self, 
        model: Any, 
        feature_names: list[str]
    ) -> dict[str, float] | None:
        coefs = {}
        
        # Linear model coefficients
        if hasattr(model, "coef_"):
            coef_array = np.atleast_1d(model.coef_).flatten()
            if len(coef_array) >= len(feature_names):
                for name, coef in zip(feature_names, coef_array[:len(feature_names)]):
                    coefs[name] = float(coef)
        
        # Intercept
        if hasattr(model, "intercept_"):
            intercept = model.intercept_
            if isinstance(intercept, np.ndarray):
                intercept = intercept.flatten()[0] if len(intercept.flatten()) > 0 else 0.0
            coefs["_intercept"] = float(intercept)
        
        # Tree feature importances
        if hasattr(model, "feature_importances_"):
            for name, imp in zip(feature_names, model.feature_importances_):
                coefs[f"{name}_importance"] = float(imp)
        
        return coefs if coefs else None
    
    def diagnostics(
        self, 
        model: Any, 
        X: np.ndarray, 
        y: np.ndarray | None
    ) -> dict[str, Any] | None:
        diagnostics = {}
        
        # Residuals for regression
        if self._task_type == "regression" and y is not None:
            y_pred = model.predict(X)
            residuals = y - y_pred
            diagnostics["residuals_mean"] = float(np.mean(residuals))
            diagnostics["residuals_std"] = float(np.std(residuals))
            diagnostics["residuals_min"] = float(np.min(residuals))
            diagnostics["residuals_max"] = float(np.max(residuals))
        
        # Iterations
        if hasattr(model, "n_iter_"):
            n_iter = model.n_iter_
            if isinstance(n_iter, np.ndarray):
                n_iter = n_iter.tolist()
            diagnostics["n_iterations"] = n_iter
        
        # Tree depth
        if hasattr(model, "tree_"):
            diagnostics["tree_depth"] = int(model.tree_.max_depth)
            diagnostics["n_leaves"] = int(model.tree_.n_leaves)
        
        # Ensemble info
        if hasattr(model, "estimators_"):
            diagnostics["n_estimators_fitted"] = len(model.estimators_)
        
        return diagnostics if diagnostics else None


# =============================================================================
# Auto-Discovery of Regressors
# =============================================================================


# Estimators to exclude (abstract, deprecated, or problematic)
EXCLUDED_ESTIMATORS = {
    "DummyRegressor",  # Too simple, not useful
    "IsotonicRegression",  # Univariate only
    "MultiOutputRegressor",  # Meta-estimator
    "MultiTaskElasticNet",  # Multi-task
    "MultiTaskElasticNetCV",
    "MultiTaskLasso",
    "MultiTaskLassoCV",
    "RegressorChain",  # Meta-estimator
    "StackingRegressor",  # Meta-estimator
    "VotingRegressor",  # Meta-estimator
    "TransformedTargetRegressor",  # Meta-estimator
    "RANSACRegressor",  # Requires base estimator
    "TheilSenRegressor",  # Very slow
    "QuantileRegressor",  # Requires solver
    "GammaRegressor",  # GLM
    "PoissonRegressor",  # GLM
    "TweedieRegressor",  # GLM
}

# Category mapping based on module path
CATEGORY_MAP = {
    "linear_model": "linear",
    "tree": "tree",
    "ensemble": "ensemble",
    "svm": "svm",
    "neighbors": "neighbors",
    "neural_network": "neural_network",
    "gaussian_process": "gaussian_process",
    "kernel_ridge": "kernel",
    "cross_decomposition": "linear",
}


def _get_category_from_module(module_name: str) -> str:
    """Determine model category from module name."""
    for key, category in CATEGORY_MAP.items():
        if key in module_name:
            return category
    return "other"


def _class_name_to_snake_case(name: str) -> str:
    """Convert CamelCase class name to snake_case."""
    # Insert underscore before uppercase letters and convert to lowercase
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def _discover_sklearn_regressors() -> list[dict[str, Any]]:
    """Auto-discover all sklearn regressors using all_estimators."""
    discovered = []
    
    try:
        regressors = all_estimators(type_filter="regressor")
    except Exception:
        # Fallback to empty list if discovery fails
        return []
    
    for name, estimator_class in regressors:
        # Skip excluded estimators
        if name in EXCLUDED_ESTIMATORS:
            continue
        
        # Skip abstract base classes
        if inspect.isabstract(estimator_class):
            continue
        
        # Get module for category detection
        module = estimator_class.__module__
        category = _get_category_from_module(module)
        
        # Create snake_case name
        snake_name = _class_name_to_snake_case(name)
        
        # Create display name from class name
        display_name = re.sub(r'(?<!^)(?=[A-Z])', ' ', name)
        
        discovered.append({
            "class": estimator_class,
            "name": snake_name,
            "display_name": display_name,
            "task_type": "regression",
            "category": category,
            "description": "",  # Will be extracted from docstring
        })
    
    return discovered


# =============================================================================
# Model Registry
# =============================================================================


class ModelRegistry:
    """Registry of available ML model types with auto-discovery."""
    
    _instance: "ModelRegistry | None" = None
    
    def __init__(self):
        self._models: dict[str, ModelType] = {}
    
    @classmethod
    def get_instance(cls) -> "ModelRegistry":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._register_defaults()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None
    
    def _register_defaults(self) -> None:
        """Register all discovered sklearn regressors."""
        discovered = _discover_sklearn_regressors()
        
        for spec in discovered:
            try:
                model_type = SklearnModelType(
                    estimator_class=spec["class"],
                    name=spec["name"],
                    display_name=spec["display_name"],
                    task_type=spec["task_type"],
                    description=spec.get("description", ""),
                    category=spec.get("category", "other"),
                )
                self.register(model_type)
            except Exception:
                # Skip estimators that fail to register
                pass
    
    def register(self, model_type: ModelType) -> None:
        self._models[model_type.name] = model_type
    
    def get(self, name: str) -> ModelType | None:
        return self._models.get(name)
    
    def list_all(self) -> list[dict[str, Any]]:
        result = []
        for model_type in self._models.values():
            params = [
                {
                    "name": p.name,
                    "display_name": p.display_name,
                    "type": p.type,
                    "required": p.required,
                    "default": p.default,
                    "description": p.description,
                    "choices": p.choices if p.choices else None,
                    "min_value": p.min_value,
                    "max_value": p.max_value,
                    "recommended_min": p.recommended_min,
                    "recommended_max": p.recommended_max,
                    "log_scale": p.log_scale,
                    "ui_group": p.ui_group,
                }
                for p in model_type.parameters
            ]
            result.append({
                "name": model_type.name,
                "display_name": model_type.display_name,
                "description": model_type.description,
                "task_type": model_type.task_type,
                "category": model_type.category,
                "parameters": params,
            })
        return result
    
    def list_by_task(self, task_type: str) -> list[dict[str, Any]]:
        return [m for m in self.list_all() if m["task_type"] == task_type]
    
    def list_by_category(self, category: str) -> list[dict[str, Any]]:
        return [m for m in self.list_all() if m.get("category") == category]


def get_model_registry() -> ModelRegistry:
    return ModelRegistry.get_instance()
