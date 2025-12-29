# PlanProof Architecture

## System Overview

PlanProof implements a **hybrid AI-rules validation system** that prioritizes deterministic extraction over AI, using LLM only as a fallback for missing or ambiguous fields.

## Core Principles

1. **Deterministic-first**: Extract fields using regex, heuristics, and pattern matching before AI
2. **Evidence-linked**: Every extracted field includes page numbers and text snippets
3. **Document-aware**: Different extraction strategies for different document types
4. **Gated AI**: LLM only triggered when necessary and appropriate
5. **Auditable**: Complete traceability through run tracking and evidence pointers

## Pipeline Stages

### 1. Ingestion (`planproof/pipeline/ingest.py`)

**Purpose**: Upload PDFs to blob storage and create database records

**Key Features**:
- Content hash (SHA256) computation for deduplication
- Automatic application creation/linking
- Blob storage with unique URIs

**Output**: Document record with `document_id`, `blob_uri`, `content_hash`

### 2. Extraction (`planproof/pipeline/extract.py`)

**Purpose**: Use Azure Document Intelligence to extract raw text and layout

**Key Features**:
- Layout analysis (text blocks, tables, page anchors)
- Metadata extraction (page count, model used)
- Artefact storage for auditability

**Output**: Raw extraction result with `text_blocks`, `tables`, `metadata`

### 3. Field Mapping (`planproof/pipeline/field_mapper.py`)

**Purpose**: Extract structured fields from raw extraction

**Strategies**:
1. **Regex patterns**: Application refs, postcodes, emails, phones
2. **Heuristics**: Address patterns, proposal sentences
3. **Label extraction**: "Site Address: ..." patterns
4. **Document classification**: Type-specific rules

**Output**: Structured `fields` dict with `evidence_index`

### 4. Validation (`planproof/pipeline/validate.py`)

**Purpose**: Apply rule-based validation against extracted fields

**Process**:
1. Load rule catalog from JSON
2. Check required fields for each rule
3. Generate findings (pass/needs_review/fail)
4. Determine if LLM gate should trigger

**Output**: Validation results with findings and summary

### 5. LLM Gating (`planproof/pipeline/llm_gate.py`)

**Purpose**: Conditionally use AI to resolve missing fields

**Trigger Conditions** (all must be true):
- Missing field has `error` severity (not `warning`)
- Field is extractable from document type (field ownership)
- Document has sufficient text coverage
- Field hasn't been resolved in this run

**Output**: LLM notes with filled fields and citations (if triggered)

## Data Flow

```
PDF → Ingest → Extract → Field Mapper → Validate → [LLM Gate] → Results
       ↓         ↓           ↓             ↓            ↓
     Blob      DocIntel   Evidence      Rules       AOAI
     Storage   Layout     Index         Catalog
```

## Field Ownership

Different document types can extract different fields:

| Document Type | Extractable Fields |
|--------------|-------------------|
| `application_form` | All fields (application_ref, site_address, proposed_use, etc.) |
| `site_plan` | site_address, proposed_use |
| `drawing` | proposed_use |
| `design_statement` | proposed_use, site_address |
| `unknown` | site_address, proposed_use (fallback) |

This prevents false negatives (e.g., not expecting `application_ref` on plan sheets).

## Evidence Tracking

Every extracted field includes evidence:
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

This enables:
- **Auditability**: Trace back to source
- **Explainability**: Show why field was extracted
- **Defensibility**: Support validation decisions

## Run Tracking

Every processing operation creates a `run` record:
- **Run type**: `single_pdf` or `batch_pdf`
- **Metadata**: Parameters, resolved fields cache
- **Status**: `running`, `completed`, `completed_with_errors`, `failed`
- **Summary**: Success/failure counts, errors

This provides:
- **Audit trail**: Who processed what, when
- **Field caching**: Resolved fields shared across documents in a run
- **Error tracking**: Failures logged with context

## Cost Optimization

LLM gating reduces costs by:
1. **Field ownership**: Don't ask for fields that can't be extracted
2. **Severity filtering**: Only errors trigger LLM, not warnings
3. **Field caching**: Resolved fields reused within a run
4. **Document type awareness**: Only suitable docs trigger LLM

Typical reduction: **80%+ fewer LLM calls** vs. naive approach.

## Extensibility

### Adding New Fields

1. Add extraction logic to `field_mapper.py`
2. Update `DOC_FIELD_OWNERSHIP` if needed
3. Add to validation rules

### Adding New Document Types

1. Add classification hints to `DOC_TYPE_HINTS`
2. Update `DOC_FIELD_OWNERSHIP` with extractable fields
3. Test with sample documents

### Adding New Rules

1. Edit `validation_requirements.md`
2. Run `scripts/build_rule_catalog.py`
3. Rules automatically loaded

## Security Considerations

- **Environment variables**: All secrets in `.env` (not committed)
- **Content hashing**: Deduplication without storing full content
- **Blob URIs**: Signed URIs for access control
- **Database**: Parameterized queries prevent SQL injection
- **API keys**: Never logged or exposed

## Performance Considerations

- **Batch processing**: Documents processed sequentially (can be parallelized)
- **Caching**: Field cache reduces redundant LLM calls
- **Deduplication**: Content hash prevents reprocessing
- **Artefact storage**: JSON artefacts stored in blob (not DB) for scalability

