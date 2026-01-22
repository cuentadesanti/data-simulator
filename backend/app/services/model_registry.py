"""Comprehensive model registry for sklearn model types.

This module provides a registry of available ML models with auto-discovery
of sklearn estimators, full parameter support, and task-specific metrics.
Supports regression, classification, and clustering tasks.
"""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Type

import numpy as np

# Sklearn imports - Core
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin, ClusterMixin

# Sklearn imports - Linear Models
from sklearn.linear_model import (
    LinearRegression,
    Ridge,
    Lasso,
    ElasticNet,
    BayesianRidge,
    HuberRegressor,
    LogisticRegression,
    RidgeClassifier,
    SGDClassifier,
    SGDRegressor,
    Perceptron,
    PassiveAggressiveClassifier,
)

# Sklearn imports - Tree Models
from sklearn.tree import (
    DecisionTreeClassifier,
    DecisionTreeRegressor,
)

# Sklearn imports - Ensemble Models
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    AdaBoostClassifier,
    AdaBoostRegressor,
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)

# Sklearn imports - SVM
from sklearn.svm import SVC, SVR, LinearSVC, LinearSVR

# Sklearn imports - Neighbors
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor

# Sklearn imports - Naive Bayes
from sklearn.naive_bayes import GaussianNB, BernoulliNB

# Sklearn imports - Neural Networks
from sklearn.neural_network import MLPClassifier, MLPRegressor

# Sklearn imports - Clustering
from sklearn.cluster import (
    KMeans,
    DBSCAN,
    AgglomerativeClustering,
    SpectralClustering,
    MeanShift,
    Birch,
    MiniBatchKMeans,
)

