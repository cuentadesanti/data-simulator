"""Distribution-related API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.models.distribution import DistributionInfo
from app.services.distribution_registry import get_distribution_registry
from app.services.scipy_distributions import search_scipy_distributions

router = APIRouter()


class DistributionsResponse(BaseModel):
    """Response for distributions list."""

    distributions: list[DistributionInfo]


class SearchResponse(BaseModel):
    """Response for distribution search."""

    results: list[DistributionInfo]
    query: str


@router.get("", response_model=DistributionsResponse)
async def list_distributions() -> DistributionsResponse:
    """List all common/curated distributions with their parameters.

    These are the recommended distributions for most use cases.
    Use /search for access to the full scipy.stats library.
    """
    registry = get_distribution_registry()
    return DistributionsResponse(distributions=registry.get_available_distributions())


@router.get("/search", response_model=SearchResponse)
async def search_distributions(
    q: str = Query(..., min_length=1, max_length=50, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
) -> SearchResponse:
    """Search scipy.stats distributions by name.

    This endpoint provides access to all scipy.stats distributions
    for advanced use cases. The query is matched against distribution
    names (e.g., 'beta', 'gamma', 'norm').

    Args:
        q: Search query (partial match on name or display name)
        limit: Maximum number of results to return (default: 10, max: 50)

    Returns:
        List of matching distributions with their parameters
    """
    results = search_scipy_distributions(q, limit=limit)
    return SearchResponse(results=results, query=q)
