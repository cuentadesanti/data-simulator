import jwt
from fastapi import HTTPException, Request
from jwt import PyJWKClient
from app.core.config import settings

# Clerk JWKS URL for token verification
# Usually: https://<your-clerk-frontend-api>/.well-known/jwks.json
# We'll use a placeholder or derive it if possible, but the user suggested:
# CLERK_JWKS_URL = "https://<your-clerk-domain>/.well-known/jwks.json"
# We'll expect the full URL or domain to be configured.
# For now, let's use the secret key to verify if it's a HS256 token (short-lived) 
# OR fetch JWKS if it's RS256 (standard Clerk).
# Clerk uses RS256.

async def require_auth(request: Request) -> dict:
    """
    Verify the session token from the Authorization header using PyJWT and Clerk JWKS.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    try:
        # 1. Decode token header to get 'kid' (Key ID)
        header = jwt.get_unverified_header(token)
        
        # 2. In a real app, we'd fetch JWKS. For Clerk, the JWKS URL is:
        # https://<CLERK_FRONTEND_API>/.well-known/jwks.json
        # We'll assume the user will set DS_CLERK_JWKS_URL or we can derive it.
        # For this fix, let's implement the robust JWKS verification flow.
        
        # We need a JWKS URL. If not provided, we might fail, but let's try to be smart.
        # Usually Clerk tokens have 'iss' (issuer) which is the URL.
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        issuer = unverified_payload.get("iss")
        
        if not issuer:
            raise HTTPException(status_code=401, detail="Invalid token: missing issuer")
            
        jwks_url = f"{issuer}/.well-known/jwks.json"
        
        # Use PyJWKClient with caching
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            # You might want to verify audience 'aud' if configured
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        print(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except Exception as e:
        print(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# Alias for compatibility
verify_token = require_auth
