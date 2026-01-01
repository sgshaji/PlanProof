"""
Validation Results & Status Endpoints
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from planproof.api.dependencies import get_db
from planproof.db import Database, Run, Document, ValidationCheck, Artefact

router = APIRouter()


class RunStatus(BaseModel):
    """Run status response."""
    run_id: int
    status: str
    started_at: str
    completed_at: Optional[str]
    document_id: Optional[int]
    error_message: Optional[str]


class ValidationFinding(BaseModel):
    """Individual validation finding."""
    rule_id: str
    title: str
    status: str
    severity: str
    message: Optional[str]
    evidence: Optional[List[Dict[str, Any]]]


class ValidationResults(BaseModel):
    """Complete validation results."""
    run_id: int
    application_ref: str
    document_id: int
    status: str
    summary: Dict[str, int]
    findings: List[ValidationFinding]
    artifacts: Dict[str, str]


@router.get("/applications/{application_ref}/status")
async def get_validation_status(
    application_ref: str,
    db: Database = Depends(get_db)
) -> List[RunStatus]:
    """
    Get processing status for all runs of an application.
    
    **Path Parameters:**
    - application_ref: Application reference (e.g., "APP/2024/001")
    
    **Returns:**
    List of runs with their current status.
    """
    session = db.get_session()
    try:
        # Find application
        from planproof.db import Application
        app = session.query(Application).filter(
            Application.application_ref == application_ref
        ).first()
        
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Get all runs for this application
        runs = session.query(Run).filter(Run.application_id == app.id).all()
        
        return [
            RunStatus(
                run_id=run.id,
                status=run.status,
                started_at=run.started_at.isoformat() if run.started_at else None,
                completed_at=run.completed_at.isoformat() if run.completed_at else None,
                document_id=run.document_id,
                error_message=run.error_message
            )
            for run in runs
        ]
    finally:
        session.close()


@router.get("/runs/{run_id}/status")
async def get_run_status(
    run_id: int,
    db: Database = Depends(get_db)
) -> RunStatus:
    """
    Get status of a specific processing run.
    
    **Path Parameters:**
    - run_id: Run ID from document upload response
    """
    session = db.get_session()
    try:
        run = session.query(Run).filter(Run.id == run_id).first()
        
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        return RunStatus(
            run_id=run.id,
            status=run.status,
            started_at=run.started_at.isoformat() if run.started_at else None,
            completed_at=run.completed_at.isoformat() if run.completed_at else None,
            document_id=run.document_id,
            error_message=run.error_message
        )
    finally:
        session.close()


@router.get("/applications/{application_ref}/results")
async def get_validation_results(
    application_ref: str,
    run_id: Optional[int] = Query(None, description="Specific run ID (latest if not provided)"),
    db: Database = Depends(get_db)
) -> ValidationResults:
    """
    Get validation results for an application.
    
    **Path Parameters:**
    - application_ref: Application reference (e.g., "APP/2024/001")
    
    **Query Parameters:**
    - run_id: Optional specific run ID (uses latest if not provided)
    
    **Returns:**
    Complete validation results with findings and evidence.
    """
    session = db.get_session()
    try:
        # Find application
        from planproof.db import Application
        app = session.query(Application).filter(
            Application.application_ref == application_ref
        ).first()
        
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Get run (specific or latest)
        if run_id:
            run = session.query(Run).filter(
                Run.id == run_id,
                Run.application_id == app.id
            ).first()
        else:
            run = session.query(Run).filter(
                Run.application_id == app.id
            ).order_by(Run.started_at.desc()).first()
        
        if not run:
            raise HTTPException(status_code=404, detail="No runs found for this application")
        
        if run.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Run {run.id} is not completed yet. Status: {run.status}"
            )
        
        # Get validation checks
        checks = session.query(ValidationCheck).filter(
            ValidationCheck.run_id == run.id
        ).all()
        
        # Get artifacts
        artifacts = session.query(Artefact).filter(
            Artefact.document_id == run.document_id
        ).all()
        
        # Build findings
        findings = []
        summary = {"pass": 0, "fail": 0, "warning": 0, "needs_review": 0}
        
        for check in checks:
            findings.append(ValidationFinding(
                rule_id=check.rule_id,
                title=check.title or check.rule_id,
                status=check.status,
                severity=check.severity or "info",
                message=check.message,
                evidence=check.evidence_data or []
            ))
            
            # Update summary
            if check.status in summary:
                summary[check.status] += 1
        
        # Build artifacts dict
        artifacts_dict = {
            art.artefact_type: art.blob_uri
            for art in artifacts
        }
        
        return ValidationResults(
            run_id=run.id,
            application_ref=application_ref,
            document_id=run.document_id,
            status=run.status,
            summary=summary,
            findings=findings,
            artifacts=artifacts_dict
        )
    finally:
        session.close()


@router.get("/runs/{run_id}/results")
async def get_run_results(
    run_id: int,
    db: Database = Depends(get_db)
):
    """
    Get validation results for a specific run.
    
    **Path Parameters:**
    - run_id: Run ID from document upload response
    """
    session = db.get_session()
    try:
        run = session.query(Run).filter(Run.id == run_id).first()
        
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        if run.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Run is not completed yet. Status: {run.status}"
            )
        
        # Get validation checks
        checks = session.query(ValidationCheck).filter(
            ValidationCheck.run_id == run.id
        ).all()
        
        summary = {"pass": 0, "fail": 0, "warning": 0, "needs_review": 0}
        findings = []
        
        for check in checks:
            findings.append({
                "rule_id": check.rule_id,
                "title": check.title or check.rule_id,
                "status": check.status,
                "severity": check.severity or "info",
                "message": check.message,
                "evidence": check.evidence_data or []
            })
            
            if check.status in summary:
                summary[check.status] += 1
        
        return {
            "run_id": run.id,
            "status": run.status,
            "summary": summary,
            "findings": findings,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None
        }
    finally:
        session.close()
