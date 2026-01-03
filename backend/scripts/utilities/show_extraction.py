"""
Show first 30 text blocks from an extracted layout artefact.
"""
import sys
import json
from planproof.storage import StorageClient

if len(sys.argv) < 2:
    print("Usage: python scripts/show_extraction.py <document_id>")
    sys.exit(1)

doc_id = int(sys.argv[1])

# Get artefact URI from DB
from planproof.db import Database
db = Database()
session = db.get_session()
try:
    from planproof.db import Artefact
    artefact = session.query(Artefact).filter(
        Artefact.document_id == doc_id,
        Artefact.artefact_type == "extracted_layout"
    ).order_by(Artefact.created_at.desc()).first()
    
    if not artefact:
        print(f"No extracted_layout artefact found for document {doc_id}")
        sys.exit(1)
    
    blob_uri = artefact.blob_uri
    print(f"Artefact URI: {blob_uri}\n")
finally:
    session.close()

# Download and parse
sc = StorageClient()
parts = blob_uri.replace("azure://", "").split("/", 2)
container = parts[1]
blob_name = parts[2]

data = sc.download_blob(container, blob_name)
result = json.loads(data.decode("utf-8"))

blocks = result.get("text_blocks", [])[:30]

print("=" * 80)
print(f"First 30 text blocks from document {doc_id}:")
print("=" * 80)
print()

for i, block in enumerate(blocks, 1):
    content = block.get("content", "")
    page_num = block.get("page_number", "N/A")
    preview = content[:100] + "..." if len(content) > 100 else content
    print(f"Block {i:2d} (Page {page_num}): {preview}")

