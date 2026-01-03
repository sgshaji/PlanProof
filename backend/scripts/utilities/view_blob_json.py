"""View the contents of a blob JSON file."""
import sys
import json
from planproof.storage import StorageClient

if len(sys.argv) < 2:
    print("Usage: python scripts/view_blob_json.py <blob_uri>")
    print("Example: python scripts/view_blob_json.py azure://planproofdevstg86723/artefacts/extracted_layout_79_20251230_034328.json")
    sys.exit(1)

blob_uri = sys.argv[1]

# Parse blob URI: azure://account/container/blob_name
parts = blob_uri.replace("azure://", "").split("/", 2)
if len(parts) != 3:
    print(f"ERROR: Invalid blob URI format: {blob_uri}")
    print("Expected format: azure://account/container/blob_name")
    sys.exit(1)

account = parts[0]
container = parts[1]
blob_name = parts[2]

print("=" * 70)
print("BLOB JSON VIEWER")
print("=" * 70)
print(f"Blob URI: {blob_uri}")
print(f"Container: {container}")
print(f"Blob Name: {blob_name}")
print()

sc = StorageClient()
try:
    data = sc.download_blob(container, blob_name)
    result = json.loads(data.decode("utf-8"))
    
    print(f"File Size: {len(data):,} bytes")
    print()
    
    # Show metadata
    if "metadata" in result:
        print("Metadata:")
        print("-" * 70)
        for key, value in result["metadata"].items():
            print(f"  {key}: {value}")
        print()
    
    # Show text blocks summary
    text_blocks = result.get("text_blocks", [])
    print(f"Text Blocks: {len(text_blocks)}")
    if text_blocks:
        print("First 5 text blocks:")
        print("-" * 70)
        for i, block in enumerate(text_blocks[:5], 1):
            content = block.get("content", "")
            page = block.get("page_number", "N/A")
            preview = content[:100] + "..." if len(content) > 100 else content
            print(f"  Block {i} (Page {page}): {preview}")
        print()
    
    # Show tables summary
    tables = result.get("tables", [])
    print(f"Tables: {len(tables)}")
    if tables:
        print("Table details:")
        print("-" * 70)
        for i, table in enumerate(tables[:3], 1):
            print(f"  Table {i}: {table.get('row_count', 0)} rows × {table.get('column_count', 0)} cols (Page {table.get('page_number', 'N/A')})")
        print()
    
    # Show fields if present (for extraction artefacts)
    if "fields" in result:
        print("Extracted Fields:")
        print("-" * 70)
        for key, value in result["fields"].items():
            print(f"  {key}: {value}")
        print()
    
    # Show evidence_index if present
    if "evidence_index" in result:
        print("Evidence Index:")
        print("-" * 70)
        ev_keys = list(result["evidence_index"].keys())
        print(f"  Evidence keys: {len(ev_keys)}")
        if ev_keys:
            print(f"  Sample keys: {', '.join(ev_keys[:5])}")
        print()
    
    # Option to save full JSON
    print("=" * 70)
    print("To view full JSON, run:")
    print(f"  python -c \"from planproof.storage import StorageClient; import json; sc = StorageClient(); data = sc.download_blob('{container}', '{blob_name}'); print(json.dumps(json.loads(data.decode('utf-8')), indent=2))\"")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

