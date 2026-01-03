"""Show detailed document processing information."""
import sys
from planproof.db import Database

if len(sys.argv) < 2:
    print("Usage: python scripts/show_document_details.py <document_id> [document_id2 ...]")
    sys.exit(1)

doc_ids = [int(x) for x in sys.argv[1:]]

db = Database()
session = db.get_session()

try:
    from planproof.db import Document
    docs = session.query(Document).filter(Document.id.in_(doc_ids)).all()
    
    print("Document Processing Details:")
    print("=" * 70)
    
    for d in docs:
        print(f"\nDocument {d.id}: {d.filename}")
        print(f"  Application ID: {d.application_id}")
        print(f"  Page Count: {d.page_count}")
        print(f"  Document Intelligence Model: {d.docintel_model}")
        print(f"  Processed At: {d.processed_at}")
        print(f"  Uploaded At: {d.uploaded_at}")
        print(f"  Content Hash: {d.content_hash[:20] if d.content_hash else 'None'}...")
        print(f"  Blob URI: {d.blob_uri[:80]}...")
finally:
    session.close()

