"""
Health Check Endpoints
"""

from fastapi import APIRouter, Depends
from planproof.api.dependencies import get_db
from planproof.db import Database

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns service status.
    """
    return {
        "status": "healthy",
        "service": "PlanProof API",
        "version": "1.0.0"
    }


@router.get("/health/db")
async def database_health(db: Database = Depends(get_db)):
    """
    Database health check.
    Verifies database connectivity.
    """
    try:
        session = db.get_session()
        # Simple query to test connection
        from planproof.db import Application
        count = session.query(Application).count()
        session.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "applications_count": count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
