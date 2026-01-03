"""
Check a specific document and its artefacts.
"""
import os
import sys
import psycopg
from dotenv import load_dotenv

load_dotenv()

if len(sys.argv) < 2:
    print("Usage: python scripts/check_document.py <document_id>")
    sys.exit(1)

doc_id = int(sys.argv[1])

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        # Get document
        cur.execute("""
            SELECT id, application_id, filename, blob_uri, page_count, processed_at 
            FROM documents 
            WHERE id=%s
        """, (doc_id,))
        doc = cur.fetchone()
        
        if not doc:
            print(f"ERROR: Document {doc_id} not found")
            sys.exit(1)
        
        print(f"Document {doc_id}:")
        print(f"  Application ID: {doc[1]}")
        print(f"  Filename: {doc[2]}")
        print(f"  Blob URI: {doc[3]}")
        print(f"  Page Count: {doc[4]}")
        print(f"  Processed At: {doc[5]}")
        
        # Get artefacts
        cur.execute("""
            SELECT id, artefact_type, blob_uri, created_at, artefact_metadata
            FROM artefacts 
            WHERE document_id=%s 
            ORDER BY created_at
        """, (doc_id,))
        arts = cur.fetchall()
        
        print(f"\nArtefacts ({len(arts)}):")
        for a in arts:
            print(f"  ID: {a[0]}, Type: {a[1]}, Created: {a[3]}")
            print(f"    Blob URI: {a[2]}")
            if a[4]:
                print(f"    Metadata: {a[4]}")

