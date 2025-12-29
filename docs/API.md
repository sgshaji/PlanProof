# PlanProof API Reference

## CLI Commands

### `single-pdf`

Process a single PDF through the full pipeline.

```bash
python main.py single-pdf --pdf <path> [--application-ref <ref>] [--out <file>]
```

**Arguments**:
- `--pdf`: Path to PDF file (required)
- `--application-ref`: Application reference (optional, auto-generated if not provided)
- `--out`: Output JSON file path (optional)

**Returns**: JSON with `run_id`, `document_id`, `blob_urls`, `artefact_ids`, `summary`

### `batch-pdf`

Process all PDFs in a folder.

```bash
python main.py batch-pdf --folder <path> --application-ref <ref> [--out <file>]
```

**Arguments**:
- `--folder`: Path to folder containing PDFs (required)
- `--application-ref`: Application reference (required)
- `--out`: Output JSON file path (optional)

**Returns**: JSON with `run_id`, `total_documents`, `successes`, `failures`, `llm_calls`, `results`

## Python API

### Configuration

```python
from planproof.config import get_settings

settings = get_settings()
# Access: settings.azure_storage_connection_string, etc.
```

### Storage

```python
from planproof.storage import StorageClient

client = StorageClient()

# Upload PDF
blob_uri = client.upload_pdf("path/to/file.pdf")

# Write JSON artefact
url = client.write_json_blob("artefacts", "path/to/artefact.json", data)

# Download blob
data = client.download_blob("container", "blob_name")
```

### Database

```python
from planproof.db import Database

db = Database()

# Create application
app = db.create_application(application_ref="APP/2024/001")

# Create document
doc = db.create_document(
    application_id=app.id,
    blob_uri="azure://...",
    filename="document.pdf",
    content_hash="sha256_hash"
)

# Create run
run = db.create_run(run_type="single_pdf", metadata={...})

# Update run
db.update_run(run_id, status="completed", metadata={...})
```

### Pipeline

```python
from planproof.pipeline import ingest_pdf, extract_document, validate_document
from planproof.pipeline.extract import extract_from_pdf_bytes
from planproof.pipeline.validate import load_rule_catalog, validate_extraction
from planproof.pipeline.field_mapper import map_fields

# Ingest
result = ingest_pdf("path/to/file.pdf", "APP/2024/001")

# Extract
extraction = extract_document(document_id)

# Map fields
mapped = map_fields(extraction["extraction_result"])

# Validate
rules = load_rule_catalog("artefacts/rule_catalog.json")
validation = validate_extraction(mapped, rules)
```

### Document Intelligence

```python
from planproof.docintel import DocumentIntelligence

docintel = DocumentIntelligence()
result = docintel.analyze_document(pdf_bytes, model="prebuilt-layout")
```

### Azure OpenAI

```python
from planproof.aoai import AzureOpenAIClient

client = AzureOpenAIClient()

# Chat with JSON response
response = client.chat_json(payload)

# Resolve field conflict
result = client.resolve_field_conflict(document_id, field_name, extracted_value)
```

## Data Models

### Extraction Result

```python
{
    "fields": {
        "site_address": "4 DURLSTON GROVE",
        "proposed_use": "LOFT WITH CONVERSION...",
        "document_type": "site_plan",
        ...
    },
    "evidence_index": {
        "site_address": [
            {"page": 1, "block_id": "p1b0", "snippet": "4 DURLSTON GROVE"}
        ],
        "text_block_0": {
            "type": "text_block",
            "content": "...",
            "snippet": "...",
            "page_number": 1
        }
    },
    "metadata": {
        "page_count": 12,
        "model": "prebuilt-layout"
    },
    "text_blocks": [...],
    "tables": [...]
}
```

### Validation Result

```python
{
    "summary": {
        "rule_count": 3,
        "pass": 2,
        "needs_review": 1,
        "fail": 0,
        "needs_llm": false
    },
    "findings": [
        {
            "rule_id": "R1",
            "severity": "error",
            "status": "pass",
            "message": "All required fields present.",
            "required_fields": ["site_address"],
            "missing_fields": [],
            "evidence": {
                "expected_sources": ["application_form", "site_plan"],
                "keywords": ["address", "postcode"],
                "evidence_snippets": [...]
            }
        },
        ...
    ]
}
```

### LLM Notes

```python
{
    "triggered": true,
    "gate_reason": {
        "missing_fields": ["site_address"],
        "affected_rule_ids": ["R1"],
        "validation_summary": {...}
    },
    "request": {...},
    "response": {
        "filled_fields": {
            "site_address": "4 DURLSTON GROVE"
        },
        "notes": "...",
        "citations": [...]
    }
}
```

