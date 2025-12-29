"""
Extract module: Use Document Intelligence to extract structured data from documents.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime

from planproof.docintel import DocumentIntelligence
from planproof.storage import StorageClient
from planproof.db import Database, Document, Artefact


def extract_document(
    document_id: int,
    model: str = "prebuilt-layout",
    docintel: Optional[DocumentIntelligence] = None,
    storage_client: Optional[StorageClient] = None,
    db: Optional[Database] = None
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

        # Download PDF from blob storage
        pdf_bytes = storage_client.download_blob(container, blob_name)

        # Analyze document with Document Intelligence
        extraction_result = docintel.analyze_document(pdf_bytes, model=model)

        # Update document metadata
        document.page_count = extraction_result["metadata"]["page_count"]
        document.docintel_model = model
        document.processed_at = datetime.utcnow()

        # Store extraction result as JSON artefact
        artefact_name = f"extracted_layout_{document_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        artefact_blob_uri = storage_client.write_artefact(extraction_result, artefact_name)

        # Create artefact record
        artefact = Artefact(
            document_id=document_id,
            artefact_type="extracted_layout",
            blob_uri=artefact_blob_uri,
            metadata={
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

        artefact_bytes = storage_client.download_blob(container, blob_name)
        return json.loads(artefact_bytes.decode("utf-8"))

    finally:
        session.close()

