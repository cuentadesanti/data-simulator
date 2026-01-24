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
        # 1. Decode token header to get 'kid' (Key ID) - useful for debug
        header = jwt.get_unverified_header(token)
        print(f"DEBUG: Token header: {header}")
        
        # 2. Decode payload to get issuer
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        issuer = unverified_payload.get("iss")
        
        if not issuer:
            print("Auth error: No issuer in token")
            raise HTTPException(status_code=401, detail="Invalid token: missing issuer")
            
        # Standard Clerk JWKS URL construction
        clean_issuer = issuer.rstrip('/')
        jwks_url = f"{clean_issuer}/.well-known/jwks.json"
        
        print(f"DEBUG: Verifying token with issuer={issuer}, jwks_url={jwks_url}")
        
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
        print("Auth error: Token expired")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        print(f"Auth error: Invalid token - {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except Exception as e:
        print(f"Auth error: Unexpected exception - {e}")
        # Return exact error for debugging
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

# Alias for compatibility
verify_token = require_auth
