# CORS Error Fix Guide

## Problem Description

**Error in Browser Console:**
```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/applications' from origin 'http://localhost:3002' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
net::ERR_FAILED
```

This error occurs when the frontend (running on `http://localhost:3002`) tries to call the backend API (`http://localhost:8000`), but the backend doesn't allow that origin.

---

## Root Cause

The PlanProof FastAPI backend uses `CORSMiddleware` to control which origins can access the API. The allowed origins are configured via the `API_CORS_ORIGINS` environment variable.

**Default allowed origins** (from `planproof/config.py`):
```python
api_cors_origins: list[str] = Field(
    default=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:8501"],
    alias="API_CORS_ORIGINS"
)
```

### Why the error happens:

1. **Missing `.env` file**: If no `.env` file exists, environment variables may not be loaded
2. **Empty `API_CORS_ORIGINS`**: If the variable is set to an empty string, no origins are allowed
3. **Wrong format**: The variable must be a comma-separated list (e.g., `http://localhost:3002,http://localhost:8501`)
4. **Backend not running**: If the API server isn't running, you'll see `net::ERR_FAILED`

---

## Solution Steps

### Step 1: Verify Backend is Running

First, check if the backend API is running:

```powershell
# Check if the process is running
Get-Process | Where-Object {$_.ProcessName -like "*python*" -or $_.ProcessName -like "*uvicorn*"}

# Test the health endpoint
curl http://localhost:8000/api/v1/health
```

**Expected response:**
```json
{"status":"healthy","service":"PlanProof API","version":"1.0.0"}
```

If the backend is **not running**, start it:

```powershell
# Option 1: Use the PowerShell script
.\start_api.ps1

# Option 2: Run directly
python run_api.py
```

---

### Step 2: Check/Create `.env` File

The `.env` file should be in the **root directory** of the project (same level as `run_api.py`).

**Check if it exists:**
```powershell
Test-Path .env
```

If it doesn't exist, create it. You can use the example file as a template:

```powershell
# Copy the example (if you have one)
Copy-Item config\production.env.example .env

# Or create a minimal .env file
@"
# Minimal configuration for local development
DATABASE_URL=postgresql://user:pass@localhost:5432/planproof
AZURE_STORAGE_CONNECTION_STRING=UseDevelopmentStorage=true
AZURE_DOCINTEL_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
AZURE_DOCINTEL_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4

# CORS Configuration - THIS IS THE KEY SETTING
API_CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:8501
"@ | Out-File -FilePath .env -Encoding utf8
```

---

### Step 3: Configure CORS Origins

Edit your `.env` file and ensure `API_CORS_ORIGINS` is set correctly:

```env
# CORS Origins (comma-separated list, NO SPACES after commas)
API_CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:8501
```

**Important notes:**
- Use **comma-separated** format (not JSON array)
- **No spaces** after commas
- Include **all ports** your frontend might run on (3000, 3001, 3002, 5173, etc.)
- Include the **Streamlit port** (8501) if using the Streamlit UI

**Example for different scenarios:**

```env
# Development (multiple local ports)
API_CORS_ORIGINS=http://localhost:3000,http://localhost:3002,http://localhost:5173,http://localhost:8501

# Production
API_CORS_ORIGINS=https://planproof.yourdomain.com,https://app.yourdomain.com

# Allow all origins (ONLY for local development, NEVER in production)
API_CORS_ORIGINS=*
```

---

### Step 4: Restart the Backend

After updating `.env`, you **must restart** the backend for changes to take effect:

```powershell
# Stop the backend (if running)
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process

# Start it again
.\start_api.ps1
# OR
python run_api.py
```

---

### Step 5: Verify CORS is Working

Test that CORS headers are being sent:

```powershell
# Send an OPTIONS request (CORS preflight)
curl -X OPTIONS http://localhost:8000/api/v1/applications `
  -H "Origin: http://localhost:3002" `
  -H "Access-Control-Request-Method: POST" `
  -I
```

**Expected headers in response:**
```
Access-Control-Allow-Origin: http://localhost:3002
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH
Access-Control-Allow-Headers: Content-Type, Authorization, X-API-Key
```

---

### Step 6: Test from Frontend

Now try uploading a file from the frontend UI. The CORS error should be gone.

If you still see errors, check the browser console for the **exact error message** and verify:

1. ✅ Backend is running on port 8000
2. ✅ Frontend is accessing `http://localhost:8000` (not a different port)
3. ✅ `.env` file has `API_CORS_ORIGINS` set correctly
4. ✅ Backend was restarted after changing `.env`

---

## Quick Fix (Development Only)

If you just want to test quickly and don't care about security (local development only), you can temporarily allow all origins:

**Edit `planproof/api/main.py`:**

