"""
Ingest module: Upload PDFs to blob storage and create database records.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from planproof.storage import StorageClient
from planproof.db import Database, Application, Document


def ingest_pdf(
    pdf_path: str,
    application_ref: str,
    applicant_name: Optional[str] = None,
    application_date: Optional[datetime] = None,
    blob_name: Optional[str] = None,
    storage_client: Optional[StorageClient] = None,
    db: Optional[Database] = None
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

    # Get or create application
    application = db.get_application_by_ref(application_ref)
    if application is None:
        application = db.create_application(
            application_ref=application_ref,
            applicant_name=applicant_name,
            application_date=application_date
        )

    # Upload PDF to blob storage
    blob_uri = storage_client.upload_pdf(pdf_path, blob_name=blob_name)

    # Create document record
    document = db.create_document(
        application_id=application.id,
        blob_uri=blob_uri,
        filename=pdf_path_obj.name
    )

    return {
        "application_id": application.id,
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
    db: Optional[Database] = None
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

    # Initialize clients if not provided
    if storage_client is None:
        storage_client = StorageClient()
    if db is None:
        db = Database()

    results = []
    for pdf_file in pdf_files:
        try:
            result = ingest_pdf(
                pdf_path=str(pdf_file),
                application_ref=application_ref,
                applicant_name=applicant_name,
                application_date=application_date,
                storage_client=storage_client,
                db=db
            )
            results.append(result)
        except Exception as e:
            # Log error but continue with other files
            results.append({
                "error": str(e),
                "filename": pdf_file.name,
                "application_ref": application_ref
            })

    return results

