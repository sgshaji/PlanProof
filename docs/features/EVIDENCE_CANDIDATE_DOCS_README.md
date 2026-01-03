# Evidence and Candidate Documents Feature

## Overview

This feature enhances validation findings with detailed evidence tracking and candidate document management, allowing users to understand what was scanned and confirm or reject mis-classified documents.

## What's New

### 1. Database Schema Changes

Added two new JSON columns to the `validation_checks` table:

- **`evidence_details`**: Stores detailed evidence with page/line references
  ```json
  [
    {
      "page": 1,
      "snippet": "4 DURLSTON GROVE",
      "evidence_key": "site_address_evidence",
      "confidence": 0.95
    }
  ]
  ```

- **`candidate_documents`**: Stores possible documents scanned for each check
  ```json
  [
    {
      "document_id": 123,
      "document_name": "application_form.pdf",
      "confidence": 1.0,
      "reason": "Primary document being validated",
      "scanned": true
    }
  ]
  ```

### 2. Validation Pipeline Updates

The validation pipeline now automatically populates:
- Evidence snippets with page numbers and context
- Candidate documents that were scanned during validation
- Confidence scores for evidence matching

### 3. API Enhancements

The `/api/v1/runs/{run_id}/results` endpoint now returns:

```typescript
{
  "findings": [
    {
      "rule_id": "RULE-001",
      "status": "needs_review",
      "message": "Missing required fields",
      "evidence_details": [
        {
          "page": 1,
          "snippet": "Extract text...",
          "evidence_key": "field_name",
          "confidence": 0.8
        }
      ],
      "candidate_documents": [
        {
          "document_id": 1,
          "document_name": "doc.pdf",
          "confidence": 1.0,
          "reason": "Primary document",
          "scanned": true
        }
      ]
    }
  ]
}
```

### 4. UI Improvements

The Results page now displays:

#### Evidence Section
- **Expandable accordion** showing all evidence items
- **Page numbers** for easy document navigation
- **Evidence snippets** with context
- **Confidence scores** when available
- **Evidence keys** for technical reference

#### Candidate Documents Section
- **Document list** showing what was scanned
- **Confidence indicators** for document relevance
- **Reason descriptions** explaining why documents were selected
- **Interactive buttons**:
  - 👍 **Confirm** - Mark document as correct
  - 👎 **Reject** - Mark document as incorrect
- **Visual indicators** for scanned vs. unscanned documents

## Usage

### For Planning Officers

1. **View Results**: Navigate to a run's results page
2. **Expand Evidence**: Click on "Evidence (X items)" to see details
3. **Review Documents**: Click on "Scanned Documents" to see what was analyzed
4. **Confirm/Reject**: Use thumbs up/down buttons to classify documents
5. **Navigate**: Use page numbers to find evidence in original PDFs

### For Developers

#### Query Evidence Details

```python
from planproof.db import Database, ValidationCheck

db = Database()
session = db.get_session()

check = session.query(ValidationCheck).filter(
    ValidationCheck.id == check_id
).first()

# Access evidence details
for evidence in check.evidence_details:
    print(f"Page {evidence['page']}: {evidence['snippet']}")

# Access candidate documents
for doc in check.candidate_documents:
    print(f"{doc['document_name']} - Confidence: {doc['confidence']}")
```

#### Update Validation Logic

When creating ValidationChecks, populate the new fields:

```python
validation_check = ValidationCheck(
    submission_id=submission_id,
    document_id=document_id,
    rule_id_string=rule.rule_id,
    status=check_status,
    explanation=finding["message"],
    evidence_ids=evidence_ids,
    evidence_details=[
        {
            "page": 1,
            "snippet": "Evidence text...",
            "evidence_key": "field_name"
        }
    ],
    candidate_documents=[
        {
            "document_id": doc.id,
            "document_name": doc.filename,
            "confidence": 1.0,
            "reason": "Primary document",
            "scanned": True
        }
    ]
)
```

## Installation

### 1. Apply Database Migration

```bash
# Navigate to project root
cd "d:\Aathira Docs\PlanProof"

# Run migration
alembic upgrade head
```

### 2. Verify Migration

```bash
# Check that columns were added
psql -h <host> -U <user> -d planning_validation -c "
  SELECT column_name, data_type 
  FROM information_schema.columns 
  WHERE table_name = 'validation_checks' 
  AND column_name IN ('evidence_details', 'candidate_documents');
"
```

### 3. Restart Services

```bash
# Restart API
python run_api.py

# Restart Frontend (in separate terminal)
cd frontend
npm run dev
```

## Testing

Run the test script to verify the implementation:

```bash
python test_evidence_candidate_docs.py
```

Expected output:
```
✅ Database Schema ...................... PASSED
✅ API Response Structure ............... PASSED
✅ Validation Pipeline .................. PASSED

🎉 All tests passed!
```

## Architecture

### Data Flow

```
PDF Upload
    ↓
Document Intelligence (Extract)
    ↓
Evidence Table (Store page/snippets)
    ↓
Validation (Check rules)
    ↓
ValidationCheck (Store evidence_details + candidate_documents)
    ↓
API Endpoint (Fetch and return)
    ↓
Frontend (Display with UI controls)
```

### Database Relationships

```sql
validation_checks
├── evidence_ids: JSON[]        -- References evidence.id
├── evidence_details: JSON[]    -- Denormalized evidence data
└── candidate_documents: JSON[] -- Documents scanned during validation

evidence
├── document_id → documents.id
├── page_id → pages.id
└── page_number, snippet, bbox, confidence
```

## Benefits

1. **Transparency**: Users can see exactly what evidence was found
2. **Auditability**: Page references allow verification of findings
3. **Accuracy**: Document confirmation helps improve future validations
4. **Debugging**: Developers can trace validation logic
5. **Compliance**: Evidence trails support regulatory requirements

## Future Enhancements

- [ ] Store user confirmations/rejections in database
- [ ] Use feedback to improve document classification
- [ ] Add PDF viewer with highlighted evidence
- [ ] Support line-level references (not just page)
- [ ] Add bulk confirm/reject operations
- [ ] Export evidence summary to PDF report

## Troubleshooting

### Evidence Not Showing

1. Check that validation pipeline is writing evidence_details:
   ```python
   # In validate.py, ensure evidence_details is populated
   evidence_details = [...]
   validation_check = ValidationCheck(..., evidence_details=evidence_details)
   ```

2. Verify database migration was applied:
   ```sql
   SELECT evidence_details FROM validation_checks LIMIT 1;
   ```

### Candidate Documents Empty

Ensure documents are being linked during validation:
```python
# In validate.py
candidate_documents = [{
    "document_id": doc.id,
    "document_name": doc.filename,
    ...
}]
```

### UI Not Displaying

1. Clear browser cache
2. Check frontend console for errors
3. Verify API response includes new fields:
   ```bash
   curl http://localhost:8000/api/v1/runs/{run_id}/results
   ```

## Files Changed

### Backend
- `planproof/db.py` - Added columns to ValidationCheck model
- `planproof/pipeline/validate.py` - Populate evidence and candidate docs
- `planproof/api/routes/validation.py` - Return new fields in API
- `alembic/versions/8a4b5c6d7e8f_add_evidence_candidate_docs.py` - Migration

### Frontend
- `frontend/src/pages/Results.tsx` - Display evidence and candidate documents

### Testing
- `test_evidence_candidate_docs.py` - Verification script

## Support

For questions or issues:
1. Check the [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) guide
2. Review test output: `python test_evidence_candidate_docs.py`
3. Check API logs for validation pipeline errors
4. Verify database schema matches model definitions
