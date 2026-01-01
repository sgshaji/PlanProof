"""
Run orchestrator: Single entry point for UI to start, monitor, and retrieve runs.
"""

import os
import json
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import threading
import hashlib

from planproof.db import Database, Run, Document
from planproof.storage import StorageClient
from planproof.docintel import DocumentIntelligence
from planproof.aoai import AzureOpenAIClient
from planproof.pipeline.ingest import ingest_pdf
from planproof.pipeline.extract import extract_from_pdf_bytes
from planproof.pipeline.validate import load_rule_catalog, validate_extraction
from planproof.pipeline.llm_gate import should_trigger_llm, resolve_with_llm_new
from planproof.config import get_settings

# Initialize settings and logger at module level
settings = get_settings()
LOGGER = logging.getLogger(__name__)


def _ensure_run_dirs(run_id: int) -> tuple:
    """Ensure run directories exist and return paths."""
    inputs_dir = Path(f"./runs/{run_id}/inputs")
    outputs_dir = Path(f"./runs/{run_id}/outputs")
    inputs_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return inputs_dir, outputs_dir


def start_run(
    app_ref: str,
    files: List[Any],  # Streamlit UploadedFile objects
    applicant_name: Optional[str] = None,
    parent_submission_id: Optional[int] = None
) -> int:
    """
    Start a processing run (single or batch).
    
    Args:
        app_ref: Application reference
        files: List of uploaded file objects (Streamlit UploadedFile)
        applicant_name: Optional applicant name
        parent_submission_id: Optional parent submission ID for revisions (V1+)
        
    Returns:
        run_id: Integer run ID
    """
    settings = get_settings()
    db = Database()
    
    # Get or create application first
    application = db.get_application_by_ref(app_ref)
    if application is None:
        application = db.create_application(
            application_ref=app_ref,
            applicant_name=applicant_name
        )
    
    # Create run record with application_id and parent_submission_id
    run = db.create_run(
        run_type="ui_batch" if len(files) > 1 else "ui_single",
        application_id=application.id,
        metadata={
            "application_ref": app_ref,
            "applicant_name": applicant_name,
            "file_count": len(files),
            "parent_submission_id": parent_submission_id,
            "is_modification": parent_submission_id is not None,
            "started_at": datetime.now(timezone.utc).isoformat()
        }
    )
    run_id = run["id"]
    
    # Save uploaded files to temp directory
    inputs_dir, outputs_dir = _ensure_run_dirs(run_id)
    saved_files = []
    
    for uploaded_file in files:
        # Save file to inputs directory
        file_path = inputs_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        saved_files.append(str(file_path))
    
    # Save file list to metadata
    db.update_run(run_id, metadata={"saved_files": saved_files, "parent_submission_id": parent_submission_id})
    
    # Start processing in background thread
    thread = threading.Thread(
        target=_process_run,
        args=(run_id, app_ref, saved_files, applicant_name, parent_submission_id),
        daemon=True
    )
    thread.start()
    
    return run_id


