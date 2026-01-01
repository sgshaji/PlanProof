"""
Ingest module: Upload PDFs to blob storage and create database records.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from planproof.storage import StorageClient
from planproof.db import Database, Application, Document, Submission


def ingest_pdf(
    pdf_path: str,
    application_ref: str,
    applicant_name: Optional[str] = None,
    application_date: Optional[datetime] = None,
    blob_name: Optional[str] = None,
    storage_client: Optional[StorageClient] = None,
    db: Optional[Database] = None,
    parent_submission_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Ingest a single PDF: upload to blob storage and create database records.

    Args:
        pdf_path: Local path to the PDF file
        application_ref: Planning application reference (e.g., "APP/2024/001")
        applicant_name: Optional applicant name
        application_date: Optional application date
        blob_name: Optional custom blob name
        storage_client: Optional StorageClient instance (creates new if not provided)
        db: Optional Database instance (creates new if not provided)
        parent_submission_id: Optional parent submission ID for modification submissions (V1+)

    Returns:
        Dictionary with:
        - application_id: Created application ID
        - document_id: Created document ID
        - blob_uri: Blob URI of uploaded PDF
        - filename: Original filename
    """
    # Initialize clients if not provided
    if storage_client is None:
        storage_client = StorageClient()
    if db is None:
        db = Database()

    # Validate PDF exists
    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if not pdf_path_obj.suffix.lower() == ".pdf":
        raise ValueError(f"File must be a PDF: {pdf_path}")

    # Compute content hash for deduplication (streaming for large files)
    hasher = hashlib.sha256()
    with open(pdf_path_obj, "rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            hasher.update(chunk)
    content_hash = hasher.hexdigest()

    # Get or create application
    application = db.get_application_by_ref(application_ref)
    if application is None:
        application = db.create_application(
            application_ref=application_ref,
            applicant_name=applicant_name,
            application_date=application_date
        )

    # Get or create submission (V0 or V1+ based on parent_submission_id)
    if parent_submission_id is not None:
        # This is a modification submission - determine next version
        parent_submission = db.get_submission_by_id(parent_submission_id)
        if parent_submission:
            # Parse parent version (e.g., "V0" -> 0, "V1" -> 1)
            parent_version_num = int(parent_submission.submission_version[1:])
            next_version = f"V{parent_version_num + 1}"
        else:
            # Parent not found, default to V1
            next_version = "V1"
        
        # Create new version submission
        submission = db.create_submission(
            planning_case_id=application.id,
            submission_version=next_version,
            status="pending",
            parent_submission_id=parent_submission_id
        )
    else:
        # Get or create V0 submission for this application
        submission = db.get_submission_by_version(application.id, "V0")
        if submission is None:
            submission = db.create_submission(
                planning_case_id=application.id,
                submission_version="V0",
                status="pending"
            )

    # Check if document with same hash already exists
    session = db.get_session()
    try:
        existing_doc = session.query(Document).filter(Document.content_hash == content_hash).first()
        if existing_doc:
            # Link existing document to this application and submission if not already linked
            if existing_doc.application_id != application.id:
                existing_doc.application_id = application.id
            if existing_doc.submission_id != submission.id:
                existing_doc.submission_id = submission.id
            session.commit()
            return {
                "application_id": application.id,
                "submission_id": submission.id,
                "document_id": existing_doc.id,
                "blob_uri": existing_doc.blob_uri,
                "filename": existing_doc.filename,
                "duplicate": True
            }
    finally:
        session.close()

    # Upload PDF to blob storage
    blob_uri = storage_client.upload_pdf(pdf_path, blob_name=blob_name)

    # Create document record with content hash, linked to both application and submission
    document = db.create_document(
        application_id=application.id,
        submission_id=submission.id,
        blob_uri=blob_uri,
        filename=pdf_path_obj.name,
        content_hash=content_hash
    )

    return {
        "application_id": application.id,
        "submission_id": submission.id,
        "document_id": document.id,
        "blob_uri": blob_uri,
        "filename": pdf_path_obj.name
    }


def ingest_folder(
    folder_path: str,
    application_ref: str,
    applicant_name: Optional[str] = None,
    application_date: Optional[datetime] = None,
    storage_client: Optional[StorageClient] = None,
    db: Optional[Database] = None,
    max_workers: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Ingest all PDFs from a folder.

    Args:
        folder_path: Path to folder containing PDFs
        application_ref: Planning application reference
        applicant_name: Optional applicant name
        application_date: Optional application date
        storage_client: Optional StorageClient instance
        db: Optional Database instance

    Returns:
        List of ingestion results (same format as ingest_pdf)
    """
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Folder not found or not a directory: {folder_path}")

    # Find all PDFs
    pdf_files = list(folder.glob("*.pdf")) + list(folder.glob("*.PDF"))

    if not pdf_files:
        raise ValueError(f"No PDF files found in folder: {folder_path}")

    results = []
    worker_count = max_workers or min(4, len(pdf_files)) or 1

    def _ingest(file_path: Path) -> Dict[str, Any]:
        local_storage_client = storage_client or StorageClient()
        local_db = db or Database()
        return ingest_pdf(
            pdf_path=str(file_path),
            application_ref=application_ref,
            applicant_name=applicant_name,
            application_date=application_date,
            storage_client=local_storage_client,
            db=local_db
        )

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {executor.submit(_ingest, pdf_file): pdf_file for pdf_file in pdf_files}
        for future in as_completed(future_map):
            pdf_file = future_map[future]
            try:
                results.append(future.result())
            except Exception as e:
                results.append({
                    "error": str(e),
                    "filename": pdf_file.name,
                    "application_ref": application_ref
                })

    return results
