"""Comprehensive tests for extended distributions in the Data Simulator.

This test suite covers Phase 6-7 features:
- Integration with scipy.stats
- Common distributions (Poisson, Exponential, Beta, Gamma, Binomial, LogNormal)
- Mixture distributions
- Truncated distributions
- Parameter validation
- Dtype compatibility
- Statistical validation (mean/variance checks)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
import scipy.stats as stats

from app.core.exceptions import DistributionError
from app.models.distribution import DistributionInfo, ParameterInfo
from app.services.distribution_registry import (
    BaseDistribution,
    DistributionRegistry,
    get_distribution_registry,
)


# =============================================================================
# SciPy Integration Tests
# =============================================================================


@pytest.mark.skip(reason="SciPy integration not implemented yet")
class TestSciPyIntegration:
    """Test integration with scipy.stats for accessing any distribution by name."""

    def test_scipy_distribution_by_name(self):
        """Test accessing any scipy.stats distribution by name."""
        # This should allow using any scipy distribution
        registry = get_distribution_registry()

        # Should be able to use scipy distributions by name
        dist = registry.get_distribution("scipy:norm")
        assert dist is not None
        assert dist.name == "scipy:norm"

    def test_scipy_beta_distribution(self):
        """Test scipy beta distribution access."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("scipy:beta")

        rng = np.random.default_rng(42)
        samples = dist.sample({"a": 2.0, "b": 5.0}, 1000, rng)

        assert len(samples) == 1000
        assert np.all(samples >= 0)
        assert np.all(samples <= 1)

    def test_scipy_parameter_validation(self):
        """Test that scipy distributions validate parameters correctly."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("scipy:gamma")

        rng = np.random.default_rng(42)

        # Should raise error for invalid shape parameter
        with pytest.raises(DistributionError):
            dist.sample({"a": -1.0}, 10, rng)

    def test_scipy_distribution_info(self):
        """Test getting distribution info for scipy distributions."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("scipy:expon")

        info = dist.get_info()
        assert info.name == "scipy:expon"
        assert info.category == "continuous"
        assert len(info.parameters) > 0

    def test_scipy_unsupported_distribution(self):
        """Test that unsupported scipy distributions raise appropriate errors."""
        registry = get_distribution_registry()

        with pytest.raises(DistributionError):
            registry.get_distribution("scipy:nonexistent_dist")


# =============================================================================
# Poisson Distribution Tests
# =============================================================================


@pytest.mark.skip(reason="Poisson distribution not implemented yet")
class TestPoissonDistribution:
    """Test Poisson distribution for count data."""

    def test_poisson_basic_sampling(self):
        """Test basic Poisson sampling."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("poisson")

        rng = np.random.default_rng(42)
        samples = dist.sample({"lambda": 5.0}, 1000, rng)

        assert len(samples) == 1000
        assert samples.dtype == np.int64
        assert np.all(samples >= 0)

    def test_poisson_statistical_properties(self):
        """Test that Poisson samples have correct statistical properties."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("poisson")

        rng = np.random.default_rng(42)
        lambda_param = 10.0
        samples = dist.sample({"lambda": lambda_param}, 5000, rng)

        # For Poisson: mean = variance = lambda
        sample_mean = np.mean(samples)
        sample_var = np.var(samples)

        # Check mean is close to lambda (within 10%)
        assert abs(sample_mean - lambda_param) / lambda_param < 0.1

        # Check variance is close to lambda (within 20%)
        assert abs(sample_var - lambda_param) / lambda_param < 0.2

    def test_poisson_parameter_validation_positive(self):
        """Test that lambda must be positive."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("poisson")

        rng = np.random.default_rng(42)

        # Lambda must be > 0
        with pytest.raises(DistributionError, match="lambda must be positive|greater than 0"):
            dist.sample({"lambda": 0.0}, 10, rng)

        with pytest.raises(DistributionError, match="lambda must be positive|greater than 0"):
            dist.sample({"lambda": -1.0}, 10, rng)

    def test_poisson_missing_parameter(self):
        """Test that missing lambda parameter raises error."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("poisson")

        rng = np.random.default_rng(42)

        with pytest.raises(DistributionError, match="Missing required parameter"):
            dist.sample({}, 10, rng)

    def test_poisson_dtype_compatibility(self):
        """Test that Poisson returns integer dtype."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("poisson")

        info = dist.get_info()
        assert info.default_dtype == "int"
        assert info.category == "discrete"

        rng = np.random.default_rng(42)
        samples = dist.sample({"lambda": 3.0}, 100, rng)
        assert samples.dtype in [np.int32, np.int64]

    def test_poisson_edge_cases(self):
        """Test Poisson with edge case parameters."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("poisson")

        rng = np.random.default_rng(42)

        # Very small lambda
        samples = dist.sample({"lambda": 0.1}, 100, rng)
        assert np.all(samples >= 0)
        # Most samples should be 0 or 1 for small lambda
        assert np.mean(samples) < 1.0

        # Large lambda
        samples = dist.sample({"lambda": 100.0}, 1000, rng)
        assert 80 < np.mean(samples) < 120


