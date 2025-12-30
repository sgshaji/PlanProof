"""
Extract module: Use Document Intelligence to extract structured data from documents.
"""

from __future__ import annotations

import json as jsonlib
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

from planproof.docintel import DocumentIntelligence

_EXTRACTION_CACHE: Dict[str, Dict[str, Any]] = {}

if TYPE_CHECKING:
    from planproof.storage import StorageClient
    from planproof.db import Database, Document, Artefact


def extract_document(
    document_id: int,
    model: str = "auto",
    docintel: Optional[DocumentIntelligence] = None,
    storage_client: Optional[StorageClient] = None,
    db: Optional[Database] = None,
    use_url: bool = True,
    page_parallelism: int = 1,
    pages_per_batch: int = 5
) -> Dict[str, Any]:
    """
    Extract structured data from a document using Document Intelligence.

    Args:
        document_id: Document ID from database
        model: Document Intelligence model to use (default: "prebuilt-layout")
        docintel: Optional DocumentIntelligence instance
        storage_client: Optional StorageClient instance
        db: Optional Database instance

    Returns:
        Dictionary with:
        - artefact_id: Created artefact ID
        - artefact_blob_uri: Blob URI of stored JSON artefact
        - extraction_result: The extraction result dictionary
    """
    from planproof.db import Document, Artefact
    from planproof.storage import StorageClient

    # Initialize clients if not provided
    if docintel is None:
        docintel = DocumentIntelligence()
    if storage_client is None:
        storage_client = StorageClient()
    if db is None:
        db = Database()

    # Get document from database
    session = db.get_session()
    try:
        document = session.query(Document).filter(Document.id == document_id).first()
        if document is None:
            raise ValueError(f"Document not found: {document_id}")

        # Extract blob URI components
        # Format: azure://{account}/{container}/{blob_name}
        blob_uri_parts = document.blob_uri.replace("azure://", "").split("/", 2)
        if len(blob_uri_parts) != 3:
            raise ValueError(f"Invalid blob URI format: {document.blob_uri}")

        container = blob_uri_parts[1]
        blob_name = blob_uri_parts[2]

        if model == "auto":
            model = docintel.select_model(document.document_type, default="prebuilt-layout")

        extraction_result = None
        if page_parallelism > 1:
            pdf_bytes = storage_client.download_blob(container, blob_name)
            extraction_result = docintel.analyze_document_parallel(
                pdf_bytes,
                model=model,
                pages_per_batch=pages_per_batch,
                max_workers=page_parallelism
            )
        elif use_url:
            try:
                document_url = storage_client.get_blob_sas_url(container, blob_name)
                extraction_result = docintel.analyze_document_url(document_url, model=model)
            except Exception:
                extraction_result = None

        if extraction_result is None:
            pdf_bytes = storage_client.download_blob(container, blob_name)
            extraction_result = docintel.analyze_document(pdf_bytes, model=model)

        # Update document metadata
        document.page_count = extraction_result["metadata"]["page_count"]
        document.docintel_model = model
        document.processed_at = datetime.utcnow()
        if not document.document_type:
            from planproof.pipeline.field_mapper import classify_document
            document.document_type = classify_document(extraction_result.get("text_blocks", []))

        # Store extraction result as JSON artefact
        # Ensure the result is fully serializable (deep copy to remove any object references)
        import copy as copy_module
        extraction_result_clean = copy_module.deepcopy(extraction_result)
        artefact_name = f"extracted_layout_{document_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        artefact_blob_uri = storage_client.write_artefact(extraction_result_clean, artefact_name)

        # Create artefact record
        artefact = Artefact(
            document_id=document_id,
            artefact_type="extracted_layout",
            blob_uri=artefact_blob_uri,
            artefact_metadata={
                "model": model,
                "extracted_at": datetime.utcnow().isoformat()
            }
        )
        session.add(artefact)
        session.commit()
        session.refresh(artefact)

        return {
            "artefact_id": artefact.id,
            "artefact_blob_uri": artefact_blob_uri,
            "extraction_result": extraction_result
        }

    finally:
        session.close()


