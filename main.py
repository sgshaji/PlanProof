"""
PlanProof - Main entry point for the planning validation system.
"""

from __future__ import annotations

import argparse
import json as jsonlib
import sys
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


def single_pdf(pdf_path: str, application_ref: Optional[str] = None) -> Dict[str, Any]:
    """Run end-to-end pipeline: ingest → extract → validate → (optional) llm."""
    pdf_path = str(Path(pdf_path).resolve())
    
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

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
    ingested = ingest_pdf(pdf_path, app_ref, storage_client=storage_client, db=db)
    db.link_document_to_run(run["id"], ingested["document_id"])

    # 2) Extract
    pdf_bytes = Path(pdf_path).read_bytes()
    extraction = extract_from_pdf_bytes(pdf_bytes, ingested, docintel=docintel)
    
    # Save extraction artefact to blob (with unique path for idempotency)
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
    validation = validate_extraction(extraction, rules, context={"run_id": run["id"]})

    validation_blob = f"runs/{run['id']}/validation_{run['id']}.json"
    validation_url = storage_client.write_json_blob("artefacts", validation_blob, validation, overwrite=True)

    validation_art = db.create_artefact_record(
        document_id=ingested["document_id"],
        artefact_type="validation",
        blob_uri=validation_url,
        metadata={"run_id": run["id"], "blob_path": validation_blob}
    )

    # 4) Gated LLM resolve (only if needed)
    # Check resolved fields from run metadata
    run_metadata = run.get("metadata", {}) or {}
    resolved_fields = run_metadata.get("resolved_fields", {})
    
    llm_notes = None
    llm_art = None
    if should_trigger_llm(validation, extraction, resolved_fields=resolved_fields):
        print(f"LLM gate triggered for run {run['id']}")
        llm_notes = resolve_with_llm_new(extraction, validation, aoai_client=aoai_client)
        if llm_notes.get("gate_reason"):
            reason = llm_notes["gate_reason"]
            print(f"  Missing fields: {reason.get('missing_fields', [])}")
            print(f"  Affected rules: {reason.get('affected_rule_ids', [])}")
        
        # Store resolved fields in run metadata
        if llm_notes.get("response", {}).get("filled_fields"):
            filled = llm_notes["response"]["filled_fields"]
            resolved_fields.update(filled)
            db.update_run(run["id"], metadata={"resolved_fields": resolved_fields})
        
        llm_blob = f"runs/{run['id']}/llm_notes_{run['id']}.json"
        llm_url = storage_client.write_json_blob("artefacts", llm_blob, llm_notes, overwrite=True)
        llm_art = db.create_artefact_record(
            document_id=ingested["document_id"],
            artefact_type="llm_notes",
            blob_uri=llm_url,
            metadata={"run_id": run["id"], "blob_path": llm_blob}
        )

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
    }


