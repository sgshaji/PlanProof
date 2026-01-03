"""
Check artefacts in Azure Blob Storage.
"""
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
if not connection_string:
    print("ERROR: AZURE_STORAGE_CONNECTION_STRING not found in .env")
    exit(1)

client = BlobServiceClient.from_connection_string(connection_string)
container_name = "artefacts"

print(f"Checking artefacts in container '{container_name}'...")
print("=" * 60)

# List all blobs with prefix "runs/"
container_client = client.get_container_client(container_name)
blobs = container_client.list_blobs(name_starts_with="runs/")

blob_list = list(blobs)
print(f"\nFound {len(blob_list)} artefact(s) in runs/")
print("-" * 60)

for blob in blob_list:
    print(f"Name: {blob.name}")
    print(f"  Size: {blob.size} bytes")
    print(f"  Last Modified: {blob.last_modified}")
    print()

# Also check for extracted_layout artefacts
print("\nChecking for extracted_layout artefacts...")
print("-" * 60)
extracted_blobs = container_client.list_blobs(name_starts_with="extracted_layout_")
extracted_list = list(extracted_blobs)
print(f"Found {len(extracted_list)} extracted_layout artefact(s)")
for blob in extracted_list[:5]:  # Show first 5
    print(f"  {blob.name} ({blob.size} bytes)")

