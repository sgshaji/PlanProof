"""
PlanProof - Main entry point for the planning validation system.

This module provides a CLI interface for processing planning application documents.
It orchestrates the complete pipeline: ingestion → extraction → validation → LLM resolution.

Usage:
    python main.py single-pdf --pdf "document.pdf" --application-ref "APP/2024/001"
    python main.py batch-pdf --folder "documents/" --application-ref "APP/2024/001"
"""

from __future__ import annotations

import argparse
import json as jsonlib
import sys
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from planproof.config import get_settings
from planproof.db import Database
from planproof.storage import StorageClient
from planproof.docintel import DocumentIntelligence
from planproof.aoai import AzureOpenAIClient
from planproof.pipeline import ingest_pdf, extract_document, validate_document, resolve_with_llm
from planproof.pipeline.extract import extract_from_pdf_bytes
from planproof.pipeline.validate import load_rule_catalog, validate_extraction
from planproof.pipeline.llm_gate import should_trigger_llm, resolve_with_llm_new

LOGGER = logging.getLogger(__name__)


def _log_event(event: str, payload: Dict[str, Any]) -> None:
    settings = get_settings()
    if settings.log_json:
        LOGGER.info(jsonlib.dumps({"event": event, **payload}))
    else:
        LOGGER.info("%s %s", event, payload)


