# Sampler Service Documentation

## Overview

The Sampler service (`app/services/sampler.py`) is the core data generation engine of the data-simulator backend. It orchestrates the entire pipeline from DAG validation to data generation and statistical computation.

## Architecture

The sampler ties together several key components:

1. **Validator** - Validates DAG structure and detects cycles
2. **Topological Sort** - Determines node generation order
3. **Distribution Registry** - Provides probability distributions
4. **Formula Parser** - Evaluates deterministic formulas
5. **Post-Processing** - Applies transformations (clipping, rounding, missing values)

## Main Functions

### `generate_preview(dag: DAGDefinition) -> PreviewResponse`

Generates a small preview of the data for quick validation and visualization.

**Flow:**
1. Validates the DAG
2. Uses `dag.metadata.preview_rows` (default 500)
3. Generates data using `_generate_data()`
4. Computes column statistics
5. Returns preview with warnings

**Example:**
```python
from app.services.sampler import generate_preview
from app.models.dag import DAGDefinition, NodeConfig, GenerationMetadata

dag = DAGDefinition(
    nodes=[...],
    edges=[...],
    metadata=GenerationMetadata(sample_size=1000, preview_rows=100)
)

preview = generate_preview(dag)
print(f"Preview: {preview.rows} rows")
print(f"Columns: {preview.columns}")
```

### `generate_data(dag: DAGDefinition) -> GenerationResult`

Generates the full dataset according to DAG specification.

**Flow:**
1. Validates the DAG
2. Generates `dag.metadata.sample_size` rows
3. For MVP: always synchronous
4. Returns GenerationResult with metadata

**Future:** Will support async generation for large datasets (> `settings.sync_threshold`).

### `_generate_data(dag, sample_size, seed) -> (DataFrame, seed, warnings)`

Core generation logic (internal function).

**Flow:**
1. Initialize RNG with seed (generates random seed if None)
2. Get topological order of nodes
3. For each node in order:
   - Sample stochastic nodes using distributions
   - Evaluate deterministic nodes using formulas
   - Apply post-processing
   - Add column to DataFrame
4. Return DataFrame, seed used, and warnings

## Node Scopes

The sampler handles three node scopes:

### 1. Row Scope (default)
Each row gets an independent sample.

```python
NodeConfig(
    id="height",
    scope="row",  # Each person has independent height
    distribution=DistributionConfig(
        type="normal",
        params={"mu": 170, "sigma": 10}
    )
)
```

**Static params:** Vectorized sampling (fast)
**Dynamic params:** Per-row sampling (slower but supports dependencies)

### 2. Global Scope
All rows share the same value.

```python
NodeConfig(
    id="inflation_rate",
    scope="global",  # Same rate for all rows
    distribution=DistributionConfig(
        type="uniform",
        params={"low": 0.02, "high": 0.05}
    )
)
```

Samples 1 value and broadcasts to all rows.

### 3. Group Scope
Samples per group (defined by `group_by` column).

```python
NodeConfig(
    id="team_budget",
    scope="group",
    group_by="team_id",  # Same budget per team
    distribution=DistributionConfig(
        type="normal",
        params={"mu": 100000, "sigma": 20000}
    )
)
```

**MVP:** Treats as row scope. Full implementation would group by `group_by` column.

## Parameter Resolution

The sampler handles different parameter types:

### Static Parameters
Literal numbers - resolved once, used for vectorized sampling.

```python
params={"mu": 170, "sigma": 10}  # Static - fast
```

### Dynamic Parameters
Reference other nodes - resolved per row.

```python
params={"mu": "base_salary * 1.2"}  # Formula - per-row
```

### Lookup Parameters
Look up values from context tables.

```python
from app.models.dag import LookupValue

params={
    "mu": LookupValue(
        lookup="salary_table",
        key="region",
        default=50000
    )
}
# Looks up context["salary_table"][row["region"]]
```

### Mapping Parameters
Inline category-to-value mappings.

```python
from app.models.dag import MappingValue

params={
    "mu": MappingValue(
        mapping={"north": 50000, "south": 45000},
        key="region",
        default=50000
    )
}
```

## Post-Processing

Applied in order:

1. **Clipping** - Constrain values to [min, max]
2. **Rounding** - Round to N decimals
3. **Missing Values** - Randomly set to NaN (MCAR)
4. **Type Casting** - Convert to target dtype

```python
PostProcessing(
    clip_min=0,
    clip_max=100,
    round_decimals=2,
    missing_rate=0.05  # 5% missing
)
```

## Statistics Computation

For each column, computes:

**Numeric columns:**
- mean, std, min, max, median
- null_count, null_rate

**Categorical columns:**
- categories (value counts)
- category_rates (proportions)
- null_count, null_rate

## Error Handling

The sampler raises specific exceptions:

- `ValidationError` - DAG validation failed
- `SampleError` - General sampling error
- `DistributionError` - Distribution-specific error
- `FormulaParseError` - Formula syntax error
- `UnknownVariableError` - Variable not found
- `LookupKeyMissingError` - Lookup key not found

All exceptions include:
- Descriptive message
- Error code
- Phase (validate, sample, resolve)
- Node ID (if applicable)
- Details dict

## Performance Considerations

### Vectorized vs Per-Row Sampling

**Vectorized (fast):**
- All parameters are static
- Samples all rows at once
- ~100x faster for large datasets

**Per-Row (slower):**
- Parameters reference other nodes
- Samples one row at a time
- Required for dependencies

### Optimization Strategies

1. **Order nodes efficiently** - Topological sort ensures dependencies
2. **Minimize dynamic params** - Use static params when possible
3. **Batch operations** - NumPy arrays for vectorization
4. **Lazy evaluation** - Only compute what's needed

## Integration with API

The sampler is called by API endpoints:

```python
# POST /api/v1/preview
@app.post("/preview")
async def preview_endpoint(dag: DAGDefinition):
    preview = generate_preview(dag)
    return preview

# POST /api/v1/generate
@app.post("/generate")
async def generate_endpoint(dag: DAGDefinition):
    result = generate_data(dag)
    return result
```

## Testing

See `test_sampler_example.py` for usage examples:

```bash
python test_sampler_example.py
```

Examples include:
1. Simple independent distributions
2. Dependent nodes (BMI from height/weight)
3. Categorical distributions
4. Context lookups (salary by region)

## Future Enhancements

1. **Async Generation** - Queue large jobs
2. **Streaming Output** - Generate in chunks
3. **Group Scope** - Full implementation
4. **Constraint Enforcement** - Reject invalid rows
5. **Incremental Generation** - Resume from checkpoint
6. **Parallel Sampling** - Multi-process for independent nodes
7. **GPU Acceleration** - For large-scale sampling

## Dependencies

- `numpy` - Random number generation and array operations
- `pandas` - DataFrame for structured data
- `pydantic` - Data validation and models
- `simpleeval` - Safe formula evaluation

## Files

- `app/services/sampler.py` - Main sampler implementation
- `app/services/validator.py` - DAG validation
- `app/services/distribution_registry.py` - Distribution catalog
- `app/services/formula_parser.py` - Formula evaluation
- `app/utils/topological_sort.py` - Node ordering
- `test_sampler_example.py` - Usage examples