# =============================================================================
# Exponential Distribution Tests
# =============================================================================


@pytest.mark.skip(reason="Exponential distribution not implemented yet")
class TestExponentialDistribution:
    """Test Exponential distribution for time-to-event data."""

    def test_exponential_basic_sampling(self):
        """Test basic Exponential sampling."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("exponential")

        rng = np.random.default_rng(42)
        samples = dist.sample({"rate": 1.0}, 1000, rng)

        assert len(samples) == 1000
        assert samples.dtype == np.float64
        assert np.all(samples >= 0)

    def test_exponential_statistical_properties(self):
        """Test that Exponential samples have correct statistical properties."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("exponential")

        rng = np.random.default_rng(42)
        rate = 2.0
        samples = dist.sample({"rate": rate}, 5000, rng)

        # For Exponential: mean = 1/rate, variance = 1/rate^2
        expected_mean = 1.0 / rate
        expected_var = 1.0 / (rate**2)

        sample_mean = np.mean(samples)
        sample_var = np.var(samples)

        # Check mean is close to expected (within 10%)
        assert abs(sample_mean - expected_mean) / expected_mean < 0.1

        # Check variance is close to expected (within 20%)
        assert abs(sample_var - expected_var) / expected_var < 0.2

    def test_exponential_parameter_validation_positive(self):
        """Test that rate must be positive."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("exponential")

        rng = np.random.default_rng(42)

        # Rate must be > 0
        with pytest.raises(DistributionError, match="rate must be positive|greater than 0"):
            dist.sample({"rate": 0.0}, 10, rng)

        with pytest.raises(DistributionError, match="rate must be positive|greater than 0"):
            dist.sample({"rate": -1.0}, 10, rng)

    def test_exponential_scale_parameterization(self):
        """Test alternative scale parameterization (scale = 1/rate)."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("exponential")

        rng = np.random.default_rng(42)

        # Should support both rate and scale parameterization
        samples_rate = dist.sample({"rate": 2.0}, 1000, rng)

        rng = np.random.default_rng(42)
        samples_scale = dist.sample({"scale": 0.5}, 1000, rng)

        # Should produce same results (scale = 1/rate)
        assert np.allclose(samples_rate, samples_scale)

    def test_exponential_dtype_compatibility(self):
        """Test that Exponential returns float dtype."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("exponential")

        info = dist.get_info()
        assert info.default_dtype == "float"
        assert info.category == "continuous"


# =============================================================================
# Beta Distribution Tests
# =============================================================================


@pytest.mark.skip(reason="Beta distribution not implemented yet")
class TestBetaDistribution:
    """Test Beta distribution for probability values."""

    def test_beta_basic_sampling(self):
        """Test basic Beta sampling."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("beta")

        rng = np.random.default_rng(42)
        samples = dist.sample({"alpha": 2.0, "beta": 5.0}, 1000, rng)

        assert len(samples) == 1000
        assert samples.dtype == np.float64
        assert np.all(samples >= 0)
        assert np.all(samples <= 1)

    def test_beta_statistical_properties(self):
        """Test that Beta samples have correct statistical properties."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("beta")

        rng = np.random.default_rng(42)
        alpha, beta_param = 5.0, 2.0
        samples = dist.sample({"alpha": alpha, "beta": beta_param}, 5000, rng)

        # For Beta: mean = alpha / (alpha + beta)
        # variance = (alpha * beta) / ((alpha + beta)^2 * (alpha + beta + 1))
        expected_mean = alpha / (alpha + beta_param)
        expected_var = (alpha * beta_param) / ((alpha + beta_param) ** 2 * (alpha + beta_param + 1))

        sample_mean = np.mean(samples)
        sample_var = np.var(samples)

        # Check mean is close to expected (within 10%)
        assert abs(sample_mean - expected_mean) / expected_mean < 0.1

        # Check variance is close to expected (within 20%)
        assert abs(sample_var - expected_var) / expected_var < 0.2

    def test_beta_parameter_validation_positive(self):
        """Test that alpha and beta must be positive."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("beta")

        rng = np.random.default_rng(42)

        # Alpha must be > 0
        with pytest.raises(DistributionError, match="alpha must be positive|greater than 0"):
            dist.sample({"alpha": 0.0, "beta": 2.0}, 10, rng)

        with pytest.raises(DistributionError, match="alpha must be positive|greater than 0"):
            dist.sample({"alpha": -1.0, "beta": 2.0}, 10, rng)

        # Beta must be > 0
        with pytest.raises(DistributionError, match="beta must be positive|greater than 0"):
            dist.sample({"alpha": 2.0, "beta": 0.0}, 10, rng)

        with pytest.raises(DistributionError, match="beta must be positive|greater than 0"):
            dist.sample({"alpha": 2.0, "beta": -1.0}, 10, rng)

    def test_beta_uniform_special_case(self):
        """Test that Beta(1,1) produces uniform distribution."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("beta")

        rng = np.random.default_rng(42)
        samples = dist.sample({"alpha": 1.0, "beta": 1.0}, 1000, rng)

        # Beta(1,1) = Uniform(0,1)
        assert 0.4 < np.mean(samples) < 0.6
        # Variance of Uniform(0,1) is 1/12 ≈ 0.0833
        assert 0.06 < np.var(samples) < 0.11

    def test_beta_dtype_compatibility(self):
        """Test that Beta returns float dtype in [0, 1]."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("beta")

        info = dist.get_info()
        assert info.default_dtype == "float"
        assert info.category == "continuous"

        rng = np.random.default_rng(42)
        samples = dist.sample({"alpha": 2.0, "beta": 5.0}, 100, rng)
        assert samples.dtype == np.float64
        assert np.all((samples >= 0) & (samples <= 1))


