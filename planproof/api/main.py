"""
FastAPI REST API - Main Application

Provides REST endpoints for BCC to integrate with PlanProof.
For MVP: No authentication required (internal use only).
For Production: Enable authentication in dependencies.py
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from planproof.config import get_settings
from .routes import applications, documents, validation, health

settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title="PlanProof API",
    description="AI-powered planning application validation system",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware (configure for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(applications.router, prefix="/api/v1", tags=["Applications"])
app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(validation.router, prefix="/api/v1", tags=["Validation"])


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
