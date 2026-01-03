#!/usr/bin/env python3
"""
Check all details for an application including documents and submissions.
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from planproof.db import Database, Application, Document, Submission


def check_application_details(app_ref: str):
    """Check all details for an application."""
    db = Database()
    session = db.get_session()
    
    try:
        # Find application
        app = session.query(Application).filter(
            Application.application_ref == app_ref
        ).first()
        
        if not app:
            print(f"Application '{app_ref}' not found")
            return
        
        print("=" * 60)
        print(f"APPLICATION: {app_ref}")
        print("=" * 60)
        print(f"ID: {app.id}")
        print(f"Applicant: {app.applicant_name or 'N/A'}")
        print(f"Created: {app.created_at}")
        print()
        
        # Find documents
        documents = session.query(Document).filter(
            Document.application_id == app.id
        ).order_by(Document.uploaded_at.desc()).all()
        
        print(f"Documents: {len(documents)}")
        for doc in documents:
            print(f"  - {doc.filename} (ID: {doc.id}, Pages: {doc.page_count or 'N/A'})")
            print(f"    Uploaded: {doc.uploaded_at}")
            print(f"    Processed: {doc.processed_at or 'Not processed'}")
        print()
        
        # Find submissions
        submissions = session.query(Submission).filter(
            Submission.planning_case_id == app.id
        ).order_by(Submission.created_at.desc()).all()
        
        print(f"Submissions: {len(submissions)}")
        for sub in submissions:
            print(f"  - {sub.submission_version} (ID: {sub.id}, Status: {sub.status})")
            print(f"    Created: {sub.created_at}")
        print()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_application_details.py <application_ref>")
        sys.exit(1)
    
    check_application_details(sys.argv[1])