def single_pdf(pdf_path: str, application_ref: Optional[str] = None) -> Dict[str, Any]:
    """
    Run end-to-end pipeline for a single PDF document.
    
    Pipeline stages:
    1. Ingest: Upload PDF to blob storage and create database records
    2. Extract: Use Document Intelligence to extract text and layout
    3. Validate: Apply rule-based validation to extracted fields
    4. LLM Gate: Conditionally resolve missing fields using Azure OpenAI
    
    Args:
        pdf_path: Path to the PDF file to process
        application_ref: Application reference (auto-generated if not provided)
        
    Returns:
        Dictionary containing run_id, document_id, blob URLs, and validation summary
    """
    pdf_path = str(Path(pdf_path).resolve())
    
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    settings = get_settings()
    # Initialize clients
    db = Database()
    storage_client = StorageClient()
    docintel = DocumentIntelligence()
    aoai_client = AzureOpenAIClient()

    # 1) Create run + ingest
    # Use timestamp + hash for idempotency (same PDF = different run ID)
    import hashlib
    pdf_hash = hashlib.md5(Path(pdf_path).read_bytes()).hexdigest()[:8]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    app_ref = application_ref or f"AUTO-{timestamp}-{pdf_hash}"
    run = db.create_run(run_type="single_pdf", metadata={"pdf_path": pdf_path, "application_ref": app_ref, "pdf_hash": pdf_hash})
    ingest_start = time.perf_counter()
    ingested = ingest_pdf(pdf_path, app_ref, storage_client=storage_client, db=db)
    ingest_ms = int((time.perf_counter() - ingest_start) * 1000)
    db.link_document_to_run(run["id"], ingested["document_id"])
    _log_event("ingest_complete", {"run_id": run["id"], "document_id": ingested["document_id"], "duration_ms": ingest_ms})

    # 2) Extract
    # Hybrid storage: Write to both JSON artefact (blob) and relational tables (DB)
    pdf_bytes = Path(pdf_path).read_bytes()
    extract_start = time.perf_counter()
    extraction = extract_from_pdf_bytes(
        pdf_bytes,
        ingested,
        docintel=docintel,
        storage_client=storage_client,
        db=db,
        write_to_tables=settings.enable_db_writes
    )
    extract_ms = int((time.perf_counter() - extract_start) * 1000)
    _log_event(
        "extract_complete",
        {"run_id": run["id"], "document_id": ingested["document_id"], "duration_ms": extract_ms},
    )
    
    # Save extraction artefact to blob (complete JSON for audit trail)
    # Note: Relational tables (Page, Evidence, ExtractedField) already written above
    extraction_blob = f"runs/{run['id']}/extraction_{run['id']}.json"
    extraction_url = storage_client.write_json_blob("artefacts", extraction_blob, extraction, overwrite=True)

    extraction_art = db.create_artefact_record(
        document_id=ingested["document_id"],
        artefact_type="extraction",
        blob_uri=extraction_url,
        metadata={"run_id": run["id"], "blob_path": extraction_blob}
    )

    # 3) Validate using parsed rule catalog (fail fast if missing/empty)
    try:
        rules = load_rule_catalog("artefacts/rule_catalog.json")
    except (FileNotFoundError, ValueError) as e:
        raise RuntimeError(f"Rule catalog error: {e}") from e
    # Hybrid storage: Write to both JSON artefact (blob) and relational tables (DB)
    validate_start = time.perf_counter()
    validation = validate_extraction(
        extraction, 
        rules, 
        context={"run_id": run["id"], "document_id": ingested["document_id"], "submission_id": ingested.get("submission_id")},
        db=db,
        write_to_tables=settings.enable_db_writes
    )
    validate_ms = int((time.perf_counter() - validate_start) * 1000)
    _log_event(
        "validate_complete",
        {"run_id": run["id"], "document_id": ingested["document_id"], "duration_ms": validate_ms},
    )

    # Save validation artefact to blob (complete JSON for audit trail)
    # Note: Relational tables (ValidationCheck) already written above
    validation_blob = f"runs/{run['id']}/validation_{run['id']}.json"
    validation_url = storage_client.write_json_blob("artefacts", validation_blob, validation, overwrite=True)

    validation_art = db.create_artefact_record(
        document_id=ingested["document_id"],
        artefact_type="validation",
        blob_uri=validation_url,
        metadata={"run_id": run["id"], "blob_path": validation_blob}
    )

    # 4) Gated LLM resolve (only if needed)
    # Get submission_id from ingested document
    submission_id = ingested.get("submission_id")
    
    # Check resolved fields from submission metadata and application-level cache
    resolved_fields = {}
    if submission_id:
        resolved_fields = db.get_resolved_fields_for_submission(submission_id)
    
    # Load application-level resolved fields cache (fallback/aggregate)
    app_resolved = db.get_resolved_fields_for_application(app_ref)
    resolved_fields = {**app_resolved, **resolved_fields}  # Merge, current submission takes precedence
    
    # Reset LLM call counter for this run
    aoai_client.reset_call_count()
    
    llm_notes = None
    llm_art = None
    llm_start = time.perf_counter()
    llm_ms = None
    if settings.enable_llm_gate and should_trigger_llm(
        validation,
        extraction,
        resolved_fields=resolved_fields,
        application_ref=app_ref,
        submission_id=submission_id,
        db=db,
    ):
        print(f"LLM gate triggered for run {run['id']}")
        llm_notes = resolve_with_llm_new(extraction, validation, aoai_client=aoai_client)
        if llm_notes.get("gate_reason"):
            reason = llm_notes["gate_reason"]
            print(f"  Missing fields: {reason.get('missing_fields', [])}")
            print(f"  Affected rules: {reason.get('affected_rule_ids', [])}")
        
        # Store resolved fields in submission metadata (preferred) and run metadata (backward compat)
        if llm_notes.get("response", {}).get("filled_fields"):
            filled = llm_notes["response"]["filled_fields"]
            resolved_fields.update(filled)
            if submission_id:
                db.update_submission_metadata(submission_id, {"resolved_fields": resolved_fields})
            # Also update run metadata for backward compatibility
            db.update_run(run["id"], metadata={"resolved_fields": resolved_fields})
        
        llm_blob = f"runs/{run['id']}/llm_notes_{run['id']}.json"
        llm_url = storage_client.write_json_blob("artefacts", llm_blob, llm_notes, overwrite=True)
        llm_art = db.create_artefact_record(
            document_id=ingested["document_id"],
            artefact_type="llm_notes",
            blob_uri=llm_url,
            metadata={"run_id": run["id"], "blob_path": llm_blob}
        )
    if settings.enable_llm_gate:
        llm_ms = int((time.perf_counter() - llm_start) * 1000)
        _log_event(
            "llm_gate_complete",
            {"run_id": run["id"], "document_id": ingested["document_id"], "duration_ms": llm_ms},
        )
    
    # Get total LLM calls for this run
    llm_calls_per_run = aoai_client.get_call_count()
    
    # Update submission metadata with LLM call count (preferred) and run metadata (backward compat)
    if submission_id:
        db.update_submission_metadata(submission_id, {"llm_calls_per_submission": llm_calls_per_run})
    db.update_run(run["id"], metadata={"llm_calls_per_run": llm_calls_per_run})
    
    # Log headline metric
    print(f"📊 LLM Calls Per Run: {llm_calls_per_run} (headline metric)")

    run_metrics = {
        "timings_ms": {
            "ingest": ingest_ms,
            "extract": extract_ms,
            "validate": validate_ms,
            "llm_gate": llm_ms if settings.enable_llm_gate else None,
            "docintel": extraction.get("metadata", {}).get("docintel_ms"),
        },
        "llm_calls_per_run": llm_calls_per_run,
    }
    db.update_run(run["id"], metadata=run_metrics)

    return {
        "run_id": run["id"],
        "document_id": ingested["document_id"],
        "blob_urls": {
            "extraction": extraction_url,
            "validation": validation_url,
            "llm_notes": (llm_art["blob_uri"] if llm_art else None),
        },
        "artefact_ids": {
            "extraction": extraction_art["id"],
            "validation": validation_art["id"],
            "llm_notes": (llm_art["id"] if llm_art else None),
        },
        "summary": validation.get("summary", {}),
        "llm_triggered": llm_notes is not None,
        "llm_calls_per_run": llm_calls_per_run,
    }


