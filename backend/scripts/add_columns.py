#!/usr/bin/env python3
"""Add missing columns to database tables."""
import psycopg
from planproof.config import get_settings

settings = get_settings()

# Parse the database URL to get connection parameters
db_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

print(f"Connecting to database...")
conn = psycopg.connect(db_url)
cursor = conn.cursor()

try:
    print("Adding site_address column to applications...")
    cursor.execute("ALTER TABLE applications ADD COLUMN IF NOT EXISTS site_address TEXT")
    
    print("Adding proposal_description column to applications...")
    cursor.execute("ALTER TABLE applications ADD COLUMN IF NOT EXISTS proposal_description TEXT")
    
    print("Adding application_type column to submissions...")
    cursor.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS application_type VARCHAR(50)")
    
    print("Adding evidence_details column to validation_checks...")
    cursor.execute("ALTER TABLE validation_checks ADD COLUMN IF NOT EXISTS evidence_details JSON")
    
    print("Adding candidate_documents column to validation_checks...")
    cursor.execute("ALTER TABLE validation_checks ADD COLUMN IF NOT EXISTS candidate_documents JSON")
    
    print("Creating run_documents table if not exists...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS run_documents (
            run_id INTEGER NOT NULL,
            document_id INTEGER NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            PRIMARY KEY (run_id, document_id),
            FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_run_documents_run_id ON run_documents(run_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_run_documents_document_id ON run_documents(document_id)")
    
    conn.commit()
    print("✓ Successfully added all missing columns and tables")
    
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()
