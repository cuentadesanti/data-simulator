import logging
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ModelFit, Pipeline, PipelineVersion, Project, UploadedSource

logger = logging.getLogger(__name__)
LEGACY_OWNER_USER_ID = "legacy"

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
    if settings.auth_bypass:
        return {"sub": "local-dev-user", "auth_mode": "bypass"}

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

        # Validate issuer if configured (prevents SSRF attacks)
        if settings.clerk_issuer:
            expected_issuer = settings.clerk_issuer.rstrip("/")
            actual_issuer = issuer.rstrip("/")
            if actual_issuer != expected_issuer:
                logger.error(f"Auth error: Invalid issuer. Expected {expected_issuer}, got {actual_issuer}")
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

def require_user_id(user: dict[str, Any]) -> str:
    """Extract and validate user ID from auth payload."""
    user_id = str(user.get("sub", "")).strip()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user_id


def _admin_user_id_set() -> set[str]:
    return {value.strip() for value in settings.admin_user_ids.split(",") if value.strip()}


def is_admin(user: dict[str, Any]) -> bool:
    return require_user_id(user) in _admin_user_id_set()


def is_admin_user_id(user_id: str) -> bool:
    return user_id in _admin_user_id_set()


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _can_access_project(project: Project, user: dict[str, Any]) -> bool:
    if is_admin(user):
        return True
    user_id = require_user_id(user)
    if project.owner_user_id == LEGACY_OWNER_USER_ID:
        return False
    return project.owner_user_id == user_id


def ensure_project_access(db: Session, project_id: str, user: dict[str, Any]) -> Project:
    project = db.get(Project, project_id)
    if not project or not _can_access_project(project, user):
        raise _not_found("Project not found")
    return project


def ensure_pipeline_access(db: Session, pipeline_id: str, user: dict[str, Any]) -> Pipeline:
    pipeline = db.get(Pipeline, pipeline_id)
    if not pipeline:
        raise _not_found("Pipeline not found")
    ensure_project_access(db, pipeline.project_id, user)
    return pipeline


def ensure_pipeline_version_access(db: Session, version_id: str, user: dict[str, Any]) -> PipelineVersion:
    version = db.get(PipelineVersion, version_id)
    if not version:
        raise _not_found("Pipeline version not found")
    ensure_pipeline_access(db, version.pipeline_id, user)
    return version


def ensure_model_fit_access(db: Session, model_id: str, user: dict[str, Any]) -> ModelFit:
    model_fit = db.get(ModelFit, model_id)
    if not model_fit:
        raise _not_found("Model not found")
    ensure_pipeline_version_access(db, model_fit.pipeline_version_id, user)
    return model_fit


def ensure_uploaded_source_access(db: Session, source_id: str, user: dict[str, Any]) -> UploadedSource:
    source = db.get(UploadedSource, source_id)
    if not source:
        raise _not_found("Source not found")
    ensure_project_access(db, source.project_id, user)
    return source


def current_user_context(user: dict[str, Any] = Depends(require_auth)) -> dict[str, Any]:
    """Return normalized current-user context for route dependencies."""
    user_id = require_user_id(user)
    return {
        "user_id": user_id,
        "is_admin": is_admin_user_id(user_id),
    }


# Alias for compatibility
verify_token = require_auth