def main():
    """
    Main CLI entry point.
    
    Supports the following commands:
    - single-pdf: Process a single PDF document
    - batch-pdf: Process all PDFs in a folder
    - ingest: Ingest a PDF (legacy)
    - extract: Extract document (legacy)
    - validate: Validate document (legacy)
    - resolve: Resolve with LLM (legacy)
    """
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    ap = argparse.ArgumentParser(description="PlanProof - Planning Validation System MVP")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # Single PDF end-to-end command
    sp = sub.add_parser("single-pdf", help="Run ingest → extract → validate → (optional) llm on one local PDF")
    sp.add_argument("--pdf", required=True, help="Path to local PDF")
    sp.add_argument("--application-ref", help="Application reference (default: auto-generated)")
    sp.add_argument("--out", default="", help="Optional: write run summary JSON to a local file")

    # Batch process folder command
    batch_parser = sub.add_parser("batch-pdf", help="Process all PDFs in a folder for one application")
    batch_parser.add_argument("--folder", required=True, help="Path to folder containing PDFs")
    batch_parser.add_argument("--application-ref", required=True, help="Application reference for all PDFs")
    batch_parser.add_argument("--applicant-name", help="Applicant name (optional)")
    batch_parser.add_argument("--workers", type=int, default=4, help="Parallel worker count (default: 4)")
    batch_parser.add_argument("--page-parallelism", type=int, default=1, help="DocIntel page parallelism per PDF")
    batch_parser.add_argument("--pages-per-batch", type=int, default=5, help="Pages per DocIntel batch")
    batch_parser.add_argument("--out", default="", help="Optional: write results JSON to a local file")

    # Legacy commands
    ingest_parser = sub.add_parser("ingest", help="Ingest a PDF file")
    ingest_parser.add_argument("pdf_path", help="Path to PDF file")
    ingest_parser.add_argument("application_ref", help="Application reference")
    ingest_parser.add_argument("applicant_name", nargs="?", help="Applicant name (optional)")

    extract_parser = sub.add_parser("extract", help="Extract document")
    extract_parser.add_argument("document_id", type=int, help="Document ID")

    validate_parser = sub.add_parser("validate", help="Validate document")
    validate_parser.add_argument("document_id", type=int, help="Document ID")

    resolve_parser = sub.add_parser("resolve", help="Resolve with LLM")
    resolve_parser.add_argument("document_id", type=int, help="Document ID")
    resolve_parser.add_argument("field_name", nargs="?", help="Field name (optional)")

    args = ap.parse_args()

    try:
        if args.cmd == "single-pdf":
            result = single_pdf(args.pdf, application_ref=getattr(args, 'application_ref', None))
            print(jsonlib.dumps(result, indent=2))
            if args.out:
                Path(args.out).write_text(jsonlib.dumps(result, indent=2), encoding="utf-8")

        elif args.cmd == "batch-pdf":
            from planproof.pipeline.ingest import ingest_folder
            
            folder_path = args.folder
            application_ref = args.application_ref
            settings = get_settings()
            
            # Initialize clients
            db = Database()
            storage_client = StorageClient()
            
            # CREATE RUN FIRST (before any processing)
            run = db.create_run(
                run_type="batch_pdf",
                metadata={
                    "folder_path": folder_path,
                    "application_ref": application_ref,
                    "started_at": datetime.now(timezone.utc).isoformat()
                }
            )
            print(f"Created run {run['id']} for batch processing")
            
            # Ingest all PDFs in folder
            print(f"Ingesting PDFs from {folder_path}...")
            ingest_start = time.perf_counter()
            ingested_results = ingest_folder(
                folder_path, 
                application_ref, 
                applicant_name=getattr(args, 'applicant_name', None),
                storage_client=storage_client,
                db=db,
                max_workers=args.workers
            )
            ingest_ms = int((time.perf_counter() - ingest_start) * 1000)
            _log_event(
                "batch_ingest_complete",
                {"run_id": run["id"], "document_count": len(ingested_results), "duration_ms": ingest_ms},
            )
            
            print(f"OK: Ingested {len(ingested_results)} PDF(s)")
            
            all_results = []
            successes = 0
            failures = 0
            errors = []
            run_metadata = run.get("metadata", {}) or {}
            resolved_fields = db.get_resolved_fields_for_application(application_ref)
            resolved_fields.update(run_metadata.get("resolved_fields", {}))

            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading
            lock = threading.Lock()
            
            try:
                rules = load_rule_catalog("artefacts/rule_catalog.json")
            except (FileNotFoundError, ValueError) as e:
                error_msg = f"Rule catalog error: {e}"
                print(f"ERROR: {error_msg}")
                db.update_run(run["id"], status="failed", error_message=error_msg)
                sys.exit(1)
            
            def _process_document(ingested: dict) -> dict:
                if "error" in ingested:
                    return {
                        "document_id": ingested.get("document_id"),
                        "filename": ingested.get("filename", "unknown"),
                        "error": ingested["error"]
                    }

                doc_id = ingested["document_id"]
                print(f"Processing document {doc_id} ({ingested['filename']})...")

                try:
                    local_docintel = DocumentIntelligence()
                    local_storage = StorageClient()
                    local_aoai = AzureOpenAIClient()

                    extract_start = time.perf_counter()
                    extraction_result = extract_document(
                        doc_id,
                        docintel=local_docintel,
                        storage_client=local_storage,
                        db=db,
                        use_url=settings.docintel_use_url,
                        page_parallelism=settings.docintel_page_parallelism,
                        pages_per_batch=settings.docintel_pages_per_batch
                    )
                    extraction_raw = extraction_result["extraction_result"]
                    extract_ms = int((time.perf_counter() - extract_start) * 1000)

                    from planproof.pipeline.field_mapper import map_fields
                    mapped = map_fields(extraction_raw)
                    fields = mapped["fields"]
                    field_evidence = mapped["evidence_index"]

                    evidence_index = {}
                    for i, block in enumerate(extraction_raw.get("text_blocks", [])):
                        block["index"] = i

                    for i, block in enumerate(extraction_raw.get("text_blocks", [])):
                        content = block.get("content", "")
                        page_num = block.get("page_number")
                        snippet = content[:100] + "..." if len(content) > 100 else content
                        evidence_index[f"text_block_{i}"] = {
                            "type": "text_block",
                            "content": content,
                            "snippet": snippet,
                            "page_number": page_num
                        }

                    for i, table in enumerate(extraction_raw.get("tables", [])):
                        page_num = table.get("page_number")
                        cells = table.get("cells", [])
                        cell_snippets = []
                        for cell in cells[:5]:
                            if cell.get("content"):
                                cell_snippets.append(cell["content"][:50])
                        snippet = " | ".join(cell_snippets) if cell_snippets else ""
                        evidence_index[f"table_{i}"] = {
                            "type": "table",
                            "row_count": table.get("row_count"),
                            "column_count": table.get("column_count"),
                            "page_number": page_num,
                            "snippet": snippet
                        }

                    for field_name, ev_list in field_evidence.items():
                        evidence_index[field_name] = ev_list

                    extraction_structured = {
                        "fields": fields,
                        "evidence_index": evidence_index,
                        "metadata": extraction_raw.get("metadata", {}),
                        "text_blocks": extraction_raw.get("text_blocks", []),
                        "tables": extraction_raw.get("tables", []),
                        "page_anchors": extraction_raw.get("page_anchors", {})
                    }

                    validate_start = time.perf_counter()
                    validation = validate_extraction(
                        extraction_structured,
                        rules,
                        context={"document_id": doc_id, "submission_id": ingested.get("submission_id")},
                        db=db,
                        write_to_tables=settings.enable_db_writes
                    )
                    validate_ms = int((time.perf_counter() - validate_start) * 1000)

                    with lock:
                        current_resolved = resolved_fields.copy()

                    llm_notes = None
                    llm_start = time.perf_counter()
                    if settings.enable_llm_gate and should_trigger_llm(
                        validation,
                        extraction_structured,
                        resolved_fields=current_resolved,
                        application_ref=application_ref,
                        db=db
                    ):
                        print(f"  LLM gate triggered for document {doc_id}")
                        llm_notes = resolve_with_llm_new(extraction_structured, validation, aoai_client=local_aoai)
                        if llm_notes.get("gate_reason"):
                            reason = llm_notes["gate_reason"]
                            print(f"    Missing fields: {reason.get('missing_fields', [])}")
                            print(f"    Affected rules: {reason.get('affected_rule_ids', [])}")

                        if llm_notes.get("response", {}).get("filled_fields"):
                            filled = llm_notes["response"]["filled_fields"]
                            with lock:
                                resolved_fields.update(filled)
                                run_metadata["resolved_fields"] = resolved_fields
                                db.update_run(run["id"], metadata=run_metadata)
                                run["metadata"] = run_metadata

                    llm_ms = int((time.perf_counter() - llm_start) * 1000) if settings.enable_llm_gate else None
                    _log_event(
                        "batch_document_complete",
                        {
                            "run_id": run["id"],
                            "document_id": doc_id,
                            "duration_ms": extract_ms + validate_ms,
                            "extract_ms": extract_ms,
                            "validate_ms": validate_ms,
                            "llm_ms": llm_ms,
                            "docintel_ms": extraction_raw.get("metadata", {}).get("docintel_ms"),
                        },
                    )

                    return {
                        "document_id": doc_id,
                        "filename": ingested["filename"],
                        "validation_summary": validation.get("summary", {}),
                        "llm_triggered": llm_notes is not None,
                        "llm_call_count": local_aoai.get_call_count(),
                        "timings_ms": {
                            "extract": extract_ms,
                            "validate": validate_ms,
                            "llm_gate": llm_ms,
                        },
                    }
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    print(f"  ERROR: Error processing document {doc_id}: {e}")
                    print(f"  Traceback: {error_details.split(chr(10))[-3] if error_details else 'N/A'}")
                    return {
                        "document_id": doc_id,
                        "filename": ingested.get("filename", "unknown"),
                        "error": str(e)
                    }

            worker_count = max(1, min(args.workers, len(ingested_results)))
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = [executor.submit(_process_document, ingested) for ingested in ingested_results]
                for future in as_completed(futures):
                    result = future.result()
                    all_results.append(result)
                    if "error" in result:
                        failures += 1
                        errors.append({
                            "document_id": result.get("document_id"),
                            "filename": result.get("filename", "unknown"),
                            "error": result["error"]
                        })
                    else:
                        successes += 1
                        print(f"  OK: Completed document {result.get('document_id')}")
            
            # Get total LLM calls for this run
            llm_calls_per_run = sum(r.get("llm_call_count", 0) for r in all_results)
            
            # Update submission metadata with LLM call count (if we have a submission)
            # For batch processing, all documents should be in the same submission (V0)
            if ingested_results and ingested_results[0].get("submission_id"):
                submission_id = ingested_results[0]["submission_id"]
                db.update_submission_metadata(submission_id, {"llm_calls_per_submission": llm_calls_per_run})
            
            # Update run with final status and LLM call count
            final_status = "completed" if failures == 0 else "completed_with_errors"
            db.update_run(
                run["id"],
                status=final_status,
                metadata={
                    "summary": {
                        "total_documents": len(ingested_results),
                        "successes": successes,
                        "failures": failures
                    },
                    "errors": errors,
                    "llm_calls_per_run": llm_calls_per_run,
                    "timings_ms": {
                        "ingest": ingest_ms,
                    },
                }
            )
            
            # Count documents that triggered LLM
            llm_triggered_count = sum(1 for r in all_results if r.get("llm_triggered", False))
            
            summary = {
                "run_id": run["id"],
                "application_ref": application_ref,
                "total_documents": len(ingested_results),
                "successes": successes,
                "failures": failures,
                "llm_triggered_documents": llm_triggered_count,
                "llm_calls_per_run": llm_calls_per_run,
                "results": all_results
            }
            
            # Log headline metric
            print(f"\n📊 LLM Calls Per Run: {llm_calls_per_run} (headline metric)")
            
            print(jsonlib.dumps(summary, indent=2))
            if args.out:
                Path(args.out).write_text(jsonlib.dumps(summary, indent=2), encoding="utf-8")

        elif args.cmd == "ingest":
            result = ingest_pdf(args.pdf_path, args.application_ref, applicant_name=args.applicant_name)
            print(f"✓ Ingested: {result['filename']}")
            print(f"  Application ID: {result['application_id']}")
            print(f"  Document ID: {result['document_id']}")
            print(f"  Blob URI: {result['blob_uri']}")

        elif args.cmd == "extract":
            result = extract_document(args.document_id)
            print(f"✓ Extracted document {args.document_id}")
            print(f"  Artefact ID: {result['artefact_id']}")
            print(f"  Artefact URI: {result['artefact_blob_uri']}")
            print(f"  Page count: {result['extraction_result']['metadata']['page_count']}")

        elif args.cmd == "validate":
            results = validate_document(args.document_id)
            print(f"✓ Validated document {args.document_id}")
            for r in results:
                status_icon = "✓" if r["status"] == "pass" else "✗"
                print(f"  {status_icon} {r['field_name']}: {r['status']} (confidence: {r.get('confidence', 'N/A')})")

        elif args.cmd == "resolve":
            results = resolve_with_llm(args.document_id, field_name=args.field_name)
            print(f"✓ Resolved with LLM for document {args.document_id}")
            for r in results:
                print(f"  {r['field_name']}: {r['status']} (confidence: {r.get('confidence', 'N/A')})")
                if r.get("reasoning"):
                    print(f"    Reasoning: {r['reasoning'][:100]}...")

    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
