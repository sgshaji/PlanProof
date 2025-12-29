# PlanProof

A hybrid AI-rules validation system for planning applications that combines deterministic field extraction with gated LLM resolution for missing or ambiguous data.

## Overview

PlanProof processes planning application documents through a multi-stage pipeline:

1. **Ingest**: Upload PDFs to Azure Blob Storage with content hash deduplication
2. **Extract**: Use Azure Document Intelligence to extract text, tables, and layout
3. **Map Fields**: Deterministic extraction of structured fields (address, proposal, etc.)
4. **Validate**: Apply rule-based validation against extracted fields
5. **LLM Gate**: Conditionally use Azure OpenAI to resolve missing fields only when necessary

### Key Features

- **Deterministic-first design**: Fields extracted using regex and heuristics before AI
- **Evidence-linked validation**: Every field includes page numbers and text snippets
- **Document-type awareness**: Different extraction rules for application forms vs. plan sheets
- **Field ownership**: LLM only triggered for fields extractable from specific document types
- **Cost-efficient**: LLM calls reduced by 80%+ through smart gating
- **Auditable**: Complete traceability with run tracking and evidence pointers

## Architecture

```
┌─────────────┐
│   PDFs      │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Ingest    │────▶│   Extract    │────▶│ Field Mapper│
│ (Blob + DB) │     │ (DocIntel)  │     │ (Determin.) │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                 │
                                                 ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Validate  │◀────│  Evidence    │     │  LLM Gate   │
│  (Rules)    │     │   Index      │     │ (Conditional)│
└──────┬──────┘     └──────────────┘     └─────────────┘
       │
       ▼
┌─────────────┐
│  Results    │
│ (JSON + DB) │
└─────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- Azure account with:
  - Blob Storage
  - PostgreSQL Flexible Server (with PostGIS)
  - Azure OpenAI
  - Document Intelligence

### Installation

1. Clone the repository:
```bash
git clone https://github.com/AathiraTD/PlanProof.git
cd PlanProof
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables (create `.env` file):
```env
# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=...

# Database
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT_NAME=...

# Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=...
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=...
```

4. Set up database:
```bash
python scripts/enable_postgis.py
python scripts/add_content_hash_column.py
```

5. Build rule catalog:
```bash
python scripts/build_rule_catalog.py
```

### Usage

#### Process a single PDF:
```bash
python main.py single-pdf --pdf "path/to/document.pdf" --application-ref "APP/2024/001"
```

#### Process a folder of PDFs:
```bash
python main.py batch-pdf --folder "path/to/folder" --application-ref "APP/2024/001"
```

#### Check results:
```bash
# List recent runs
python scripts/list_runs.py

# Check a specific run
python scripts/check_run.py <run_id>

# Analyze batch results
python scripts/analyze_batch.py batch_results.json
```

## Project Structure

```
PlanProof/
├── planproof/              # Main package
│   ├── config.py           # Configuration management
│   ├── storage.py          # Azure Blob Storage helpers
│   ├── db.py               # Database models and helpers
│   ├── docintel.py         # Document Intelligence wrapper
│   ├── aoai.py             # Azure OpenAI wrapper
│   ├── pipeline/           # Processing pipeline
│   │   ├── ingest.py       # PDF ingestion
│   │   ├── extract.py      # Document extraction
│   │   ├── field_mapper.py # Deterministic field extraction
│   │   ├── validate.py     # Rule-based validation
│   │   └── llm_gate.py     # LLM resolution gating
│   └── rules/              # Rule catalog
│       └── catalog.py      # Rule parser
├── scripts/                # Utility scripts
│   ├── build_rule_catalog.py
│   ├── analyze_batch.py
│   ├── check_*.py          # Various check scripts
│   └── ...
├── artefacts/              # Generated artefacts
│   └── rule_catalog.json   # Parsed validation rules
├── main.py                 # CLI entry point
├── validation_requirements.md  # Source of truth for rules
└── requirements.txt        # Python dependencies
```

## Validation Rules

Rules are defined in `validation_requirements.md` and parsed into `artefacts/rule_catalog.json`.

Each rule specifies:
- **Required fields**: Fields that must be present
- **Evidence sources**: Document types where evidence can be found
- **Severity**: `error` (blocks) or `warning` (informational)
- **Keywords**: Optional hints for extraction

Example rule:
```markdown
RULE-1: Site Address Validation

Required fields: site_address
Evidence: application_form, site_plan
Keywords: address, postcode, location
Severity: error
```

## Field Extraction

The field mapper uses multiple strategies:

1. **Regex patterns**: Application references, postcodes, emails, phones
2. **Heuristics**: Address-like patterns, proposal sentences
3. **Label extraction**: "Site Address: ..." patterns
4. **Document classification**: Different rules for different doc types

Extracted fields include evidence pointers:
```json
{
  "site_address": "4 DURLSTON GROVE",
  "evidence_index": {
    "site_address": [
      {
        "page": 1,
        "block_id": "p1b0",
        "snippet": "4 DURLSTON GROVE"
      }
    ]
  }
}
```

## LLM Gating Logic

LLM is only triggered when:
- Missing field has `error` severity (not `warning`)
- Field is extractable from the document type (field ownership)
- Document has sufficient text coverage
- Field hasn't already been resolved in this run

This reduces LLM calls by 80%+ while maintaining accuracy.

## Database Schema

- **applications**: Planning application records
- **documents**: PDF documents with content hash for deduplication
- **artefacts**: Extracted JSON artefacts (extraction, validation, LLM notes)
- **runs**: Processing run audit trail
- **validation_results**: (Optional) Detailed validation results

## Development

### Running Tests

```bash
# Smoke test Azure connections
python scripts/smoke_test.py

# Verify blob storage
python scripts/check_blobs.py

# Check database
python scripts/check_db.py
```

### Adding New Fields

1. Add extraction logic to `planproof/pipeline/field_mapper.py`
2. Update validation rules in `validation_requirements.md`
3. Rebuild catalog: `python scripts/build_rule_catalog.py`

### Adding New Rules

1. Edit `validation_requirements.md` following the existing format
2. Rebuild catalog: `python scripts/build_rule_catalog.py`
3. Rules are automatically loaded during validation

## Performance Metrics

Typical batch processing results:
- **Field extraction**: 70-90% of fields extracted deterministically
- **LLM call rate**: 10-20% of documents (vs. 100% without gating)
- **Validation pass rate**: 60-80% of rules pass without LLM
- **Processing time**: ~5-10 seconds per document

## Limitations & Future Work

- **Field extraction**: Currently supports 10 core fields; can be extended
- **Document types**: Supports 6 document types; more can be added
- **Rule complexity**: Currently supports simple field presence rules
- **Multi-document**: Field cache works within a run; could be extended to application-level

## License

[Add your license here]

## Contributing

[Add contribution guidelines if applicable]

## Contact

[Add contact information]