# =============================================================================
# Gamma Distribution Tests
# =============================================================================


@pytest.mark.skip(reason="Gamma distribution not implemented yet")
class TestGammaDistribution:
    """Test Gamma distribution for positive continuous data."""

    def test_gamma_basic_sampling(self):
        """Test basic Gamma sampling."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("gamma")

        rng = np.random.default_rng(42)
        samples = dist.sample({"shape": 2.0, "scale": 2.0}, 1000, rng)

        assert len(samples) == 1000
        assert samples.dtype == np.float64
        assert np.all(samples > 0)

    def test_gamma_statistical_properties(self):
        """Test that Gamma samples have correct statistical properties."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("gamma")

        rng = np.random.default_rng(42)
        shape, scale = 3.0, 2.0
        samples = dist.sample({"shape": shape, "scale": scale}, 5000, rng)

        # For Gamma: mean = shape * scale, variance = shape * scale^2
        expected_mean = shape * scale
        expected_var = shape * (scale**2)

        sample_mean = np.mean(samples)
        sample_var = np.var(samples)

        # Check mean is close to expected (within 10%)
        assert abs(sample_mean - expected_mean) / expected_mean < 0.1

        # Check variance is close to expected (within 20%)
        assert abs(sample_var - expected_var) / expected_var < 0.2

    def test_gamma_parameter_validation_positive(self):
        """Test that shape and scale must be positive."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("gamma")

        rng = np.random.default_rng(42)

        # Shape must be > 0
        with pytest.raises(DistributionError, match="shape must be positive|greater than 0"):
            dist.sample({"shape": 0.0, "scale": 2.0}, 10, rng)

        with pytest.raises(DistributionError, match="shape must be positive|greater than 0"):
            dist.sample({"shape": -1.0, "scale": 2.0}, 10, rng)

        # Scale must be > 0
        with pytest.raises(DistributionError, match="scale must be positive|greater than 0"):
            dist.sample({"shape": 2.0, "scale": 0.0}, 10, rng)

        with pytest.raises(DistributionError, match="scale must be positive|greater than 0"):
            dist.sample({"shape": 2.0, "scale": -1.0}, 10, rng)

    def test_gamma_exponential_special_case(self):
        """Test that Gamma(1, scale) matches Exponential(rate=1/scale)."""
        registry = get_distribution_registry()
        gamma_dist = registry.get_distribution("gamma")
        expon_dist = registry.get_distribution("exponential")

        rng = np.random.default_rng(42)
        gamma_samples = gamma_dist.sample({"shape": 1.0, "scale": 2.0}, 1000, rng)

        rng = np.random.default_rng(42)
        expon_samples = expon_dist.sample({"scale": 2.0}, 1000, rng)

        # Means should be similar
        assert abs(np.mean(gamma_samples) - np.mean(expon_samples)) < 0.5

    def test_gamma_dtype_compatibility(self):
        """Test that Gamma returns positive float dtype."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("gamma")

        info = dist.get_info()
        assert info.default_dtype == "float"
        assert info.category == "continuous"


