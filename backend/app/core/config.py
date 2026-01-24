"""Application configuration and constants."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API
    app_name: str = "Data Simulator"
    debug: bool = False
    environment: str = "dev"  # dev, staging, prod

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


settings = Settings()


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