def get_extraction_result(
    document_id: int,
    storage_client: Optional[StorageClient] = None,
    db: Optional[Database] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieve the most recent extraction result for a document.

    Args:
        document_id: Document ID
        storage_client: Optional StorageClient instance
        db: Optional Database instance

    Returns:
        Extraction result dictionary or None if not found
    """
    from planproof.db import Artefact
    from planproof.storage import StorageClient

    if storage_client is None:
        storage_client = StorageClient()
    if db is None:
        db = Database()

    session = db.get_session()
    try:
        # Get most recent extracted_layout artefact
        artefact = (
            session.query(Artefact)
            .filter(
                Artefact.document_id == document_id,
                Artefact.artefact_type == "extracted_layout"
            )
            .order_by(Artefact.created_at.desc())
            .first()
        )

        if artefact is None:
            return None

        # Extract blob URI components and download
        blob_uri_parts = artefact.blob_uri.replace("azure://", "").split("/", 2)
        if len(blob_uri_parts) != 3:
            return None

        container = blob_uri_parts[1]
        blob_name = blob_uri_parts[2]

        cache_key = artefact.blob_uri
        if cache_key in _EXTRACTION_CACHE:
            return _EXTRACTION_CACHE[cache_key]

        artefact_bytes = storage_client.download_blob(container, blob_name)
        result = jsonlib.loads(artefact_bytes.decode("utf-8"))
        _EXTRACTION_CACHE[cache_key] = result
        return result

    finally:
        session.close()


def extract_from_pdf_bytes(
    pdf_bytes: bytes,
    document_meta: Dict[str, Any],
    model: str = "prebuilt-layout",
    docintel: Optional[DocumentIntelligence] = None,
    storage_client: Optional[StorageClient] = None,
    db: Optional[Database] = None,
    write_to_tables: bool = True
) -> Dict[str, Any]:
    """
    Extract structured data from PDF bytes (for use in end-to-end pipeline).
    
    **Hybrid Storage Strategy:**
    - Returns dict format (for JSON artefact storage in blob)
    - Optionally writes to relational tables (Page, Evidence, ExtractedField)
    - Both storage methods are maintained going forward

    Args:
        pdf_bytes: PDF file content as bytes
        document_meta: Dictionary with document metadata (e.g., from ingest)
        model: Document Intelligence model to use
        docintel: Optional DocumentIntelligence instance
        db: Optional Database instance for writing to relational tables
        write_to_tables: If True, write to relational tables (Page, Evidence, ExtractedField)
                        Note: JSON artefact is always created separately in main pipeline

    Returns:
        Extraction result dictionary with fields and evidence_index (for JSON artefact)
    """
    if docintel is None:
        docintel = DocumentIntelligence()
    if storage_client is None:
        from planproof.storage import StorageClient
        storage_client = StorageClient()
    
    # Check if document was already extracted (caching to avoid redundant API calls)
    document_id = document_meta.get("document_id")
    existing_extraction = None
    if document_id and db:
        # Check for existing extraction artefact
        session = db.get_session()
        try:
            from planproof.db import Artefact
            artefact = (
                session.query(Artefact)
                .filter(
                    Artefact.document_id == document_id,
                    Artefact.artefact_type == "extracted_layout"
                )
                .order_by(Artefact.created_at.desc())
                .first()
            )
            if artefact:
                # Download cached extraction result from blob storage
                # This avoids expensive Document Intelligence API call (saves 5-30 seconds!)
                try:
                    blob_uri_parts = artefact.blob_uri.replace("azure://", "").split("/", 2)
                    if len(blob_uri_parts) == 3:
                        container = blob_uri_parts[1]
                        blob_name = blob_uri_parts[2]
                        artefact_bytes = storage_client.download_blob(container, blob_name)
                        existing_extraction = jsonlib.loads(artefact_bytes.decode("utf-8"))
                except Exception as e:
                    # If caching fails (e.g., blob not accessible), fall back to fresh extraction
                    # This ensures pipeline doesn't break if blob access fails
                    pass
        finally:
            session.close()
    
    if existing_extraction:
        # Use cached extraction result - skip expensive API call
        extraction_result = existing_extraction
    else:
        # Analyze document with Document Intelligence (new extraction)
        extraction_result = docintel.analyze_document(pdf_bytes, model=model)

    # Use field mapper to extract structured fields
    from planproof.pipeline.field_mapper import map_fields
    
    mapped = map_fields(extraction_result)
    fields = mapped["fields"]
    field_evidence = mapped["evidence_index"]
    
    # Get document_id and submission_id from document_meta
    document_id = document_meta.get("document_id")
    submission_id = document_meta.get("submission_id")
    
    # Build general evidence_index for text blocks and tables
    evidence_index = {}
    
    page_map = {}  # page_number -> page_id
    evidence_records = []
    field_evidence_records = []
    extracted_field_records = []

    session = None
    if write_to_tables and db and document_id:
        session = db.get_session()
        try:
            from planproof.db import Page
            page_count = extraction_result.get("metadata", {}).get("page_count", 0)
            existing_pages = session.query(Page).filter(
                Page.document_id == document_id
            ).all()
            for page in existing_pages:
                page_map[page.page_number] = page.id

            new_pages = []
            for page_num in range(1, page_count + 1):
                if page_num not in page_map:
                    new_pages.append(Page(document_id=document_id, page_number=page_num))

            if new_pages:
                session.add_all(new_pages)
                session.flush()
                for page in new_pages:
                    page_map[page.page_number] = page.id
        except Exception:
            session.rollback()
            session.close()
            session = None

    # Extract text blocks as evidence with page numbers and snippets
    for i, block in enumerate(extraction_result.get("text_blocks", [])):
        content = block.get("content", "")
        page_num = block.get("page_number", 1)
        # Create snippet (first 100 chars)
        snippet = content[:100] + "..." if len(content) > 100 else content
        
        evidence_key = f"text_block_{i}"
        evidence_index[evidence_key] = {
            "type": "text_block",
            "content": content,
            "snippet": snippet,
            "page_number": page_num,
            "bounding_box": block.get("bounding_box")
        }
        
        if session and document_id:
            from planproof.db import Evidence
            page_id = page_map.get(page_num)
            evidence_records.append(Evidence(
                document_id=document_id,
                page_id=page_id,
                page_number=page_num,
                evidence_type="text_block",
                evidence_key=evidence_key,
                snippet=snippet,
                content=content,
                bbox=block.get("bounding_box")
            ))
        
        # Add index to block for field mapper reference
        block["index"] = i

    # Extract tables as evidence with page numbers
    for i, table in enumerate(extraction_result.get("tables", [])):
        page_num = table.get("page_number", 1)
        # Create snippet from first few cells
        cells = table.get("cells", [])
        cell_snippets = []
        for cell in cells[:5]:  # First 5 cells
            if cell.get("content"):
                cell_snippets.append(cell["content"][:50])
        snippet = " | ".join(cell_snippets) if cell_snippets else ""
        
        evidence_key = f"table_{i}"
        evidence_index[evidence_key] = {
            "type": "table",
            "row_count": table.get("row_count"),
            "column_count": table.get("column_count"),
            "page_number": page_num,
            "snippet": snippet,
            "cells": cells
        }
        
        if session and document_id:
            from planproof.db import Evidence
            page_id = page_map.get(page_num)
            evidence_records.append(Evidence(
                document_id=document_id,
                page_id=page_id,
                page_number=page_num,
                evidence_type="table",
                evidence_key=evidence_key,
                snippet=snippet,
                bbox=table.get("bounding_box")
            ))
    
    # Merge field-specific evidence into general evidence_index
    for field_name, ev_list in field_evidence.items():
        evidence_index[field_name] = ev_list
        
        if session and document_id and isinstance(ev_list, list) and len(ev_list) > 0:
            from planproof.db import Evidence
            ev_item = ev_list[0]
            page_num = ev_item.get("page", 1)
            snippet = ev_item.get("snippet", "")
            page_id = page_map.get(page_num)
            evidence = Evidence(
                document_id=document_id,
                page_id=page_id,
                page_number=page_num,
                evidence_type="field_extraction",
                evidence_key=field_name,
                snippet=snippet
            )
            evidence_records.append(evidence)
            if submission_id and field_name != "document_type":
                field_evidence_records.append((field_name, evidence))

    if session:
        try:
            if evidence_records:
                session.add_all(evidence_records)
                session.flush()
            if field_evidence_records:
                from planproof.db import ExtractedField
                for field_name, evidence in field_evidence_records:
                    extracted_field_records.append(ExtractedField(
                        submission_id=submission_id,
                        field_name=field_name,
                        field_value=str(fields.get(field_name)) if fields.get(field_name) is not None else None,
                        extractor="deterministic",
                        evidence_id=evidence.id
                    ))
                session.add_all(extracted_field_records)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    # Build result with persistence keys
    result = {
        "fields": fields,
        "evidence_index": evidence_index,
        "metadata": extraction_result.get("metadata", {}),
        "text_blocks": extraction_result.get("text_blocks", []),
        "tables": extraction_result.get("tables", []),
        "page_anchors": extraction_result.get("page_anchors", {})
    }
    
    # Add persistence keys
    if document_id:
        result["document_id"] = document_id
    if submission_id:
        result["submission_id"] = submission_id
    
    # Get run_id from document_meta
    run_id = document_meta.get("run_id") or document_meta.get("context", {}).get("run_id")
    if run_id:
        result["run_id"] = run_id
    
    # Add document hash if available in document_meta
    if "content_hash" in document_meta:
        result["document_hash"] = document_meta["content_hash"]
    
    # Add analyzed_at timestamp
    from datetime import datetime, timezone
    result["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    
    return result