def main():
    """Main entry point."""
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
            
            # Initialize clients
            db = Database()
            storage_client = StorageClient()
            docintel = DocumentIntelligence()
            aoai_client = AzureOpenAIClient()
            
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
            ingested_results = ingest_folder(
                folder_path, 
                application_ref, 
                applicant_name=getattr(args, 'applicant_name', None),
                storage_client=storage_client,
                db=db
            )
            
            print(f"OK: Ingested {len(ingested_results)} PDF(s)")
            
            # Process each document
            all_results = []
            successes = 0
            failures = 0
            errors = []
            
            try:
                rules = load_rule_catalog("artefacts/rule_catalog.json")
            except (FileNotFoundError, ValueError) as e:
                error_msg = f"Rule catalog error: {e}"
                print(f"ERROR: {error_msg}")
                db.update_run(run["id"], status="failed", error_message=error_msg)
                sys.exit(1)
            
            for ingested in ingested_results:
                if "error" in ingested:
                    print(f"ERROR: Skipping {ingested.get('filename', 'unknown')}: {ingested['error']}")
                    continue
                
                doc_id = ingested["document_id"]
                print(f"Processing document {doc_id} ({ingested['filename']})...")
                
                try:
                    # Extract using extract_document (gets from DB or creates new)
                    extraction_result = extract_document(doc_id, docintel=docintel, storage_client=storage_client, db=db)
                    extraction_raw = extraction_result["extraction_result"]
                    
                    # Apply field mapper to extract structured fields
                    from planproof.pipeline.field_mapper import map_fields
                    mapped = map_fields(extraction_raw)
                    fields = mapped["fields"]
                    field_evidence = mapped["evidence_index"]
                    
                    # Build general evidence_index for text blocks and tables
                    evidence_index = {}
                    
                    # Add index to blocks for field mapper reference
                    for i, block in enumerate(extraction_raw.get("text_blocks", [])):
                        block["index"] = i
                    
                    # Extract text blocks as evidence with snippets
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
                    
                    # Extract tables as evidence with snippets
                    for i, table in enumerate(extraction_raw.get("tables", [])):
                        page_num = table.get("page_number")
                        cells = table.get("cells", [])
                        cell_snippets = []
                        for cell in cells[:5]:  # First 5 cells
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
                    
                    # Merge field-specific evidence into general evidence_index
                    for field_name, ev_list in field_evidence.items():
                        evidence_index[field_name] = ev_list
                    
                    # Build structured extraction with mapped fields
                    extraction_structured = {
                        "fields": fields,
                        "evidence_index": evidence_index,
                        "metadata": extraction_raw.get("metadata", {}),
                        "text_blocks": extraction_raw.get("text_blocks", []),
                        "tables": extraction_raw.get("tables", []),
                        "page_anchors": extraction_raw.get("page_anchors", {})
                    }
                    
                    # Validate
                    validation = validate_extraction(extraction_structured, rules, context={"document_id": doc_id})
                    
                    # LLM gate if needed (check resolved fields from run)
                    run_metadata = run.get("metadata", {}) or {}
                    resolved_fields = run_metadata.get("resolved_fields", {})
                    
                    llm_notes = None
                    if should_trigger_llm(validation, extraction_structured, resolved_fields=resolved_fields):
                        print(f"  LLM gate triggered for document {doc_id}")
                        llm_notes = resolve_with_llm_new(extraction_structured, validation, aoai_client=aoai_client)
                        if llm_notes.get("gate_reason"):
                            reason = llm_notes["gate_reason"]
                            print(f"    Missing fields: {reason.get('missing_fields', [])}")
                            print(f"    Affected rules: {reason.get('affected_rule_ids', [])}")
                        
                        # Update resolved fields in run metadata
                        if llm_notes.get("response", {}).get("filled_fields"):
                            filled = llm_notes["response"]["filled_fields"]
                            resolved_fields.update(filled)
                            # Update run metadata
                            existing_metadata = run_metadata.copy()
                            existing_metadata["resolved_fields"] = resolved_fields
                            db.update_run(run["id"], metadata=existing_metadata)
                            run["metadata"] = existing_metadata  # Update local copy
                    
                    all_results.append({
                        "document_id": doc_id,
                        "filename": ingested["filename"],
                        "validation_summary": validation.get("summary", {}),
                        "llm_triggered": llm_notes is not None
                    })
                    successes += 1
                    print(f"  OK: Completed document {doc_id}")
                    
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    failures += 1
                    error_msg = str(e)
                    errors.append({
                        "document_id": doc_id,
                        "filename": ingested.get("filename", "unknown"),
                        "error": error_msg
                    })
                    print(f"  ERROR: Error processing document {doc_id}: {e}")
                    print(f"  Traceback: {error_details.split(chr(10))[-3] if error_details else 'N/A'}")
                    all_results.append({
                        "document_id": doc_id,
                        "filename": ingested.get("filename", "unknown"),
                        "error": error_msg
                    })
            
            # Update run with final status
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
                    "errors": errors
                }
            )
            
            # Count LLM calls
            llm_calls = sum(1 for r in all_results if r.get("llm_triggered", False))
            
            summary = {
                "run_id": run["id"],
                "application_ref": application_ref,
                "total_documents": len(ingested_results),
                "successes": successes,
                "failures": failures,
                "llm_calls": llm_calls,
                "llm_calls_per_run": llm_calls,
                "results": all_results
            }
            
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

