"""
Runs Management Endpoints
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func

from planproof.api.dependencies import get_db, get_current_user
from planproof.db import Database, Run, Application

router = APIRouter()


class RunResponse(BaseModel):
    """Run response model."""
    id: int
    application_ref: Optional[str]
    run_type: str
    status: str
    started_at: str
    completed_at: Optional[str]
    error_message: Optional[str]
    metadata: Optional[Dict[str, Any]]


class RunListResponse(BaseModel):
    """Paginated run list response."""
    runs: List[RunResponse]
    total: int
    page: int
    page_size: int


@router.get("/runs")
async def list_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
) -> List[RunResponse]:
    """
    List all validation runs.
    
    **Query Parameters:**
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    - status: Filter by status (pending, running, completed, failed)
    """
    session = db.get_session()
    try:
        query = session.query(Run).join(
            Application, Run.application_id == Application.id, isouter=True
        )
        
        if status:
            query = query.filter(Run.status == status)
        
        query = query.order_by(Run.started_at.desc())
        runs = query.offset(skip).limit(limit).all()
        
        results = []
        for run in runs:
            # Get application ref if available
            app = session.query(Application).filter(
                Application.id == run.application_id
            ).first()
            
            results.append(RunResponse(
                id=run.id,
                application_ref=app.application_ref if app else None,
                run_type=run.run_type,
                status=run.status,
                started_at=run.started_at.isoformat() if run.started_at else None,
                completed_at=run.completed_at.isoformat() if run.completed_at else None,
                error_message=run.error_message,
                metadata=None  # Simplified for now
            ))
        
        return results
    finally:
        session.close()


@router.get("/runs/{run_id}")
async def get_run(
    run_id: int,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
) -> RunResponse:
    """
    Get run details by ID.
    
    **Path Parameters:**
    - run_id: Run ID
    """
    session = db.get_session()
    try:
        run = session.query(Run).filter(Run.id == run_id).first()
        
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Get application ref if available
        app = session.query(Application).filter(
            Application.id == run.application_id
        ).first()
        
        return RunResponse(
            id=run.id,
            application_ref=app.application_ref if app else None,
            run_type=run.run_type,
            status=run.status,
            started_at=run.started_at.isoformat() if run.started_at else None,
            completed_at=run.completed_at.isoformat() if run.completed_at else None,
            error_message=run.error_message,
            metadata=None  # Simplified for now
        )
    finally:
        session.close()


@router.get("/runs/{run_id}/results")
async def get_run_results(
    run_id: int,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get validation results for a run.
    
    **Path Parameters:**
    - run_id: Run ID
    """
    session = db.get_session()
    try:
        run = session.query(Run).filter(Run.id == run_id).first()
        
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Get application
        app = session.query(Application).filter(
            Application.id == run.application_id
        ).first()
        
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Get validation checks for this run
        from planproof.db import ValidationCheck, Submission, Document
        
        # Find submissions/documents associated with this run
        # This is a simplified version - you may need to adjust based on your data model
        results = {
            "run_id": run.id,
            "application_ref": app.application_ref,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "summary": {
                "total_checks": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0,
                "pending": 0
            },
            "findings": []
        }
        
        return results
    finally:
        session.close()
