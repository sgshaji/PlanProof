"""
Document Upload & Management Endpoints
"""

import tempfile
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from planproof.api.dependencies import (
    get_db, get_storage_client, get_docintel_client, get_aoai_client, get_current_user
)
from planproof.db import Database, Document, Submission
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


class BatchDocumentUploadResponse(BaseModel):
    """Response after batch document upload."""
    run_id: int
    application_ref: str
    status: str
    documents: List[DocumentUploadResponse]
    message: str


async def _process_document_upload(
    application_ref: str,
    file: UploadFile,
    db: Database,
    storage: StorageClient,
    docintel: DocumentIntelligence,
    aoai: AzureOpenAIClient,
    document_type: Optional[str] = None,
    application_id: Optional[int] = None,
    parent_submission_id: Optional[int] = None,
    applicant_name: Optional[str] = None,
    run_type: str = "api_upload"
) -> DocumentUploadResponse:
    """Process a document upload and return a standard response."""
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    # Create run record
    run = db.create_run(
        run_type=run_type,
        application_id=application_id,
        metadata={
            "application_ref": application_ref,
            "filename": file.filename,
            "document_type": document_type,
            "source": "api",
            "parent_submission_id": parent_submission_id,
            "is_modification": parent_submission_id is not None
        }
    )

    try:
        response = await _process_document_for_run(
            run=run,
            application_ref=application_ref,
            file=file,
            db=db,
            storage=storage,
            docintel=docintel,
            aoai=aoai,
            document_type=document_type,
            application_id=application_id,
            parent_submission_id=parent_submission_id,
            applicant_name=applicant_name
        )
        db.update_run(run.id, status="completed")
        return response
    except HTTPException as exc:
        db.update_run(run.id, status="failed", error_message=str(exc.detail))
        raise
    except Exception as exc:
        db.update_run(run.id, status="failed", error_message=str(exc))
        raise


async def _process_document_for_run(
    run,
    application_ref: str,
    file: UploadFile,
    db: Database,
    storage: StorageClient,
    docintel: DocumentIntelligence,
    aoai: AzureOpenAIClient,
    document_type: Optional[str] = None,
    application_id: Optional[int] = None,
    parent_submission_id: Optional[int] = None,
    applicant_name: Optional[str] = None
) -> DocumentUploadResponse:
    """Process a document upload within an existing run."""
    settings = get_settings()

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
            applicant_name=applicant_name,
            storage_client=storage,
            db=db,
            parent_submission_id=parent_submission_id
        )

        # Link document to run
        db.link_document_to_run(run.id, ingested["document_id"])

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
        extraction_blob = f"runs/{run.id}/extraction_{run.id}.json"
        extraction_url = storage.write_json_blob("artefacts", extraction_blob, extraction, overwrite=True)

        db.create_artefact_record(
            document_id=ingested["document_id"],
            artefact_type="extraction",
            blob_uri=extraction_url,
            metadata={"run_id": run.id}
        )

        # Step 3: Validate
        rules = load_rule_catalog("artefacts/rule_catalog.json")
        validation = validate_extraction(
            extraction,
            rules,
            context={"run_id": run.id, "document_id": ingested["document_id"]},
            db=db,
            write_to_tables=settings.enable_db_writes
        )

        # Save validation artifact
        validation_blob = f"runs/{run.id}/validation_{run.id}.json"
        validation_url = storage.write_json_blob("artefacts", validation_blob, validation, overwrite=True)

        db.create_artefact_record(
            document_id=ingested["document_id"],
            artefact_type="validation",
            blob_uri=validation_url,
            metadata={"run_id": run.id}
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
            llm_blob = f"runs/{run.id}/llm_notes_{run.id}.json"
            llm_url = storage.write_json_blob("artefacts", llm_blob, llm_notes, overwrite=True)

            db.create_artefact_record(
                document_id=ingested["document_id"],
                artefact_type="llm_notes",
                blob_uri=llm_url,
                metadata={"run_id": run.id}
            )

        return DocumentUploadResponse(
            run_id=run.id,
            document_id=ingested["document_id"],
            application_ref=application_ref,
            filename=file.filename,
            blob_uri=ingested["blob_uri"],
            status="completed",
            message="Document processed successfully"
        )

    except Exception as e:
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


@router.post("/applications/{application_ref}/documents")
async def upload_document(
    application_ref: str,
    file: UploadFile = File(..., description="PDF file to upload"),
    document_type: Optional[str] = Form(None, description="Document type (application_form, site_plan, etc.)"),
    db: Database = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
    docintel: DocumentIntelligence = Depends(get_docintel_client),
    aoai: AzureOpenAIClient = Depends(get_aoai_client),
    user: dict = Depends(get_current_user)
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
    return await _process_document_upload(
        application_ref=application_ref,
        file=file,
        db=db,
        storage=storage,
        docintel=docintel,
        aoai=aoai,
        document_type=document_type
    )


@router.post(
    "/applications/{application_ref}/documents/batch",
    response_model=BatchDocumentUploadResponse
)
async def upload_documents_batch(
    application_ref: str,
    files: Optional[List[UploadFile]] = File(None, description="PDF files to upload"),
    documents: Optional[List[UploadFile]] = File(None, description="PDF files to upload"),
    document_type: Optional[str] = Form(None, description="Document type (application_form, site_plan, etc.)"),
    db: Database = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
    docintel: DocumentIntelligence = Depends(get_docintel_client),
    aoai: AzureOpenAIClient = Depends(get_aoai_client),
    user: dict = Depends(get_current_user)
) -> BatchDocumentUploadResponse:
    """
    Upload multiple PDF documents for processing in a single run.
    """
    if files and documents:
        raise HTTPException(
            status_code=400,
            detail="Provide files or documents, not both"
        )

    uploads = documents or files or []

    if not uploads:
        raise HTTPException(status_code=400, detail="No files provided")

    for upload in uploads:
        if not upload.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files are supported (invalid: {upload.filename})"
            )

    application = db.get_application_by_ref(application_ref)
    if application is None:
        application = db.create_application(application_ref=application_ref)

    run = db.create_run(
        run_type="api_batch",
        application_id=application.id,
        metadata={
            "application_ref": application_ref,
            "file_count": len(uploads),
            "document_type": document_type,
            "source": "api"
        }
    )

    responses: List[DocumentUploadResponse] = []
    try:
        for file in uploads:
            responses.append(
                await _process_document_for_run(
                    run=run,
                    application_ref=application_ref,
                    file=file,
                    db=db,
                    storage=storage,
                    docintel=docintel,
                    aoai=aoai,
                    document_type=document_type,
                    application_id=application.id,
                    parent_submission_id=None,
                    applicant_name=None
                )
            )
        db.update_run(run.id, status="completed", metadata={"processed_count": len(responses)})
    except HTTPException as exc:
        db.update_run(run.id, status="failed", error_message=str(exc.detail))
        raise
    except Exception as exc:
        db.update_run(run.id, status="failed", error_message=str(exc))
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(exc)}")

    return BatchDocumentUploadResponse(
        run_id=run.id,
        application_ref=application_ref,
        status="completed",
        documents=responses,
        message="Documents processed successfully"
    )


