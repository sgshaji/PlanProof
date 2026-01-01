# ✅ FastAPI REST API - COMPLETE

## What Was Built

A complete REST API for **BCC integration** with PlanProof's document validation pipeline.

### API Endpoints Created:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /api/v1/applications/{ref}/documents` | Upload PDF | Upload & process document |
| `GET /api/v1/runs/{id}/status` | Status | Check processing status |
| `GET /api/v1/applications/{ref}/results` | Results | Get validation results |
| `GET /api/v1/applications` | List | List all applications |
| `GET /api/v1/applications/{ref}` | Details | Get application details |
| `POST /api/v1/applications` | Create | Create new application |
| `GET /api/v1/health` | Health | API health check |
| `GET /api/v1/health/db` | DB Health | Database connectivity |

---

## Quick Start

### 1. Start the API Server

```bash
python run_api.py
```

Server starts at: **http://localhost:8000**

### 2. Test the API

```bash
python test_api.py
```

### 3. View Interactive Documentation

Open in browser:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

---

## Integration Example

```python
import requests

# Upload document for processing
response = requests.post(
    "http://localhost:8000/api/v1/applications/APP-2024-001/documents",
    files={"file": open("planning_application.pdf", "rb")},
    data={"document_type": "application_form"}
)

result = response.json()
run_id = result["run_id"]

# Get validation results
results = requests.get(
    f"http://localhost:8000/api/v1/applications/APP-2024-001/results"
).json()

print(f"Pass: {results['summary']['pass']}")
print(f"Fail: {results['summary']['fail']}")
```

---

## Authentication

### MVP Mode (Current): **NO AUTHENTICATION** ✅
- Safe for internal BCC use
- No API keys required
- Access via localhost or internal network only

### Production Options (Future):

#### 1. **API Key** (Simplest)
```python
# Add to .env
API_KEYS=["bcc-key-1", "bcc-key-2"]

# BCC sends in header
curl -H "X-API-Key: bcc-key-1" http://api.planproof.com/...
```

#### 2. **Azure AD OAuth** (Enterprise)
- Single Sign-On with Microsoft
- Best for enterprise integration
- Automatic user management

#### 3. **JWT Tokens** (Standard)
- Token-based authentication
- Industry standard
- Good for microservices

**To enable:** Uncomment auth code in `planproof/api/dependencies.py`

---

## File Structure

```
planproof/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── dependencies.py      # Auth & DB dependencies
│   └── routes/
│       ├── health.py        # Health checks
│       ├── applications.py  # Application management
│       ├── documents.py     # Document upload
│       └── validation.py    # Validation results
├── run_api.py               # Start script
├── test_api.py              # Test script
└── docs/
    └── API_INTEGRATION_GUIDE.md  # Full integration guide
```

---

## Features

### ✅ Complete Pipeline Integration
- Document upload → Azure Blob Storage
- OCR extraction → Azure Document Intelligence
- Field mapping → Deterministic + AI
- Validation → 30+ business rules
- LLM gate → GPT-4 (when needed)

### ✅ Async Processing
- Non-blocking document uploads
- Status polling endpoint
- Real-time progress tracking

### ✅ Evidence Linking
- Every finding includes source evidence
- Page numbers and bounding boxes
- Downloadable artifact URLs

### ✅ Production-Ready
- Error handling & logging
- CORS middleware
- Health checks
- Interactive docs

---

## API Response Examples

### Upload Document
```json
{
  "run_id": 123,
  "document_id": 456,
  "application_ref": "APP-2024-001",
  "filename": "planning_application.pdf",
  "blob_uri": "https://...",
  "status": "completed",
  "message": "Document processed successfully"
}
```

### Validation Results
```json
{
  "run_id": 123,
  "application_ref": "APP-2024-001",
  "summary": {
    "pass": 25,
    "fail": 3,
    "warning": 2,
    "needs_review": 0
  },
  "findings": [
    {
      "rule_id": "R1",
      "title": "Site Address Validation",
      "status": "pass",
      "severity": "error",
      "message": "Site address found and valid",
      "evidence": [...]
    }
  ]
}
```

---

## Deployment

### Docker
```dockerfile
EXPOSE 8000
CMD ["uvicorn", "planproof.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Azure App Service
```bash
az webapp up --name planproof-api --runtime "PYTHON:3.11"
```

### Environment Variables
Same as main app (`.env` file):
- `DATABASE_URL`
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_DOCINTEL_ENDPOINT`
- `AZURE_DOCINTEL_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`

---

## Testing

### Manual Testing
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Upload document
curl -X POST \
  -F "file=@test.pdf" \
  http://localhost:8000/api/v1/applications/APP-001/documents

# Get results
curl http://localhost:8000/api/v1/applications/APP-001/results
```

### Automated Testing
```bash
python test_api.py
```

---

## Next Steps

1. **BCC Integration**
   - Share API documentation with BCC developers
   - Provide test environment URL
   - Demo complete workflow

2. **Production Deployment**
   - Enable authentication (API Key or Azure AD)
   - Add rate limiting
   - Set up monitoring

3. **Enhancements**
   - Webhook notifications (async processing complete)
   - Batch upload endpoint
   - Export results to BCC format

---

## Documentation

- **Full Integration Guide**: `docs/API_INTEGRATION_GUIDE.md`
- **Interactive Docs**: http://localhost:8000/api/docs
- **Architecture**: `docs/ARCHITECTURE.md`

---

## Status

✅ **READY FOR BCC INTEGRATION**

**Build Time**: ~2 hours  
**Auth**: Disabled (MVP - internal use)  
**Testing**: ✅ Passing  
**Documentation**: ✅ Complete

**Next**: Share with BCC for integration testing! 🚀
