"""
Authentication routes for login, token refresh, and user management.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
import jwt
import hashlib

from planproof.config import get_settings
from planproof.api.dependencies import get_current_user


router = APIRouter(prefix="/auth", tags=["authentication"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class LoginRequest(BaseModel):
    """Login request with username and password."""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Login response with JWT token and user info."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: dict


class UserInfoResponse(BaseModel):
    """User information response."""
    user_id: str
    username: str
    role: str
    auth_type: str
    can_review: bool


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return hash_password(plain_password) == hashed_password


def get_demo_users() -> dict:
    """
    Get demo users for MVP authentication.
    
    In production, this would query a User table in the database.
    For MVP, we use hardcoded demo users with different roles.
    
    Returns:
        Dict mapping username to user info (password_hash, role, user_id)
    """
    return {
        "officer": {
            "password_hash": hash_password("demo123"),
            "role": "officer",
            "user_id": "officer_1",
            "username": "officer"
        },
        "admin": {
            "password_hash": hash_password("admin123"),
            "role": "admin",
            "user_id": "admin_1",
            "username": "admin"
        },
        "planner": {
            "password_hash": hash_password("planner123"),
            "role": "planner",
            "user_id": "planner_1",
            "username": "planner"
        },
        "reviewer": {
            "password_hash": hash_password("reviewer123"),
            "role": "reviewer",
            "user_id": "reviewer_1",
            "username": "reviewer"
        },
        "guest": {
            "password_hash": hash_password("guest123"),
            "role": "guest",
            "user_id": "guest_1",
            "username": "guest"
        }
    }


def create_access_token(user_info: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token for user.
    
    Args:
        user_info: User information to encode (user_id, username, role)
        expires_delta: Token expiration time (default: 24 hours)
        
    Returns:
        JWT token string
    """
    settings = get_settings()
    
    if not settings.jwt_secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT authentication not configured. Set JWT_SECRET_KEY environment variable."
        )
    
    # Default expiration: 24 hours
    if expires_delta is None:
        expires_delta = timedelta(hours=24)
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    # Token payload
    payload = {
        "sub": user_info["user_id"],
        "user_id": user_info["user_id"],
        "username": user_info["username"],
        "role": user_info["role"],
        "auth_type": "jwt",
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return token


# ============================================================================
# ROUTES
# ============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token.
    
    For MVP, uses hardcoded demo users. In production, this would:
    1. Query User table in database
    2. Verify password hash
    3. Check if account is active
    4. Log login attempt
    
    Demo users:
    - officer / demo123 (can review)
    - admin / admin123 (can review)
    - planner / planner123 (can review)
    - reviewer / reviewer123 (can review)
    - guest / guest123 (cannot review)
    """
    demo_users = get_demo_users()
    
    # Check if user exists
    if request.username not in demo_users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_info = demo_users[request.username]
    
    # Verify password
    if not verify_password(request.password, user_info["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Create access token
    token_expires = timedelta(hours=24)
    access_token = create_access_token(user_info, token_expires)
    
    # Determine if user can review
    allowed_review_roles = ['officer', 'admin', 'reviewer', 'planner']
    can_review = user_info["role"] in allowed_review_roles
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(token_expires.total_seconds()),
        user={
            "user_id": user_info["user_id"],
            "username": user_info["username"],
            "role": user_info["role"],
            "auth_type": "jwt",
            "can_review": can_review
        }
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Requires valid JWT token in Authorization header.
    Returns user profile information including role and permissions.
    """
    allowed_review_roles = ['officer', 'admin', 'reviewer', 'planner']
    user_role = user.get('role', 'guest')
    
    return UserInfoResponse(
        user_id=user.get('user_id', user.get('sub', 'unknown')),
        username=user.get('username', 'unknown'),
        role=user_role,
        auth_type=user.get('auth_type', 'jwt'),
        can_review=user_role in allowed_review_roles
    )


@router.post("/refresh")
async def refresh_token(user: dict = Depends(get_current_user)):
    """
    Refresh JWT token for authenticated user.
    
    Requires valid JWT token in Authorization header.
    Returns new token with extended expiration.
    """
    # Create new token with fresh expiration
    user_info = {
        "user_id": user.get('user_id', user.get('sub')),
        "username": user.get('username'),
        "role": user.get('role', 'guest')
    }
    
    token_expires = timedelta(hours=24)
    access_token = create_access_token(user_info, token_expires)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": int(token_expires.total_seconds())
    }


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """
    Logout current user.
    
    Since JWT tokens are stateless, logout is handled client-side by deleting the token.
    This endpoint exists for logging/auditing purposes and future token blacklist functionality.
    """
    return {
        "message": "Logged out successfully",
        "user_id": user.get('user_id', user.get('sub'))
    }
