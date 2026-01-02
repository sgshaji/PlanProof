"""Test script to diagnose API query timeout issue."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from planproof.db import Database, Application, Submission
from sqlalchemy import func
import time

def test_applications_query():
    """Test the applications endpoint query."""
    print("🔍 Testing applications query...")
    
    db = Database()
    session = db.get_session()
    
    try:
        print("📊 Testing simple count query...")
        start = time.time()
        count = session.query(Application).count()
        elapsed = time.time() - start
        print(f"✓ Applications count: {count} (took {elapsed:.2f}s)")
        
        print("\n📊 Testing query with join and group_by (like /applications endpoint)...")
        start = time.time()
        
        apps_with_counts = session.query(
            Application,
            func.count(Submission.id).label('submission_count')
        ).outerjoin(
            Submission,
            Submission.planning_case_id == Application.id
        ).group_by(
            Application.id
        ).limit(10).all()
        
        elapsed = time.time() - start
        print(f"✓ Query completed in {elapsed:.2f}s")
        print(f"✓ Found {len(apps_with_counts)} applications")
        
        for app, submission_count in apps_with_counts:
            print(f"  - {app.application_ref}: {submission_count} submissions")
        
        print("\n✅ Query completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    test_applications_query()
