"""
Migration script to populate new relational tables from existing data.

This script:
1. Creates V0 submissions for all existing applications
2. Links existing documents to submissions
3. Extracts fields and evidence from existing artefacts and populates relational tables
4. Creates pages from existing extraction data
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from planproof.db import Database, Application, Document, Submission, Page, Evidence, ExtractedField, Artefact
from planproof.storage import StorageClient

load_dotenv()


def create_submissions_for_applications(db: Database) -> Dict[int, int]:
    """
    Create V0 submissions for all existing applications.
    
    Returns:
        Dictionary mapping application_id -> submission_id
    """
    session = db.get_session()
    try:
        applications = session.query(Application).all()
        app_to_submission = {}
        
        for app in applications:
            # Check if submission already exists
            existing = db.get_submission_by_version(app.id, "V0")
            if existing:
                app_to_submission[app.id] = existing.id
                print(f"  Application {app.id} ({app.application_ref}) already has V0 submission {existing.id}")
            else:
                submission = db.create_submission(
                    planning_case_id=app.id,
                    submission_version="V0",
                    status="completed"
                )
                app_to_submission[app.id] = submission.id
                print(f"  Created V0 submission {submission.id} for application {app.id} ({app.application_ref})")
        
        return app_to_submission
    finally:
        session.close()


def link_documents_to_submissions(db: Database, app_to_submission: Dict[int, int]):
    """Link existing documents to their submissions."""
    session = db.get_session()
    try:
        documents = session.query(Document).filter(Document.submission_id.is_(None)).all()
        
        for doc in documents:
            if doc.application_id in app_to_submission:
                doc.submission_id = app_to_submission[doc.application_id]
                session.commit()
                print(f"  Linked document {doc.id} to submission {app_to_submission[doc.application_id]}")
    finally:
        session.close()


def migrate_pages_from_extraction(db: Database, storage_client: StorageClient):
    """Create Page records from existing extraction artefacts."""
    session = db.get_session()
    try:
        # Get all extraction artefacts
        extraction_artefacts = session.query(Artefact).filter(
            Artefact.artefact_type == "extraction"
        ).all()
        
        for artefact in extraction_artefacts:
            try:
                # Download extraction JSON from blob
                blob_uri = artefact.blob_uri
                # Parse blob URI: azure://account/container/blob_path
                if blob_uri.startswith("azure://"):
                    parts = blob_uri.replace("azure://", "").split("/", 2)
                    if len(parts) == 3:
                        container = parts[1]
                        blob_path = parts[2]
                        try:
                            extraction_data = storage_client.read_json_blob(container, blob_path)
                        except Exception as e:
                            print(f"    Warning: Could not read blob {blob_path}: {e}")
                            continue
                        
                        # Get page count from extraction metadata
                        page_count = extraction_data.get("metadata", {}).get("page_count")
                        if page_count:
                            # Create page records
                            for page_num in range(1, page_count + 1):
                                # Check if page already exists
                                existing = session.query(Page).filter(
                                    Page.document_id == artefact.document_id,
                                    Page.page_number == page_num
                                ).first()
                                
                                if not existing:
                                    db.create_page(
                                        document_id=artefact.document_id,
                                        page_number=page_num,
                                        metadata={"migrated": True}
                                    )
                                    print(f"  Created page {page_num} for document {artefact.document_id}")
            except Exception as e:
                print(f"  Warning: Could not migrate pages for artefact {artefact.id}: {e}")
                continue
    finally:
        session.close()


def migrate_evidence_from_extraction(db: Database, storage_client: StorageClient):
    """Create Evidence records from existing extraction artefacts."""
    session = db.get_session()
    try:
        # Get all extraction artefacts
        extraction_artefacts = session.query(Artefact).filter(
            Artefact.artefact_type == "extraction"
        ).all()
        
        for artefact in extraction_artefacts:
            try:
                # Download extraction JSON from blob
                blob_uri = artefact.blob_uri
                if blob_uri.startswith("azure://"):
                    parts = blob_uri.replace("azure://", "").split("/", 2)
                    if len(parts) == 3:
                        container = parts[1]
                        blob_path = parts[2]
                        extraction_data = storage_client.read_json_blob(container, blob_path)
                        
                        # Get evidence_index from extraction
                        evidence_index = extraction_data.get("evidence_index", {})
                        
                        for evidence_key, evidence_data in evidence_index.items():
                            # Check if evidence already exists
                            existing = session.query(Evidence).filter(
                                Evidence.document_id == artefact.document_id,
                                Evidence.evidence_key == evidence_key
                            ).first()
                            
                            if not existing:
                                # Determine evidence type
                                if evidence_key.startswith("text_block_"):
                                    evidence_type = "text_block"
                                elif evidence_key.startswith("table_"):
                                    evidence_type = "table"
                                else:
                                    evidence_type = "field_extraction"
                                
                                # Extract page number
                                if isinstance(evidence_data, list) and len(evidence_data) > 0:
                                    page_num = evidence_data[0].get("page", 1)
                                    snippet = evidence_data[0].get("snippet", "")
                                elif isinstance(evidence_data, dict):
                                    page_num = evidence_data.get("page_number", evidence_data.get("page", 1))
                                    snippet = evidence_data.get("snippet", evidence_data.get("content", ""))[:200]
                                else:
                                    page_num = 1
                                    snippet = ""
                                
                                # Get page_id if page exists
                                page = session.query(Page).filter(
                                    Page.document_id == artefact.document_id,
                                    Page.page_number == page_num
                                ).first()
                                page_id = page.id if page else None
                                
                                # Create evidence record
                                db.create_evidence(
                                    document_id=artefact.document_id,
                                    page_number=page_num,
                                    evidence_type=evidence_type,
                                    evidence_key=evidence_key,
                                    snippet=snippet[:500] if snippet else None,
                                    content=evidence_data.get("content") if isinstance(evidence_data, dict) else None,
                                    page_id=page_id
                                )
                                print(f"  Created evidence {evidence_key} for document {artefact.document_id}")
            except Exception as e:
                print(f"  Warning: Could not migrate evidence for artefact {artefact.id}: {e}")
                continue
    finally:
        session.close()


def migrate_fields_from_extraction(db: Database, storage_client: StorageClient):
    """Create ExtractedField records from existing extraction artefacts."""
    session = db.get_session()
    try:
        # Get all extraction artefacts
        extraction_artefacts = session.query(Artefact).filter(
            Artefact.artefact_type == "extraction"
        ).all()
        
        for artefact in extraction_artefacts:
            try:
                # Get document to find submission_id
                document = session.query(Document).filter(Document.id == artefact.document_id).first()
                if not document or not document.submission_id:
                    print(f"  Warning: Document {artefact.document_id} has no submission, skipping fields")
                    continue
                
                # Download extraction JSON from blob
                blob_uri = artefact.blob_uri
                if blob_uri.startswith("azure://"):
                    parts = blob_uri.replace("azure://", "").split("/", 2)
                    if len(parts) == 3:
                        container = parts[1]
                        blob_path = parts[2]
                        try:
                            extraction_data = storage_client.read_json_blob(container, blob_path)
                        except Exception as e:
                            print(f"    Warning: Could not read blob {blob_path}: {e}")
                            continue
                        
                        # Get fields from extraction
                        fields = extraction_data.get("fields", {})
                        evidence_index = extraction_data.get("evidence_index", {})
                        
                        for field_name, field_value in fields.items():
                            # Skip document_type as it's metadata, not a field
                            if field_name == "document_type":
                                continue
                            
                            # Check if field already exists
                            existing = session.query(ExtractedField).filter(
                                ExtractedField.submission_id == document.submission_id,
                                ExtractedField.field_name == field_name
                            ).first()
                            
                            if not existing:
                                # Find evidence for this field
                                evidence_id = None
                                if field_name in evidence_index:
                                    ev_data = evidence_index[field_name]
                                    if isinstance(ev_data, list) and len(ev_data) > 0:
                                        ev_key = f"{field_name}_evidence"
                                    else:
                                        ev_key = field_name
                                    
                                    evidence = session.query(Evidence).filter(
                                        Evidence.document_id == artefact.document_id,
                                        Evidence.evidence_key == ev_key
                                    ).first()
                                    if evidence:
                                        evidence_id = evidence.id
                                
                                # Create extracted field record
                                db.create_extracted_field(
                                    submission_id=document.submission_id,
                                    field_name=field_name,
                                    field_value=str(field_value) if field_value is not None else None,
                                    extractor="migrated",
                                    evidence_id=evidence_id
                                )
                                print(f"  Created field {field_name} for submission {document.submission_id}")
            except Exception as e:
                print(f"  Warning: Could not migrate fields for artefact {artefact.id}: {e}")
                continue
    finally:
        session.close()


def migrate_resolved_fields_to_submissions(db: Database):
    """Migrate resolved_fields from run metadata to submission metadata."""
    session = db.get_session()
    try:
        # Get all runs with resolved_fields in metadata
        from planproof.db import Run
        runs = session.query(Run).filter(
            Run.run_metadata.isnot(None)
        ).all()
        
        for run in runs:
            if not run.run_metadata:
                continue
            
            resolved_fields = run.run_metadata.get("resolved_fields")
            if not resolved_fields:
                continue
            
            # Find submission for this run
            if run.document_id:
                document = session.query(Document).filter(Document.id == run.document_id).first()
                if document and document.submission_id:
                    # Update submission metadata
                    db.update_submission_metadata(
                        document.submission_id,
                        {"resolved_fields": resolved_fields}
                    )
                    print(f"  Migrated resolved_fields from run {run.id} to submission {document.submission_id}")
    finally:
        session.close()


def main():
    """Run migration."""
    print("Starting migration to relational tables...")
    print("=" * 60)
    
    db = Database()
    storage_client = StorageClient()
    
    # Step 1: Create submissions for all applications
    print("\n1. Creating V0 submissions for applications...")
    app_to_submission = create_submissions_for_applications(db)
    print(f"   Created/linked {len(app_to_submission)} submissions")
    
    # Step 2: Link documents to submissions
    print("\n2. Linking documents to submissions...")
    link_documents_to_submissions(db, app_to_submission)
    
    # Step 3: Migrate pages
    print("\n3. Migrating pages from extraction data...")
    migrate_pages_from_extraction(db, storage_client)
    
    # Step 4: Migrate evidence
    print("\n4. Migrating evidence from extraction data...")
    migrate_evidence_from_extraction(db, storage_client)
    
    # Step 5: Migrate fields
    print("\n5. Migrating extracted fields...")
    migrate_fields_from_extraction(db, storage_client)
    
    # Step 6: Migrate resolved fields
    print("\n6. Migrating resolved fields from runs to submissions...")
    migrate_resolved_fields_to_submissions(db)
    
    print("\n" + "=" * 60)
    print("Migration completed!")


if __name__ == "__main__":
    main()

