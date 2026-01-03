"""
Verify a blob artefact exists and is readable.
"""
import os
import sys
import json
from dotenv import load_dotenv
from planproof.storage import StorageClient

load_dotenv()

if len(sys.argv) < 2:
    print("Usage: python scripts/verify_blob.py <blob_uri>")
    sys.exit(1)

blob_uri = sys.argv[1]

# Parse blob URI: azure://account/container/blob_name
parts = blob_uri.replace("azure://", "").split("/", 2)
if len(parts) != 3:
    print(f"ERROR: Invalid blob URI format: {blob_uri}")
    sys.exit(1)

container = parts[1]
blob_name = parts[2]

sc = StorageClient()
data = sc.download_blob(container, blob_name)
result = json.loads(data.decode("utf-8"))

print(f"OK: Artefact downloaded from {blob_uri}")
print(f"  Size: {len(data)} bytes")
print(f"  Pages: {result.get('metadata', {}).get('page_count', 'N/A')}")
print(f"  Text blocks: {len(result.get('text_blocks', []))}")
print(f"  Tables: {len(result.get('tables', []))}")

