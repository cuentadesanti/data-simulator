"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import dag, distributions, modeling, pipelines, projects, transforms
from app.core import DataSimulatorError, settings
from app.core.rate_limiter import limiter
from app.core.auth import require_auth

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Synthetic data generator from probabilistic DAG models",
)

# Register rate limiter with app state
app.state.limiter = limiter

# Add rate limit exceeded exception handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DataSimulatorError)
async def data_simulator_error_handler(request: Request, exc: DataSimulatorError) -> JSONResponse:
    """Handle custom DataSimulatorError exceptions."""
    return JSONResponse(
        status_code=400,
        content=exc.to_dict(),
    )


# Include routers with optional authentication (commented out for now to avoid breaking existing workflow if keys are missing)
# To enable strict auth, uncomment dependencies=[Depends(require_auth)]
# For the purpose of "Simplest" demo, we will protect the DAG and Projects routes.

app.include_router(dag.router, prefix="/api/dag", tags=["DAG"], dependencies=[Depends(require_auth)])
app.include_router(distributions.router, prefix="/api/distributions", tags=["Distributions"], dependencies=[Depends(require_auth)])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"], dependencies=[Depends(require_auth)])
app.include_router(pipelines.router, prefix="/api/pipelines", tags=["Pipelines"], dependencies=[Depends(require_auth)])
app.include_router(transforms.router, prefix="/api/transforms", tags=["Transforms"], dependencies=[Depends(require_auth)])
app.include_router(modeling.router, prefix="/api/modeling", tags=["Modeling"], dependencies=[Depends(require_auth)])


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }
