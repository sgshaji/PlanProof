"""
Validation Results & Status Endpoints
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from planproof.api.dependencies import get_db, get_current_user
from planproof.db import Database, Run, Document, ValidationCheck, Artefact

router = APIRouter()


class RunStatus(BaseModel):
    """Run status response."""
    run_id: int
    status: str
    started_at: str
    completed_at: Optional[str]
    document_id: Optional[int]
    document_ids: Optional[List[int]] = None
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
    document_id: Optional[int]
    document_ids: Optional[List[int]] = None
    status: str
    summary: Dict[str, int]
    findings: List[ValidationFinding]
    artifacts: Dict[str, str]


@router.get("/applications/{application_ref}/status")
async def get_validation_status(
    application_ref: str,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
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
                document_ids=[doc.id for doc in run.documents] if run.documents else None,
                error_message=run.error_message
            )
            for run in runs
        ]
    finally:
        session.close()


@router.get("/runs/{run_id}/status")
async def get_run_status(
    run_id: int,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
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
            document_ids=[doc.id for doc in run.documents] if run.documents else None,
            error_message=run.error_message
        )
    finally:
        session.close()


@router.get("/applications/{application_ref}/results")
async def get_validation_results(
    application_ref: str,
    run_id: Optional[int] = Query(None, description="Specific run ID (latest if not provided)"),
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
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
        
        document_ids = [doc.id for doc in run.documents] if run.documents else []
        if not document_ids and run.document_id:
            document_ids = [run.document_id]

        checks = []
        artifacts = []
        if document_ids:
            # Get validation checks
            checks = session.query(ValidationCheck).filter(
                ValidationCheck.document_id.in_(document_ids)
            ).all()

            # Get artifacts
            artifacts = session.query(Artefact).filter(
                Artefact.document_id.in_(document_ids)
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
            document_ids=document_ids,
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
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
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
        
        documents = list(run.documents) if run.documents else []
        if not documents and run.document_id:
            document = session.query(Document).filter(Document.id == run.document_id).first()
            if document:
                documents = [document]

        if not documents:
            raise HTTPException(
                status_code=404,
                detail="No documents associated with this run"
            )

        document_ids = [doc.id for doc in documents]
        document_lookup = {doc.id: doc for doc in documents}

        document_entries = [
            {
                "document_id": doc.id,
                "document_name": doc.filename,
                "document_type": doc.document_type or "Unknown",
                "status": "processed" if run.status == "completed" else "pending"
            }
            for doc in documents
        ]

        checks = session.query(ValidationCheck).filter(
            ValidationCheck.document_id.in_(document_ids)
        ).all()
        
        summary = {"pass": 0, "fail": 0, "warning": 0, "needs_review": 0}
        findings = []
        
        for check in checks:
            # Map ValidationCheck status enum to string
            status_str = check.status.value if hasattr(check.status, 'value') else str(check.status)
            
            severity = None
            if check.rule and check.rule.severity:
                severity = check.rule.severity
            
            findings.append({
                "id": check.id,
                "rule_id": check.rule_id_string or str(check.rule_id),
                "title": check.rule_id_string or str(check.rule_id),
                "status": status_str,
                "severity": severity or "info",
                "message": check.explanation or "",
                "evidence": check.evidence_ids or [],
                "details": check.rule.rule_config if check.rule and check.rule.rule_config else None,
                "document_name": document_lookup.get(check.document_id).filename if check.document_id in document_lookup else None
            })
            
            # Count by status
            if status_str.lower() in ["pass", "passed"]:
                summary["pass"] += 1
            elif status_str.lower() in ["fail", "failed"]:
                summary["fail"] += 1
            elif status_str.lower() == "warning":
                summary["warning"] += 1
            else:
                summary["needs_review"] += 1
        
        # Get document details to show extracted fields
        extracted_fields = {}
        for doc in documents:
            extraction_artefact = session.query(Artefact).filter(
                Artefact.document_id == doc.id,
                Artefact.artefact_type == "extraction"
            ).first()

            if extraction_artefact and extraction_artefact.blob_uri:
                extracted_fields[doc.id] = {"note": "Extraction data available at blob storage"}
        
        # Count LLM calls from artefacts
        llm_count = 0
        if document_ids:
            llm_count = session.query(Artefact).filter(
                Artefact.document_id.in_(document_ids),
                Artefact.artefact_type == "llm_notes"
            ).count()
        
        # Build response with correct structure
        response_summary = {
            "total_documents": len(document_ids),
            "processed": len(document_ids) if run.status == "completed" else 0,
            "errors": 1 if run.status == "failed" else 0,
            "pass": summary["pass"],
            "fail": summary["fail"],
            "warning": summary["warning"],
            "needs_review": summary["needs_review"]
        }
        
        return {
            "run_id": run.id,
            "status": run.status,
            "summary": response_summary,
            "documents": document_entries,
            "findings": findings,
            "llm_calls_per_run": llm_count,
            "extracted_fields": extracted_fields,
            "document_names": [doc.filename for doc in documents],
            "completed_at": run.completed_at.isoformat() if run.completed_at else None
        }
    finally:
        session.close()
