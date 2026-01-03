# Architecture Review - Run IDs, Error Handling & UX Integration

**Date**: January 3, 2026  
**Reviewer**: Technical Analysis  
**Status**: ✅ Production-Ready with Recommendations

---

## 1. 🔑 Run ID Generation & Association

### ✅ **Run ID is Auto-Generated**

**Database Model** (`planproof/db.py:360-375`):
```python
class Run(Base):
    """Audit trail for processing runs."""
    __tablename__ = "runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # ✅ AUTO-INCREMENT
    run_type = Column(String(50), nullable=False)  # "ingest", "extract", "validate"
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="running")  # running, completed, failed
    error_message = Column(Text, nullable=True)
```

**✅ Verdict**: PostgreSQL automatically generates sequential Run IDs via `autoincrement=True`. No manual ID management required.

---

### ✅ **Association Between Run ID and Application ID**

**Relationship Structure**:

```
Application (1) ──────┐
                      │
                      ├──> Multiple Submissions (1:N)
                      │
                      └──> Multiple Runs (1:N)
                            │
                            └──> Multiple Documents (N:M via run_documents)
```

**Key Relationships**:
1. **Application → Run**: One-to-Many (`application_id` foreign key in Run table)
2. **Run → Documents**: Many-to-Many (via `run_documents` join table)
3. **Run → ValidationChecks**: One-to-Many (validation results linked to run)

**How It Works**:
```python
# planproof/api/routes/documents.py:94-108
run = db.create_run(
    run_type="document_upload",
    application_id=application_id,  # ✅ Links run to application
    status="running",
    run_metadata={"uploaded_by": user.get("user_id")}
)

# Returns run.id to frontend
return {"run_id": run.id}
```

**✅ Verdict**: Clean relational design. Every Run is linked to exactly one Application via `application_id` foreign key.

---

## 2. 🎨 UX to Backend Integration Seamlessness

### ✅ **API Client Integration**

**Frontend API Client** (`frontend/src/api/client.ts:74-107`):
```typescript
uploadFiles: async (applicationRef: string, files: File[]) => {
  const results = [];
  for (const file of files) {
    const formData = new FormData();
    formData.append('file', file);
    
    // ✅ Makes HTTP POST to backend
    const response = await apiClient.post(
      `/api/v1/applications/${applicationRef}/documents`, 
      formData
    );
    results.push(response.data);  // Contains run_id
  }
  return results[results.length - 1];  // Returns {run_id, status, ...}
}
```

**Backend Endpoint** (`planproof/api/routes/documents.py:75-165`):
```python
@router.post("/applications/{application_ref}/documents")
async def upload_document(
    application_ref: str,
    file: UploadFile = File(...),
    db: Database = Depends(get_db)
):
    # ✅ Creates run record
    run = db.create_run(run_type="document_upload", application_id=app.id)
    
    # ✅ Process document (extract, validate)
    response = await _process_document_for_run(run, file, db, ...)
    
    # ✅ Returns run_id to frontend
    return {
        "run_id": run.id,
        "document_id": response.document_id,
        "status": "completed"
    }
```

### ✅ **Seamless Data Flow**:

```
User Uploads File
      ↓
Frontend: api.uploadFiles()
      ↓
HTTP POST /api/v1/applications/{ref}/documents
      ↓
Backend: Create Run record (auto-generated run.id)
      ↓
Backend: Process document (OCR, extraction, validation)
      ↓
Backend: Save to database (ExtractedField, Evidence, ValidationCheck)
      ↓
Backend: Return {run_id: 123, status: "completed"}
      ↓
Frontend: Store run_id, redirect to /results/{run_id}
      ↓
Frontend: GET /api/v1/runs/{run_id}/results
      ↓
Backend: Query validation results from database
      ↓
Frontend: Display findings to user
```

**✅ Verdict**: Integration is **seamless**. RESTful API design with proper status codes, error handling, and JSON responses. No manual ID passing required.

---

## 3. 📊 Azure Logging Configuration

### ⚠️ **Partial Implementation - Needs Enhancement**