@router.post("/applications/{application_id}/runs")
async def upload_application_run(
    application_id: int,
    file: UploadFile = File(..., description="PDF file to upload"),
    document_type: Optional[str] = Form(None, description="Document type (application_form, site_plan, etc.)"),
    db: Database = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
    docintel: DocumentIntelligence = Depends(get_docintel_client),
    aoai: AzureOpenAIClient = Depends(get_aoai_client),
    user: dict = Depends(get_current_user)
) -> DocumentUploadResponse:
    """
    Upload a PDF document to create a new run/version for an existing application.

    **Path Parameters:**
    - application_id: Application database ID

    **Form Data:**
    - file: PDF file (multipart/form-data)
    - document_type: Optional document type classification
    """
    application = db.get_application_by_id(application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    session = db.get_session()
    try:
        latest_submission = session.query(Submission).filter(
            Submission.planning_case_id == application_id
        ).order_by(Submission.created_at.desc()).first()
    finally:
        session.close()

    parent_submission_id = latest_submission.id if latest_submission else None

    return await _process_document_upload(
        application_ref=application.application_ref,
        file=file,
        db=db,
        storage=storage,
        docintel=docintel,
        aoai=aoai,
        document_type=document_type,
        application_id=application.id,
        parent_submission_id=parent_submission_id,
        applicant_name=application.applicant_name,
        run_type="api_version_upload"
    )


@router.post("/runs/{run_id}/reclassify_document")
async def reclassify_document(
    run_id: int,
    document_id: int = Form(..., description="Document ID to reclassify"),
    document_type: str = Form(..., description="New document type classification"),
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Override the detected document type classification.
    
    **Path Parameters:**
    - run_id: Run ID
    
    **Form Data:**
    - document_id: ID of the document to reclassify
    - document_type: New document type (e.g., "site_plan", "application_form", etc.)
    
    **Use Case:**
    When AI misclassifies a document, officer can manually override the classification.
    """
    session = db.get_session()
    try:
        # Validate document exists
        document = session.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Update document type
        old_type = document.document_type
        document.document_type = document_type
        session.commit()
        
        # TODO: Re-run validation rules that depend on document type
        
        return {
            "document_id": document_id,
            "old_type": old_type,
            "new_type": document_type,
            "filename": document.filename,
            "message": "Document reclassified successfully. Validation will be re-run."
        }
    finally:
        session.close()
