"""
List all runs in the database.
"""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, run_type, document_id, application_id, started_at, status 
            FROM runs 
            ORDER BY started_at DESC 
            LIMIT 10
        """)
        rows = cur.fetchall()
        
        print(f"Recent runs (showing last 10):")
        print("=" * 80)
        print(f"{'ID':<6} {'Type':<15} {'Doc ID':<8} {'App ID':<8} {'Status':<12} {'Started':<20}")
        print("-" * 80)
        
        for r in rows:
            print(f"{r[0]:<6} {r[1]:<15} {str(r[2] or ''):<8} {str(r[3] or ''):<8} {r[5]:<12} {str(r[4]):<20}")

