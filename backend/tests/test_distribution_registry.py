"""Tests for distribution registry."""

import numpy as np
import pytest

from app.core.exceptions import DistributionError
from app.services.distribution_registry import (
    BernoulliDistribution,
    CategoricalDistribution,
    DistributionRegistry,
    NormalDistribution,
    UniformDistribution,
    get_distribution_registry,
)


class TestDistributionRegistry:
    """Test the DistributionRegistry class."""

    def test_register_and_get_distribution(self):
        """Test registering and retrieving distributions."""
        registry = DistributionRegistry()
        normal = NormalDistribution()

        registry.register_distribution(normal)
        retrieved = registry.get_distribution("normal")

        assert retrieved.name == "normal"
        assert retrieved.display_name == "Normal"

    def test_duplicate_registration_raises_error(self):
        """Test that registering duplicate distribution raises error."""
        registry = DistributionRegistry()
        normal = NormalDistribution()

        registry.register_distribution(normal)

        with pytest.raises(ValueError, match="already registered"):
            registry.register_distribution(normal)

    def test_get_nonexistent_distribution_raises_error(self):
        """Test that getting non-existent distribution raises error."""
        registry = DistributionRegistry()

        with pytest.raises(DistributionError, match="Unknown distribution"):
            registry.get_distribution("nonexistent")

    def test_get_available_distributions(self):
        """Test getting list of available distributions."""
        registry = DistributionRegistry()
        registry.register_distribution(NormalDistribution())
        registry.register_distribution(UniformDistribution())

        available = registry.get_available_distributions()

        assert len(available) == 2
        names = [dist.name for dist in available]
        assert "normal" in names
        assert "uniform" in names

    def test_is_registered(self):
        """Test checking if distribution is registered."""
        registry = DistributionRegistry()
        registry.register_distribution(NormalDistribution())

        assert registry.is_registered("normal") is True
        assert registry.is_registered("nonexistent") is False

    def test_global_registry_has_builtin_distributions(self):
        """Test that global registry has all built-in distributions."""
        registry = get_distribution_registry()

        assert registry.is_registered("normal")
        assert registry.is_registered("uniform")
        assert registry.is_registered("categorical")
        assert registry.is_registered("bernoulli")


class TestNormalDistribution:
    """Test the Normal distribution."""

    def test_sample_basic(self):
        """Test basic sampling from normal distribution."""
        dist = NormalDistribution()
        rng = np.random.default_rng(42)

        samples = dist.sample({"mu": 0.0, "sigma": 1.0}, 100, rng)

        assert len(samples) == 100
        assert samples.dtype == np.float64
        # Check that mean is roughly 0 (with some tolerance)
        assert -0.5 < np.mean(samples) < 0.5
        # Check that std is roughly 1 (with some tolerance)
        assert 0.5 < np.std(samples) < 1.5

    def test_sample_with_different_params(self):
        """Test sampling with different mu and sigma."""
        dist = NormalDistribution()
        rng = np.random.default_rng(42)

        samples = dist.sample({"mu": 10.0, "sigma": 2.0}, 100, rng)

        assert 8.0 < np.mean(samples) < 12.0
        assert 1.0 < np.std(samples) < 3.0

    def test_missing_parameter_raises_error(self):
        """Test that missing parameters raise error."""
        dist = NormalDistribution()
        rng = np.random.default_rng(42)

        with pytest.raises(DistributionError, match="Missing required parameter"):
            dist.sample({"mu": 0.0}, 10, rng)

    def test_negative_sigma_raises_error(self):
        """Test that negative sigma raises error."""
        dist = NormalDistribution()
        rng = np.random.default_rng(42)

        with pytest.raises(DistributionError, match="non-negative"):
            dist.sample({"mu": 0.0, "sigma": -1.0}, 10, rng)

    def test_distribution_info(self):
        """Test distribution metadata."""
        dist = NormalDistribution()
        info = dist.get_info()

        assert info.name == "normal"
        assert info.display_name == "Normal"
        assert info.category == "continuous"
        assert info.default_dtype == "float"
        assert len(info.parameters) == 2


class TestUniformDistribution:
    """Test the Uniform distribution."""

    def test_sample_basic(self):
        """Test basic sampling from uniform distribution."""
        dist = UniformDistribution()
        rng = np.random.default_rng(42)

        samples = dist.sample({"low": 0.0, "high": 10.0}, 100, rng)

        assert len(samples) == 100
        assert samples.dtype == np.float64
        assert np.all(samples >= 0.0)
        assert np.all(samples < 10.0)

    def test_invalid_bounds_raises_error(self):
        """Test that low >= high raises error."""
        dist = UniformDistribution()
        rng = np.random.default_rng(42)

        with pytest.raises(DistributionError, match="low must be less than high"):
            dist.sample({"low": 10.0, "high": 5.0}, 10, rng)

    def test_distribution_info(self):
        """Test distribution metadata."""
        dist = UniformDistribution()
        info = dist.get_info()

        assert info.name == "uniform"
        assert info.category == "continuous"
        assert info.default_dtype == "float"


