# Model Registry

The model registry provides auto-discovery and management of sklearn regression models for the data simulator's modeling workbench.

## Features

### Auto-Discovery
The registry automatically discovers all sklearn regressors using `sklearn.utils.all_estimators(type_filter="regressor")`. This means:
- New regressors from future sklearn releases are automatically available
- No manual registration required for standard sklearn models
- Abstract and meta-estimators are filtered out

### Parameter Enrichment
Parameters are enriched with metadata for better UI rendering:

| Field | Description |
|-------|-------------|
| `ui_group` | "core", "advanced", or "internal" for collapsing in UI |
| `recommended_min` / `recommended_max` | Suggested ranges for hyperparameter tuning |
| `log_scale` | Whether to use logarithmic scale for sliders |
| `choices` | Valid options for dropdown parameters |
| `description` | Human-friendly description |

### UI Groups

Parameters are categorized by importance:

- **Core**: High-impact parameters always visible (e.g., `alpha`, `C`, `n_estimators`, `max_depth`)
- **Advanced**: Less critical parameters collapsed by default (e.g., `tol`, `max_iter`, `criterion`)
- **Internal**: Hidden by default (e.g., `verbose`, `n_jobs`, `random_state`)

## Available Models

The registry includes all sklearn regressors, organized by category:

### Linear Models
- `linear_regression` - Ordinary Least Squares
- `ridge` - L2 regularization
- `lasso` - L1 regularization
- `elastic_net` - Combined L1/L2
- `bayesian_ridge` - Bayesian ridge regression
- `lars` - Least Angle Regression
- `sgd_regressor` - Stochastic Gradient Descent

### Ensemble Models
- `random_forest_regressor` - Random Forest
- `gradient_boosting_regressor` - Gradient Boosting
- `hist_gradient_boosting_regressor` - Histogram-based Gradient Boosting
- `extra_trees_regressor` - Extremely Randomized Trees
- `ada_boost_regressor` - AdaBoost
- `bagging_regressor` - Bootstrap Aggregating

### Support Vector Machines
- `svr` - Support Vector Regressor
- `linear_svr` - Linear SVR
- `nu_svr` - Nu-SVR

### Neighbors
- `k_neighbors_regressor` - K-Nearest Neighbors
- `radius_neighbors_regressor` - Radius Neighbors

### Neural Networks
- `mlp_regressor` - Multi-layer Perceptron

### Gaussian Process
- `gaussian_process_regressor` - Gaussian Process

### Kernel Methods
- `kernel_ridge` - Kernel Ridge Regression

## Usage

### Python API

```python
from app.services.model_registry import get_model_registry

# Get the registry singleton
registry = get_model_registry()

# List all models
models = registry.list_all()

# Get a specific model
model = registry.get("ridge")

# Filter by category
linear_models = registry.list_by_category("linear")
```

### REST API

```bash
# List all models
GET /api/modeling/models

# Fit a model
POST /api/modeling/fit
{
  "pipeline_version_id": "...",
  "name": "My Model",
  "model_name": "ridge",
  "target": "income",
  "features": ["age", "education"],
  "model_params": {"alpha": 1.0}
}
```

## Adding Custom Models

To register a custom model:

```python
from app.services.model_registry import get_model_registry, SklearnModelType

# Create a custom model type
custom = SklearnModelType(
    estimator_class=MyCustomRegressor,
    name="my_custom_regressor",
    display_name="My Custom Regressor",
    task_type="regression",
    category="custom",
    description="A custom regression model",
)

# Register it
registry = get_model_registry()
registry.register(custom)
```

## Configuration

### Excluding Estimators
The `EXCLUDED_ESTIMATORS` set in `model_registry.py` controls which estimators are skipped during discovery.

### Parameter Enrichment
Customize parameter behavior by updating these maps:
- `PARAM_CHOICES` - Valid options for dropdown parameters
- `NUMERIC_CONSTRAINTS` - Min/max values and log scales
- `PARAM_DESCRIPTIONS` - Human-friendly descriptions
- `CORE_PARAMS` / `ADVANCED_PARAMS` / `INTERNAL_PARAMS` - UI grouping
