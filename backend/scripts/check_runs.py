#!/usr/bin/env python3
"""Check runs table for application_id values."""
import psycopg
from planproof.config import get_settings

settings = get_settings()
db_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

conn = psycopg.connect(db_url)
cur = conn.cursor()

cur.execute("""
    SELECT r.id, r.run_type, r.application_id, r.status, a.application_ref
    FROM runs r
    LEFT JOIN applications a ON r.application_id = a.id
    ORDER BY r.started_at DESC 
    LIMIT 10
""")

rows = cur.fetchall()

print("Run ID | Run Type     | App ID | Status    | App Ref")
print("-" * 70)
for r in rows:
    app_id = str(r[2]) if r[2] else "NULL"
    app_ref = r[4] if r[4] else "N/A"
    print(f"{r[0]:<7} | {r[1]:<12} | {app_id:<7} | {r[3]:<9} | {app_ref}")

cur.close()
conn.close()
