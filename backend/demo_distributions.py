"""Demo script to show distribution registry functionality.

This script demonstrates how to use the distribution registry to sample
from different probability distributions.
"""

import numpy as np

from app.services.distribution_registry import get_distribution_registry


def main():
    """Demonstrate distribution registry usage."""
    # Get the global registry
    registry = get_distribution_registry()

    # Create a random number generator with fixed seed for reproducibility
    rng = np.random.default_rng(42)

    print("=" * 70)
    print("Distribution Registry Demo")
    print("=" * 70)

    # Show available distributions
    print("\nAvailable Distributions:")
    print("-" * 70)
    available = registry.get_available_distributions()
    for dist_info in available:
        print(f"\n{dist_info.display_name} ({dist_info.name})")
        print(f"  Category: {dist_info.category}")
        print(f"  Default dtype: {dist_info.default_dtype}")
        print(f"  Description: {dist_info.description}")
        print("  Parameters:")
        for param in dist_info.parameters:
            required = "required" if param.required else "optional"
            default = f", default={param.default}" if param.default is not None else ""
            print(f"    - {param.name} ({param.type}, {required}{default}): {param.description}")

    # Demonstrate sampling from each distribution
    print("\n" + "=" * 70)
    print("Sampling Examples")
    print("=" * 70)

    # Normal distribution
    print("\n1. Normal Distribution (mu=0, sigma=1)")
    print("-" * 70)
    normal = registry.get_distribution("normal")
    samples = normal.sample({"mu": 0.0, "sigma": 1.0}, 10, rng)
    print(f"Samples: {samples}")
    print(f"Mean: {np.mean(samples):.3f}, Std: {np.std(samples):.3f}")

    # Uniform distribution
    print("\n2. Uniform Distribution (low=0, high=100)")
    print("-" * 70)
    uniform = registry.get_distribution("uniform")
    samples = uniform.sample({"low": 0.0, "high": 100.0}, 10, rng)
    print(f"Samples: {samples}")
    print(f"Min: {np.min(samples):.3f}, Max: {np.max(samples):.3f}")

    # Categorical distribution
    print("\n3. Categorical Distribution")
    print("-" * 70)
    categorical = registry.get_distribution("categorical")
    samples = categorical.sample(
        {"categories": ["Red", "Green", "Blue"], "probs": [0.5, 0.3, 0.2]}, 20, rng
    )
    print(f"Samples: {samples}")
    # Count occurrences
    unique, counts = np.unique(samples, return_counts=True)
    print("Counts:")
    for cat, count in zip(unique, counts, strict=False):
        print(f"  {cat}: {count} ({count / 20 * 100:.1f}%)")

    # Bernoulli distribution
    print("\n4. Bernoulli Distribution (p=0.7)")
    print("-" * 70)
    bernoulli = registry.get_distribution("bernoulli")
    samples = bernoulli.sample({"p": 0.7}, 20, rng)
    print(f"Samples: {samples}")
    print(f"Success rate: {np.mean(samples):.2f} (expected: 0.7)")

    # Demonstrate reproducibility
    print("\n" + "=" * 70)
    print("Reproducibility Demo")
    print("=" * 70)
    print("\nSampling with seed 42:")
    rng1 = np.random.default_rng(42)
    samples1 = normal.sample({"mu": 0.0, "sigma": 1.0}, 5, rng1)
    print(f"  {samples1}")

    print("\nSampling again with seed 42:")
    rng2 = np.random.default_rng(42)
    samples2 = normal.sample({"mu": 0.0, "sigma": 1.0}, 5, rng2)
    print(f"  {samples2}")

    print(f"\nAre they equal? {np.allclose(samples1, samples2)}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