# Sklearn imports - Metrics
from sklearn.metrics import (
    # Classification metrics
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    log_loss,
    roc_auc_score,
    cohen_kappa_score,
    matthews_corrcoef,
    # Regression metrics
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    explained_variance_score,
    max_error,
    mean_absolute_percentage_error,
    median_absolute_error,
    # Clustering metrics
    silhouette_score,
    calinski_harabasz_score,
    davies_bouldin_score,
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
    log_scale: bool = False  # For hyperparameter tuning


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
    return "string"


# Known parameter choices for common sklearn parameters
PARAM_CHOICES = {
    "solver": ["auto", "svd", "cholesky", "lsqr", "sparse_cg", "sag", "saga", "lbfgs"],
    "criterion": ["gini", "entropy", "log_loss", "squared_error", "friedman_mse", "absolute_error", "poisson"],
    "loss": ["squared_error", "absolute_error", "huber", "quantile", "log_loss", "deviance", "exponential", "hinge", "log", "modified_huber", "squared_hinge", "perceptron"],
    "penalty": ["l1", "l2", "elasticnet", None],
    "kernel": ["linear", "poly", "rbf", "sigmoid", "precomputed"],
    "activation": ["identity", "logistic", "tanh", "relu"],
    "multi_class": ["auto", "ovr", "multinomial"],
    "class_weight": ["balanced", None],
    "max_features": ["sqrt", "log2", None, "auto"],
    "splitter": ["best", "random"],
    "algorithm": ["auto", "ball_tree", "kd_tree", "brute", "lloyd", "elkan", "full"],
    "linkage": ["ward", "complete", "average", "single"],
    "affinity": ["euclidean", "manhattan", "cosine", "precomputed", "nearest_neighbors", "rbf"],
    "init": ["k-means++", "random"],
}

# Boolean parameters
BOOLEAN_PARAMS = {
    "bootstrap", "oob_score", "warm_start", "fit_intercept", 
    "normalize", "copy_X", "positive", "shuffle", "verbose",
    "probability", "shrinking", "dual", "early_stopping",
}

# Numeric parameters with constraints
NUMERIC_CONSTRAINTS = {
    "n_estimators": {"min": 1, "type": "integer"},
    "max_depth": {"min": 1, "type": "integer"},
    "min_samples_split": {"min": 2, "type": "integer"},
    "min_samples_leaf": {"min": 1, "type": "integer"},
    "n_neighbors": {"min": 1, "type": "integer"},
    "max_iter": {"min": 1, "type": "integer"},
    "n_jobs": {"min": -1, "type": "integer"},
    "n_clusters": {"min": 2, "type": "integer"},
    "C": {"min": 0.0001, "log_scale": True, "type": "number"},
    "alpha": {"min": 0.0001, "log_scale": True, "type": "number"},
    "learning_rate_init": {"min": 0.0001, "log_scale": True, "type": "number"},
    "tol": {"min": 1e-10, "log_scale": True, "type": "number"},
    "test_size": {"min": 0.0, "max": 1.0, "type": "number"},
    "subsample": {"min": 0.0, "max": 1.0, "type": "number"},
    "max_samples": {"min": 0.0, "max": 1.0, "type": "number"},
    "eps": {"min": 0.0001, "log_scale": True, "type": "number"},
    "min_samples": {"min": 1, "type": "integer"},
}


def _extract_sklearn_params(estimator_class: Type[BaseEstimator]) -> list[ModelParameter]:
    """Extract parameters from a sklearn estimator class."""
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
        log_scale = constraints.get("log_scale", False)
        if "type" in constraints:
            param_type = constraints["type"]
        
        params.append(ModelParameter(
            name=param_name,
            display_name=display_name,
            type="choice" if choices else param_type,
            required=param.default is inspect.Parameter.empty,
            default=default,
            description=f"Parameter: {param_name}",
            choices=choices,
            min_value=min_value,
            max_value=max_value,
            log_scale=log_scale,
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


def compute_classification_metrics(
    y_true: np.ndarray, 
    y_pred: np.ndarray,
    y_proba: np.ndarray | None = None
) -> dict[str, float]:
    """Compute comprehensive classification metrics."""
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }
    
    try:
        unique_classes = np.unique(y_true)
        n_classes = len(unique_classes)
        
        if n_classes == 2:
            # Binary classification
            metrics["precision"] = float(precision_score(y_true, y_pred, zero_division=0))
            metrics["recall"] = float(recall_score(y_true, y_pred, zero_division=0))
            metrics["f1"] = float(f1_score(y_true, y_pred, zero_division=0))
            metrics["cohen_kappa"] = float(cohen_kappa_score(y_true, y_pred))
            
            try:
                metrics["matthews_corrcoef"] = float(matthews_corrcoef(y_true, y_pred))
            except Exception:
                pass
            
            if y_proba is not None and y_proba.shape[1] == 2:
                try:
                    metrics["roc_auc"] = float(roc_auc_score(y_true, y_proba[:, 1]))
                except Exception:
                    pass
        else:
            # Multi-class classification
            metrics["balanced_accuracy"] = float(balanced_accuracy_score(y_true, y_pred))
            metrics["f1_macro"] = float(f1_score(y_true, y_pred, average='macro', zero_division=0))
            metrics["f1_weighted"] = float(f1_score(y_true, y_pred, average='weighted', zero_division=0))
            metrics["precision_macro"] = float(precision_score(y_true, y_pred, average='macro', zero_division=0))
            metrics["recall_macro"] = float(recall_score(y_true, y_pred, average='macro', zero_division=0))
        
        if y_proba is not None:
            try:
                metrics["log_loss"] = float(log_loss(y_true, y_proba))
            except Exception:
                pass
                
    except Exception:
        pass
    
    return metrics


def compute_clustering_metrics(X: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    """Compute clustering quality metrics."""
    metrics = {}
    
    # Only compute metrics if we have more than 1 cluster
    unique_labels = np.unique(labels)
    unique_labels = unique_labels[unique_labels != -1]  # Exclude noise label from DBSCAN
    n_clusters = len(unique_labels)
    
    if n_clusters < 2:
        metrics["n_clusters"] = n_clusters
        metrics["warning"] = "Less than 2 clusters found, some metrics unavailable"
        return metrics
    
    metrics["n_clusters"] = n_clusters
    
    try:
        # Silhouette score: -1 to 1, higher is better
        metrics["silhouette_score"] = float(silhouette_score(X, labels))
    except Exception:
        pass
    
    try:
        # Calinski-Harabasz index: higher is better
        metrics["calinski_harabasz_score"] = float(calinski_harabasz_score(X, labels))
    except Exception:
        pass
    
    try:
        # Davies-Bouldin index: lower is better
        metrics["davies_bouldin_score"] = float(davies_bouldin_score(X, labels))
    except Exception:
        pass
    
    # Cluster sizes
    try:
        cluster_sizes = {int(label): int(np.sum(labels == label)) for label in unique_labels}
        metrics["cluster_sizes"] = cluster_sizes
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
        """Task type: 'regression', 'classification', or 'clustering'."""
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
        self._description = description or (estimator_class.__doc__ or "").split("\n")[0]
        self._category = category
    
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
        
        if self._task_type == "clustering":
            # Clustering doesn't use y
            model.fit(X)
            labels = model.labels_ if hasattr(model, 'labels_') else model.predict(X)
            metrics = compute_clustering_metrics(X, labels)
        else:
            model.fit(X, y)
            y_pred = model.predict(X)
            
            if self._task_type == "regression":
                metrics = compute_regression_metrics(y, y_pred)
            else:
                y_proba = None
                if hasattr(model, "predict_proba"):
                    try:
                        y_proba = model.predict_proba(X)
                    except Exception:
                        pass
                metrics = compute_classification_metrics(y, y_pred, y_proba)
        
        return model, metrics, {}
    
    def predict(self, model: Any, X: np.ndarray) -> np.ndarray:
        if self._task_type == "clustering":
            if hasattr(model, "predict"):
                return model.predict(X)
            elif hasattr(model, "labels_"):
                # Some clustering algorithms don't have predict
                return model.labels_
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
        
        # Cluster centers for clustering
        if hasattr(model, "cluster_centers_"):
            coefs["_n_clusters"] = len(model.cluster_centers_)
            for i, center in enumerate(model.cluster_centers_):
                for j, name in enumerate(feature_names):
                    if j < len(center):
                        coefs[f"cluster_{i}_{name}"] = float(center[j])
        
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
        
        # Clustering info
        if hasattr(model, "inertia_"):
            diagnostics["inertia"] = float(model.inertia_)
        
        if hasattr(model, "labels_"):
            unique_labels = np.unique(model.labels_)
            diagnostics["labels_unique"] = len(unique_labels)
        
        return diagnostics if diagnostics else None


# =============================================================================
# Model Specifications
# =============================================================================


SKLEARN_MODELS = [
    # =========================================================================
    # Linear Models - Regression
    # =========================================================================
    {"class": LinearRegression, "name": "linear_regression", "display_name": "Linear Regression", 
     "task_type": "regression", "category": "linear", "description": "Ordinary least squares linear regression"},
    {"class": Ridge, "name": "ridge_regression", "display_name": "Ridge Regression", 
     "task_type": "regression", "category": "linear", "description": "Linear regression with L2 regularization"},
    {"class": Lasso, "name": "lasso_regression", "display_name": "Lasso Regression", 
     "task_type": "regression", "category": "linear", "description": "Linear regression with L1 regularization"},
    {"class": ElasticNet, "name": "elasticnet_regression", "display_name": "ElasticNet Regression", 
     "task_type": "regression", "category": "linear", "description": "Combined L1 and L2 regularization"},
    {"class": BayesianRidge, "name": "bayesian_ridge", "display_name": "Bayesian Ridge Regression", 
     "task_type": "regression", "category": "linear", "description": "Bayesian ridge regression"},
    {"class": HuberRegressor, "name": "huber_regression", "display_name": "Huber Regression", 
     "task_type": "regression", "category": "linear", "description": "Linear regression robust to outliers"},
    {"class": SGDRegressor, "name": "sgd_regressor", "display_name": "SGD Regressor", 
     "task_type": "regression", "category": "linear", "description": "Stochastic gradient descent regressor"},
    
    # =========================================================================
    # Linear Models - Classification
    # =========================================================================
    {"class": LogisticRegression, "name": "logistic_regression", "display_name": "Logistic Regression", 
     "task_type": "classification", "category": "linear", "description": "Logistic regression classifier"},
    {"class": RidgeClassifier, "name": "ridge_classifier", "display_name": "Ridge Classifier", 
     "task_type": "classification", "category": "linear", "description": "Ridge regression classifier"},
    {"class": SGDClassifier, "name": "sgd_classifier", "display_name": "SGD Classifier", 
     "task_type": "classification", "category": "linear", "description": "Stochastic gradient descent classifier"},
    {"class": Perceptron, "name": "perceptron", "display_name": "Perceptron", 
     "task_type": "classification", "category": "linear", "description": "Simple perceptron classifier"},
    {"class": PassiveAggressiveClassifier, "name": "passive_aggressive_classifier", "display_name": "Passive Aggressive Classifier", 
     "task_type": "classification", "category": "linear", "description": "Online learning classifier"},
    
    # =========================================================================
    # Tree Models
    # =========================================================================
    {"class": DecisionTreeRegressor, "name": "decision_tree_regressor", "display_name": "Decision Tree Regressor", 
     "task_type": "regression", "category": "tree", "description": "Decision tree for regression"},
    {"class": DecisionTreeClassifier, "name": "decision_tree_classifier", "display_name": "Decision Tree Classifier", 
     "task_type": "classification", "category": "tree", "description": "Decision tree for classification"},
    
    # =========================================================================
    # Ensemble Models - Random Forest
    # =========================================================================
    {"class": RandomForestRegressor, "name": "random_forest_regressor", "display_name": "Random Forest Regressor", 
     "task_type": "regression", "category": "ensemble", "description": "Ensemble of decision trees for regression"},
    {"class": RandomForestClassifier, "name": "random_forest_classifier", "display_name": "Random Forest Classifier", 
     "task_type": "classification", "category": "ensemble", "description": "Ensemble of decision trees for classification"},
    {"class": ExtraTreesRegressor, "name": "extra_trees_regressor", "display_name": "Extra Trees Regressor", 
     "task_type": "regression", "category": "ensemble", "description": "Extremely randomized trees regressor"},
    {"class": ExtraTreesClassifier, "name": "extra_trees_classifier", "display_name": "Extra Trees Classifier", 
     "task_type": "classification", "category": "ensemble", "description": "Extremely randomized trees classifier"},
    
    # =========================================================================
    # Ensemble Models - Gradient Boosting
    # =========================================================================
    {"class": GradientBoostingRegressor, "name": "gradient_boosting_regressor", "display_name": "Gradient Boosting Regressor", 
     "task_type": "regression", "category": "ensemble", "description": "Gradient boosting for regression"},
    {"class": GradientBoostingClassifier, "name": "gradient_boosting_classifier", "display_name": "Gradient Boosting Classifier", 
     "task_type": "classification", "category": "ensemble", "description": "Gradient boosting for classification"},
    {"class": HistGradientBoostingRegressor, "name": "hist_gradient_boosting_regressor", "display_name": "Histogram Gradient Boosting Regressor", 
     "task_type": "regression", "category": "ensemble", "description": "Fast histogram-based gradient boosting regressor"},
    {"class": HistGradientBoostingClassifier, "name": "hist_gradient_boosting_classifier", "display_name": "Histogram Gradient Boosting Classifier", 
     "task_type": "classification", "category": "ensemble", "description": "Fast histogram-based gradient boosting classifier"},
    
    # =========================================================================
    # Ensemble Models - AdaBoost
    # =========================================================================
    {"class": AdaBoostRegressor, "name": "adaboost_regressor", "display_name": "AdaBoost Regressor", 
     "task_type": "regression", "category": "ensemble", "description": "AdaBoost ensemble for regression"},
    {"class": AdaBoostClassifier, "name": "adaboost_classifier", "display_name": "AdaBoost Classifier", 
     "task_type": "classification", "category": "ensemble", "description": "AdaBoost ensemble for classification"},
    
    # =========================================================================
    # Support Vector Machines
    # =========================================================================
    {"class": SVR, "name": "svr", "display_name": "Support Vector Regressor", 
     "task_type": "regression", "category": "svm", "description": "Support vector regression"},
    {"class": SVC, "name": "svc", "display_name": "Support Vector Classifier", 
     "task_type": "classification", "category": "svm", "description": "Support vector classification"},
    {"class": LinearSVR, "name": "linear_svr", "display_name": "Linear SVR", 
     "task_type": "regression", "category": "svm", "description": "Linear support vector regression"},
    {"class": LinearSVC, "name": "linear_svc", "display_name": "Linear SVC", 
     "task_type": "classification", "category": "svm", "description": "Linear support vector classification"},
    
    # =========================================================================
    # Neighbors
    # =========================================================================
    {"class": KNeighborsRegressor, "name": "knn_regressor", "display_name": "K-Neighbors Regressor", 
     "task_type": "regression", "category": "neighbors", "description": "K-nearest neighbors for regression"},
    {"class": KNeighborsClassifier, "name": "knn_classifier", "display_name": "K-Neighbors Classifier", 
     "task_type": "classification", "category": "neighbors", "description": "K-nearest neighbors for classification"},
    
    # =========================================================================
    # Naive Bayes
    # =========================================================================
    {"class": GaussianNB, "name": "gaussian_nb", "display_name": "Gaussian Naive Bayes", 
     "task_type": "classification", "category": "naive_bayes", "description": "Gaussian Naive Bayes classifier"},
    {"class": BernoulliNB, "name": "bernoulli_nb", "display_name": "Bernoulli Naive Bayes", 
     "task_type": "classification", "category": "naive_bayes", "description": "Bernoulli Naive Bayes for binary features"},
    
    # =========================================================================
    # Neural Networks
    # =========================================================================
    {"class": MLPRegressor, "name": "mlp_regressor", "display_name": "MLP Regressor", 
     "task_type": "regression", "category": "neural_network", "description": "Multi-layer Perceptron regressor"},
    {"class": MLPClassifier, "name": "mlp_classifier", "display_name": "MLP Classifier", 
     "task_type": "classification", "category": "neural_network", "description": "Multi-layer Perceptron classifier"},
    
    # =========================================================================
    # Clustering
    # =========================================================================
    {"class": KMeans, "name": "kmeans", "display_name": "K-Means Clustering", 
     "task_type": "clustering", "category": "clustering", "description": "K-Means clustering algorithm"},
    {"class": MiniBatchKMeans, "name": "minibatch_kmeans", "display_name": "Mini-Batch K-Means", 
     "task_type": "clustering", "category": "clustering", "description": "Mini-batch variant of K-Means for large datasets"},
    {"class": DBSCAN, "name": "dbscan", "display_name": "DBSCAN", 
     "task_type": "clustering", "category": "clustering", "description": "Density-based spatial clustering"},
    {"class": AgglomerativeClustering, "name": "agglomerative_clustering", "display_name": "Agglomerative Clustering", 
     "task_type": "clustering", "category": "clustering", "description": "Hierarchical agglomerative clustering"},
    {"class": SpectralClustering, "name": "spectral_clustering", "display_name": "Spectral Clustering", 
     "task_type": "clustering", "category": "clustering", "description": "Spectral clustering using graph Laplacian"},
    {"class": MeanShift, "name": "mean_shift", "display_name": "Mean Shift", 
     "task_type": "clustering", "category": "clustering", "description": "Mean shift clustering"},
    {"class": Birch, "name": "birch", "display_name": "BIRCH Clustering", 
     "task_type": "clustering", "category": "clustering", "description": "BIRCH hierarchical clustering for large datasets"},
]


# =============================================================================
# Model Registry
# =============================================================================


class ModelRegistry:
    """Registry of available ML model types."""
    
    _instance: "ModelRegistry | None" = None
    
    def __init__(self):
        self._models: dict[str, ModelType] = {}
    
    @classmethod
    def get_instance(cls) -> "ModelRegistry":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._register_defaults()
        return cls._instance
    
    def _register_defaults(self) -> None:
        for spec in SKLEARN_MODELS:
            model_type = SklearnModelType(
                estimator_class=spec["class"],
                name=spec["name"],
                display_name=spec["display_name"],
                task_type=spec["task_type"],
                description=spec.get("description", ""),
                category=spec.get("category", "other"),
            )
            self.register(model_type)
    
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
                    "log_scale": p.log_scale,
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
