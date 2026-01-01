"""
API Dependencies - Database, Auth, etc.

For MVP: Authentication is disabled.
For Production: Uncomment auth functions and add to route dependencies.
"""

from typing import Optional
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from planproof.db import Database
from planproof.storage import StorageClient
from planproof.docintel import DocumentIntelligence
from planproof.aoai import AzureOpenAIClient


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
# AUTHENTICATION (Disabled for MVP)
# ============================================================================

# Uncomment for API Key authentication:
# 
# async def verify_api_key(
#     x_api_key: str = Header(..., description="API Key for authentication")
# ):
#     """Verify API key from header."""
#     from planproof.config import get_settings
#     settings = get_settings()
#     
#     # Check against configured API keys
#     valid_keys = settings.api_keys or []  # Add API_KEYS to .env
#     if x_api_key not in valid_keys:
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid API key"
#         )
#     return x_api_key


# Uncomment for Bearer token authentication:
# 
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# 
# security = HTTPBearer()
# 
# async def verify_token(
#     credentials: HTTPAuthorizationCredentials = Depends(security)
# ):
#     """Verify JWT token from header."""
#     token = credentials.credentials
#     # TODO: Implement token verification logic
#     return token


# To enable auth, add to route decorators:
# @router.get("/protected", dependencies=[Depends(verify_api_key)])
# or
# @router.get("/protected", dependencies=[Depends(verify_token)])
