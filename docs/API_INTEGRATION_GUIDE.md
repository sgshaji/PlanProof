# PlanProof REST API - Integration Guide for BCC

## Quick Start

### Starting the API Server

```bash
# Development mode (auto-reload)
python run_api.py

# Production mode
uvicorn planproof.api.main:app --host 0.0.0.0 --port 8000
```

API will be available at:
- **Base URL:** `http://localhost:8000`
- **Interactive Docs:** `http://localhost:8000/api/docs` (Swagger UI)
- **Alternative Docs:** `http://localhost:8000/api/redoc` (ReDoc)

---

## Authentication

**MVP Mode:** No authentication required (internal use only).

**Production:** See [Authentication Options](#authentication-options) below.

---

## API Endpoints

### 1. Upload Document for Processing

**Upload a PDF and trigger full validation pipeline.**

```http
POST /api/v1/applications/{application_ref}/documents
Content-Type: multipart/form-data

file: <PDF file>
document_type: application_form  # Optional
```

**Example (cURL):**
```bash
curl -X POST "http://localhost:8000/api/v1/applications/APP-2024-001/documents" \
  -F "file=@planning_application.pdf" \
  -F "document_type=application_form"
```

**Example (Python):**
```python
import requests

url = "http://localhost:8000/api/v1/applications/APP-2024-001/documents"
files = {"file": open("planning_application.pdf", "rb")}
data = {"document_type": "application_form"}

response = requests.post(url, files=files, data=data)
result = response.json()

print(f"Run ID: {result['run_id']}")
print(f"Status: {result['status']}")
```

**Response:**
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

---

### 2. Check Processing Status

**Get status of a specific processing run.**

```http
GET /api/v1/runs/{run_id}/status
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/runs/123/status"
```

**Response:**
```json
{
  "run_id": 123,
  "status": "completed",
  "started_at": "2026-01-01T10:30:00Z",
  "completed_at": "2026-01-01T10:31:45Z",
  "document_id": 456,
  "error_message": null
}
```

**Status Values:**
- `pending` - Processing not started
- `running` - Currently processing
- `completed` - Successfully completed
- `failed` - Processing failed (see error_message)

---

### 3. Get Validation Results

**Get complete validation results for an application.**

```http
GET /api/v1/applications/{application_ref}/results?run_id={optional}
```

**Example:**
```bash
# Get latest results
curl "http://localhost:8000/api/v1/applications/APP-2024-001/results"

# Get specific run results
curl "http://localhost:8000/api/v1/applications/APP-2024-001/results?run_id=123"
```

**Response:**
```json
{
  "run_id": 123,
  "application_ref": "APP-2024-001",
  "document_id": 456,
  "status": "completed",
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
      "evidence": [
        {
          "page": 1,
          "snippet": "123 Main Street, Bristol, BS1 1AA",
          "confidence": 0.95
        }
      ]
    },
    {
      "rule_id": "R-FEE-001",
      "title": "Planning Fee Validation",
      "status": "fail",
      "severity": "error",
      "message": "Fee amount does not match calculated fee",
      "evidence": []
    }
  ],
  "artifacts": {
    "extraction": "https://..../extraction_123.json",
    "validation": "https://..../validation_123.json",
    "llm_notes": "https://..../llm_notes_123.json"
  }
}
```

---

### 4. List Applications

**Get all planning applications.**

```http
GET /api/v1/applications?skip=0&limit=100
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/applications?skip=0&limit=10"
```

**Response:**
```json
[
  {
    "id": 1,
    "application_ref": "APP-2024-001",
    "applicant_name": "John Smith",
    "created_at": "2026-01-01T09:00:00Z",
    "updated_at": "2026-01-01T10:30:00Z",
    "submission_count": 2
  }
]
```

---

### 5. Get Application Details

**Get details of a specific application.**

```http
GET /api/v1/applications/{application_ref}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/applications/APP-2024-001"
```

**Response:**
```json
{
  "id": 1,
  "application_ref": "APP-2024-001",
  "applicant_name": "John Smith",
  "application_date": "2024-12-15T00:00:00Z",
  "created_at": "2026-01-01T09:00:00Z",
  "updated_at": "2026-01-01T10:30:00Z",
  "submissions": [
    {
      "id": 1,
      "version": "V0",
      "status": "pending",
      "created_at": "2026-01-01T09:00:00Z"
    },
    {
      "id": 2,
      "version": "V1",
      "status": "validated",
      "created_at": "2026-01-01T10:00:00Z"
    }
  ]
}
```

---

### 6. Health Checks

**Check if API is running.**

```http
GET /api/v1/health
```

**Check database connectivity.**

```http
GET /api/v1/health/db
```

---

## Complete Workflow Example

### Scenario: Process a new planning application

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

# Step 1: Create application (optional - will auto-create on upload)
app_ref = "APP/2024/001"

# Step 2: Upload document for processing
print("Uploading document...")
upload_response = requests.post(
    f"{BASE_URL}/applications/{app_ref}/documents",
    files={"file": open("planning_application.pdf", "rb")},
    data={"document_type": "application_form"}
)
upload_result = upload_response.json()
run_id = upload_result["run_id"]
print(f"Run ID: {run_id}")
print(f"Status: {upload_result['status']}")

# Step 3: Poll for completion (if processing is async)
while True:
    status_response = requests.get(f"{BASE_URL}/runs/{run_id}/status")
    status = status_response.json()
    
    if status["status"] == "completed":
        print("Processing completed!")
        break
    elif status["status"] == "failed":
        print(f"Processing failed: {status['error_message']}")
        exit(1)
    
    print(f"Status: {status['status']}...")
    time.sleep(2)

# Step 4: Get validation results
results_response = requests.get(f"{BASE_URL}/applications/{app_ref}/results")
results = results_response.json()

print(f"\nValidation Summary:")
print(f"  Pass: {results['summary']['pass']}")
print(f"  Fail: {results['summary']['fail']}")
print(f"  Warning: {results['summary']['warning']}")
print(f"  Needs Review: {results['summary']['needs_review']}")

print(f"\nFindings:")
for finding in results["findings"]:
    print(f"  [{finding['status'].upper()}] {finding['title']}")
    if finding['message']:
        print(f"    {finding['message']}")
```

---

## Authentication Options

### For Production Deployment

#### Option 1: API Key Authentication (Simplest)

1. **Add to `.env`:**
   ```bash
   API_KEYS=["your-secret-key-1", "your-secret-key-2"]
   ```

2. **Uncomment in `dependencies.py`:**
   ```python
   async def verify_api_key(
       x_api_key: str = Header(..., description="API Key")
   ):
       ...
   ```

3. **Add to routes:**
   ```python
   @router.post("/documents", dependencies=[Depends(verify_api_key)])
   ```

4. **BCC sends key in header:**
   ```bash
   curl -H "X-API-Key: your-secret-key-1" ...
   ```

---

#### Option 2: Azure AD OAuth (Enterprise)

Best for enterprise integration with Microsoft SSO.

```python
from fastapi.security import OAuth2AuthorizationCodeBearer

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
    tokenUrl="https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
)

