"""
API Dependencies - Database, Auth, etc.

Authentication is now enabled via JWT tokens or API keys.
Configure via environment variables: JWT_SECRET_KEY, API_KEYS
"""

from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from planproof.db import Database
from planproof.storage import StorageClient
from planproof.docintel import DocumentIntelligence
from planproof.aoai import AzureOpenAIClient
from planproof.config import get_settings


def get_db() -> Database:
    """Get database instance."""
    return Database()


def get_storage_client() -> StorageClient:
    """Get storage client instance."""
    return StorageClient()


def get_docintel_client() -> DocumentIntelligence:
    """Get Document Intelligence client instance."""
    return DocumentIntelligence()


def get_aoai_client() -> AzureOpenAIClient:
    """Get Azure OpenAI client instance."""
    return AzureOpenAIClient()


# ============================================================================
# AUTHENTICATION
# ============================================================================

security = HTTPBearer(auto_error=False)


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, description="API Key for authentication")
) -> Optional[str]:
    """
    Verify API key from X-API-Key header.

    Configure valid keys via API_KEYS environment variable (comma-separated).
    Returns the API key if valid, raises HTTPException otherwise.
    """
    settings = get_settings()

    # If no API keys configured, skip authentication (MVP mode)
    if not settings.api_keys:
        return None

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # Check against configured API keys
    if x_api_key not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return x_api_key


async def verify_jwt_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Verify JWT token from Authorization header.

    Configure JWT_SECRET_KEY in environment to enable JWT authentication.
    Returns decoded token payload if valid, raises HTTPException otherwise.
    """
    settings = get_settings()

    # If no JWT secret configured, skip authentication (MVP mode)
    if not settings.jwt_secret_key:
        return None

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )

        return payload

    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


async def get_current_user(
    api_key: Optional[str] = Depends(verify_api_key),
    jwt_payload: Optional[dict] = Depends(verify_jwt_token)
) -> dict:
    """
    Get current authenticated user from either API key or JWT token.

    This dependency supports both authentication methods:
    - X-API-Key header for API key authentication
    - Authorization: Bearer <token> for JWT authentication

    If neither authentication method is configured, allows unauthenticated access (MVP mode).

    Usage in routes:
        @router.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            # user contains authentication info
            pass
    """
    settings = get_settings()

    # If no auth configured, allow unauthenticated access
    if not settings.api_keys and not settings.jwt_secret_key:
        return {"user_id": "anonymous", "auth_type": "none"}

    # JWT token takes precedence
    if jwt_payload:
        return {
            "user_id": jwt_payload.get("sub", "unknown"),
            "auth_type": "jwt",
            "payload": jwt_payload
        }

    # Fall back to API key
    if api_key:
        return {
            "user_id": f"api_key_{api_key[:8]}",
            "auth_type": "api_key"
        }

    # Neither auth method succeeded
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload to encode (should include 'sub' for user identifier)
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string

    Example:
        token = create_access_token(
            data={"sub": "user@example.com", "role": "officer"},
            expires_delta=timedelta(hours=1)
        )
    """
    settings = get_settings()

    if not settings.jwt_secret_key:
        raise ValueError("JWT_SECRET_KEY not configured")

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


# ============================================================================
# USAGE NOTES
# ============================================================================
#
# To protect a route with authentication:
#
# Option 1: Require authentication (API key OR JWT)
#   @router.get("/protected")
#   async def protected_route(user: dict = Depends(get_current_user)):
#       # user contains auth info
#       pass
#
# Option 2: API key only
#   @router.get("/api-key-only", dependencies=[Depends(verify_api_key)])
#   async def api_key_route():
#       pass
#
# Option 3: JWT only
#   @router.get("/jwt-only", dependencies=[Depends(verify_jwt_token)])
#   async def jwt_route():
#       pass
#
# Configuration:
# - Set API_KEYS="key1,key2,key3" in .env for API key auth
# - Set JWT_SECRET_KEY="your-secret-key" in .env for JWT auth
# - If neither is set, all routes allow unauthenticated access (MVP mode)
