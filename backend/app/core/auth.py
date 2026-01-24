from fastapi import Depends, HTTPException, Security, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from clerk_backend_api import Clerk
from app.core.config import settings

# Initialize Clerk client
clerk = Clerk(bearer_auth=settings.clerk_secret_key)

async def require_auth(request: Request):
    """
    Verify the session token from the Authorization header using Clerk.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    try:
        # Verify the session token using Clerk SDK
        # Note: The user hint suggested clerk.sessions.verify(token)
        # We'll use that exact signature.
        session = clerk.sessions.verify_token(token)
        return session
    except Exception as e:
        # Log the error for debugging
        print(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

# Alias for compatibility if needed, but we will update main.py
verify_token = require_auth
