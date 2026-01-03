#!/usr/bin/env python3
"""
Check the status of the latest run for a given application reference.
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

from planproof.db import Database, Run, Application
from datetime import datetime


def check_application_status(app_ref: str):
    """Check the latest run status for an application."""
    db = Database()
    session = db.get_session()
    
    try:
        # Find application
        app = session.query(Application).filter(
            Application.application_ref == app_ref
        ).first()
        
        if not app:
            print(f"❌ Application '{app_ref}' not found in database")
            return
        
        print(f"✅ Found application: {app_ref}")
        print(f"   Application ID: {app.id}")
        print(f"   Created: {app.created_at}")
        print()
        
        # Find all runs for this application
        runs = session.query(Run).filter(
            Run.application_id == app.id
        ).order_by(Run.started_at.desc()).all()
        
        if not runs:
            print(f"⚠️  No runs found for application '{app_ref}'")
            return
        
        print(f"📊 Found {len(runs)} run(s)")
        print()
        
        # Show latest run
        latest_run = runs[0]
        print("=" * 60)
        print("LATEST RUN")
        print("=" * 60)
        print(f"Run ID: {latest_run.id}")
        print(f"Type: {latest_run.run_type}")
        print(f"Status: {latest_run.status}")
        print(f"Started: {latest_run.started_at}")
        print(f"Completed: {latest_run.completed_at}")
        
        if latest_run.error_message:
            print(f"❌ Error: {latest_run.error_message}")
        
        metadata = latest_run.run_metadata or {}
        
        # Show summary if available
        if "summary" in metadata:
            summary = metadata["summary"]
            print()
            print("Summary:")
            print(f"  Total Documents: {summary.get('total_documents', 'N/A')}")
            print(f"  Processed: {summary.get('processed', 'N/A')}")
            print(f"  Errors: {summary.get('errors', 'N/A')}")
        
        if "llm_calls_per_run" in metadata:
            print(f"  LLM Calls: {metadata['llm_calls_per_run']}")
        
        # Show progress if running
        if latest_run.status == "running" and "progress" in metadata:
            progress = metadata["progress"]
            print()
            print("Progress:")
            print(f"  {progress.get('current', 0)} / {progress.get('total', 0)} documents")
            if progress.get("current_file"):
                print(f"  Current file: {progress['current_file']}")
        
        # Show errors if any
        if "errors" in metadata and metadata["errors"]:
            print()
            print(f"⚠️  {len(metadata['errors'])} error(s):")
            for error in metadata["errors"][:3]:  # Show first 3
                print(f"  - {error.get('filename', 'unknown')}: {error.get('error', 'unknown error')}")
        
        print()
        print("=" * 60)
        
        # Show all runs summary
        if len(runs) > 1:
            print()
            print(f"All {len(runs)} runs:")
            for i, run in enumerate(runs[:5], 1):  # Show first 5
                status_icon = "✅" if run.status == "completed" else "🔄" if run.status == "running" else "❌"
                print(f"  {i}. {status_icon} Run {run.id} - {run.status} ({run.started_at})")
        
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_application_status.py <application_ref>")
        print("Example: python scripts/check_application_status.py 202506361PA")
        sys.exit(1)
    
    app_ref = sys.argv[1]
    check_application_status(app_ref)

