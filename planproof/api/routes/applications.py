"""
Application Management Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from planproof.api.dependencies import get_db
from planproof.db import Database, Application, Submission

router = APIRouter()


class ApplicationResponse(BaseModel):
    """Application response model."""
    id: int
    application_ref: str
    applicant_name: Optional[str]
    created_at: str
    updated_at: Optional[str]
    submission_count: int


class ApplicationCreateRequest(BaseModel):
    """Request to create new application."""
    application_ref: str
    applicant_name: Optional[str] = None


@router.get("/applications")
async def list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Database = Depends(get_db)
) -> List[ApplicationResponse]:
    """
    List all planning applications.
    
    **Query Parameters:**
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    """
    session = db.get_session()
    try:
        apps = session.query(Application).offset(skip).limit(limit).all()
        
        results = []
        for app in apps:
            submission_count = session.query(Submission).filter(
                Submission.planning_case_id == app.id
            ).count()
            
            results.append(ApplicationResponse(
                id=app.id,
                application_ref=app.application_ref,
                applicant_name=app.applicant_name,
                created_at=app.created_at.isoformat() if app.created_at else None,
                updated_at=app.updated_at.isoformat() if app.updated_at else None,
                submission_count=submission_count
            ))
        
        return results
    finally:
        session.close()


@router.get("/applications/{application_ref}")
async def get_application(
    application_ref: str,
    db: Database = Depends(get_db)
):
    """
    Get application details by reference.
    
    **Path Parameters:**
    - application_ref: Application reference (e.g., "APP/2024/001")
    """
    session = db.get_session()
    try:
        app = session.query(Application).filter(
            Application.application_ref == application_ref
        ).first()
        
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Get submissions
        submissions = session.query(Submission).filter(
            Submission.planning_case_id == app.id
        ).all()
        
        return {
            "id": app.id,
            "application_ref": app.application_ref,
            "applicant_name": app.applicant_name,
            "application_date": app.application_date.isoformat() if app.application_date else None,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            "submissions": [
                {
                    "id": sub.id,
                    "version": sub.submission_version,
                    "status": sub.status,
                    "created_at": sub.created_at.isoformat() if sub.created_at else None
                }
                for sub in submissions
            ]
        }
    finally:
        session.close()


@router.post("/applications")
async def create_application(
    request: ApplicationCreateRequest,
    db: Database = Depends(get_db)
):
    """
    Create a new planning application.
    
    **Request Body:**
    ```json
    {
        "application_ref": "APP/2024/001",
        "applicant_name": "John Smith"
    }
    ```
    """
    session = db.get_session()
    try:
        # Check if already exists
        existing = session.query(Application).filter(
            Application.application_ref == request.application_ref
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Application {request.application_ref} already exists"
            )
        
        # Create new application
        app = db.create_application(
            application_ref=request.application_ref,
            applicant_name=request.applicant_name
        )
        
        return {
            "id": app.id,
            "application_ref": app.application_ref,
            "applicant_name": app.applicant_name,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "message": "Application created successfully"
        }
    finally:
        session.close()
