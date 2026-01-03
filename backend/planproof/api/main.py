"""
FastAPI REST API - Main Application

Provides REST endpoints for BCC to integrate with PlanProof.

Authentication: All endpoints require authentication via JWT token or API key.
- Configure API_KEYS environment variable for API key authentication
- Configure JWT_SECRET_KEY environment variable for JWT token authentication
- If neither is configured, authentication is bypassed (MVP mode only)
"""

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from planproof.config import get_settings
from .routes import applications, documents, validation, health, runs, review, auth
from .dependencies import get_current_user

settings = get_settings()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Initialize FastAPI app
app = FastAPI(
    title="PlanProof API",
    description="AI-powered planning application validation system",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - restrict to configured origins
# Configure allowed origins via API_CORS_ORIGINS environment variable
# Format: comma-separated list, e.g., "http://localhost:3000,https://app.example.com"
cors_origins = settings.api_cors_origins
if isinstance(cors_origins, str):
    cors_origins = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(applications.router, prefix="/api/v1", tags=["Applications"])
app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(validation.router, prefix="/api/v1", tags=["Validation"])
app.include_router(runs.router, prefix="/api/v1", tags=["Runs"])
app.include_router(review.router, prefix="/api/v1", tags=["Review"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "type": type(exc).__name__
        }
    )


# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "PlanProof API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/api/docs"
    }


# User info endpoint for authentication
@app.get("/api/v1/auth/user-info")
async def get_user_info(user: dict = Depends(get_current_user)):
    """
    Get current user information from JWT token.
    
    Returns:
        - user_id: User identifier
        - role: User role (officer, admin, reviewer, planner, guest)
        - auth_type: Authentication method (jwt, apikey, none)
        - can_review: Boolean indicating if user can perform HIL reviews
    """
    allowed_review_roles = ['officer', 'admin', 'reviewer', 'planner']
    user_role = user.get('role', 'guest')
    
    return {
        "user_id": user.get('user_id'),
        "role": user_role,
        "auth_type": user.get('auth_type', 'none'),
        "can_review": user_role in allowed_review_roles
    }