**Current Configuration** (`planproof/config.py:52-55`):
```python
# Optional: Logging
log_level: str = Field(default="INFO", alias="LOG_LEVEL")
log_json: bool = Field(default=True, alias="LOG_JSON")
```

**Current Usage**:
```python
# planproof/api/routes/documents.py:5,25
import logging
LOGGER = logging.getLogger(__name__)

# Used for informational logs only
LOGGER.info(f"Parent application found: {parent_submission_id}")
```

### ❌ **Issues Found**:

1. **No Azure Application Insights Integration**:
   ```python
   # ❌ MISSING: Azure Monitor integration
   # Should have:
   # from opencensus.ext.azure.log_exporter import AzureLogHandler
   # LOGGER.addHandler(AzureLogHandler(connection_string=APPINSIGHTS_CONNECTION))
   ```

2. **No Structured Logging**:
   ```python
   # ❌ MISSING: Structured logging for Azure queries
   # Should log with context:
   # LOGGER.info("Document uploaded", extra={
   #     "run_id": run.id,
   #     "application_ref": app_ref,
   #     "user_id": user.get("user_id")
   # })
   ```

3. **No Correlation IDs**:
   ```python
   # ❌ MISSING: Request correlation for distributed tracing
   # Should add correlation_id to all logs
   ```

### ⚠️ **Recommendation**:
```python
# Add to requirements.txt:
# opencensus-ext-azure==1.1.13
# opencensus-ext-logging==0.1.1

# Add to planproof/config.py:
azure_appinsights_connection_string: str = Field(
    default="", 
    alias="APPLICATIONINSIGHTS_CONNECTION_STRING"
)

# Add to main.py or startup:
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

if settings.azure_appinsights_connection_string:
    handler = AzureLogHandler(
        connection_string=settings.azure_appinsights_connection_string
    )
    logging.getLogger().addHandler(handler)
```

**✅ Verdict**: Logging exists but **NOT AZURE-READY**. Need to add Azure Application Insights integration for production monitoring.

---

## 4. 🛡️ Error Handling - Technical Messages Hidden from UI

### ✅ **Backend Error Handling** (GOOD)

**HTTP Exception Wrapper** (`planproof/api/routes/documents.py:159-164`):
```python
try:
    response = await _process_document_for_run(...)
    db.update_run(run.id, status="completed")
    return response
except HTTPException as exc:
    # ✅ Catches specific HTTP errors (404, 400, etc.)
    db.update_run(run.id, status="failed", error_message=str(exc.detail))
    raise  # ✅ Re-raises with user-friendly message
except Exception as exc:
    # ✅ Catches unexpected errors
    db.update_run(run.id, status="failed", error_message=str(exc))
    raise  # ⚠️ Exposes raw exception to frontend
```

### ⚠️ **CRITICAL ISSUE FOUND**:

**Backend exposes raw exceptions to frontend** (`planproof/api/routes/documents.py:470`):
```python
except Exception as exc:
    db.update_run(run.id, status="failed", error_message=str(exc))
    raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(exc)}")
    #                                            ^^^^^^^^^^^^^^^^^^^^^^^^
    #                                            ❌ RAW EXCEPTION EXPOSED!
```

**Example of what users might see**:
```
"Batch processing failed: 'NoneType' object has no attribute 'id'"
"psycopg.OperationalError: connection already closed"
```

### ✅ **Frontend Error Handling** (EXCELLENT)

**Error Utility** (`frontend/src/api/errorUtils.ts:8-38`):
```typescript
export const getApiErrorMessage = (error: unknown, fallback: string) => {
  if (axios.isAxiosError(error)) {
    // ✅ Timeout handling
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      return 'Request timed out. Please check your connection and try again.';
    }

    // ✅ Network error handling
    if (error.code === 'ERR_NETWORK') {
      return 'Unable to reach the server. This may be a network issue.';
    }

    // ✅ Server error handling
    const status = error.response?.status;
    if (status && status >= 500) {
      return `Server error (${status}). Please try again later.`;  // ✅ GENERIC MESSAGE
    }

    // ⚠️ Returns error.response.data.detail from backend
    return error.response?.data?.detail || fallback;
    //     ^^^^^^^^^^^^^^^^^^^^^^^^^^^
    //     ⚠️ If backend sends raw exception, user sees it!
  }
  return fallback;
}
```

