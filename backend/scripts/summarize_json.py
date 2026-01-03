"""Summarize a JSON file."""
import sys
import json

if len(sys.argv) < 2:
    print("Usage: python scripts/summarize_json.py <json_file>")
    sys.exit(1)

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)

print("JSON File Summary:")
print("=" * 70)
print(f"File: {sys.argv[1]}")

if "metadata" in data:
    meta = data["metadata"]
    print(f"Pages: {meta.get('page_count', 'N/A')}")
    print(f"Model: {meta.get('model', 'N/A')}")

text_blocks = data.get("text_blocks", [])
tables = data.get("tables", [])
print(f"Text Blocks: {len(text_blocks)}")
print(f"Tables: {len(tables)}")

if "fields" in data:
    print(f"\nExtracted Fields: {len(data['fields'])}")
    for key, value in data["fields"].items():
        print(f"  {key}: {value}")

print(f"\nFirst 10 Text Blocks:")
print("-" * 70)
for i, block in enumerate(text_blocks[:10], 1):
    content = block.get("content", "")
    page = block.get("page_number", "?")
    preview = content[:70] + "..." if len(content) > 70 else content
    print(f"{i:2d}. Page {page}: {preview}")

