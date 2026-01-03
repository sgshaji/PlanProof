#!/usr/bin/env python3
"""Fix existing runs by linking them to their applications."""
import psycopg
import json
from planproof.config import get_settings

settings = get_settings()
db_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

print("Connecting to database...")
conn = psycopg.connect(db_url)
cursor = conn.cursor()

try:
    # Find all runs with NULL application_id but have application_ref in metadata
    print("\nFinding runs with NULL application_id...")
    cursor.execute("""
        SELECT id, run_metadata
        FROM runs
        WHERE application_id IS NULL
        AND run_metadata IS NOT NULL
        ORDER BY id DESC
    """)
    
    runs_to_fix = cursor.fetchall()
    print(f"Found {len(runs_to_fix)} runs to fix")
    
    fixed_count = 0
    skipped_count = 0
    
    for run_id, metadata in runs_to_fix:
        # Parse metadata to get application_ref
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                print(f"  ⚠️  Run {run_id}: Could not parse metadata")
                skipped_count += 1
                continue
        
        if not isinstance(metadata, dict):
            print(f"  ⚠️  Run {run_id}: Metadata is not a dict")
            skipped_count += 1
            continue
        
        app_ref = metadata.get('application_ref')
        if not app_ref:
            print(f"  ⚠️  Run {run_id}: No application_ref in metadata")
            skipped_count += 1
            continue
        
        # Find the application by reference
        cursor.execute("""
            SELECT id FROM applications WHERE application_ref = %s
        """, (app_ref,))
        
        app_result = cursor.fetchone()
        if not app_result:
            print(f"  ⚠️  Run {run_id}: Application '{app_ref}' not found in database")
            skipped_count += 1
            continue
        
        app_id = app_result[0]
        
        # Update the run's application_id
        cursor.execute("""
            UPDATE runs
            SET application_id = %s
            WHERE id = %s
        """, (app_id, run_id))
        
        print(f"  ✓ Run {run_id} linked to Application {app_id} ({app_ref})")
        fixed_count += 1
    
    conn.commit()
    
    print(f"\n{'='*60}")
    print(f"✓ Successfully fixed {fixed_count} runs")
    if skipped_count > 0:
        print(f"⚠️  Skipped {skipped_count} runs (no app_ref or app not found)")
    print(f"{'='*60}")
    
    # Show updated runs
    print("\nVerifying fixed runs...")
    cursor.execute("""
        SELECT r.id, r.run_type, r.application_id, r.status, a.application_ref
        FROM runs r
        LEFT JOIN applications a ON r.application_id = a.id
        ORDER BY r.started_at DESC 
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    print("\nRun ID | Run Type     | App ID | Status    | App Ref")
    print("-" * 70)
    for r in rows:
        app_id = str(r[2]) if r[2] else "NULL"
        app_ref = r[4] if r[4] else "N/A"
        print(f"{r[0]:<7} | {r[1]:<12} | {app_id:<7} | {r[3]:<9} | {app_ref}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
    import traceback
    traceback.print_exc()
finally:
    cursor.close()
    conn.close()
