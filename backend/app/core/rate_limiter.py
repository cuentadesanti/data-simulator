"""Rate limiting configuration using slowapi.

This module provides rate limiting for expensive API endpoints to prevent
abuse and ensure fair usage of computational resources.

Rate limiting is disabled in dev environment for easier development and testing.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Check if we're in development mode
IS_DEV_ENVIRONMENT = settings.environment.lower() == "dev"

# Create the limiter instance with IP-based key function
# Uses in-memory storage by default (suitable for single-instance deployment)
# For distributed systems, configure Redis storage:
#   limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")
# Rate limiting is disabled in dev environment
limiter = Limiter(key_func=get_remote_address, enabled=not IS_DEV_ENVIRONMENT)

# Rate limit constants for documentation and consistency
GENERATE_RATE_LIMIT = "10/minute"  # Data generation is expensive
PREVIEW_RATE_LIMIT = "30/minute"   # Preview is lighter but still computationally intensive