# =============================================================================
# Binomial Distribution Tests
# =============================================================================


@pytest.mark.skip(reason="Binomial distribution not implemented yet")
class TestBinomialDistribution:
    """Test Binomial distribution for count data with fixed trials."""

    def test_binomial_basic_sampling(self):
        """Test basic Binomial sampling."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("binomial")

        rng = np.random.default_rng(42)
        samples = dist.sample({"n": 10, "p": 0.5}, 1000, rng)

        assert len(samples) == 1000
        assert samples.dtype in [np.int32, np.int64]
        assert np.all(samples >= 0)
        assert np.all(samples <= 10)

    def test_binomial_statistical_properties(self):
        """Test that Binomial samples have correct statistical properties."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("binomial")

        rng = np.random.default_rng(42)
        n, p = 20, 0.3
        samples = dist.sample({"n": n, "p": p}, 5000, rng)

        # For Binomial: mean = n*p, variance = n*p*(1-p)
        expected_mean = n * p
        expected_var = n * p * (1 - p)

        sample_mean = np.mean(samples)
        sample_var = np.var(samples)

        # Check mean is close to expected (within 10%)
        assert abs(sample_mean - expected_mean) / expected_mean < 0.1

        # Check variance is close to expected (within 20%)
        assert abs(sample_var - expected_var) / expected_var < 0.2

    def test_binomial_parameter_validation(self):
        """Test parameter validation for Binomial."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("binomial")

        rng = np.random.default_rng(42)

        # n must be positive integer
        with pytest.raises(DistributionError):
            dist.sample({"n": -1, "p": 0.5}, 10, rng)

        # p must be in [0, 1]
        with pytest.raises(DistributionError, match="p must be between 0 and 1"):
            dist.sample({"n": 10, "p": 1.5}, 10, rng)

        with pytest.raises(DistributionError, match="p must be between 0 and 1"):
            dist.sample({"n": 10, "p": -0.1}, 10, rng)

    def test_binomial_edge_cases(self):
        """Test Binomial with edge case parameters."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("binomial")

        rng = np.random.default_rng(42)

        # p=0 should always give 0
        samples = dist.sample({"n": 10, "p": 0.0}, 100, rng)
        assert np.all(samples == 0)

        # p=1 should always give n
        samples = dist.sample({"n": 10, "p": 1.0}, 100, rng)
        assert np.all(samples == 10)

    def test_binomial_dtype_compatibility(self):
        """Test that Binomial returns integer dtype."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("binomial")

        info = dist.get_info()
        assert info.default_dtype == "int"
        assert info.category == "discrete"


# =============================================================================
# LogNormal Distribution Tests
# =============================================================================


@pytest.mark.skip(reason="LogNormal distribution not implemented yet")
class TestLogNormalDistribution:
    """Test LogNormal distribution for positive continuous data."""

    def test_lognormal_basic_sampling(self):
        """Test basic LogNormal sampling."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("lognormal")

        rng = np.random.default_rng(42)
        samples = dist.sample({"mu": 0.0, "sigma": 1.0}, 1000, rng)

        assert len(samples) == 1000
        assert samples.dtype == np.float64
        assert np.all(samples > 0)

    def test_lognormal_statistical_properties(self):
        """Test that LogNormal samples have correct statistical properties."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("lognormal")

        rng = np.random.default_rng(42)
        mu, sigma = 0.0, 0.5
        samples = dist.sample({"mu": mu, "sigma": sigma}, 5000, rng)

        # For LogNormal: mean = exp(mu + sigma^2/2)
        expected_mean = np.exp(mu + (sigma**2) / 2)

        sample_mean = np.mean(samples)

        # Check mean is close to expected (within 15%)
        assert abs(sample_mean - expected_mean) / expected_mean < 0.15

    def test_lognormal_parameter_validation(self):
        """Test that sigma must be non-negative."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("lognormal")

        rng = np.random.default_rng(42)

        # Sigma must be non-negative
        with pytest.raises(DistributionError, match="sigma must be non-negative|positive"):
            dist.sample({"mu": 0.0, "sigma": -1.0}, 10, rng)

    def test_lognormal_relationship_to_normal(self):
        """Test that log(LogNormal samples) follows Normal distribution."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("lognormal")

        rng = np.random.default_rng(42)
        mu, sigma = 1.0, 0.5
        samples = dist.sample({"mu": mu, "sigma": sigma}, 5000, rng)

        # log(samples) should be approximately Normal(mu, sigma)
        log_samples = np.log(samples)
        assert abs(np.mean(log_samples) - mu) < 0.1
        assert abs(np.std(log_samples) - sigma) < 0.1

    def test_lognormal_dtype_compatibility(self):
        """Test that LogNormal returns positive float dtype."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("lognormal")

        info = dist.get_info()
        assert info.default_dtype == "float"
        assert info.category == "continuous"