async def verify_azure_token(token: str = Depends(oauth2_scheme)):
    # Verify Azure AD token
    ...
```

---

#### Option 3: JWT Tokens

Standard token-based authentication.

```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    token = credentials.credentials
    # Verify JWT token
    ...
```

---

## Error Handling

All endpoints return standard error responses:

```json
{
  "error": "Error type",
  "message": "Detailed error message",
  "type": "ExceptionType"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad request (invalid input)
- `404` - Resource not found
- `409` - Conflict (duplicate resource)
- `500` - Internal server error

---

## Rate Limiting

**MVP:** No rate limiting.

**Production:** Add rate limiting middleware:
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/documents")
@limiter.limit("10/minute")
async def upload_document(...):
    ...
```

---

## Testing the API

### Using the Interactive Docs

1. Start API: `python run_api.py`
2. Open browser: `http://localhost:8000/api/docs`
3. Click "Try it out" on any endpoint
4. Fill in parameters and execute

### Using Postman

Import the OpenAPI spec:
`http://localhost:8000/api/openapi.json`

---

## Deployment

### Docker

```dockerfile
# Add to Dockerfile
EXPOSE 8000
CMD ["uvicorn", "planproof.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Azure App Service

```bash
az webapp up --name planproof-api --runtime "PYTHON:3.11"
```

---

## Support

For API issues or integration questions:
- Email: api-support@planproof.com
- Docs: http://localhost:8000/api/docs
- Source: `planproof/api/`
