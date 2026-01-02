"""
Application Management Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func

from planproof.api.dependencies import get_db, get_current_user
from planproof.db import Database, Application, Submission, Run, Document, ValidationCheck, ExtractedField

router = APIRouter()


class ApplicationResponse(BaseModel):
    """Application response model."""
    id: int
    application_ref: str
    applicant_name: Optional[str]
    created_at: str
    updated_at: Optional[str]
    submission_count: int
    latest_run_id: Optional[int] = None
    run_count: int = 0
    status: str = "unknown"  # based on latest run status


class ApplicationCreateRequest(BaseModel):
    """Request to create new application."""
    application_ref: str
    applicant_name: Optional[str] = None


@router.get("/applications")
async def list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
) -> List[ApplicationResponse]:
    """
    List all planning applications.
    
    **Query Parameters:**
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    """
    session = db.get_session()
    try:
        # Fix N+1 query: Use a single query with join and group_by
        apps_with_counts = session.query(
            Application,
            func.count(Submission.id).label('submission_count')
        ).outerjoin(
            Submission,
            Submission.planning_case_id == Application.id
        ).group_by(
            Application.id
        ).offset(skip).limit(limit).all()

        results = []
        for app, submission_count in apps_with_counts:
            # Get latest run for this application
            latest_run = session.query(Run).filter(
                Run.application_id == app.id
            ).order_by(Run.started_at.desc()).first()
            
            # Count total runs for this application
            run_count = session.query(func.count(Run.id)).filter(
                Run.application_id == app.id
            ).scalar() or 0
            
            # Determine status from latest run
            status = "unknown"
            if latest_run:
                if latest_run.status == "completed":
                    status = "completed"
                elif latest_run.status == "failed":
                    status = "issues"
                elif latest_run.status in ["pending", "running"]:
                    status = "processing"
            
            results.append(ApplicationResponse(
                id=app.id,
                application_ref=app.application_ref,
                applicant_name=app.applicant_name,
                created_at=app.created_at.isoformat() if app.created_at else None,
                updated_at=app.updated_at.isoformat() if app.updated_at else None,
                submission_count=submission_count,
                latest_run_id=latest_run.id if latest_run else None,
                run_count=run_count,
                status=status
            ))

        return results
    finally:
        session.close()


@router.get("/applications/{application_ref}")
async def get_application(
    application_ref: str,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
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


@router.get("/applications/id/{application_id}")
async def get_application_details(
    application_id: int,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Get full application details with run history by ID.
    
    **Path Parameters:**
    - application_id: Application database ID
    
    **Returns:**
    - Application metadata
    - List of all runs with documents and validation summary
    """
    session = db.get_session()
    try:
        app = session.query(Application).filter(Application.id == application_id).first()
        
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Get all runs for this application (most recent first)
        runs = session.query(Run).filter(
            Run.application_id == application_id
        ).order_by(Run.started_at.desc()).all()
        
        run_history = []
        for run in runs:
            document_ids = [doc.id for doc in run.documents] if run.documents else []
            if not document_ids and run.document_id:
                document_ids = [run.document_id]

            # Count validation checks by status
            checks_pass = session.query(func.count(ValidationCheck.id)).filter(
                ValidationCheck.document_id.in_(document_ids),
                ValidationCheck.status == 'pass'
            ).scalar() if document_ids else 0
            
            checks_fail = session.query(func.count(ValidationCheck.id)).filter(
                ValidationCheck.document_id.in_(document_ids),
                ValidationCheck.status == 'fail'
            ).scalar() if document_ids else 0
            
            checks_warning = session.query(func.count(ValidationCheck.id)).filter(
                ValidationCheck.document_id.in_(document_ids),
                ValidationCheck.status == 'warning'
            ).scalar() if document_ids else 0
            
            checks_needs_review = session.query(func.count(ValidationCheck.id)).filter(
                ValidationCheck.document_id.in_(document_ids),
                ValidationCheck.status == 'needs_review'
            ).scalar() if document_ids else 0
            
            run_history.append({
                "id": run.id,
                "created_at": run.started_at.isoformat() if run.started_at else None,
                "status": run.status,
                "validation_summary": {
                    "pass": checks_pass,
                    "fail": checks_fail,
                    "warning": checks_warning,
                    "needs_review": checks_needs_review
                }
            })
        
        latest_submission = session.query(Submission).filter(
            Submission.planning_case_id == application_id
        ).order_by(Submission.created_at.desc()).first()

        def _get_latest_field_value(field_names: List[str]) -> Optional[str]:
            if not latest_submission:
                return None
            field = session.query(ExtractedField).filter(
                ExtractedField.submission_id == latest_submission.id,
                ExtractedField.field_name.in_(field_names)
            ).order_by(
                ExtractedField.confidence.desc().nullslast(),
                ExtractedField.created_at.desc()
            ).first()
            return field.field_value if field else None

        # Update Application fields from latest extraction if not already set
        extracted_address = _get_latest_field_value(["site_address", "address"])
        extracted_proposal = _get_latest_field_value(["proposal_description", "proposed_use"])
        extracted_applicant = _get_latest_field_value(["applicant_name"])

        # Update Application record if we have better data from extraction
        if extracted_address and not app.site_address:
            app.site_address = extracted_address
        if extracted_proposal and not app.proposal_description:
            app.proposal_description = extracted_proposal
        if extracted_applicant and not app.applicant_name:
            app.applicant_name = extracted_applicant
        
        if extracted_address or extracted_proposal or extracted_applicant:
            session.commit()

        # Determine overall status from latest run
        latest_status = runs[0].status if runs else "unknown"
        
        return {
            "id": app.id,
            "reference_number": app.application_ref,
            "address": app.site_address or extracted_address or "Not available",
            "proposal": app.proposal_description or extracted_proposal or "Not available",
            "applicant_name": app.applicant_name or extracted_applicant or "Unknown",
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "status": latest_status,
            "run_history": run_history
        }
    finally:
        session.close()


@router.post("/applications")
async def create_application(
    request: ApplicationCreateRequest,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
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
