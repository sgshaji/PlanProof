"""
Check run and artefact records in the database.
"""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

# Get run_id from environment or command line
import sys
if len(sys.argv) > 1:
    run_id = sys.argv[1]
else:
    run_id = os.environ.get("RUN_ID")

if not run_id:
    print("Usage: python scripts/check_run.py <run_id>")
    print("   OR: RUN_ID=<run_id> python scripts/check_run.py")
    sys.exit(1)

try:
    run_id = int(run_id)
except ValueError:
    print(f"ERROR: Run ID must be an integer, got: {run_id}")
    sys.exit(1)

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        # Check run
        cur.execute("SELECT id, run_type, document_id, application_id, started_at, status FROM runs WHERE id=%s", (run_id,))
        run_row = cur.fetchone()
        if run_row:
            print(f"Run {run_id}:")
            print(f"  Type: {run_row[1]}")
            print(f"  Document ID: {run_row[2]}")
            print(f"  Application ID: {run_row[3]}")
            print(f"  Started: {run_row[4]}")
            print(f"  Status: {run_row[5]}")
        else:
            print(f"ERROR: Run {run_id} not found")
            sys.exit(1)

        # Get document_id from run
        document_id = run_row[2]
        
        if document_id:
            # Check artefacts for this document
            cur.execute("""
                SELECT id, artefact_type, blob_uri, created_at 
                FROM artefacts 
                WHERE document_id=%s 
                ORDER BY created_at
            """, (document_id,))
            artefact_rows = cur.fetchall()
            print(f"\nArtefacts for document {document_id}: {len(artefact_rows)}")
            for r in artefact_rows:
                print(f"  ID: {r[0]}, Type: {r[1]}, Created: {r[3]}")
                print(f"    Blob URI: {r[2]}")
        else:
            print("\nNo document_id linked to this run")

        # Also check all documents for the application
        application_id = run_row[3]
        if application_id:
            cur.execute("""
                SELECT id, filename, blob_uri, uploaded_at 
                FROM documents 
                WHERE application_id=%s 
                ORDER BY uploaded_at
            """, (application_id,))
            doc_rows = cur.fetchall()
            print(f"\nDocuments for application {application_id}: {len(doc_rows)}")
            for r in doc_rows:
                print(f"  Doc ID: {r[0]}, File: {r[1]}, Uploaded: {r[3]}")

