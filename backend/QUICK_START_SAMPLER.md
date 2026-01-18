# Quick Start: Using the Sampler Service

## Basic Usage

```python
from app.services.sampler import generate_preview, generate_data
from app.models.dag import DAGDefinition, NodeConfig, GenerationMetadata

# Define your DAG
dag = DAGDefinition(
    nodes=[
        NodeConfig(
            id="age",
            name="Age",
            kind="stochastic",
            distribution={"type": "normal", "params": {"mu": 35, "sigma": 10}}
        )
    ],
    metadata=GenerationMetadata(sample_size=1000)
)

# Generate preview (small sample)
preview = generate_preview(dag)
print(f"Preview: {preview.rows} rows, {len(preview.columns)} columns")

# Generate full dataset
result = generate_data(dag)
print(f"Generated {result.rows} rows successfully")
```

## Common Patterns

### 1. Simple Independent Distributions

```python
nodes = [
    NodeConfig(
        id="height",
        kind="stochastic",
        distribution={"type": "normal", "params": {"mu": 170, "sigma": 10}}
    ),
    NodeConfig(
        id="weight", 
        kind="stochastic",
        distribution={"type": "normal", "params": {"mu": 70, "sigma": 15}}
    )
]
```

### 2. Dependent Calculations

```python
nodes = [
    NodeConfig(id="price", kind="stochastic", ...),
    NodeConfig(id="tax", kind="stochastic", ...),
    NodeConfig(
        id="total",
        kind="deterministic",
        formula="price + tax"
    )
]
edges = [
    DAGEdge(source="price", target="total"),
    DAGEdge(source="tax", target="total")
]
```

### 3. Categorical with Probabilities

```python
NodeConfig(
    id="region",
    kind="stochastic",
    distribution={
        "type": "categorical",
        "params": {
            "categories": ["north", "south", "east", "west"],
            "probs": [0.3, 0.3, 0.2, 0.2]
        }
    }
)
```

### 4. Dynamic Parameters

```python
from app.models.dag import MappingValue

NodeConfig(
    id="salary",
    kind="stochastic",
    distribution={
        "type": "normal",
        "params": {
            "mu": MappingValue(
                mapping={"manager": 80000, "developer": 60000},
                key="role",
                default=50000
            ),
            "sigma": 5000
        }
    }
)
```

### 5. Post-Processing

```python
NodeConfig(
    id="score",
    kind="stochastic",
    distribution={"type": "normal", "params": {"mu": 75, "sigma": 15}},
    post_processing={
        "clip_min": 0,
        "clip_max": 100,
        "round_decimals": 0,
        "missing_rate": 0.05
    }
)
```

## Error Handling

```python
from app.core import ValidationError, SampleError

try:
    result = generate_data(dag)
except ValidationError as e:
    print(f"DAG validation failed: {e.message}")
    print(f"Errors: {e.details['errors']}")
except SampleError as e:
    print(f"Generation failed at node {e.node_id}: {e.message}")
```

## Accessing Results

```python
# Preview Response
preview = generate_preview(dag)
for row in preview.data[:5]:  # First 5 rows
    print(row)

# Statistics
for stat in preview.column_stats:
    if stat.mean:  # Numeric
        print(f"{stat.node_id}: mean={stat.mean:.2f}, std={stat.std:.2f}")
    elif stat.categories:  # Categorical
        print(f"{stat.node_id}: categories={list(stat.categories.keys())}")

# Generation Result
result = generate_data(dag)
print(f"Status: {result.status}")
print(f"Rows: {result.rows}")
print(f"Seed: {result.seed}")
print(f"Warnings: {result.warnings}")
```

## Tips

1. **Always set a seed** for reproducibility: `metadata=GenerationMetadata(seed=42)`
2. **Start small** - test with preview before full generation
3. **Check warnings** - they indicate potential issues
4. **Use post-processing** - for realistic data (clipping, rounding, missing values)
5. **Order matters** - dependencies must be declared in edges

## See Also

- `SAMPLER_DOCUMENTATION.md` - Full documentation
- `test_sampler_example.py` - Complete examples
- `app/services/sampler.py` - Implementation
