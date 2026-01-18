"""Example usage of the Sampler service.

This file demonstrates how to use the sampler service to generate data from a DAG.
It's meant as documentation and for manual testing when dependencies are installed.
"""

from app.models.dag import (
    DAGDefinition,
    NodeConfig,
    DAGEdge,
    DistributionConfig,
    GenerationMetadata,
    PostProcessing,
)
from app.services.sampler import generate_preview, generate_data


def example_simple_dag():
    """Example: Simple DAG with independent normal distributions."""

    dag = DAGDefinition(
        nodes=[
            NodeConfig(
                id="height",
                name="Height (cm)",
                kind="stochastic",
                dtype="float",
                scope="row",
                distribution=DistributionConfig(type="normal", params={"mu": 170.0, "sigma": 10.0}),
                post_processing=PostProcessing(round_decimals=1, clip_min=150.0, clip_max=200.0),
            ),
            NodeConfig(
                id="weight",
                name="Weight (kg)",
                kind="stochastic",
                dtype="float",
                scope="row",
                distribution=DistributionConfig(type="normal", params={"mu": 70.0, "sigma": 15.0}),
                post_processing=PostProcessing(round_decimals=1, clip_min=40.0, clip_max=120.0),
            ),
        ],
        edges=[],
        metadata=GenerationMetadata(sample_size=1000, seed=42, preview_rows=100),
    )

    return dag


def example_dependent_dag():
    """Example: DAG with dependencies - BMI calculated from height and weight."""

    dag = DAGDefinition(
        nodes=[
            NodeConfig(
                id="height_cm",
                name="Height (cm)",
                kind="stochastic",
                dtype="float",
                scope="row",
                distribution=DistributionConfig(type="normal", params={"mu": 170.0, "sigma": 10.0}),
                post_processing=PostProcessing(clip_min=150.0, clip_max=200.0),
            ),
            NodeConfig(
                id="weight_kg",
                name="Weight (kg)",
                kind="stochastic",
                dtype="float",
                scope="row",
                distribution=DistributionConfig(type="normal", params={"mu": 70.0, "sigma": 15.0}),
                post_processing=PostProcessing(clip_min=40.0, clip_max=120.0),
            ),
            NodeConfig(
                id="bmi",
                name="Body Mass Index",
                kind="deterministic",
                dtype="float",
                scope="row",
                formula="weight_kg / ((height_cm / 100) ** 2)",
                post_processing=PostProcessing(round_decimals=1),
            ),
        ],
        edges=[
            DAGEdge(source="height_cm", target="bmi"),
            DAGEdge(source="weight_kg", target="bmi"),
        ],
        metadata=GenerationMetadata(sample_size=1000, seed=42, preview_rows=100),
    )

    return dag


def example_categorical_dag():
    """Example: Categorical distribution with dynamic parameters."""

    dag = DAGDefinition(
        nodes=[
            NodeConfig(
                id="region",
                name="Region",
                kind="stochastic",
                dtype="category",
                scope="row",
                distribution=DistributionConfig(
                    type="categorical",
                    params={
                        "categories": ["north", "south", "east", "west"],
                        "probs": [0.3, 0.3, 0.2, 0.2],
                    },
                ),
            ),
            NodeConfig(
                id="is_urban",
                name="Is Urban",
                kind="stochastic",
                dtype="bool",
                scope="row",
                distribution=DistributionConfig(type="bernoulli", params={"p": 0.7}),
            ),
        ],
        edges=[],
        metadata=GenerationMetadata(sample_size=1000, seed=42, preview_rows=100),
    )

    return dag


def example_with_context():
    """Example: Using context for lookups (salary based on region)."""
    from app.models.dag import MappingValue

    dag = DAGDefinition(
        nodes=[
            NodeConfig(
                id="region",
                name="Region",
                kind="stochastic",
                dtype="category",
                scope="row",
                distribution=DistributionConfig(
                    type="categorical",
                    params={
                        "categories": ["north", "south", "east", "west"],
                        "probs": [0.25, 0.25, 0.25, 0.25],
                    },
                ),
            ),
            NodeConfig(
                id="base_salary",
                name="Base Salary",
                kind="stochastic",
                dtype="float",
                scope="row",
                distribution=DistributionConfig(
                    type="normal",
                    params={
                        "mu": MappingValue(
                            mapping={"north": 50000, "south": 45000, "east": 55000, "west": 52000},
                            key="region",
                            default=50000,
                        ),
                        "sigma": 5000,
                    },
                ),
                post_processing=PostProcessing(round_decimals=0),
            ),
        ],
        edges=[
            DAGEdge(source="region", target="base_salary"),
        ],
        metadata=GenerationMetadata(sample_size=1000, seed=42, preview_rows=100),
        context={},
    )

    return dag


def run_examples():
    """Run all examples (requires dependencies to be installed)."""

    print("=" * 60)
    print("Example 1: Simple DAG")
    print("=" * 60)
    dag1 = example_simple_dag()
    preview1 = generate_preview(dag1)
    print(f"Generated {preview1.rows} preview rows")
    print(f"Columns: {preview1.columns}")
    print(f"First 3 rows:")
    for row in preview1.data[:3]:
        print(f"  {row}")
    print(f"\nColumn Stats:")
    for stat in preview1.column_stats:
        print(f"  {stat.node_id}: mean={stat.mean:.1f}, std={stat.std:.1f}")

    print("\n" + "=" * 60)
    print("Example 2: Dependent DAG (BMI)")
    print("=" * 60)
    dag2 = example_dependent_dag()
    preview2 = generate_preview(dag2)
    print(f"Generated {preview2.rows} preview rows")
    print(f"Columns: {preview2.columns}")
    print(f"First 3 rows:")
    for row in preview2.data[:3]:
        print(
            f"  height={row['height_cm']:.1f}, weight={row['weight_kg']:.1f}, bmi={row['bmi']:.1f}"
        )

    print("\n" + "=" * 60)
    print("Example 3: Categorical DAG")
    print("=" * 60)
    dag3 = example_categorical_dag()
    preview3 = generate_preview(dag3)
    print(f"Generated {preview3.rows} preview rows")
    print(f"First 5 rows:")
    for row in preview3.data[:5]:
        print(f"  region={row['region']}, is_urban={row['is_urban']}")
    print(f"\nRegion distribution:")
    region_stats = next(s for s in preview3.column_stats if s.node_id == "region")
    for cat, rate in region_stats.category_rates.items():
        print(f"  {cat}: {rate:.1%}")

    print("\n" + "=" * 60)
    print("Example 4: With Context (Salary by Region)")
    print("=" * 60)
    dag4 = example_with_context()
    preview4 = generate_preview(dag4)
    print(f"Generated {preview4.rows} preview rows")
    print(f"First 5 rows:")
    for row in preview4.data[:5]:
        print(f"  region={row['region']}, base_salary=${row['base_salary']:,.0f}")

    print("\n" + "=" * 60)
    print("Full Generation")
    print("=" * 60)
    result = generate_data(dag1)
    print(f"Status: {result.status}")
    print(f"Rows: {result.rows}")
    print(f"Columns: {result.columns}")
    print(f"Seed: {result.seed}")


if __name__ == "__main__":
    # This will only work if dependencies are installed
    try:
        run_examples()
    except ImportError as e:
        print(f"Dependencies not installed: {e}")
        print("Please install: pip install -e .")
