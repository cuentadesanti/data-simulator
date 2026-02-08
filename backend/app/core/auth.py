import logging
from functools import lru_cache

import jwt
from fastapi import HTTPException, Request
from jwt import PyJWKClient

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global cache for JWKS clients (one per issuer domain)
_jwks_clients: dict[str, PyJWKClient] = {}


@lru_cache(maxsize=10)
def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    """Get or create a cached JWKS client for the given URL.

    JWKS clients are expensive to create and should be reused.
    This function caches clients per issuer to avoid recreating them.

    Args:
        jwks_url: The JWKS URL for the issuer

    Returns:
        Cached PyJWKClient instance
    """
    if jwks_url not in _jwks_clients:
        # Create client with caching enabled (default cache TTL is 300s)
        _jwks_clients[jwks_url] = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_clients[jwks_url]

async def require_auth(request: Request) -> dict:
    """Verify the session token from the Authorization header using PyJWT and Clerk JWKS.

    Uses cached JWKS clients for better performance and returns generic errors
    in production to avoid leaking implementation details.

    Args:
        request: FastAPI request object

    Returns:
        Decoded JWT payload

    Raises:
        HTTPException: 401 if authentication fails
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        # 1. Decode token header to get 'kid' (Key ID) - useful for debug
        header = jwt.get_unverified_header(token)
        logger.debug(f"Token header: {header}")

        # 2. Decode payload to get issuer
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        issuer = unverified_payload.get("iss")

        if not issuer:
            logger.error("Auth error: No issuer in token")
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Standard Clerk JWKS URL construction
        clean_issuer = issuer.rstrip("/")
        jwks_url = f"{clean_issuer}/.well-known/jwks.json"

        logger.debug(f"Verifying token with issuer={issuer}, jwks_url={jwks_url}")

        # Get cached JWKS client
        jwks_client = _get_jwks_client(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            # You might want to verify audience 'aud' if configured
        )
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Auth error: Token expired")
        raise HTTPException(status_code=401, detail="Token has expired")

    except jwt.InvalidTokenError as e:
        logger.error(f"Auth error: Invalid token - {e}")
        # In production, return generic error to avoid leaking details
        detail = "Not authenticated" if settings.environment == "prod" else f"Invalid token: {e}"
        raise HTTPException(status_code=401, detail=detail)

    except Exception as e:
        logger.exception(f"Auth error: Unexpected exception - {e}")
        # In production, return generic error to avoid leaking implementation details
        detail = "Not authenticated" if settings.environment == "prod" else f"Authentication failed: {str(e)}"
        raise HTTPException(status_code=401, detail=detail)

# Alias for compatibility
verify_token = require_auth
