"""
Document Upload & Management Endpoints
"""

import tempfile
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from planproof.api.dependencies import (
    get_db, get_storage_client, get_docintel_client, get_aoai_client
)
from planproof.db import Database
from planproof.storage import StorageClient
from planproof.docintel import DocumentIntelligence
from planproof.aoai import AzureOpenAIClient
from planproof.pipeline import ingest_pdf
from planproof.pipeline.extract import extract_from_pdf_bytes
from planproof.pipeline.validate import load_rule_catalog, validate_extraction
from planproof.pipeline.llm_gate import should_trigger_llm, resolve_with_llm_new
from planproof.config import get_settings

router = APIRouter()


class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    run_id: int
    document_id: int
    application_ref: str
    filename: str
    blob_uri: str
    status: str
    message: str


@router.post("/applications/{application_ref}/documents")
async def upload_document(
    application_ref: str,
    file: UploadFile = File(..., description="PDF file to upload"),
    document_type: Optional[str] = Form(None, description="Document type (application_form, site_plan, etc.)"),
    db: Database = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
    docintel: DocumentIntelligence = Depends(get_docintel_client),
    aoai: AzureOpenAIClient = Depends(get_aoai_client)
) -> DocumentUploadResponse:
    """
    Upload a PDF document for processing.
    
    This endpoint will:
    1. Upload PDF to Azure Blob Storage
    2. Extract text using Azure Document Intelligence
    3. Run validation rules
    4. Trigger LLM if needed
    
    **Path Parameters:**
    - application_ref: Application reference (e.g., "APP/2024/001")
    
    **Form Data:**
    - file: PDF file (multipart/form-data)
    - document_type: Optional document type classification
    
    **Returns:**
    - run_id: ID to track processing status
    - document_id: Database document ID
    - blob_uri: Location of uploaded PDF
    """
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    settings = get_settings()
    
    # Create run record
    run = db.create_run(metadata={
        "application_ref": application_ref,
        "filename": file.filename,
        "document_type": document_type,
        "source": "api"
    })

    # Save uploaded file to temp location
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Step 1: Ingest (upload to blob storage)
        ingested = ingest_pdf(
            tmp_path,
            application_ref,
            storage_client=storage,
            db=db
        )
        
        # Link document to run
        db.link_document_to_run(run["id"], ingested["document_id"])
        
        # Step 2: Extract (OCR with Document Intelligence)
        extraction = extract_from_pdf_bytes(
            content,
            ingested,
            docintel=docintel,
            storage_client=storage,
            db=db,
            write_to_tables=settings.enable_db_writes
        )
        
        # Save extraction artifact
        extraction_blob = f"runs/{run['id']}/extraction_{run['id']}.json"
        extraction_url = storage.write_json_blob("artefacts", extraction_blob, extraction, overwrite=True)
        
        db.create_artefact_record(
            document_id=ingested["document_id"],
            artefact_type="extraction",
            blob_uri=extraction_url,
            metadata={"run_id": run["id"]}
        )
        
        # Step 3: Validate
        rules = load_rule_catalog("artefacts/rule_catalog.json")
        validation = validate_extraction(
            extraction,
            rules,
            context={"run_id": run["id"], "document_id": ingested["document_id"]},
            db=db,
            write_to_tables=settings.enable_db_writes
        )
        
        # Save validation artifact
        validation_blob = f"runs/{run['id']}/validation_{run['id']}.json"
        validation_url = storage.write_json_blob("artefacts", validation_blob, validation, overwrite=True)
        
        db.create_artefact_record(
            document_id=ingested["document_id"],
            artefact_type="validation",
            blob_uri=validation_url,
            metadata={"run_id": run["id"]}
        )
        
        # Step 4: LLM Gate (if needed)
        submission_id = ingested.get("submission_id")
        resolved_fields = {}
        if submission_id:
            resolved_fields = db.get_resolved_fields_for_submission(submission_id)
        
        if settings.enable_llm_gate and should_trigger_llm(
            validation,
            extraction,
            resolved_fields=resolved_fields,
            application_ref=application_ref,
            submission_id=submission_id,
            db=db
        ):
            llm_notes = resolve_with_llm_new(extraction, validation, aoai_client=aoai)
            
            if llm_notes.get("response", {}).get("filled_fields"):
                filled = llm_notes["response"]["filled_fields"]
                resolved_fields.update(filled)
                if submission_id:
                    db.update_submission_metadata(submission_id, {"resolved_fields": resolved_fields})
            
            # Save LLM notes
            llm_blob = f"runs/{run['id']}/llm_notes_{run['id']}.json"
            llm_url = storage.write_json_blob("artefacts", llm_blob, llm_notes, overwrite=True)
            
            db.create_artefact_record(
                document_id=ingested["document_id"],
                artefact_type="llm_notes",
                blob_uri=llm_url,
                metadata={"run_id": run["id"]}
            )
        
        # Update run status
        db.update_run(run["id"], status="completed")

        return DocumentUploadResponse(
            run_id=run["id"],
            document_id=ingested["document_id"],
            application_ref=application_ref,
            filename=file.filename,
            blob_uri=ingested["blob_uri"],
            status="completed",
            message="Document processed successfully"
        )

    except Exception as e:
        # Update run with error
        db.update_run(run["id"], status="failed", error_message=str(e))

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )

    finally:
        # Always cleanup temp file, even if processing failed
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception as cleanup_error:
                # Log but don't fail the request due to cleanup error
                import logging
                logging.warning(f"Failed to cleanup temp file {tmp_path}: {cleanup_error}")