```python
# Find this section (around line 45-55)
cors_origins = settings.api_cors_origins
if isinstance(cors_origins, str):
    cors_origins = [origin.strip() for origin in cors_origins.split(",")]

# Replace with:
cors_origins = ["*"]  # Allow all origins - DEVELOPMENT ONLY!
```

**⚠️ WARNING:** This is insecure and should **NEVER** be used in production. Only use for local testing, and revert it immediately after.

---

## How CORS Works in PlanProof

### Code Flow

1. **Configuration** (`planproof/config.py`):
   - Loads `API_CORS_ORIGINS` from environment
   - Default: `["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:8501"]`

2. **FastAPI Setup** (`planproof/api/main.py`):
   ```python
   cors_origins = settings.api_cors_origins
   if isinstance(cors_origins, str):
       cors_origins = [origin.strip() for origin in cors_origins.split(",")]
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=cors_origins,
       allow_credentials=True,
       allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
       allow_headers=["Content-Type", "Authorization", "X-API-Key"],
   )
   ```

3. **Request Flow**:
   - Browser sends OPTIONS preflight request
   - FastAPI checks if origin is in `allow_origins`
   - If allowed, sends `Access-Control-Allow-Origin` header
   - Browser allows the actual request

---

## Troubleshooting

### Issue: "Still getting CORS error after setting API_CORS_ORIGINS"

**Possible causes:**

1. **Backend not restarted**: You must restart the backend after changing `.env`
   ```powershell
   Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process
   python run_api.py
   ```

2. **Wrong format**: Check for spaces or quotes
   ```env
   # ❌ WRONG
   API_CORS_ORIGINS="http://localhost:3002"
   API_CORS_ORIGINS=http://localhost:3002, http://localhost:8501
   
   # ✅ CORRECT
   API_CORS_ORIGINS=http://localhost:3002,http://localhost:8501
   ```

3. **Port mismatch**: Verify frontend is running on the port you specified
   ```powershell
   # Check what port the frontend is using
   netstat -ano | findstr :3002
   ```

### Issue: "net::ERR_FAILED" (no CORS error message)

This usually means the backend isn't running at all.

**Fix:**
```powershell
# Check if backend is running
curl http://localhost:8000/api/v1/health

# If not, start it
python run_api.py
```

### Issue: "CORS error only on POST requests, not GET"

This is normal browser behavior (preflight requests). The fix is the same - ensure `API_CORS_ORIGINS` is set correctly.

---

## Frontend Configuration

The frontend also needs to be configured to point to the correct API URL.

**Check `frontend/.env` (or `frontend/.env.local`):**

```env
# Option 1: Direct URL (may cause CORS issues)
VITE_API_URL=http://localhost:8000

# Option 2: Relative path (uses proxy, avoids CORS)
VITE_API_URL=/api
```

If using **Option 2** (proxy), you need to configure Vite's proxy in `frontend/vite.config.ts`:

```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api')
      }
    }
  }
})
```

---

## Production Deployment

For production, set `API_CORS_ORIGINS` to your actual domain(s):

```env
# Production .env
API_CORS_ORIGINS=https://planproof.yourdomain.com,https://app.yourdomain.com
```

**Security best practices:**

1. ✅ **Never use `*`** in production
2. ✅ **Use HTTPS** (not HTTP) for all origins
3. ✅ **Limit to specific domains** you control
4. ✅ **Use environment-specific** `.env` files
5. ✅ **Keep `.env` out of version control** (add to `.gitignore`)

---

## Summary Checklist

- [ ] Backend is running on port 8000
- [ ] `.env` file exists in project root
- [ ] `API_CORS_ORIGINS` is set in `.env` (comma-separated, no spaces)
- [ ] Origin includes the frontend port (e.g., `http://localhost:3002`)
- [ ] Backend was restarted after changing `.env`
- [ ] Health endpoint responds: `curl http://localhost:8000/api/v1/health`
- [ ] CORS headers are present in OPTIONS response
- [ ] Frontend API URL points to `http://localhost:8000`

---

## Need More Help?

If you're still experiencing issues:

1. **Check backend logs**: Look for startup errors or CORS-related messages
2. **Check browser console**: Look for the exact error message
3. **Test with curl**: Verify the API is accessible outside the browser
4. **Check firewall**: Ensure Windows Firewall isn't blocking port 8000

**Useful commands:**

```powershell
# View backend logs (if running in background)
Get-Content -Path "backend.log" -Tail 50 -Wait

# Check what's listening on port 8000
netstat -ano | findstr :8000

# Test API directly (bypasses CORS)
curl http://localhost:8000/api/v1/health
```

---

## Related Files

- **Backend CORS config**: `planproof/api/main.py` (lines 42-55)
- **Settings definition**: `planproof/config.py` (lines 76-80)
- **Environment file**: `.env` (root directory)
- **Frontend API client**: `frontend/src/api/client.ts`
- **Startup script**: `run_api.py`

---

**Last Updated:** 2026-01-03