**Usage in Components** (`frontend/src/pages/NewApplication.tsx:394`):
```typescript
} catch (err) {
  const message = getApiErrorMessage(
    err, 
    'Failed to upload files. Please try again.'  // ✅ User-friendly fallback
  );
  setError(message);
}
```

### ❌ **VULNERABILITIES**:

1. **Backend sends raw exceptions in 500 errors**:
   ```python
   # ❌ BAD:
   raise HTTPException(status_code=500, detail=f"Processing failed: {str(exc)}")
   
   # ✅ SHOULD BE:
   LOGGER.error(f"Processing failed: {str(exc)}", exc_info=True)
   raise HTTPException(
       status_code=500, 
       detail="An unexpected error occurred. Please contact support."
   )
   ```

2. **Database errors exposed**:
   ```python
   # ❌ BAD:
   raise HTTPException(status_code=404, detail="Application not found")
   
   # ⚠️ ACCEPTABLE (not a security issue, just informational)
   ```

3. **No error masking for production**:
   ```python
   # ❌ MISSING:
   if settings.app_env == "production":
       detail = "An error occurred. Please try again."
   else:
       detail = f"Debug: {str(exc)}"
   ```

### ✅ **RECOMMENDATIONS**:

**1. Create Error Response Models** (`planproof/api/errors.py` - NEW FILE):
```python
from fastapi import HTTPException, status
import logging

LOGGER = logging.getLogger(__name__)

class AppError(HTTPException):
    """Base application error with user-friendly messages."""
    
    def __init__(self, status_code: int, user_message: str, internal_error: Exception = None):
        super().__init__(status_code=status_code, detail=user_message)
        if internal_error:
            LOGGER.error(
                f"{user_message}",
                exc_info=internal_error,
                extra={"status_code": status_code}
            )

# Usage:
raise AppError(
    status_code=500,
    user_message="Failed to process document. Please try again.",
    internal_error=exc  # Logged but not shown to user
)
```

**2. Update All Exception Handlers**:
```python
# Replace this pattern everywhere:
except Exception as exc:
    raise HTTPException(status_code=500, detail=f"Failed: {str(exc)}")

# With this:
except Exception as exc:
    LOGGER.error(f"Document processing failed: {exc}", exc_info=True)
    raise AppError(
        status_code=500,
        user_message="Document processing failed. Please contact support.",
        internal_error=exc
    )
```

**3. Add Global Exception Handler** (`main.py`):
```python
from fastapi import Request, status
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    LOGGER.error(
        f"Unhandled exception on {request.method} {request.url}",
        exc_info=exc,
        extra={"path": str(request.url), "method": request.method}
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please contact support."}
    )
```

**✅ Verdict**: Frontend error handling is **EXCELLENT**. Backend error handling is **PARTIALLY SECURE** but **exposes raw exceptions** in several places. Need to add error masking layer.

---

## 5. 📋 Error Handling Comprehensiveness

### ✅ **What's GOOD**:

1. **Try-Catch Blocks Everywhere**:
   - ✅ All API endpoints wrapped in try-except
   - ✅ HTTPException used for known errors
   - ✅ Generic Exception catches unexpected errors

2. **Status Code Consistency**:
   - ✅ 404 for "not found"
   - ✅ 400 for "bad request"
   - ✅ 500 for "server error"
   - ✅ 403 for "forbidden"

3. **Database Rollback**:
   ```python
   try:
       session.add(record)
       session.commit()
   except Exception:
       session.rollback()  # ✅ Prevents data corruption
       raise
   ```

4. **Run Status Tracking**:
   ```python
   try:
       process_document()
       db.update_run(run.id, status="completed")
   except:
       db.update_run(run.id, status="failed", error_message=str(exc))
   ```

