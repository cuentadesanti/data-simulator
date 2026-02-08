"""Application configuration and constants."""

from __future__ import annotations

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API
    app_name: str = "Data Simulator"
    debug: bool = False
    environment: str = "dev"  # dev, staging, prod
    clerk_secret_key: str = ""

    # CORS - comma-separated list of allowed origins
    # Default allows localhost for dev. In prod, set explicitly to your frontend domain(s)
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"

    # Generation limits
    max_rows_hard: int = 10_000_000
    max_nodes: int = 500
    max_edges: int = 2000
    max_formula_length: int = 1000
    generation_timeout_seconds: int = 600

    # Chunking
    chunk_size: int = 50_000
    sync_threshold: int = 50_000  # Above this, use async

    # Preview
    default_preview_rows: int = 500

    # Output
    output_dir: str = "./outputs"
    output_expiration_hours: int = 24
    max_output_size_mb: int = 500

    # Database
    database_url: str = "sqlite:///./data_simulator.db"

    class Config:
        env_file = ".env"
        env_prefix = "DS_"
        extra = "ignore"


settings = Settings()


def get_cors_origins() -> list[str]:
    """Parse CORS origins from settings.

    Returns:
        List of allowed origin strings. Returns ["*"] only in dev mode if origins is "*".
    """
    origins_str = settings.cors_origins.strip()

    # Only allow wildcard in dev mode
    if origins_str == "*":
        if settings.environment == "dev":
            return ["*"]
        else:
            # In prod, never allow wildcard - default to empty (no CORS)
            return []

    # Parse comma-separated list
    return [origin.strip() for origin in origins_str.split(",") if origin.strip()]


# Reserved function names (cannot be used as node IDs)
RESERVED_FUNCTIONS = {
    "abs",
    "min",
    "max",
    "round",
    "floor",
    "ceil",
    "sqrt",
    "log",
    "log10",
    "exp",
    "pow",
    "sin",
    "cos",
    "tan",
    "clamp",
    "if_else",
}

# Reserved context keys (built-in constants)
RESERVED_CONTEXT = {
    "PI": 3.14159265358979,
    "E": 2.71828182845904,
    "TRUE": True,
    "FALSE": False,
}

# Schema version
CURRENT_SCHEMA_VERSION = "1.0"
