"""
Add content_hash column to documents table for deduplication.
Run this once to add the column to existing database.
"""
import os
from dotenv import load_dotenv
import psycopg

load_dotenv()

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        # Check if column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='documents' AND column_name='content_hash'
        """)
        exists = cur.fetchone()
        
        if exists:
            print("Column 'content_hash' already exists")
        else:
            # Add column
            cur.execute("""
                ALTER TABLE documents 
                ADD COLUMN content_hash VARCHAR(64) UNIQUE
            """)
            conn.commit()
            print("Added 'content_hash' column to documents table")
            
            # Create index
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_content_hash 
                ON documents(content_hash)
            """)
            conn.commit()
            print("Created index on content_hash")

