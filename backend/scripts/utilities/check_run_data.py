#!/usr/bin/env python3
"""Check if run data was persisted to database tables."""

import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from planproof.db import Database, Document, Page, Evidence, ExtractedField, ValidationCheck, Run

def check_run_data(run_id: int):
    """Check what data was persisted for a run."""
    db = Database()
    session = db.get_session()
    
    try:
        # Get run
        run = session.query(Run).filter(Run.id == run_id).first()
        if not run:
            print(f"Run {run_id} not found")
            return
        
        print(f"Run {run_id}: {run.status}")
        print(f"Application ID: {run.application_id}")
        print()
        
        # Get application
        if run.application_id:
            from planproof.db import Application
            app = session.query(Application).filter(Application.id == run.application_id).first()
            if app:
                print(f"Application: {app.application_ref}")
                print()
                
                # Get documents for this application
                documents = session.query(Document).filter(
                    Document.application_id == run.application_id
                ).all()
                
                print(f"Documents: {len(documents)}")
                for doc in documents:
                    print(f"\nDocument {doc.id}: {doc.filename}")
                    
                    # Check pages
                    pages = session.query(Page).filter(Page.document_id == doc.id).all()
                    print(f"  Pages: {len(pages)}")
                    
                    # Check evidence
                    evidence = session.query(Evidence).filter(Evidence.document_id == doc.id).all()
                    print(f"  Evidence records: {len(evidence)}")
                    
                    # Check extracted fields
                    if doc.submission_id:
                        fields = session.query(ExtractedField).filter(
                            ExtractedField.submission_id == doc.submission_id
                        ).all()
                        print(f"  Extracted fields: {len(fields)}")
                        for field in fields[:5]:  # Show first 5
                            print(f"    - {field.field_name}: {field.field_value[:50] if field.field_value else 'None'}...")
                    
                    # Check validation checks
                    checks = session.query(ValidationCheck).filter(
                        ValidationCheck.document_id == doc.id
                    ).all()
                    print(f"  Validation checks: {len(checks)}")
                    for check in checks[:3]:  # Show first 3
                        print(f"    - {check.rule_id_string}: {check.status.value}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    run_id = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    check_run_data(run_id)

