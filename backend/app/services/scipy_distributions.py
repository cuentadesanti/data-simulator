"""SciPy distribution discovery and search.

This module provides functionality to discover and search scipy.stats distributions
for use in data generation.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats
from scipy.stats._distn_infrastructure import rv_continuous_frozen, rv_discrete_frozen

from app.models.distribution import DistributionInfo, ParameterInfo


# Exclusion list for distributions that are deprecated, internal, or problematic
EXCLUDED_DISTRIBUTIONS = {
    # Internal/helper classes
    "rv_continuous",
    "rv_discrete",
    "rv_frozen",
    "rv_histogram",
    "rv_sample",
    # Deprecated or aliases
    "nbinom",  # alias for negative_binomial (we keep negbinom)
    # Problematic or very specialized
    "levy_stable",  # can be slow/unstable
    "studentized_range",  # very specialized
}

# Display name overrides for common distributions
DISPLAY_NAMES = {
    "norm": "Normal",
    "uniform": "Uniform",
    "expon": "Exponential",
    "gamma": "Gamma",
    "beta": "Beta",
    "lognorm": "Log-Normal",
    "poisson": "Poisson",
    "binom": "Binomial",
    "bernoulli": "Bernoulli",
    "geom": "Geometric",
    "hypergeom": "Hypergeometric",
    "nbinom": "Negative Binomial",
    "negbinom": "Negative Binomial",
    "chi2": "Chi-Square",
    "t": "Student's t",
    "f": "F",
    "pareto": "Pareto",
    "weibull_min": "Weibull (min)",
    "weibull_max": "Weibull (max)",
    "triang": "Triangular",
    "truncnorm": "Truncated Normal",
    "truncexpon": "Truncated Exponential",
    "laplace": "Laplace",
    "cauchy": "Cauchy",
    "logistic": "Logistic",
    "gumbel_r": "Gumbel (right)",
    "gumbel_l": "Gumbel (left)",
    "vonmises": "Von Mises",
    "wald": "Wald (Inverse Gaussian)",
    "invgamma": "Inverse Gamma",
    "invgauss": "Inverse Gaussian",
    "halfnorm": "Half-Normal",
    "halfcauchy": "Half-Cauchy",
    "foldnorm": "Folded Normal",
    "foldcauchy": "Folded Cauchy",
    "rayleigh": "Rayleigh",
    "rice": "Rice",
    "maxwell": "Maxwell",
    "zipf": "Zipf",
    "zipfian": "Zipfian",
    "planck": "Planck",
    "dlaplace": "Discrete Laplace",
    "randint": "Random Integer",
    "skewnorm": "Skew-Normal",
    "alpha": "Alpha",
    "anglit": "Anglit",
    "arcsine": "Arcsine",
    "argus": "ARGUS",
    "betaprime": "Beta Prime",
    "bradford": "Bradford",
    "burr": "Burr",
    "burr12": "Burr Type XII",
    "cosine": "Cosine",
    "crystalball": "Crystal Ball",
    "dgamma": "Double Gamma",
    "dweibull": "Double Weibull",
    "erlang": "Erlang",
    "exponnorm": "Exponentially Modified Normal",
    "exponpow": "Exponential Power",
    "exponweib": "Exponentiated Weibull",
    "fatiguelife": "Fatigue Life (Birnbaum-Saunders)",
    "fisk": "Fisk (Log-Logistic)",
    "genexpon": "Generalized Exponential",
    "genextreme": "Generalized Extreme Value",
    "gengamma": "Generalized Gamma",
    "genhalflogistic": "Generalized Half-Logistic",
    "genhyperbolic": "Generalized Hyperbolic",
    "geninvgauss": "Generalized Inverse Gaussian",
    "genlogistic": "Generalized Logistic",
    "gennorm": "Generalized Normal",
    "genpareto": "Generalized Pareto",
    "gilbrat": "Gilbrat",
    "gompertz": "Gompertz",
    "halfgennorm": "Half-Generalized Normal",
    "halflogistic": "Half-Logistic",
    "hypsecant": "Hyperbolic Secant",
    "invweibull": "Inverse Weibull",
    "johnsonsb": "Johnson SB",
    "johnsonsu": "Johnson SU",
    "kappa3": "Kappa3",
    "kappa4": "Kappa4",
    "ksone": "Kolmogorov-Smirnov One-Sided",
    "kstwo": "Kolmogorov-Smirnov Two-Sided",
    "kstwobign": "Kolmogorov-Smirnov Two-Sided (large N)",
    "levy": "Levy",
    "loggamma": "Log-Gamma",
    "loglaplace": "Log-Laplace",
    "loguniform": "Log-Uniform",
    "lomax": "Lomax (Pareto Type II)",
    "mielke": "Mielke Beta-Kappa",
    "moyal": "Moyal",
    "nakagami": "Nakagami",
    "ncf": "Noncentral F",
    "nct": "Noncentral t",
    "ncx2": "Noncentral Chi-Square",
    "norminvgauss": "Normal Inverse Gaussian",
    "pearson3": "Pearson Type III",
    "powerlaw": "Power-Law",
    "powerlognorm": "Power Log-Normal",
    "powernorm": "Power Normal",
    "recipinvgauss": "Reciprocal Inverse Gaussian",
    "reciprocal": "Reciprocal",
    "rel_breitwigner": "Relativistic Breit-Wigner",
    "semicircular": "Semicircular",
    "skewcauchy": "Skew-Cauchy",
    "trapezoid": "Trapezoidal",
    "truncpareto": "Truncated Pareto",
    "truncweibull_min": "Truncated Weibull (min)",
    "tukeylambda": "Tukey Lambda",
    "wrapcauchy": "Wrapped Cauchy",
    "yulesimon": "Yule-Simon",
    "betabinom": "Beta-Binomial",
    "boltzmann": "Boltzmann",
    "logser": "Logarithmic (Log-Series)",
    "nhypergeom": "Negative Hypergeometric",
    "nchypergeom_fisher": "Noncentral Hypergeometric (Fisher)",
    "nchypergeom_wallenius": "Noncentral Hypergeometric (Wallenius)",
    "skellam": "Skellam",
}


def _get_scipy_distributions() -> dict[str, Any]:
    """Get all valid scipy.stats distribution objects.

    Returns only rv_continuous and rv_discrete instances, excluding
    deprecated/internal ones.
    """
    distributions = {}

    for name in dir(stats):
        if name.startswith("_") or name in EXCLUDED_DISTRIBUTIONS:
            continue

        obj = getattr(stats, name)

        # Check if it's a distribution (continuous or discrete)
        is_continuous = isinstance(obj, stats.rv_continuous)
        is_discrete = isinstance(obj, stats.rv_discrete)

        if is_continuous or is_discrete:
            distributions[name] = {
                "obj": obj,
                "kind": "continuous" if is_continuous else "discrete",
            }

    return distributions


def _get_distribution_info(name: str, dist_data: dict[str, Any]) -> DistributionInfo:
    """Convert a scipy distribution to DistributionInfo.

    Args:
        name: The scipy distribution name
        dist_data: Dict with 'obj' and 'kind' keys

    Returns:
        DistributionInfo for the distribution
    """
    obj = dist_data["obj"]
    kind = dist_data["kind"]

    # Get display name
    display_name = DISPLAY_NAMES.get(name, name.replace("_", " ").title())

    # Get shape parameters from the distribution
    shape_params = []
    if hasattr(obj, "shapes") and obj.shapes:
        shape_names = [s.strip() for s in obj.shapes.split(",")]
        for shape_name in shape_names:
            shape_params.append(
                ParameterInfo(
                    name=shape_name,
                    description=f"Shape parameter '{shape_name}'",
                    type="float",
                    required=True,
                    default=1.0,
                )
            )

    # Add loc and scale for continuous distributions
    if kind == "continuous":
        shape_params.extend(
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
        # Discrete distributions only have loc
        shape_params.append(
            ParameterInfo(
                name="loc",
                description="Location parameter (shift)",
                type="float",
                required=False,
                default=0.0,
            )
        )

    # Try to get docstring for description
    description = ""
    if obj.__doc__:
        # Get first line of docstring
        first_line = obj.__doc__.strip().split("\n")[0]
        description = first_line[:200]  # Limit length
    if not description:
        description = f"SciPy {display_name} distribution"

    return DistributionInfo(
        name=f"scipy.{name}",  # Prefix with scipy. to distinguish
        display_name=display_name,
        description=description,
        category=kind,
        default_dtype="float" if kind == "continuous" else "int",
        parameters=shape_params,
    )


# Cache the discovered distributions
_scipy_distributions: dict[str, Any] | None = None


def get_scipy_distributions() -> dict[str, Any]:
    """Get cached scipy distributions."""
    global _scipy_distributions
    if _scipy_distributions is None:
        _scipy_distributions = _get_scipy_distributions()
    return _scipy_distributions


def search_scipy_distributions(query: str, limit: int = 10) -> list[DistributionInfo]:
    """Search scipy distributions by name.

    Args:
        query: Search query (partial match on name or display name)
        limit: Maximum number of results to return

    Returns:
        List of matching DistributionInfo objects
    """
    query = query.lower().strip()
    if not query:
        return []

    distributions = get_scipy_distributions()
    results = []

    for name, dist_data in distributions.items():
        display_name = DISPLAY_NAMES.get(name, name.replace("_", " ").title())

        # Check if query matches name or display name
        if query in name.lower() or query in display_name.lower():
            results.append(_get_distribution_info(name, dist_data))

            if len(results) >= limit:
                break

    # Sort by relevance (exact prefix match first, then by name length)
    def sort_key(info: DistributionInfo):
        name = info.name.replace("scipy.", "").lower()
        display = info.display_name.lower()

        # Exact prefix matches come first
        if name.startswith(query) or display.startswith(query):
            return (0, len(name))
        return (1, len(name))

    results.sort(key=sort_key)
    return results[:limit]


def get_all_scipy_distribution_infos() -> list[DistributionInfo]:
    """Get info for all scipy distributions.

    Returns:
        List of all DistributionInfo objects
    """
    distributions = get_scipy_distributions()
    return [_get_distribution_info(name, data) for name, data in distributions.items()]
