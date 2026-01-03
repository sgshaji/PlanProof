"""
Validation Results & Status Endpoints
"""

from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from planproof.api.dependencies import get_db, get_current_user, get_storage_client
from planproof.db import Database, Run, Document, ValidationCheck, Artefact
from planproof.storage import StorageClient

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
    evidence_details: Optional[List[Dict[str, Any]]] = None  # [{"page": 1, "snippet": "...", "evidence_key": "..."}]
    candidate_documents: Optional[List[Dict[str, Any]]] = None  # [{"document_id": 1, "document_name": "...", "confidence": 0.8}]


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


def _parse_blob_uri(blob_uri: str) -> Optional[Tuple[str, str]]:
    if not blob_uri or not blob_uri.startswith("azure://"):
        return None
    path = blob_uri.replace("azure://", "", 1)
    parts = path.split("/", 2)
    if len(parts) < 3:
        return None
    container = parts[1]
    blob_path = parts[2]
    return container, blob_path


def _normalize_llm_calls(
    llm_notes: Dict[str, Any],
    fallback_timestamp: Optional[str] = None
) -> List[Dict[str, Any]]:
    raw_calls = llm_notes.get("llm_calls") or llm_notes.get("llm_call_details") or []
    if not isinstance(raw_calls, list):
        return []
    normalized: List[Dict[str, Any]] = []
    for call in raw_calls:
        if not isinstance(call, dict):
            continue
        normalized.append({
            "timestamp": call.get("timestamp") or fallback_timestamp,
            "purpose": call.get("purpose") or "LLM call",
            "rule_type": call.get("rule_type") or "unknown",
            "tokens_used": int(call.get("tokens_used") or 0),
            "model": call.get("model") or "unknown",
            "response_time_ms": int(call.get("response_time_ms") or 0)
        })
    return normalized


def _normalize_status(status: str) -> str:
    return (status or "").strip().lower()


def _is_issue_status(status: str) -> bool:
    normalized = _normalize_status(status)
    return normalized not in {"pass", "passed"}


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        import json as json_module
        return json_module.dumps(value, sort_keys=True, ensure_ascii=False)
    except TypeError:
        return str(value)


def _build_findings_map(
    checks: List[ValidationCheck],
    document_lookup: Dict[int, Document]
) -> Dict[str, Dict[str, Any]]:
    findings_map: Dict[str, Dict[str, Any]] = {}
    for check in checks:
        rule_id = check.rule_id_string or str(check.rule_id)
        doc_id = check.document_id or 0
        status_str = check.status.value if hasattr(check.status, "value") else str(check.status)
        key = f"{rule_id}:{doc_id}"
        findings_map[key] = {
            "rule_id": rule_id,
            "title": rule_id,
            "status": status_str,
            "severity": check.rule.severity if check.rule and check.rule.severity else "info",
            "message": check.explanation or "",
            "document_id": check.document_id,
            "document_name": document_lookup.get(check.document_id).filename if check.document_id in document_lookup else None,
        }
    return findings_map