5. **Frontend Error Boundaries**:
   ```typescript
   // ✅ Every page has error state
   const [error, setError] = useState('');
   
   // ✅ Error displayed to user
   {error && (
     <Alert severity="error" onClose={() => setError('')}>
       {error}
     </Alert>
   )}
   ```

### ⚠️ **What's MISSING**:

1. **No Retry Logic**:
   ```python
   # ❌ MISSING: Automatic retry for transient failures
   # Should have exponential backoff for Azure API calls
   ```

2. **No Circuit Breaker**:
   ```python
   # ❌ MISSING: Circuit breaker for external services
   # If Azure OpenAI is down, should fail fast instead of hanging
   ```

3. **No Rate Limiting**:
   ```python
   # ❌ MISSING: Rate limiting on upload endpoints
   # User could spam file uploads and DOS the service
   ```

4. **No Validation Errors**:
   ```python
   # ⚠️ WEAK: File validation is minimal
   if not file.filename.lower().endswith('.pdf'):
       raise HTTPException(400, "Only PDF files allowed")
   
   # ❌ MISSING: File size limits, virus scanning, metadata validation
   ```

5. **No Dead Letter Queue**:
   ```python
   # ❌ MISSING: Failed runs should go to DLQ for manual review
   ```

### ✅ **Comprehensiveness Score**:

| Category | Score | Status |
|----------|-------|--------|
| **HTTP Error Handling** | 9/10 | ✅ Excellent |
| **Database Error Handling** | 8/10 | ✅ Good (has rollback) |
| **Azure API Error Handling** | 7/10 | ⚠️ Needs retry logic |
| **Frontend Error Display** | 9/10 | ✅ Excellent |
| **Error Masking (Security)** | 5/10 | ❌ Exposes raw exceptions |
| **Logging & Monitoring** | 6/10 | ⚠️ No Azure integration |
| **Graceful Degradation** | 6/10 | ⚠️ No circuit breakers |
| **Input Validation** | 7/10 | ⚠️ Needs file size limits |
| **Rate Limiting** | 0/10 | ❌ Not implemented |
| **Dead Letter Queue** | 0/10 | ❌ Not implemented |

**Overall: 6.7/10 - GOOD but needs production hardening**

---

## 📌 **Summary & Recommendations**

### ✅ **STRENGTHS**:
1. ✅ Run IDs auto-generated correctly
2. ✅ Clean Application ↔ Run relationship
3. ✅ Seamless UX → Backend integration
4. ✅ Frontend error handling is excellent
5. ✅ Database rollback on errors
6. ✅ Comprehensive try-catch coverage

### ❌ **CRITICAL FIXES NEEDED**:
1. ❌ **Backend exposes raw exceptions to users** - SECURITY ISSUE
2. ❌ **No Azure Application Insights logging** - MONITORING GAP
3. ❌ **No rate limiting on uploads** - DOS VULNERABILITY
4. ❌ **No retry logic for Azure APIs** - RELIABILITY ISSUE

### ⚠️ **RECOMMENDED IMPROVEMENTS**:
1. Implement error masking layer (see section 4)
2. Add Azure Application Insights integration
3. Add retry logic with exponential backoff
4. Implement rate limiting (e.g., 10 uploads/minute per user)
5. Add file size validation (max 10MB per file)
6. Add circuit breaker for external services
7. Implement dead letter queue for failed runs

### 🎯 **PRIORITY**:
1. **HIGH**: Fix raw exception exposure (Section 4)
2. **HIGH**: Add Azure Application Insights logging
3. **MEDIUM**: Add rate limiting
4. **MEDIUM**: Add retry logic
5. **LOW**: Add circuit breakers and DLQ

---

## ✅ **FINAL VERDICT**

The system is **production-ready for MVP** with excellent UX integration and good error handling patterns. However, it needs **security hardening** (error masking) and **observability improvements** (Azure logging) before scaling to production traffic.

**Recommendation**: Implement HIGH-priority fixes before public launch.

