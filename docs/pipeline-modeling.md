# Pipeline & Modeling Workbench

This document describes the Pipeline & Modeling Workbench feature, which enables users to create reproducible data transformation pipelines and train machine learning models on synthetic data.

## Overview

The Pipeline Workbench extends the Data Simulator by providing:
- **Versioned Pipelines**: Create reproducible data transformation pipelines
- **Transform Steps**: Add derived columns using formulas and built-in transforms
- **ML Modeling**: Train and evaluate sklearn models on pipeline data
- **Lineage Tracking**: Track how derived columns are computed

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   PipelineView  │   FormulaBar    │   ModelsPanel               │
│   (Main UI)     │   (Add steps)   │   (Train models)            │
├─────────────────┴─────────────────┴─────────────────────────────┤
│                    pipelineStore.ts                              │
│                    (State management)                            │
├─────────────────────────────────────────────────────────────────┤
│               pipelineApi.ts / modelingApi.ts                    │
│               (API clients)                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Backend                                  │
├─────────────────────────────────────────────────────────────────┤
│   /api/pipelines     /api/transforms     /api/modeling          │
│   (CRUD routes)      (List transforms)   (Fit/Predict)          │
├─────────────────────────────────────────────────────────────────┤
│   pipeline_service   transform_registry   modeling_service      │
│   (Business logic)   (Transform catalog)  (ML operations)       │
├─────────────────────────────────────────────────────────────────┤
│   pipeline_source    model_registry       hashing               │
│   (Load data)        (Model catalog)      (Reproducibility)     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Database                                   │
├─────────────────┬─────────────────┬─────────────────────────────┤
│    Pipeline     │ PipelineVersion │     ModelFit                │
│    (Entity)     │ (Steps/Schema)  │     (Trained model)         │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## Data Model

### Pipeline

Each pipeline represents a reproducible data transformation configuration:

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| project_id | FK | Parent project |
| name | String | Human-readable name |
| source_type | String | "simulation" or "upload" |
| current_version_id | FK | Active version |
| created_at | DateTime | Creation timestamp |

### PipelineVersion

Each version contains the full transformation recipe:

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| pipeline_id | FK | Parent pipeline |
| version_number | Integer | Monotonically increasing |
| steps | JSON | List of transform steps |
| input_schema | JSON | Source column definitions |
| output_schema | JSON | Result column definitions |
| lineage | JSON | Column derivation graph |
| source_dag_version_id | String | DAG version used |
| source_seed | Integer | Random seed |
| source_sample_size | Integer | Number of rows |
| source_fingerprint | String | SHA-256 of source config |
| steps_hash | String | SHA-256 of steps |
| created_at | DateTime | Creation timestamp |

### ModelFit

Stores trained model artifacts and metrics:

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| pipeline_version_id | FK | Pipeline version used |
| name | String | Human-readable name |
| model_type | String | e.g., "linear_regression" |
| task_type | String | "regression" or "classification" |
| target_column | String | Target variable name |
| feature_spec | JSON | Feature column list |
| split_spec | JSON | Train/test split config |
| model_params | JSON | Hyperparameters |
| artifact_blob | Text | Base64 pickled model |
| metrics | JSON | Evaluation metrics |
| coefficients | JSON | Model coefficients |
| diagnostics | JSON | Additional diagnostics |
| created_at | DateTime | Creation timestamp |

## API Reference

### Pipeline Endpoints

#### POST /api/pipelines
Create a new pipeline from a simulation source.

**Request:**
```json
{
  "project_id": "uuid",
  "name": "My Pipeline",
  "source": {
    "type": "simulation",
    "dag_version_id": "uuid",
    "seed": 42,
    "sample_size": 1000
  }
}
```

**Response:**
```json
{
  "pipeline_id": "uuid",
  "current_version_id": "uuid",
  "schema": [{"name": "income", "dtype": "float"}, ...]
}
```

#### POST /api/pipelines/{id}/versions/{vid}/steps
Add a transform step, creating a new version.

**Request:**
```json
{
  "step": {
    "type": "formula",
    "output_column": "log_income",
    "params": {"expression": "log(income)"},
    "allow_overwrite": false
  },
  "preview_limit": 200
}
```

**Response:**
```json
{
  "new_version_id": "uuid",
  "schema": [...],
  "added_columns": ["log_income"],
  "preview_rows": [...],
  "warnings": 0
}
```

#### GET /api/pipelines/{id}/versions/{vid}/materialization
Materialize pipeline data.

**Query Parameters:**
- `limit` (default: 1000)
- `columns` (optional, comma-separated)

**Response:**
```json
{
  "schema": [...],
  "rows": [...]
}
```

### Modeling Endpoints

#### POST /api/modeling/fit
Train a model on pipeline data.

**Request:**
```json
{
  "pipeline_version_id": "uuid",
  "name": "Income Predictor",
  "model_name": "linear_regression",
  "target": "income",
  "features": ["age", "education"],
  "model_params": {},
  "split_spec": {
    "type": "random",
    "test_size": 0.2,
    "random_state": 42
  }
}
```