def _load_extraction_fields(
    session,
    storage: StorageClient,
    documents: List[Document]
) -> Dict[str, Dict[str, Any]]:
    fields_map: Dict[str, Dict[str, Any]] = {}
    for doc in documents:
        extraction_artefact = session.query(Artefact).filter(
            Artefact.document_id == doc.id,
            Artefact.artefact_type == "extraction"
        ).order_by(Artefact.created_at.desc()).first()
        if not extraction_artefact or not extraction_artefact.blob_uri:
            continue
        parsed = _parse_blob_uri(extraction_artefact.blob_uri)
        if not parsed:
            continue
        container, blob_path = parsed
        try:
            extraction_result = storage.read_json_blob(container, blob_path)
        except Exception:
            continue
        fields = extraction_result.get("fields", {}) if isinstance(extraction_result, dict) else {}
        if not isinstance(fields, dict):
            continue
        for field_name, value in fields.items():
            key = f"{doc.id}:{field_name}"
            fields_map[key] = {
                "field": field_name,
                "value": value,
                "document_id": doc.id,
                "document_name": doc.filename,
            }
    return fields_map


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
    storage: StorageClient = Depends(get_storage_client),
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
        
        if run.status not in ["completed", "reviewed"]:
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
            
            # Fetch detailed evidence from Evidence table if evidence_ids exist
            evidence_list = []
            if check.evidence_ids:
                from planproof.db import Evidence
                evidences = session.query(Evidence).filter(
                    Evidence.id.in_(check.evidence_ids)
                ).all()
                for ev in evidences:
                    evidence_list.append({
                        "id": ev.id,
                        "page": ev.page_number,
                        "snippet": ev.snippet[:200] if ev.snippet else "",
                        "evidence_key": ev.evidence_key,
                        "confidence": ev.confidence,
                        "bbox": ev.bbox
                    })
            
            findings.append({
                "id": check.id,
                "rule_id": check.rule_id_string or str(check.rule_id),
                "title": check.rule_id_string or str(check.rule_id),
                "status": status_str,
                "severity": severity or "info",
                "message": check.explanation or "",
                "evidence": check.evidence_ids or [],
                "evidence_details": check.evidence_details or evidence_list,
                "candidate_documents": check.candidate_documents or [],
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
        llm_calls: List[Dict[str, Any]] = []
        if document_ids:
            llm_artefacts = session.query(Artefact).filter(
                Artefact.document_id.in_(document_ids),
                Artefact.artefact_type == "llm_notes"
            ).order_by(Artefact.created_at.asc()).all()
            llm_count = len(llm_artefacts)
            for artefact in llm_artefacts:
                parsed = _parse_blob_uri(artefact.blob_uri)
                if not parsed:
                    continue
                container, blob_path = parsed
                try:
                    llm_notes = storage.read_json_blob(container, blob_path)
                except Exception:
                    continue
                llm_calls.extend(
                    _normalize_llm_calls(
                        llm_notes,
                        fallback_timestamp=artefact.created_at.isoformat() if artefact.created_at else None
                    )
                )
        total_tokens = sum(call.get("tokens_used", 0) for call in llm_calls)
        total_calls = len(llm_calls) if llm_calls else llm_count
        
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
            "llm_calls": llm_calls,
            "llm_call_totals": {
                "total_calls": total_calls,
                "total_tokens": total_tokens
            },
            "extracted_fields": extracted_fields,
            "document_names": [doc.filename for doc in documents],
            "completed_at": run.completed_at.isoformat() if run.completed_at else None
        }
    finally:
        session.close()


@router.get("/runs/compare")
async def compare_runs(
    run_id_a: int = Query(..., description="Base run ID"),
    run_id_b: int = Query(..., description="Comparison run ID"),
    db: Database = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
    user: dict = Depends(get_current_user)
):
    """
    Compare validation findings and extracted fields between two runs.
    """
    session = db.get_session()
    try:
        run_a = session.query(Run).filter(Run.id == run_id_a).first()
        run_b = session.query(Run).filter(Run.id == run_id_b).first()

        if not run_a or not run_b:
            raise HTTPException(status_code=404, detail="One or both runs not found")

        if run_a.status != "completed" or run_b.status != "completed":
            raise HTTPException(status_code=400, detail="Both runs must be completed to compare")

        if run_a.application_id and run_b.application_id and run_a.application_id != run_b.application_id:
            raise HTTPException(status_code=400, detail="Runs must belong to the same application")

        def _load_documents(run: Run) -> List[Document]:
            documents = list(run.documents) if run.documents else []
            if not documents and run.document_id:
                document = session.query(Document).filter(Document.id == run.document_id).first()
                if document:
                    documents = [document]
            return documents

        documents_a = _load_documents(run_a)
        documents_b = _load_documents(run_b)

        if not documents_a or not documents_b:
            raise HTTPException(status_code=404, detail="Both runs must have associated documents")

        doc_lookup_a = {doc.id: doc for doc in documents_a}
        doc_lookup_b = {doc.id: doc for doc in documents_b}

        checks_a = session.query(ValidationCheck).filter(
            ValidationCheck.document_id.in_([doc.id for doc in documents_a])
        ).all()
        checks_b = session.query(ValidationCheck).filter(
            ValidationCheck.document_id.in_([doc.id for doc in documents_b])
        ).all()

        findings_a = _build_findings_map(checks_a, doc_lookup_a)
        findings_b = _build_findings_map(checks_b, doc_lookup_b)

        issues_a = {key for key, val in findings_a.items() if _is_issue_status(val["status"])}
        issues_b = {key for key, val in findings_b.items() if _is_issue_status(val["status"])}

        new_issues = [findings_b[key] for key in sorted(issues_b - issues_a)]
        resolved_issues = [findings_a[key] for key in sorted(issues_a - issues_b)]

        status_changes = []
        for key in sorted(set(findings_a.keys()) & set(findings_b.keys())):
            status_a = findings_a[key]["status"]
            status_b = findings_b[key]["status"]
            if _normalize_status(status_a) != _normalize_status(status_b):
                status_changes.append({
                    **findings_b[key],
                    "from_status": status_a,
                    "to_status": status_b,
                })

        fields_a = _load_extraction_fields(session, storage, documents_a)
        fields_b = _load_extraction_fields(session, storage, documents_b)

        added_fields = []
        removed_fields = []
        changed_fields = []

        keys_a = set(fields_a.keys())
        keys_b = set(fields_b.keys())

        for key in sorted(keys_b - keys_a):
            item = fields_b[key]
            added_fields.append({
                "field": item["field"],
                "value": _stringify_value(item["value"]),
                "document_id": item["document_id"],
                "document_name": item["document_name"],
            })

        for key in sorted(keys_a - keys_b):
            item = fields_a[key]
            removed_fields.append({
                "field": item["field"],
                "value": _stringify_value(item["value"]),
                "document_id": item["document_id"],
                "document_name": item["document_name"],
            })

        for key in sorted(keys_a & keys_b):
            old_value = _stringify_value(fields_a[key]["value"])
            new_value = _stringify_value(fields_b[key]["value"])
            if old_value != new_value:
                item = fields_b[key]
                changed_fields.append({
                    "field": item["field"],
                    "old_value": old_value,
                    "new_value": new_value,
                    "document_id": item["document_id"],
                    "document_name": item["document_name"],
                })

        return {
            "run_a": {
                "id": run_a.id,
                "created_at": run_a.started_at.isoformat() if run_a.started_at else None,
            },
            "run_b": {
                "id": run_b.id,
                "created_at": run_b.started_at.isoformat() if run_b.started_at else None,
            },
            "findings": {
                "new_issues": new_issues,
                "resolved_issues": resolved_issues,
                "status_changes": status_changes,
            },
            "extracted_fields": {
                "added": added_fields,
                "removed": removed_fields,
                "changed": changed_fields,
            },
        }
    finally:
        session.close()


class BNGDecisionRequest(BaseModel):
    """Request to submit BNG applicability decision."""
    bng_applicable: bool
    exemption_reason: Optional[str] = None


@router.post("/runs/{run_id}/bng-decision")
async def submit_bng_decision(
    run_id: int,
    request: BNGDecisionRequest,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Submit BNG (Biodiversity Net Gain) applicability decision for a run.
    
    **Path Parameters:**
    - run_id: Run ID
    
    **Request Body:**
    ```json
    {
        "bng_applicable": true,
        "exemption_reason": "Householder application - BNG not required"
    }
    ```
    """
    from planproof.db import ExtractedField, Submission
    
    session = db.get_session()
    try:
        # Validate run exists
        run = session.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Get submission associated with this run
        submission = None
        if run.application_id:
            from planproof.db import Application
            app = session.query(Application).filter(Application.id == run.application_id).first()
            if app and app.submissions:
                submission = app.submissions[-1]  # Get latest submission
        
        if not submission:
            raise HTTPException(status_code=400, detail="No submission found for this run")
        
        # Update or create bng_applicable field
        bng_field = session.query(ExtractedField).filter(
            ExtractedField.submission_id == submission.id,
            ExtractedField.field_name == "bng_applicable"
        ).first()
        
        if bng_field:
            bng_field.field_value = str(request.bng_applicable).lower()
            bng_field.confidence = 1.0
            bng_field.extractor = "user"
        else:
            bng_field = ExtractedField(
                submission_id=submission.id,
                field_name="bng_applicable",
                field_value=str(request.bng_applicable).lower(),
                confidence=1.0,
                extractor="user"
            )
            session.add(bng_field)
        
        # Update or create bng_exemption_reason if provided
        if not request.bng_applicable and request.exemption_reason:
            exemption_field = session.query(ExtractedField).filter(
                ExtractedField.submission_id == submission.id,
                ExtractedField.field_name == "bng_exemption_reason"
            ).first()
            
            if exemption_field:
                exemption_field.field_value = request.exemption_reason
                exemption_field.confidence = 1.0
                exemption_field.extractor = "user"
            else:
                exemption_field = ExtractedField(
                    submission_id=submission.id,
                    field_name="bng_exemption_reason",
                    field_value=request.exemption_reason,
                    confidence=1.0,
                    extractor="user"
                )
                session.add(exemption_field)
        
        session.commit()
        
        return {
            "run_id": run_id,
            "submission_id": submission.id,
            "bng_applicable": request.bng_applicable,
            "exemption_reason": request.exemption_reason,
            "message": "BNG decision recorded successfully"
        }
    finally:
        session.close()