# =============================================================================
# Mixture Distribution Tests
# =============================================================================


@pytest.mark.skip(reason="Mixture distributions not implemented yet")
class TestMixtureDistribution:
    """Test mixture distributions combining multiple components."""

    def test_mixture_basic_sampling(self):
        """Test basic mixture distribution sampling."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("mixture")

        rng = np.random.default_rng(42)
        params = {
            "components": [
                {"type": "normal", "params": {"mu": 0, "sigma": 1}, "weight": 0.7},
                {"type": "normal", "params": {"mu": 5, "sigma": 0.5}, "weight": 0.3},
            ]
        }
        samples = dist.sample(params, 1000, rng)

        assert len(samples) == 1000
        assert samples.dtype == np.float64

    def test_mixture_bimodal_distribution(self):
        """Test that mixture creates bimodal distribution."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("mixture")

        rng = np.random.default_rng(42)
        params = {
            "components": [
                {"type": "normal", "params": {"mu": 0, "sigma": 1}, "weight": 0.5},
                {"type": "normal", "params": {"mu": 10, "sigma": 1}, "weight": 0.5},
            ]
        }
        samples = dist.sample(params, 5000, rng)

        # Samples should have values around 0 and 10
        samples_near_0 = np.sum((samples > -3) & (samples < 3))
        samples_near_10 = np.sum((samples > 7) & (samples < 13))

        # Most samples should be near one of the two modes
        assert samples_near_0 + samples_near_10 > 4000

    def test_mixture_weights_validation(self):
        """Test that mixture weights must sum to 1."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("mixture")

        rng = np.random.default_rng(42)

        # Weights don't sum to 1
        params = {
            "components": [
                {"type": "normal", "params": {"mu": 0, "sigma": 1}, "weight": 0.5},
                {"type": "normal", "params": {"mu": 5, "sigma": 1}, "weight": 0.3},
            ]
        }

        with pytest.raises(DistributionError, match="weights must sum to 1"):
            dist.sample(params, 100, rng)

    def test_mixture_negative_weights_validation(self):
        """Test that mixture weights must be non-negative."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("mixture")

        rng = np.random.default_rng(42)

        params = {
            "components": [
                {"type": "normal", "params": {"mu": 0, "sigma": 1}, "weight": 1.2},
                {"type": "normal", "params": {"mu": 5, "sigma": 1}, "weight": -0.2},
            ]
        }

        with pytest.raises(DistributionError, match="weights must be non-negative"):
            dist.sample(params, 100, rng)

    def test_mixture_empty_components(self):
        """Test that mixture requires at least one component."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("mixture")

        rng = np.random.default_rng(42)

        params = {"components": []}

        with pytest.raises(DistributionError, match="at least one component"):
            dist.sample(params, 100, rng)

    def test_mixture_different_distribution_types(self):
        """Test mixture with different distribution types."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("mixture")

        rng = np.random.default_rng(42)
        params = {
            "components": [
                {"type": "uniform", "params": {"low": 0, "high": 5}, "weight": 0.6},
                {"type": "normal", "params": {"mu": 10, "sigma": 2}, "weight": 0.4},
            ]
        }
        samples = dist.sample(params, 1000, rng)

        assert len(samples) == 1000
        # Some samples should be in [0, 5] range, some around 10
        samples_low = np.sum((samples >= 0) & (samples <= 5))
        assert samples_low > 400  # Expect roughly 60% but allow variance

    def test_mixture_single_component_equals_base(self):
        """Test that mixture with single component equals base distribution."""
        registry = get_distribution_registry()
        mixture_dist = registry.get_distribution("mixture")
        normal_dist = registry.get_distribution("normal")

        # Same seed for both
        rng1 = np.random.default_rng(42)
        mixture_samples = mixture_dist.sample(
            {"components": [{"type": "normal", "params": {"mu": 5, "sigma": 2}, "weight": 1.0}]},
            1000,
            rng1,
        )

        rng2 = np.random.default_rng(42)
        normal_samples = normal_dist.sample({"mu": 5, "sigma": 2}, 1000, rng2)

        # Means should be very similar
        assert abs(np.mean(mixture_samples) - np.mean(normal_samples)) < 0.5

    def test_mixture_distribution_info(self):
        """Test mixture distribution metadata."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("mixture")

        info = dist.get_info()
        assert info.name == "mixture"
        assert info.category == "continuous"


# =============================================================================
# Truncated Distribution Tests
# =============================================================================


@pytest.mark.skip(reason="Truncated distributions not implemented yet")
class TestTruncatedDistributions:
    """Test truncated distributions with bounds."""

    def test_truncated_normal_basic(self):
        """Test basic truncated normal distribution."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("truncated_normal")

        rng = np.random.default_rng(42)
        samples = dist.sample({"mu": 0, "sigma": 1, "low": -1, "high": 1}, 1000, rng)

        assert len(samples) == 1000
        assert np.all(samples >= -1)
        assert np.all(samples <= 1)

    def test_truncated_normal_statistical_properties(self):
        """Test that truncated normal respects bounds."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("truncated_normal")

        rng = np.random.default_rng(42)
        samples = dist.sample({"mu": 0, "sigma": 2, "low": 0, "high": 5}, 5000, rng)

        # All samples should be in [0, 5]
        assert np.all(samples >= 0)
        assert np.all(samples <= 5)

        # Mean should be shifted toward the truncation bounds
        # For truncation at [0, 5] with mu=0, mean should be > 0
        assert np.mean(samples) > 0

    def test_truncated_bounds_validation(self):
        """Test that truncated distribution validates bounds."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("truncated_normal")

        rng = np.random.default_rng(42)

        # low must be < high
        with pytest.raises(DistributionError, match="low must be less than high"):
            dist.sample({"mu": 0, "sigma": 1, "low": 5, "high": 0}, 10, rng)

    def test_generic_truncation_wrapper(self):
        """Test generic truncation wrapper for any distribution."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("truncated")

        rng = np.random.default_rng(42)
        params = {
            "base_distribution": "uniform",
            "base_params": {"low": 0, "high": 10},
            "low": 2,
            "high": 8,
        }
        samples = dist.sample(params, 1000, rng)

        # All samples should be in [2, 8]
        assert np.all(samples >= 2)
        assert np.all(samples <= 8)

    def test_truncated_uniform(self):
        """Test truncating uniform distribution."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("truncated")

        rng = np.random.default_rng(42)
        params = {
            "base_distribution": "uniform",
            "base_params": {"low": 0, "high": 100},
            "low": 40,
            "high": 60,
        }
        samples = dist.sample(params, 1000, rng)

        assert np.all(samples >= 40)
        assert np.all(samples <= 60)
        # Should be roughly uniform in [40, 60]
        assert 45 < np.mean(samples) < 55

    def test_truncated_exponential(self):
        """Test truncating exponential distribution."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("truncated")

        rng = np.random.default_rng(42)
        params = {
            "base_distribution": "exponential",
            "base_params": {"rate": 1.0},
            "low": 0,
            "high": 2,
        }
        samples = dist.sample(params, 1000, rng)

        assert np.all(samples >= 0)
        assert np.all(samples <= 2)

    def test_truncated_one_sided_bounds(self):
        """Test truncation with only lower or upper bound."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("truncated_normal")

        rng = np.random.default_rng(42)

        # Only lower bound
        samples = dist.sample({"mu": 0, "sigma": 1, "low": 0}, 1000, rng)
        assert np.all(samples >= 0)

        # Only upper bound
        rng = np.random.default_rng(42)
        samples = dist.sample({"mu": 0, "sigma": 1, "high": 0}, 1000, rng)
        assert np.all(samples <= 0)

    def test_truncated_narrow_range(self):
        """Test truncation with very narrow range."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("truncated_normal")

        rng = np.random.default_rng(42)
        # Very narrow range
        samples = dist.sample({"mu": 0, "sigma": 10, "low": 0, "high": 0.1}, 1000, rng)

        assert np.all(samples >= 0)
        assert np.all(samples <= 0.1)
        assert len(samples) == 1000


# =============================================================================
# Parameter Validation Tests
# =============================================================================


class TestExtendedParameterValidation:
    """Test parameter validation across all extended distributions."""

    @pytest.mark.skip(reason="Extended distributions not implemented yet")
    def test_all_extended_distributions_registered(self):
        """Test that all extended distributions are registered."""
        registry = get_distribution_registry()

        expected_distributions = [
            "poisson",
            "exponential",
            "beta",
            "gamma",
            "binomial",
            "lognormal",
            "mixture",
            "truncated",
            "truncated_normal",
        ]

        for dist_name in expected_distributions:
            assert registry.is_registered(dist_name), f"{dist_name} not registered"

    @pytest.mark.skip(reason="Extended distributions not implemented yet")
    def test_distribution_info_completeness(self):
        """Test that all extended distributions have complete metadata."""
        registry = get_distribution_registry()

        distributions = [
            "poisson",
            "exponential",
            "beta",
            "gamma",
            "binomial",
            "lognormal",
        ]

        for dist_name in distributions:
            dist = registry.get_distribution(dist_name)
            info = dist.get_info()

            assert info.name == dist_name
            assert len(info.display_name) > 0
            assert len(info.description) > 0
            assert info.category in ["continuous", "discrete", "categorical"]
            assert info.default_dtype in ["float", "int", "category", "bool"]
            assert len(info.parameters) > 0

    @pytest.mark.skip(reason="Extended distributions not implemented yet")
    def test_missing_required_parameters(self):
        """Test that missing required parameters raise errors."""
        registry = get_distribution_registry()
        rng = np.random.default_rng(42)

        # Poisson missing lambda
        dist = registry.get_distribution("poisson")
        with pytest.raises(DistributionError, match="Missing required parameter"):
            dist.sample({}, 10, rng)

        # Beta missing alpha
        dist = registry.get_distribution("beta")
        with pytest.raises(DistributionError, match="Missing required parameter"):
            dist.sample({"beta": 2.0}, 10, rng)

        # Beta missing beta
        with pytest.raises(DistributionError, match="Missing required parameter"):
            dist.sample({"alpha": 2.0}, 10, rng)

    @pytest.mark.skip(reason="Extended distributions not implemented yet")
    def test_parameter_type_validation(self):
        """Test that incorrect parameter types raise errors."""
        registry = get_distribution_registry()
        rng = np.random.default_rng(42)

        # Poisson with string lambda
        dist = registry.get_distribution("poisson")
        with pytest.raises(DistributionError):
            dist.sample({"lambda": "invalid"}, 10, rng)

        # Binomial with float n (should be int)
        dist = registry.get_distribution("binomial")
        # This might be allowed or converted, depending on implementation


# =============================================================================
# Dtype Compatibility Tests
# =============================================================================


class TestDtypeCompatibility:
    """Test that distributions produce correct dtypes."""

    @pytest.mark.skip(reason="Extended distributions not implemented yet")
    def test_discrete_distributions_return_int(self):
        """Test that discrete distributions return integer dtypes."""
        registry = get_distribution_registry()
        rng = np.random.default_rng(42)

        discrete_dists = [
            ("poisson", {"lambda": 5.0}),
            ("binomial", {"n": 10, "p": 0.5}),
        ]

        for dist_name, params in discrete_dists:
            dist = registry.get_distribution(dist_name)
            samples = dist.sample(params, 100, rng)
            assert samples.dtype in [
                np.int32,
                np.int64,
            ], f"{dist_name} should return int dtype"

    @pytest.mark.skip(reason="Extended distributions not implemented yet")
    def test_continuous_distributions_return_float(self):
        """Test that continuous distributions return float dtypes."""
        registry = get_distribution_registry()
        rng = np.random.default_rng(42)

        continuous_dists = [
            ("exponential", {"rate": 1.0}),
            ("beta", {"alpha": 2.0, "beta": 5.0}),
            ("gamma", {"shape": 2.0, "scale": 2.0}),
            ("lognormal", {"mu": 0.0, "sigma": 1.0}),
        ]

        for dist_name, params in continuous_dists:
            dist = registry.get_distribution(dist_name)
            samples = dist.sample(params, 100, rng)
            assert samples.dtype == np.float64, f"{dist_name} should return float dtype"

    @pytest.mark.skip(reason="Extended distributions not implemented yet")
    def test_beta_values_in_unit_interval(self):
        """Test that Beta distribution produces values in [0, 1]."""
        registry = get_distribution_registry()
        rng = np.random.default_rng(42)

        dist = registry.get_distribution("beta")
        samples = dist.sample({"alpha": 2.0, "beta": 5.0}, 1000, rng)

        assert np.all(samples >= 0)
        assert np.all(samples <= 1)
        assert samples.dtype == np.float64


# =============================================================================
# Reproducibility Tests
# =============================================================================


class TestExtendedReproducibility:
    """Test reproducibility with same seed for extended distributions."""

    @pytest.mark.skip(reason="Extended distributions not implemented yet")
    def test_poisson_reproducibility(self):
        """Test that Poisson sampling is reproducible."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("poisson")

        rng1 = np.random.default_rng(42)
        samples1 = dist.sample({"lambda": 5.0}, 100, rng1)

        rng2 = np.random.default_rng(42)
        samples2 = dist.sample({"lambda": 5.0}, 100, rng2)

        assert np.array_equal(samples1, samples2)

    @pytest.mark.skip(reason="Extended distributions not implemented yet")
    def test_mixture_reproducibility(self):
        """Test that mixture sampling is reproducible."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("mixture")

        params = {
            "components": [
                {"type": "normal", "params": {"mu": 0, "sigma": 1}, "weight": 0.5},
                {"type": "normal", "params": {"mu": 5, "sigma": 1}, "weight": 0.5},
            ]
        }

        rng1 = np.random.default_rng(42)
        samples1 = dist.sample(params, 100, rng1)

        rng2 = np.random.default_rng(42)
        samples2 = dist.sample(params, 100, rng2)

        assert np.allclose(samples1, samples2)

    @pytest.mark.skip(reason="Extended distributions not implemented yet")
    def test_truncated_reproducibility(self):
        """Test that truncated sampling is reproducible."""
        registry = get_distribution_registry()
        dist = registry.get_distribution("truncated_normal")

        params = {"mu": 0, "sigma": 1, "low": -1, "high": 1}

        rng1 = np.random.default_rng(42)
        samples1 = dist.sample(params, 100, rng1)

        rng2 = np.random.default_rng(42)
        samples2 = dist.sample(params, 100, rng2)

        assert np.allclose(samples1, samples2)
