"""DAG-related API routes."""

from __future__ import annotations

from io import StringIO
from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from app.core.rate_limiter import GENERATE_RATE_LIMIT, PREVIEW_RATE_LIMIT, limiter
from app.models.dag import DAGDefinition, ValidationResult
from app.models.generation import PreviewResponse
from app.services.validator import validate_dag

router = APIRouter()


@router.post("/validate", response_model=ValidationResult)
async def validate(dag: DAGDefinition) -> ValidationResult:
    """Validate a DAG definition.

    Checks for:
    - Cycles in the graph
    - MECE node configuration (stochastic XOR deterministic)
    - Valid parent references
    - Reserved keyword usage
    - Configuration limits
    """
    return validate_dag(dag)


@router.post("/preview", response_model=PreviewResponse)
@limiter.limit(PREVIEW_RATE_LIMIT)
async def preview(request: Request, dag: DAGDefinition) -> PreviewResponse:
    """Generate a preview sample from the DAG.

    Uses the same engine as /generate but with a smaller sample size.
    Always returns JSON, always synchronous.

    Rate limited to 30 requests per minute per IP.
    """
    # Import here to avoid circular imports
    from app.services.sampler import generate_preview

    return generate_preview(dag)


@router.post("/generate")
@limiter.limit(GENERATE_RATE_LIMIT)
async def generate(
    request: Request,
    dag: DAGDefinition,
    format: Literal["csv", "json", "parquet"] = Query(default="csv"),
):
    """Generate synthetic data from the DAG.

    Returns the generated data in the requested format (csv, json, parquet).
    For small datasets, streams data directly.
    For large datasets (future), would return a job_id for async processing.

    Rate limited to 10 requests per minute per IP.
    """
    # Import here to avoid circular imports
    from app.services.sampler import generate_data_with_df

    df, result = generate_data_with_df(dag)

    if format == "csv":
        # Stream CSV data
        output = StringIO()
        df.to_csv(output, index=False)
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=dataset_{result.seed}.csv",
                "X-Seed": str(result.seed),
                "X-Rows": str(result.rows),
                "X-Columns": ",".join(result.columns),
            },
        )

    elif format == "json":
        # Return JSON data
        return {
            "data": df.to_dict(orient="records"),
            "metadata": result.model_dump(),
        }

    elif format == "parquet":
        # Stream Parquet data
        from io import BytesIO

        output = BytesIO()
        df.to_parquet(output, index=False)
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename=dataset_{result.seed}.parquet",
                "X-Seed": str(result.seed),
                "X-Rows": str(result.rows),
                "X-Columns": ",".join(result.columns),
            },
        )