def _process_run(
    run_id: int,
    app_ref: str,
    file_paths: List[str],
    applicant_name: Optional[str],
    parent_submission_id: Optional[int] = None
):
    """Process a run in background thread."""
    db = Database()
    storage_client = StorageClient()
    docintel = DocumentIntelligence()
    aoai_client = AzureOpenAIClient()
    
    try:
        db.update_run(run_id, status="running")
        
        # Load rules once
        try:
            rules = load_rule_catalog("artefacts/rule_catalog.json")
        except (FileNotFoundError, ValueError) as e:
            raise RuntimeError(f"Rule catalog error: {e}") from e
        
        # Initialize progress tracking
        total_docs = len(file_paths)
        processed = 0
        errors = []
        all_results = []
        
        # Get resolved fields cache (application-level)
        resolved_fields = db.get_resolved_fields_for_application(app_ref)
        aoai_client.reset_call_count()
        
        # If this is a modification (V1+), run delta workflow after processing
        is_modification = parent_submission_id is not None
        
        # Process each document
        for idx, file_path in enumerate(file_paths):
            try:
                # Update progress
                db.update_run(run_id, metadata={
                    "progress": {
                        "current": idx + 1,
                        "total": total_docs,
                        "current_file": Path(file_path).name,
                        "status": "processing",
                        "is_modification": is_modification
                    }
                })
                
                # Ingest with parent_submission_id
                ingested = ingest_pdf(
                    file_path,
                    app_ref,
                    applicant_name=applicant_name,
                    storage_client=storage_client,
                    db=db,
                    parent_submission_id=parent_submission_id  # Pass parent for version linking
                )
                db.link_document_to_run(run_id, ingested["document_id"])
                
                # Extract
                pdf_bytes = Path(file_path).read_bytes()
                # Add context to ingested dict for persistence keys
                ingested_with_context = {**ingested, "context": {"run_id": run_id}}
                extraction = extract_from_pdf_bytes(
                    pdf_bytes,
                    ingested_with_context,
                    docintel=docintel,
                    storage_client=storage_client,
                    db=db,
                    write_to_tables=settings.enable_db_writes
                )
                
                # Save extraction to local outputs
                inputs_dir, outputs_dir = _ensure_run_dirs(run_id)
                extraction_file = outputs_dir / f"extraction_{ingested['document_id']}.json"
                with open(extraction_file, "w", encoding="utf-8") as f:
                    json.dump(extraction, f, indent=2, ensure_ascii=False)
                
                # Validate
                validation = validate_extraction(
                    extraction,
                    rules,
                    context={
                        "run_id": run_id,
                        "document_id": ingested["document_id"],
                        "submission_id": ingested.get("submission_id")
                    },
                    db=db,
                    write_to_tables=settings.enable_db_writes
                )
                
                # Save validation to local outputs
                validation_file = outputs_dir / f"validation_{ingested['document_id']}.json"
                with open(validation_file, "w", encoding="utf-8") as f:
                    json.dump(validation, f, indent=2, ensure_ascii=False)
                
                # LLM gate
                submission_id = ingested.get("submission_id")
                llm_notes = None
                
                try:
                    if settings.enable_llm_gate and should_trigger_llm(
                        validation,
                        extraction,
                        resolved_fields=resolved_fields,
                        application_ref=app_ref,
                        submission_id=submission_id,
                        db=db
                    ):
                        llm_notes = resolve_with_llm_new(
                            extraction,
                            validation,
                            aoai_client=aoai_client
                        )
                        
                        # Update resolved fields cache
                        if llm_notes.get("response", {}).get("filled_fields"):
                            filled = llm_notes["response"]["filled_fields"]
                            resolved_fields.update(filled)
                            # Update run metadata with resolved fields (for application-level cache)
                            session = db.get_session()
                            try:
                                run_obj = session.query(Run).filter(Run.id == run_id).first()
                                if run_obj:
                                    current_metadata = run_obj.run_metadata or {}
                                    current_metadata["resolved_fields"] = resolved_fields
                                    db.update_run(run_id, metadata=current_metadata)
                            finally:
                                session.close()
                        
                        # Save LLM notes to local outputs
                        llm_file = outputs_dir / f"llm_notes_{ingested['document_id']}.json"
                        with open(llm_file, "w", encoding="utf-8") as f:
                            json.dump(llm_notes, f, indent=2, ensure_ascii=False)
                except Exception as llm_error:
                    # LLM gate error shouldn't stop processing - log and continue
                    error_details = traceback.format_exc()
                    print(f"Warning: LLM gate error for doc {ingested['document_id']}: {llm_error}")
                    # Save error but don't fail the document
                    llm_error_file = outputs_dir / f"llm_gate_error_{ingested['document_id']}.txt"
                    with open(llm_error_file, "w", encoding="utf-8") as f:
                        f.write(f"LLM gate error (non-fatal):\n\n{error_details}")
                
                # Track result
                all_results.append({
                    "document_id": ingested["document_id"],
                    "filename": Path(file_path).name,
                    "validation_summary": validation.get("summary", {}),
                    "llm_triggered": llm_notes is not None,
                    "llm_call_count": llm_notes.get("llm_call_count", 0) if llm_notes else 0
                })
                
                processed += 1
                
            except Exception as e:
                error_details = traceback.format_exc()
                error_info = {
                    "filename": Path(file_path).name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": error_details,
                    "step": "unknown",  # Will be overridden if we know which step failed
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Try to determine which step failed
                if "ingest" in error_details.lower():
                    error_info["step"] = "ingestion"
                elif "extract" in error_details.lower() or "docintel" in error_details.lower():
                    error_info["step"] = "extraction"
                elif "validate" in error_details.lower():
                    error_info["step"] = "validation"
                elif "llm" in error_details.lower():
                    error_info["step"] = "llm_gate"
                
                errors.append(error_info)
                print(f"ERROR processing {Path(file_path).name} at step '{error_info['step']}': {str(e)}")
                
                # Save error to outputs
                inputs_dir, outputs_dir = _ensure_run_dirs(run_id)
                error_file = outputs_dir / f"error_{Path(file_path).name}.txt"
                with open(error_file, "w", encoding="utf-8") as f:
                    f.write(f"Error processing {Path(file_path).name}:\n")
                    f.write(f"Step: {error_info['step']}\n")
                    f.write(f"Error Type: {error_info['error_type']}\n")
                    f.write(f"Timestamp: {error_info['timestamp']}\n\n")
                    f.write(error_details)
        
        # Get total LLM calls
        llm_calls_per_run = aoai_client.get_call_count()
        
        # Update run with final status (ensure this always happens)
        final_status = "completed" if len(errors) == 0 else "completed_with_errors"
        
        # Create summary data
        summary_data = {
            "run_id": run_id,
            "application_ref": app_ref,
            "status": final_status,
            "summary": {
                "total_documents": total_docs,
                "processed": processed,
                "errors": len(errors)
            },
            "results": all_results,
            "errors": errors,
            "llm_calls_per_run": llm_calls_per_run,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Save summary to file for easy access
        inputs_dir, outputs_dir = _ensure_run_dirs(run_id)
        summary_file = outputs_dir / "summary.json"
        try:
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            print(f"Summary saved to {summary_file}")
        except Exception as summary_error:
            print(f"Warning: Failed to save summary file: {summary_error}")
        
        try:
            db.update_run(
                run_id,
                status=final_status,
                metadata=summary_data
            )
            print(f"Run {run_id} status updated to {final_status}")
        except Exception as update_error:
            # If update fails, try one more time with just status
            print(f"Warning: Failed to update run {run_id} with full metadata: {update_error}")
            error_traceback = traceback.format_exc()
            try:
                # Try minimal update without metadata
                db.update_run(run_id, status=final_status)
                print(f"Run {run_id} status updated (minimal update)")
            except Exception as retry_error:
                # Critical: Log the error but don't crash the thread
                print(f"CRITICAL: Failed to update run {run_id} status on retry: {retry_error}")
                print(f"Original error: {update_error}")
                print(f"Traceback:\n{error_traceback}")
                # Save error to file for debugging
                try:
                    inputs_dir, outputs_dir = _ensure_run_dirs(run_id)
                    error_file = outputs_dir / "critical_update_error.txt"
                    with open(error_file, "w", encoding="utf-8") as f:
                        f.write(f"Critical error updating run status:\n")
                        f.write(f"Run ID: {run_id}\n")
                        f.write(f"Original error: {update_error}\n")
                        f.write(f"Retry error: {retry_error}\n\n")
                        f.write(f"Traceback:\n{error_traceback}")
                except Exception as file_error:
                    print(f"Failed to save error file: {file_error}")
        
    except Exception as e:
        error_details = traceback.format_exc()
        db.update_run(
            run_id,
            status="failed",
            error_message=str(e),
            metadata={"traceback": error_details}
        )
        # Save error to outputs
        inputs_dir, outputs_dir = _ensure_run_dirs(run_id)
        error_file = outputs_dir / "run_error.txt"
        with open(error_file, "w", encoding="utf-8") as f:
            f.write(f"Run failed:\n\n{error_details}")


def get_run_status(run_id: int) -> Dict[str, Any]:
    """
    Get current status of a run.
    
    Returns:
        {
            "state": "running" | "completed" | "failed" | "completed_with_errors",
            "progress": {
                "current": int,
                "total": int,
                "current_file": str
            },
            "error": str | None,
            "traceback": str | None
        }
    """
    db = Database()
    session = db.get_session()
    
    try:
        run = session.query(Run).filter(Run.id == run_id).first()
        if not run:
            return {"state": "not_found", "error": f"Run {run_id} not found"}
        
        metadata = run.run_metadata or {}
        progress = metadata.get("progress", {})
        
        result = {
            "state": run.status,
            "progress": {
                "current": progress.get("current", 0),
                "total": progress.get("total", 1),
                "current_file": progress.get("current_file", "")
            }
        }
        
        if run.error_message:
            result["error"] = run.error_message
            result["traceback"] = metadata.get("traceback")
        
        return result
        
    except Exception as e:
        return {
            "state": "error",
            "error": str(e),
            "progress": {"current": 0, "total": 1, "current_file": ""}
        }
    finally:
        session.close()


def get_run_results(run_id: int) -> Dict[str, Any]:
    """
    Get structured results for a completed run.
    
    Returns:
        {
            "run_id": int,
            "application_ref": str,
            "summary": {
                "total_documents": int,
                "processed": int,
                "errors": int,
                "llm_calls_per_run": int
            },
            "results": [
                {
                    "document_id": int,
                    "filename": str,
                    "validation_summary": {...},
                    "llm_triggered": bool,
                    "llm_call_count": int
                }
            ],
            "errors": [...],
            "validation_findings": [
                {
                    "rule_id": str,
                    "rule_name": str,
                    "status": str,
                    "document_id": int,
                    "document_name": str,
                    "confidence": float,
                    "evidence": {...}
                }
            ]
        }
    """
    db = Database()
    session = db.get_session()
    
    try:
        run = session.query(Run).filter(Run.id == run_id).first()
        if not run:
            return {"error": f"Run {run_id} not found"}
        
        if run.status == "running":
            return {"error": "Run still in progress"}
        
        metadata = run.run_metadata or {}
        application_ref = metadata.get("application_ref", "")
        
        # Read results directly from output files (more reliable than metadata)
        outputs_dir = Path(f"./runs/{run_id}/outputs")
        inputs_dir = Path(f"./runs/{run_id}/inputs")
        
        # Find all validation and extraction files
        validation_files = sorted(outputs_dir.glob("validation_*.json"))
        extraction_files = sorted(outputs_dir.glob("extraction_*.json"))
        error_files = sorted(outputs_dir.glob("error_*.txt"))
        
        findings = []
        results = []
        errors = []
        
        # Process each document
        processed_doc_ids = set()
        
        for validation_file in validation_files:
            try:
                # Extract document ID from filename (validation_81.json -> 81)
                doc_id = int(validation_file.stem.split("_")[1])
                processed_doc_ids.add(doc_id)
                
                # Load validation
                with open(validation_file, "r", encoding="utf-8") as f:
                    validation = json.load(f)
                
                # Find corresponding extraction file
                extraction_file = outputs_dir / f"extraction_{doc_id}.json"
                extraction = {}
                if extraction_file.exists():
                    with open(extraction_file, "r", encoding="utf-8") as f:
                        extraction = json.load(f)
                
                # Get document info from database
                doc = session.query(Document).filter(Document.id == doc_id).first()
                filename = doc.filename if doc else f"document_{doc_id}"
                
                # Get document path (from inputs dir)
                document_path = str(inputs_dir / filename) if (inputs_dir / filename).exists() else None
                
                # Build validation findings
                for finding in validation.get("findings", []):
                    # Enhance evidence with document path
                    evidence = finding.get("evidence", {})
                    evidence_snippets = evidence.get("evidence_snippets", [])
                    
                    # Add document path to each evidence snippet
                    enhanced_evidence = []
                    for ev in evidence_snippets:
                        enhanced_ev = ev.copy()
                        enhanced_ev["document_id"] = doc_id
                        enhanced_ev["document_path"] = document_path
                        enhanced_ev["document_name"] = filename
                        enhanced_evidence.append(enhanced_ev)
                    
                    findings.append({
                        "rule_id": finding.get("rule_id", ""),
                        "rule_name": finding.get("rule_id", ""),  # Use rule_id as name for now
                        "status": finding.get("status", "unknown"),
                        "severity": finding.get("severity", "unknown"),
                        "document_id": doc_id,
                        "document_name": filename,
                        "document_path": document_path,
                        "message": finding.get("message", ""),
                        "missing_fields": finding.get("missing_fields", []),
                        "evidence": evidence,
                        "evidence_enhanced": enhanced_evidence
                    })
                
                # Build result summary
                results.append({
                    "document_id": doc_id,
                    "filename": filename,
                    "validation_summary": validation.get("summary", {}),
                    "llm_triggered": False,  # Check if LLM file exists
                    "llm_call_count": 0
                })
                
                # Check for LLM notes
                llm_file = outputs_dir / f"llm_notes_{doc_id}.json"
                if llm_file.exists():
                    with open(llm_file, "r", encoding="utf-8") as f:
                        llm_notes = json.load(f)
                    results[-1]["llm_triggered"] = True
                    results[-1]["llm_call_count"] = llm_notes.get("llm_call_count", 0)
                    
            except Exception as e:
                errors.append({
                    "filename": validation_file.name,
                    "error": f"Error reading {validation_file.name}: {str(e)}"
                })
        
        # Read error files
        for error_file in error_files:
            try:
                with open(error_file, "r", encoding="utf-8") as f:
                    error_content = f.read()
                errors.append({
                    "filename": error_file.name,
                    "error": error_content.split("\n")[0] if error_content else "Unknown error",
                    "traceback": error_content
                })
            except (IOError, OSError) as read_error:
                # Log but don't fail if we can't read an error file
                LOGGER.warning(f"Failed to read error file {error_file}: {read_error}")
                errors.append({
                    "filename": error_file.name,
                    "error": f"Failed to read error file: {str(read_error)}",
                    "traceback": None
                })
            except Exception as unexpected_error:
                # Catch any other unexpected errors
                LOGGER.error(f"Unexpected error reading error file {error_file}: {unexpected_error}")
                errors.append({
                    "filename": error_file.name,
                    "error": f"Unexpected error reading file: {str(unexpected_error)}",
                    "traceback": None
                })
        
        # Build summary
        total_docs = len(validation_files)
        processed = len(results)
        error_count = len(errors)
        
        # Get LLM calls from metadata or count LLM files
        llm_calls = metadata.get("llm_calls_per_run", 0)
        if llm_calls == 0:
            llm_files = list(outputs_dir.glob("llm_notes_*.json"))
            llm_calls = len(llm_files)
        
        summary = {
            "total_documents": total_docs,
            "processed": processed,
            "errors": error_count,
            "llm_calls_per_run": llm_calls
        }
        
        return {
            "run_id": run_id,
            "application_ref": application_ref,
            "summary": summary,
            "results": results,
            "errors": errors,
            "validation_findings": findings,
            "llm_calls_per_run": llm_calls
        }
        
    except Exception as e:
        return {"error": f"Error retrieving results: {str(e)}"}
    finally:
        session.close()
