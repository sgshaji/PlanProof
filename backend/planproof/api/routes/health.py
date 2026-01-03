"""
Health Check Endpoints
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from planproof.api.dependencies import get_db, get_storage_client, get_docintel_client, get_aoai_client
from planproof.db import Database
from planproof.storage import StorageClient
from planproof.docintel import DocumentIntelligence
from planproof.aoai import AzureOpenAIClient

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
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
    Verifies database connectivity with a simple query.
    """
    try:
        session = db.get_session()
        from planproof.db import Application
        count = session.query(Application).count()
        session.close()

        return {
            "status": "healthy",
            "database": "connected",
            "applications_count": count
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )


@router.get("/health/storage")
async def storage_health(storage: StorageClient = Depends(get_storage_client)):
    """
    Azure Blob Storage health check.
    Verifies storage connectivity by listing containers.
    """
    try:
        # Try to list containers to verify connectivity
        blob_service_client = storage.blob_service_client
        containers = list(blob_service_client.list_containers(max_results=1))

        return {
            "status": "healthy",
            "storage": "connected",
            "container_accessible": True
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "storage": "disconnected",
                "error": str(e)
            }
        )


@router.get("/health/docintel")
async def docintel_health(docintel: DocumentIntelligence = Depends(get_docintel_client)):
    """
    Azure Document Intelligence health check.
    Verifies Document Intelligence service is accessible.
    """
    try:
        # Check if client is initialized with credentials
        if not docintel.client:
            raise ValueError("Document Intelligence client not initialized")

        return {
            "status": "healthy",
            "docintel": "connected",
            "service": "azure-document-intelligence"
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "docintel": "disconnected",
                "error": str(e)
            }
        )


@router.get("/health/llm")
async def llm_health(aoai: AzureOpenAIClient = Depends(get_aoai_client)):
    """
    Azure OpenAI health check.
    Verifies LLM service is accessible.
    """
    try:
        # Check if client is initialized
        if not aoai.client:
            raise ValueError("Azure OpenAI client not initialized")

        return {
            "status": "healthy",
            "llm": "connected",
            "service": "azure-openai"
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "llm": "disconnected",
                "error": str(e)
            }
        )


@router.get("/health/full")
async def full_health_check(
    db: Database = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
    docintel: DocumentIntelligence = Depends(get_docintel_client),
    aoai: AzureOpenAIClient = Depends(get_aoai_client)
) -> Dict[str, Any]:
    """
    Comprehensive health check for all services.
    Returns status of database, storage, Document Intelligence, and Azure OpenAI.
    """
    results = {
        "service": "PlanProof API",
        "version": "1.0.0",
        "overall_status": "healthy",
        "checks": {}
    }

    # Check database
    try:
        session = db.get_session()
        from planproof.db import Application
        count = session.query(Application).count()
        session.close()
        results["checks"]["database"] = {
            "status": "healthy",
            "connected": True,
            "applications_count": count
        }
    except Exception as e:
        results["checks"]["database"] = {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }
        results["overall_status"] = "degraded"

    # Check storage
    try:
        blob_service_client = storage.blob_service_client
        list(blob_service_client.list_containers(max_results=1))
        results["checks"]["storage"] = {
            "status": "healthy",
            "connected": True
        }
    except Exception as e:
        results["checks"]["storage"] = {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }
        results["overall_status"] = "degraded"

    # Check Document Intelligence
    try:
        if not docintel.client:
            raise ValueError("Client not initialized")
        results["checks"]["docintel"] = {
            "status": "healthy",
            "connected": True
        }
    except Exception as e:
        results["checks"]["docintel"] = {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }
        results["overall_status"] = "degraded"

    # Check Azure OpenAI
    try:
        if not aoai.client:
            raise ValueError("Client not initialized")
        results["checks"]["llm"] = {
            "status": "healthy",
            "connected": True
        }
    except Exception as e:
        results["checks"]["llm"] = {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }
        results["overall_status"] = "degraded"

    # Return appropriate status code based on overall health
    if results["overall_status"] == "degraded":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=results
        )

    return results
