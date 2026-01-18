"""Distribution registry for sampling random variables.

This module provides a registry of probability distributions that can be used
to generate random data. Each distribution implements a common interface and
can be registered with the global registry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol

import numpy as np
from scipy import stats

from app.core.exceptions import DistributionError
from app.models.distribution import DistributionInfo, ParameterInfo


class Distribution(Protocol):
    """Protocol for distribution implementations.

    All distributions must implement this protocol to be registered
    in the distribution registry.
    """

    name: str
    display_name: str
    description: str
    category: str  # "continuous" | "discrete" | "categorical"
    default_dtype: str  # "float" | "int" | "category" | "bool"
    parameters: list[ParameterInfo]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        """Generate random samples from this distribution.

        Args:
            params: Dictionary of parameter values (already resolved to concrete values)
            size: Number of samples to generate
            rng: NumPy random number generator for reproducibility

        Returns:
            Array of samples with shape (size,)

        Raises:
            DistributionError: If sampling fails due to invalid parameters
        """
        ...


class BaseDistribution(ABC):
    """Base class for distribution implementations.

    Provides common functionality and enforces the Distribution protocol.
    """

    name: str
    display_name: str
    description: str
    category: str
    default_dtype: str
    parameters: list[ParameterInfo]

    @abstractmethod
    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        """Generate random samples from this distribution."""
        pass

    def get_info(self) -> DistributionInfo:
        """Get distribution metadata as DistributionInfo."""
        return DistributionInfo(
            name=self.name,
            display_name=self.display_name,
            description=self.description,
            category=self.category,  # type: ignore
            default_dtype=self.default_dtype,  # type: ignore
            parameters=self.parameters,
        )

    def _validate_param(
        self, params: dict[str, Any], param_name: str, param_type: type | tuple[type, ...]
    ) -> Any:
        """Validate and extract a parameter from the params dict.

        Args:
            params: Dictionary of parameters
            param_name: Name of the parameter to extract
            param_type: Expected type(s) of the parameter (single type or tuple)

        Returns:
            The parameter value

        Raises:
            DistributionError: If parameter is missing or has wrong type
        """
        if param_name not in params:
            raise DistributionError(self.name, f"Missing required parameter: {param_name}")

        value = params[param_name]
        if not isinstance(value, param_type):
            if isinstance(param_type, tuple):
                type_names = " or ".join(t.__name__ for t in param_type)
            else:
                type_names = param_type.__name__
            raise DistributionError(
                self.name,
                f"Parameter '{param_name}' must be {type_names}, got {type(value).__name__}",
            )

        return value


class NormalDistribution(BaseDistribution):
    """Normal (Gaussian) distribution.

    Generates continuous values following a normal distribution with
    specified mean (mu) and standard deviation (sigma).
    """

    name = "normal"
    display_name = "Normal"
    description = "Normal (Gaussian) distribution with mean μ and standard deviation σ"
    category = "continuous"
    default_dtype = "float"
    parameters = [
        ParameterInfo(
            name="mu",
            description="Mean (center) of the distribution",
            type="float",
            required=True,
            default=0.0,
        ),
        ParameterInfo(
            name="sigma",
            description="Standard deviation (spread) of the distribution",
            type="float",
            required=True,
            default=1.0,
            min_value=0.0,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        """Generate samples from normal distribution.

        Args:
            params: Must contain 'mu' (float) and 'sigma' (float)
            size: Number of samples to generate
            rng: NumPy random number generator

        Returns:
            Array of float samples

        Raises:
            DistributionError: If parameters are invalid
        """
        mu = self._validate_param(params, "mu", (int, float))
        sigma = self._validate_param(params, "sigma", (int, float))

        if sigma < 0:
            raise DistributionError(self.name, f"sigma must be non-negative, got {sigma}")

        try:
            return rng.normal(loc=mu, scale=sigma, size=size)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class UniformDistribution(BaseDistribution):
    """Continuous uniform distribution.

    Generates continuous values uniformly distributed between low and high.
    """

    name = "uniform"
    display_name = "Uniform"
    description = "Continuous uniform distribution between low and high"
    category = "continuous"
    default_dtype = "float"
    parameters = [
        ParameterInfo(
            name="low",
            description="Lower bound (inclusive)",
            type="float",
            required=True,
            default=0.0,
        ),
        ParameterInfo(
            name="high",
            description="Upper bound (exclusive)",
            type="float",
            required=True,
            default=1.0,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        """Generate samples from uniform distribution.

        Args:
            params: Must contain 'low' (float) and 'high' (float)
            size: Number of samples to generate
            rng: NumPy random number generator

        Returns:
            Array of float samples

        Raises:
            DistributionError: If parameters are invalid
        """
        low = self._validate_param(params, "low", (int, float))
        high = self._validate_param(params, "high", (int, float))

        if low >= high:
            raise DistributionError(
                self.name, f"low must be less than high, got low={low}, high={high}"
            )

        try:
            return rng.uniform(low=low, high=high, size=size)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class CategoricalDistribution(BaseDistribution):
    """Categorical distribution.

    Generates string values from a list of categories according to
    specified probabilities.
    """

    name = "categorical"
    display_name = "Categorical"
    description = "Categorical distribution over string categories with specified probabilities"
    category = "categorical"
    default_dtype = "category"
    parameters = [
        ParameterInfo(
            name="categories",
            description="List of string categories to sample from",
            type="list",
            required=True,
        ),
        ParameterInfo(
            name="probs",
            description="List of probabilities for each category (must sum to 1.0)",
            type="list",
            required=True,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        """Generate samples from categorical distribution.

        Args:
            params: Must contain 'categories' (list of str or comma-separated string)
                    and 'probs' (list of float or comma-separated string)
            size: Number of samples to generate
            rng: NumPy random number generator

        Returns:
            Array of string samples

        Raises:
            DistributionError: If parameters are invalid
        """
        raw_categories = params.get("categories")
        raw_probs = params.get("probs")

        # Handle comma-separated string format (from frontend)
        if isinstance(raw_categories, str):
            categories = [c.strip() for c in raw_categories.split(",") if c.strip()]
        elif isinstance(raw_categories, list):
            categories = raw_categories
        else:
            raise DistributionError(
                self.name,
                f"categories must be a list or comma-separated string, got {type(raw_categories).__name__}",
            )

        if isinstance(raw_probs, str):
            try:
                probs = [float(p.strip()) for p in raw_probs.split(",") if p.strip()]
            except ValueError as e:
                raise DistributionError(self.name, f"probs must be numeric values: {str(e)}")
        elif isinstance(raw_probs, list):
            probs = raw_probs
        else:
            raise DistributionError(
                self.name,
                f"probs must be a list or comma-separated string, got {type(raw_probs).__name__}",
            )

        if len(categories) == 0:
            raise DistributionError(self.name, "categories list cannot be empty")

        if len(categories) != len(probs):
            raise DistributionError(
                self.name,
                f"categories and probs must have same length, got {len(categories)} and {len(probs)}",
            )

        # Validate all categories are strings
        for i, cat in enumerate(categories):
            if not isinstance(cat, str):
                raise DistributionError(
                    self.name,
                    f"All categories must be strings, got {type(cat).__name__} at index {i}",
                )

        # Validate and normalize probabilities
        try:
            probs_array = np.array(probs, dtype=float)
        except (ValueError, TypeError) as e:
            raise DistributionError(self.name, f"probs must be numeric values: {str(e)}")

        if np.any(probs_array < 0):
            raise DistributionError(self.name, "All probabilities must be non-negative")

        prob_sum = np.sum(probs_array)
        if not np.isclose(prob_sum, 1.0, rtol=1e-5):
            raise DistributionError(
                self.name,
                f"Probabilities must sum to 1.0, got {prob_sum}. Consider normalizing.",
            )

        try:
            # Use numpy's choice to sample indices, then map to categories
            indices = rng.choice(len(categories), size=size, p=probs_array)
            return np.array([categories[i] for i in indices], dtype=object)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class BernoulliDistribution(BaseDistribution):
    """Bernoulli distribution.

    Generates binary values (0 or 1) with specified probability of success.
    """

    name = "bernoulli"
    display_name = "Bernoulli"
    description = "Bernoulli distribution (binary 0/1) with probability p of success"
    category = "discrete"
    default_dtype = "int"
    parameters = [
        ParameterInfo(
            name="p",
            description="Probability of success (returning 1)",
            type="float",
            required=True,
            default=0.5,
            min_value=0.0,
            max_value=1.0,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        """Generate samples from Bernoulli distribution.

        Args:
            params: Must contain 'p' (float between 0 and 1)
            size: Number of samples to generate
            rng: NumPy random number generator

        Returns:
            Array of integer samples (0 or 1)

        Raises:
            DistributionError: If parameters are invalid
        """
        p = self._validate_param(params, "p", (int, float))

        if not 0.0 <= p <= 1.0:
            raise DistributionError(self.name, f"p must be between 0 and 1, got {p}")

        try:
            # Generate uniform random numbers and threshold at p
            return (rng.uniform(0, 1, size=size) < p).astype(int)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class PoissonDistribution(BaseDistribution):
    """Poisson distribution.

    Generates discrete non-negative integer values representing the number
    of events occurring in a fixed interval.
    """

    name = "poisson"
    display_name = "Poisson"
    description = "Poisson distribution for count data with rate parameter λ"
    category = "discrete"
    default_dtype = "int"
    parameters = [
        ParameterInfo(
            name="lam",
            description="Average rate of events (λ, must be positive)",
            type="float",
            required=True,
            default=1.0,
            min_value=0.0,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        lam = self._validate_param(params, "lam", (int, float))
        if lam < 0:
            raise DistributionError(self.name, f"lam must be non-negative, got {lam}")
        try:
            return rng.poisson(lam=lam, size=size)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class ExponentialDistribution(BaseDistribution):
    """Exponential distribution.

    Generates continuous positive values representing time between events
    in a Poisson process.
    """

    name = "exponential"
    display_name = "Exponential"
    description = "Exponential distribution for waiting times with scale parameter"
    category = "continuous"
    default_dtype = "float"
    parameters = [
        ParameterInfo(
            name="scale",
            description="Scale parameter (1/rate, must be positive)",
            type="float",
            required=True,
            default=1.0,
            min_value=0.0,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        scale = self._validate_param(params, "scale", (int, float))
        if scale <= 0:
            raise DistributionError(self.name, f"scale must be positive, got {scale}")
        try:
            return rng.exponential(scale=scale, size=size)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class BetaDistribution(BaseDistribution):
    """Beta distribution.

    Generates continuous values between 0 and 1, useful for modeling
    probabilities and proportions.
    """

    name = "beta"
    display_name = "Beta"
    description = "Beta distribution for values between 0 and 1 (proportions, probabilities)"
    category = "continuous"
    default_dtype = "float"
    parameters = [
        ParameterInfo(
            name="a",
            description="Alpha shape parameter (must be positive)",
            type="float",
            required=True,
            default=2.0,
            min_value=0.0,
        ),
        ParameterInfo(
            name="b",
            description="Beta shape parameter (must be positive)",
            type="float",
            required=True,
            default=2.0,
            min_value=0.0,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        a = self._validate_param(params, "a", (int, float))
        b = self._validate_param(params, "b", (int, float))
        if a <= 0:
            raise DistributionError(self.name, f"a must be positive, got {a}")
        if b <= 0:
            raise DistributionError(self.name, f"b must be positive, got {b}")
        try:
            return rng.beta(a=a, b=b, size=size)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class GammaDistribution(BaseDistribution):
    """Gamma distribution.

    Generates continuous positive values, often used for waiting times
    and modeling skewed positive data.
    """

    name = "gamma"
    display_name = "Gamma"
    description = "Gamma distribution for positive continuous values"
    category = "continuous"
    default_dtype = "float"
    parameters = [
        ParameterInfo(
            name="shape",
            description="Shape parameter k (must be positive)",
            type="float",
            required=True,
            default=2.0,
            min_value=0.0,
        ),
        ParameterInfo(
            name="scale",
            description="Scale parameter θ (must be positive)",
            type="float",
            required=True,
            default=1.0,
            min_value=0.0,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        shape = self._validate_param(params, "shape", (int, float))
        scale = self._validate_param(params, "scale", (int, float))
        if shape <= 0:
            raise DistributionError(self.name, f"shape must be positive, got {shape}")
        if scale <= 0:
            raise DistributionError(self.name, f"scale must be positive, got {scale}")
        try:
            return rng.gamma(shape=shape, scale=scale, size=size)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class LogNormalDistribution(BaseDistribution):
    """Log-normal distribution.

    Generates continuous positive values where the logarithm is normally distributed.
    Useful for modeling quantities that are products of many small factors.
    """

    name = "lognormal"
    display_name = "Log-Normal"
    description = "Log-normal distribution (log of values is normally distributed)"
    category = "continuous"
    default_dtype = "float"
    parameters = [
        ParameterInfo(
            name="mean",
            description="Mean of the underlying normal distribution",
            type="float",
            required=True,
            default=0.0,
        ),
        ParameterInfo(
            name="sigma",
            description="Standard deviation of the underlying normal distribution",
            type="float",
            required=True,
            default=1.0,
            min_value=0.0,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        mean = self._validate_param(params, "mean", (int, float))
        sigma = self._validate_param(params, "sigma", (int, float))
        if sigma < 0:
            raise DistributionError(self.name, f"sigma must be non-negative, got {sigma}")
        try:
            return rng.lognormal(mean=mean, sigma=sigma, size=size)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class BinomialDistribution(BaseDistribution):
    """Binomial distribution.

    Generates discrete values representing the number of successes
    in n independent Bernoulli trials.
    """

    name = "binomial"
    display_name = "Binomial"
    description = "Binomial distribution for number of successes in n trials"
    category = "discrete"
    default_dtype = "int"
    parameters = [
        ParameterInfo(
            name="n",
            description="Number of trials (must be positive integer)",
            type="int",
            required=True,
            default=10,
            min_value=1,
        ),
        ParameterInfo(
            name="p",
            description="Probability of success in each trial",
            type="float",
            required=True,
            default=0.5,
            min_value=0.0,
            max_value=1.0,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        n = self._validate_param(params, "n", (int, float))
        p = self._validate_param(params, "p", (int, float))
        n = int(n)
        if n < 1:
            raise DistributionError(self.name, f"n must be at least 1, got {n}")
        if not 0.0 <= p <= 1.0:
            raise DistributionError(self.name, f"p must be between 0 and 1, got {p}")
        try:
            return rng.binomial(n=n, p=p, size=size)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class TriangularDistribution(BaseDistribution):
    """Triangular distribution.

    Generates continuous values with a triangular probability density,
    useful for modeling with limited data or expert estimates.
    """

    name = "triangular"
    display_name = "Triangular"
    description = "Triangular distribution defined by min, mode, and max"
    category = "continuous"
    default_dtype = "float"
    parameters = [
        ParameterInfo(
            name="left",
            description="Lower bound",
            type="float",
            required=True,
            default=0.0,
        ),
        ParameterInfo(
            name="mode",
            description="Mode (most likely value)",
            type="float",
            required=True,
            default=0.5,
        ),
        ParameterInfo(
            name="right",
            description="Upper bound",
            type="float",
            required=True,
            default=1.0,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        left = self._validate_param(params, "left", (int, float))
        mode = self._validate_param(params, "mode", (int, float))
        right = self._validate_param(params, "right", (int, float))
        if not left <= mode <= right:
            raise DistributionError(
                self.name, f"Must have left <= mode <= right, got {left}, {mode}, {right}"
            )
        try:
            return rng.triangular(left=left, mode=mode, right=right, size=size)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class WeibullDistribution(BaseDistribution):
    """Weibull distribution.

    Generates continuous positive values, commonly used in reliability
    engineering and survival analysis.
    """

    name = "weibull"
    display_name = "Weibull"
    description = "Weibull distribution for reliability and survival analysis"
    category = "continuous"
    default_dtype = "float"
    parameters = [
        ParameterInfo(
            name="a",
            description="Shape parameter (must be positive)",
            type="float",
            required=True,
            default=1.0,
            min_value=0.0,
        ),
        ParameterInfo(
            name="scale",
            description="Scale parameter (must be positive)",
            type="float",
            required=False,
            default=1.0,
            min_value=0.0,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        a = self._validate_param(params, "a", (int, float))
        scale = params.get("scale", 1.0)
        if a <= 0:
            raise DistributionError(self.name, f"a must be positive, got {a}")
        if scale <= 0:
            raise DistributionError(self.name, f"scale must be positive, got {scale}")
        try:
            # NumPy's weibull doesn't have scale, so we multiply
            return scale * rng.weibull(a=a, size=size)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class ChiSquareDistribution(BaseDistribution):
    """Chi-square distribution.

    Generates continuous positive values, the distribution of a sum of
    squares of standard normal random variables.
    """

    name = "chisquare"
    display_name = "Chi-Square"
    description = "Chi-square distribution with k degrees of freedom"
    category = "continuous"
    default_dtype = "float"
    parameters = [
        ParameterInfo(
            name="df",
            description="Degrees of freedom (must be positive)",
            type="float",
            required=True,
            default=2.0,
            min_value=0.0,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        df = self._validate_param(params, "df", (int, float))
        if df <= 0:
            raise DistributionError(self.name, f"df must be positive, got {df}")
        try:
            return rng.chisquare(df=df, size=size)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class StudentTDistribution(BaseDistribution):
    """Student's t-distribution.

    Generates continuous values, similar to normal but with heavier tails.
    Useful for small sample sizes and robust statistics.
    """

    name = "student_t"
    display_name = "Student's t"
    description = "Student's t-distribution with heavier tails than normal"
    category = "continuous"
    default_dtype = "float"
    parameters = [
        ParameterInfo(
            name="df",
            description="Degrees of freedom (must be positive)",
            type="float",
            required=True,
            default=10.0,
            min_value=0.0,
        ),
        ParameterInfo(
            name="loc",
            description="Location parameter (mean)",
            type="float",
            required=False,
            default=0.0,
        ),
        ParameterInfo(
            name="scale",
            description="Scale parameter",
            type="float",
            required=False,
            default=1.0,
            min_value=0.0,
        ),
    ]

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        df = self._validate_param(params, "df", (int, float))
        loc = params.get("loc", 0.0)
        scale = params.get("scale", 1.0)
        if df <= 0:
            raise DistributionError(self.name, f"df must be positive, got {df}")
        if scale < 0:
            raise DistributionError(self.name, f"scale must be non-negative, got {scale}")
        try:
            return loc + scale * rng.standard_t(df=df, size=size)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class ScipyDistributionWrapper(BaseDistribution):
    """Wrapper for scipy.stats distributions.

    Allows any scipy.stats distribution to be used with the registry
    by dynamically extracting parameters and sampling.
    """

    def __init__(self, scipy_name: str):
        """Initialize wrapper for a scipy distribution.

        Args:
            scipy_name: Name of the scipy.stats distribution (e.g., 'norm', 'beta')
        """
        if not hasattr(stats, scipy_name):
            raise ValueError(f"Unknown scipy distribution: {scipy_name}")

        self._scipy_dist = getattr(stats, scipy_name)
        self._scipy_name = scipy_name

        # Determine if continuous or discrete
        self._is_continuous = isinstance(self._scipy_dist, stats.rv_continuous)

        # Set up metadata
        self.name = f"scipy.{scipy_name}"
        self.display_name = scipy_name.replace("_", " ").title()
        self.category = "continuous" if self._is_continuous else "discrete"
        self.default_dtype = "float" if self._is_continuous else "int"

        # Get description from docstring
        if self._scipy_dist.__doc__:
            first_line = self._scipy_dist.__doc__.strip().split("\n")[0]
            self.description = first_line[:200]
        else:
            self.description = f"SciPy {self.display_name} distribution"

        # Build parameter list
        self.parameters = self._build_parameters()

    def _build_parameters(self) -> list[ParameterInfo]:
        """Build parameter list from scipy distribution."""
        params = []

        # Get shape parameters
        if hasattr(self._scipy_dist, "shapes") and self._scipy_dist.shapes:
            shape_names = [s.strip() for s in self._scipy_dist.shapes.split(",")]
            for shape_name in shape_names:
                params.append(
                    ParameterInfo(
                        name=shape_name,
                        description=f"Shape parameter '{shape_name}'",
                        type="float",
                        required=True,
                        default=1.0,
                    )
                )

        # Add loc and scale
        if self._is_continuous:
            params.extend(
                [
                    ParameterInfo(
                        name="loc",
                        description="Location parameter (shift)",
                        type="float",
                        required=False,
                        default=0.0,
                    ),
                    ParameterInfo(
                        name="scale",
                        description="Scale parameter",
                        type="float",
                        required=False,
                        default=1.0,
                        min_value=0.0,
                    ),
                ]
            )
        else:
            params.append(
                ParameterInfo(
                    name="loc",
                    description="Location parameter (shift)",
                    type="float",
                    required=False,
                    default=0.0,
                )
            )

        return params

    def sample(self, params: dict[str, Any], size: int, rng: np.random.Generator) -> np.ndarray:
        """Generate samples using the scipy distribution.

        Args:
            params: Distribution parameters
            size: Number of samples
            rng: NumPy random generator

        Returns:
            Array of samples
        """
        # Extract shape parameters
        shape_args = []
        if hasattr(self._scipy_dist, "shapes") and self._scipy_dist.shapes:
            shape_names = [s.strip() for s in self._scipy_dist.shapes.split(",")]
            for shape_name in shape_names:
                if shape_name not in params:
                    raise DistributionError(
                        self.name, f"Missing required shape parameter: {shape_name}"
                    )
                shape_args.append(float(params[shape_name]))

        # Extract loc and scale
        loc = float(params.get("loc", 0.0))
        scale = float(params.get("scale", 1.0)) if self._is_continuous else None

        try:
            # Create frozen distribution and sample
            if self._is_continuous:
                frozen = self._scipy_dist(*shape_args, loc=loc, scale=scale)
            else:
                frozen = self._scipy_dist(*shape_args, loc=loc)

            # Use the numpy random state for reproducibility
            samples = frozen.rvs(size=size, random_state=rng)
            return np.asarray(samples)
        except Exception as e:
            raise DistributionError(self.name, f"Sampling failed: {str(e)}")


class DistributionRegistry:
    """Registry for managing available distributions.

    Provides methods to register distributions and retrieve them by name.
    """

    def __init__(self):
        """Initialize an empty distribution registry."""
        self._distributions: dict[str, Distribution] = {}
        self._scipy_cache: dict[str, ScipyDistributionWrapper] = {}

    def register_distribution(self, dist: Distribution) -> None:
        """Register a distribution in the registry.

        Args:
            dist: Distribution instance to register

        Raises:
            ValueError: If a distribution with the same name already exists
        """
        if dist.name in self._distributions:
            raise ValueError(f"Distribution '{dist.name}' is already registered")
        self._distributions[dist.name] = dist

    def get_distribution(self, name: str) -> Distribution:
        """Get a distribution by name.

        Supports both registered distributions and scipy distributions
        with the "scipy." prefix (e.g., "scipy.norm", "scipy.gamma").

        Args:
            name: Name of the distribution to retrieve

        Returns:
            The requested distribution

        Raises:
            DistributionError: If distribution is not found
        """
        # Check registered distributions first
        if name in self._distributions:
            return self._distributions[name]

        # Check for scipy.* distributions
        if name.startswith("scipy."):
            scipy_name = name[6:]  # Remove "scipy." prefix

            # Check cache first
            if name in self._scipy_cache:
                return self._scipy_cache[name]

            # Try to create a wrapper for the scipy distribution
            try:
                wrapper = ScipyDistributionWrapper(scipy_name)
                self._scipy_cache[name] = wrapper
                return wrapper
            except ValueError:
                raise DistributionError(
                    name,
                    f"Unknown scipy distribution: {scipy_name}",
                )

        # Not found
        available = list(self._distributions.keys())
        raise DistributionError(
            name,
            f"Unknown distribution '{name}'. Available: {available}. "
            "For scipy distributions, use 'scipy.<name>' (e.g., 'scipy.norm').",
        )

    def get_available_distributions(self) -> list[DistributionInfo]:
        """Get information about all registered distributions.

        Returns:
            List of DistributionInfo objects describing each distribution
        """
        distributions_info = []
        for dist in self._distributions.values():
            # If the distribution is a BaseDistribution, use get_info()
            if isinstance(dist, BaseDistribution):
                distributions_info.append(dist.get_info())
            else:
                # Otherwise, construct DistributionInfo manually
                distributions_info.append(
                    DistributionInfo(
                        name=dist.name,
                        display_name=dist.display_name,
                        description=dist.description,
                        category=dist.category,  # type: ignore
                        default_dtype=dist.default_dtype,  # type: ignore
                        parameters=dist.parameters,
                    )
                )
        return distributions_info

    def is_registered(self, name: str) -> bool:
        """Check if a distribution is registered.

        Args:
            name: Distribution name to check

        Returns:
            True if the distribution is registered, False otherwise
        """
        return name in self._distributions


# Global registry instance
_global_registry = DistributionRegistry()


# Register built-in distributions (common/curated list)
_global_registry.register_distribution(NormalDistribution())
_global_registry.register_distribution(UniformDistribution())
_global_registry.register_distribution(CategoricalDistribution())
_global_registry.register_distribution(BernoulliDistribution())
_global_registry.register_distribution(PoissonDistribution())
_global_registry.register_distribution(ExponentialDistribution())
_global_registry.register_distribution(BetaDistribution())
_global_registry.register_distribution(GammaDistribution())
_global_registry.register_distribution(LogNormalDistribution())
_global_registry.register_distribution(BinomialDistribution())
_global_registry.register_distribution(TriangularDistribution())
_global_registry.register_distribution(WeibullDistribution())
_global_registry.register_distribution(ChiSquareDistribution())
_global_registry.register_distribution(StudentTDistribution())


def get_distribution_registry() -> DistributionRegistry:
    """Get the global distribution registry.

    Returns:
        The global DistributionRegistry instance
    """
    return _global_registry
