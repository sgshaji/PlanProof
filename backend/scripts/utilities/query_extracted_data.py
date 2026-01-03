"""Query extracted data from artefacts table."""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        print("=" * 70)
        print("EXTRACTED DATA - Artefacts Table")
        print("=" * 70)
        print("\nArtefact Types and Counts:")
        print("-" * 70)
        
        # Count by type
        cur.execute("""
            SELECT artefact_type, COUNT(*) as count
            FROM artefacts
            GROUP BY artefact_type
            ORDER BY count DESC
        """)
        types = cur.fetchall()
        for t in types:
            print(f"  {t[0]}: {t[1]} artefact(s)")
        
        print("\n" + "=" * 70)
        print("Recent Extracted Layout Artefacts (contains raw extraction data):")
        print("-" * 70)
        
        # Show recent extracted_layout artefacts
        cur.execute("""
            SELECT 
                a.id,
                a.document_id,
                d.filename,
                a.artefact_type,
                a.created_at,
                a.blob_uri,
                a.artefact_metadata->>'model' as model,
                a.artefact_metadata->>'extracted_at' as extracted_at
            FROM artefacts a
            JOIN documents d ON a.document_id = d.id
            WHERE a.artefact_type = 'extracted_layout'
            ORDER BY a.created_at DESC
            LIMIT 5
        """)
        layouts = cur.fetchall()
        for l in layouts:
            print(f"\n  Artefact ID: {l[0]}")
            print(f"  Document: {l[2]} (ID: {l[1]})")
            print(f"  Type: {l[3]}")
            print(f"  Created: {l[4]}")
            print(f"  Model: {l[6]}")
            print(f"  Blob URI: {l[5][:80]}...")
        
        print("\n" + "=" * 70)
        print("Extraction Artefacts (contains mapped fields + evidence):")
        print("-" * 70)
        
        # Show extraction artefacts (with fields)
        cur.execute("""
            SELECT 
                a.id,
                a.document_id,
                d.filename,
                a.artefact_type,
                a.created_at,
                a.blob_uri
            FROM artefacts a
            JOIN documents d ON a.document_id = d.id
            WHERE a.artefact_type = 'extraction'
            ORDER BY a.created_at DESC
            LIMIT 5
        """)
        extractions = cur.fetchall()
        for e in extractions:
            print(f"\n  Artefact ID: {e[0]}")
            print(f"  Document: {e[2]} (ID: {e[1]})")
            print(f"  Created: {e[4]}")
            print(f"  Blob URI: {e[5][:80]}...")
        
        print("\n" + "=" * 70)
        print("Validation Artefacts (contains validation results):")
        print("-" * 70)
        
        # Show validation artefacts
        cur.execute("""
            SELECT 
                a.id,
                a.document_id,
                d.filename,
                a.created_at,
                a.blob_uri
            FROM artefacts a
            JOIN documents d ON a.document_id = d.id
            WHERE a.artefact_type = 'validation'
            ORDER BY a.created_at DESC
            LIMIT 5
        """)
        validations = cur.fetchall()
        for v in validations:
            print(f"\n  Artefact ID: {v[0]}")
            print(f"  Document: {v[2]} (ID: {v[1]})")
            print(f"  Created: {v[3]}")
            print(f"  Blob URI: {v[4][:80]}...")