**Response:**
```json
{
  "model_id": "uuid",
  "metrics": {"r2": 0.85, "rmse": 1234.5, "mae": 987.6},
  "coefficients": {"age": 500.2, "education": 2000.5, "intercept": 15000},
  "diagnostics": {...}
}
```

#### POST /api/modeling/predict
Generate predictions using a trained model.

**Request:**
```json
{
  "model_id": "uuid",
  "pipeline_version_id": "uuid",  // optional, uses training version by default
  "limit": 1000
}
```

**Response:**
```json
{
  "predictions": [45000.5, 52000.2, ...],
  "preview_rows_with_pred": [
    {"age": 30, "education": 4, "prediction": 45000.5},
    ...
  ]
}
```

## Available Transforms

| Name | Description | Parameters |
|------|-------------|------------|
| formula | Evaluate a safe expression | `expression`: formula string |
| log | Natural logarithm | `column`: source column |
| sqrt | Square root | `column`: source column |
| exp | Exponential (e^x) | `column`: source column |
| bin | Bin into categories | `column`, `bins` (default: 5) |

### Formula Syntax

The formula transform supports a safe subset of Python/NumPy operations:

**Operators:** `+`, `-`, `*`, `/`, `**`, `//`, `%`, `<`, `>`, `<=`, `>=`, `==`, `!=`, `and`, `or`, `not`

**Functions:**
- Math: `log`, `exp`, `sqrt`, `abs`, `min`, `max`, `floor`, `ceil`, `round`
- Conditionals: `where(condition, true_val, false_val)`, `if_else`
- Null handling: `isnan`, `isnull`, `coalesce`
- Clipping: `clip(x, low, high)`, `clamp`

**Examples:**
```python
log(income)                           # Natural log
income * 12                           # Annual from monthly
where(age >= 18, 1, 0)               # Binary encoding
log(income + 1)                       # Handle zeros
clip(score, 0, 100)                  # Constrain values
```

## Available Models

| Name | Task | Metrics |
|------|------|---------|
| linear_regression | Regression | R², RMSE, MAE |
| logistic_regression | Classification | Accuracy, ROC-AUC, Log Loss |

## Reproducibility

The pipeline system ensures reproducibility through:

1. **Source Fingerprinting**: Each pipeline version stores a SHA-256 hash of (dag_version_id, seed, sample_size, sampler_version, registry_version)

2. **Steps Hashing**: Transform steps are hashed to detect equivalent pipelines

3. **Deterministic Generation**: The same fingerprint always produces identical data

4. **Version Tracking**: Every step creates a new immutable version

## Usage Guide

### Creating a Pipeline

1. Navigate to the **DAG Canvas** tab
2. Create nodes and edges for your data generation
3. Go to **Data Preview** and generate a preview
4. Navigate to **Pipeline** tab
5. Click **Create Pipeline** and configure:
   - Pipeline name
   - Random seed (for reproducibility)
   - Sample size

### Adding Transform Steps

1. In the Pipeline tab, use the **FormulaBar**:
   - Select transform type (formula, log, sqrt, etc.)
   - Enter output column name
   - Enter expression or select source column
   - Click **Apply**

2. Each step creates a new version automatically

3. View steps in the **Recipe** panel on the right

### Training Models

1. Switch to the **Models** subtab
2. Select:
   - Target column
   - Feature columns (multi-select)
   - Model type
   - Train/test split configuration

3. Click **Fit Model**

4. View results:
   - Metrics (R², accuracy, etc.)
   - Coefficients table
   - Diagnostics

### Materializing Data

1. Set desired row limit
2. Click **Materialize** to generate full dataset
3. View in the data table

## Default Values

| Parameter | Default Value |
|-----------|---------------|
| preview_limit | 200 rows |
| materialize limit | 1000 rows |
| allow_overwrite | false |
| split_spec.type | "random" |
| split_spec.test_size | 0.2 |
| split_spec.random_state | 42 |
| logistic_regression.C | 1.0 |
| logistic_regression.max_iter | 200 |

## Testing

### Backend Tests

```bash
cd backend
pytest tests/test_pipeline_service.py -v
pytest tests/test_modeling_service.py -v
```

### E2E Manual Test

1. Create a DAG with nodes: income (normal), age (uniform_int)
2. Generate preview
3. Create pipeline (seed=42, n=5000)
4. Add step: `log_income = log(income)`
5. Materialize 200 rows with columns [income, log_income, age]
6. Fit linear regression: target=income, features=[age]
7. Verify metrics and coefficients

## Future Enhancements

- [ ] Complex group/window scope transforms
- [ ] Drag-and-drop step reordering
- [ ] Hyperparameter search
- [ ] Multiple dataset joins
- [ ] Parquet caching for large datasets
- [ ] Model export (ONNX, PMML)