class TestCategoricalDistribution:
    """Test the Categorical distribution."""

    def test_sample_basic(self):
        """Test basic sampling from categorical distribution."""
        dist = CategoricalDistribution()
        rng = np.random.default_rng(42)

        samples = dist.sample(
            {"categories": ["A", "B", "C"], "probs": [0.5, 0.3, 0.2]},
            100,
            rng,
        )

        assert len(samples) == 100
        # Check that all samples are valid categories
        assert all(s in ["A", "B", "C"] for s in samples)

    def test_probability_distribution(self):
        """Test that sampling respects probabilities."""
        dist = CategoricalDistribution()
        rng = np.random.default_rng(42)

        # Sample many times to get statistical confidence
        samples = dist.sample(
            {"categories": ["A", "B"], "probs": [0.8, 0.2]},
            1000,
            rng,
        )

        # Count occurrences
        counts = {"A": 0, "B": 0}
        for s in samples:
            counts[s] += 1

        # Check that A appears roughly 80% of the time (with tolerance)
        assert 0.7 < counts["A"] / 1000 < 0.9

    def test_mismatched_lengths_raises_error(self):
        """Test that mismatched categories and probs raises error."""
        dist = CategoricalDistribution()
        rng = np.random.default_rng(42)

        with pytest.raises(DistributionError, match="same length"):
            dist.sample(
                {"categories": ["A", "B"], "probs": [0.5, 0.3, 0.2]},
                10,
                rng,
            )

    def test_probs_not_summing_to_one_raises_error(self):
        """Test that probabilities not summing to 1 raises error."""
        dist = CategoricalDistribution()
        rng = np.random.default_rng(42)

        with pytest.raises(DistributionError, match="sum to 1.0"):
            dist.sample(
                {"categories": ["A", "B"], "probs": [0.5, 0.3]},
                10,
                rng,
            )

    def test_negative_probs_raises_error(self):
        """Test that negative probabilities raise error."""
        dist = CategoricalDistribution()
        rng = np.random.default_rng(42)

        with pytest.raises(DistributionError, match="non-negative"):
            dist.sample(
                {"categories": ["A", "B"], "probs": [1.2, -0.2]},
                10,
                rng,
            )

    def test_empty_categories_raises_error(self):
        """Test that empty categories list raises error."""
        dist = CategoricalDistribution()
        rng = np.random.default_rng(42)

        with pytest.raises(DistributionError, match="cannot be empty"):
            dist.sample({"categories": [], "probs": []}, 10, rng)

    def test_distribution_info(self):
        """Test distribution metadata."""
        dist = CategoricalDistribution()
        info = dist.get_info()

        assert info.name == "categorical"
        assert info.category == "categorical"
        assert info.default_dtype == "category"


class TestBernoulliDistribution:
    """Test the Bernoulli distribution."""

    def test_sample_basic(self):
        """Test basic sampling from Bernoulli distribution."""
        dist = BernoulliDistribution()
        rng = np.random.default_rng(42)

        samples = dist.sample({"p": 0.5}, 100, rng)

        assert len(samples) == 100
        assert samples.dtype == np.int64
        # Check that all samples are 0 or 1
        assert np.all((samples == 0) | (samples == 1))

    def test_probability_of_success(self):
        """Test that sampling respects probability parameter."""
        dist = BernoulliDistribution()
        rng = np.random.default_rng(42)

        # Sample many times with high p
        samples = dist.sample({"p": 0.8}, 1000, rng)

        # Check that roughly 80% are 1s (with tolerance)
        success_rate = np.mean(samples)
        assert 0.7 < success_rate < 0.9

    def test_p_out_of_range_raises_error(self):
        """Test that p outside [0,1] raises error."""
        dist = BernoulliDistribution()
        rng = np.random.default_rng(42)

        with pytest.raises(DistributionError, match="between 0 and 1"):
            dist.sample({"p": 1.5}, 10, rng)

        with pytest.raises(DistributionError, match="between 0 and 1"):
            dist.sample({"p": -0.1}, 10, rng)

    def test_edge_cases(self):
        """Test edge cases p=0 and p=1."""
        dist = BernoulliDistribution()
        rng = np.random.default_rng(42)

        # p=0 should always give 0
        samples = dist.sample({"p": 0.0}, 10, rng)
        assert np.all(samples == 0)

        # p=1 should always give 1
        samples = dist.sample({"p": 1.0}, 10, rng)
        assert np.all(samples == 1)

    def test_distribution_info(self):
        """Test distribution metadata."""
        dist = BernoulliDistribution()
        info = dist.get_info()

        assert info.name == "bernoulli"
        assert info.category == "discrete"
        assert info.default_dtype == "int"


class TestReproducibility:
    """Test that sampling is reproducible with same seed."""

    def test_reproducible_sampling(self):
        """Test that same seed produces same samples."""
        dist = NormalDistribution()

        rng1 = np.random.default_rng(42)
        samples1 = dist.sample({"mu": 0.0, "sigma": 1.0}, 10, rng1)

        rng2 = np.random.default_rng(42)
        samples2 = dist.sample({"mu": 0.0, "sigma": 1.0}, 10, rng2)

        assert np.allclose(samples1, samples2)

    def test_different_seeds_produce_different_samples(self):
        """Test that different seeds produce different samples."""
        dist = NormalDistribution()

        rng1 = np.random.default_rng(42)
        samples1 = dist.sample({"mu": 0.0, "sigma": 1.0}, 10, rng1)

        rng2 = np.random.default_rng(123)
        samples2 = dist.sample({"mu": 0.0, "sigma": 1.0}, 10, rng2)

        assert not np.allclose(samples1, samples2)
