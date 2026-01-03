"""
Check database records - applications, documents, and artefacts.
"""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        # Check applications
        cur.execute("SELECT COUNT(*) FROM applications")
        app_count = cur.fetchone()[0]
        print(f"Applications: {app_count}")
        
        if app_count > 0:
            cur.execute("SELECT id, application_ref, applicant_name FROM applications ORDER BY id DESC LIMIT 5")
            apps = cur.fetchall()
            print("  Recent applications:")
            for a in apps:
                print(f"    ID: {a[0]}, Ref: {a[1]}, Applicant: {a[2]}")
        
        # Check documents
        cur.execute("SELECT COUNT(*) FROM documents")
        doc_count = cur.fetchone()[0]
        print(f"\nDocuments: {doc_count}")
        
        if doc_count > 0:
            cur.execute("SELECT id, application_id, filename, blob_uri FROM documents ORDER BY id DESC LIMIT 5")
            docs = cur.fetchall()
            print("  Recent documents:")
            for d in docs:
                print(f"    ID: {d[0]}, App ID: {d[1]}, File: {d[2]}")
                print(f"      Blob: {d[3][:80]}...")
        
        # Check artefacts
        cur.execute("SELECT COUNT(*) FROM artefacts")
        art_count = cur.fetchone()[0]
        print(f"\nArtefacts: {art_count}")
        
        if art_count > 0:
            cur.execute("""
                SELECT id, document_id, artefact_type, blob_uri, created_at 
                FROM artefacts 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            arts = cur.fetchall()
            print("  Recent artefacts:")
            for a in arts:
                print(f"    ID: {a[0]}, Doc ID: {a[1]}, Type: {a[2]}, Created: {a[4]}")
                print(f"      Blob: {a[3][:80]}...")
        
        # Check runs
        cur.execute("SELECT COUNT(*) FROM runs")
        run_count = cur.fetchone()[0]
        print(f"\nRuns: {run_count}")

