# CORS Quick Reference Card

## 🚨 Error in Browser Console

```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/...' from origin 'http://localhost:3002' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present
```

---

## ⚡ Quick Fix (3 Steps)

### 1. Check Backend is Running
```powershell
curl http://localhost:8000/api/v1/health
```
- ✅ **If working**: Continue to step 2
- ❌ **If failing**: Run `python run_api.py`

### 2. Add CORS to `.env`
```env
API_CORS_ORIGINS=http://localhost:3000,http://localhost:3002,http://localhost:8501
```

### 3. Restart Backend
```powershell
# Stop Python processes
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process

# Start backend
python run_api.py
```

---

## 🔧 Automated Diagnostic

Run the diagnostic script:
```powershell
.\fix-cors.ps1
```

This will:
- ✓ Check if backend is running
- ✓ Verify `.env` configuration
- ✓ Test CORS headers
- ✓ Show active ports
- ✓ Provide specific fix recommendations

---

## 📋 Common Issues & Solutions

| Symptom | Cause | Fix |
|---------|-------|-----|
| `net::ERR_FAILED` | Backend not running | `python run_api.py` |
| `No 'Access-Control-Allow-Origin'` | Missing CORS config | Add `API_CORS_ORIGINS` to `.env` |
| CORS error after config change | Backend not restarted | Restart backend |
| Works in Postman, fails in browser | CORS only affects browsers | Configure CORS properly |
| Error on POST but not GET | Preflight request failing | Same fix as above |

---

## 📝 `.env` Configuration

**Minimal `.env` for CORS:**
```env
# Required Azure credentials (get from Azure Portal)
DATABASE_URL=postgresql://user:pass@localhost:5432/planproof
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_DOCINTEL_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
AZURE_DOCINTEL_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4

# CORS - THIS IS THE KEY LINE
API_CORS_ORIGINS=http://localhost:3000,http://localhost:3002,http://localhost:8501
```

**Important:**
- ✅ Comma-separated (no spaces)
- ✅ Include all frontend ports
- ❌ Don't use quotes
- ❌ Don't add spaces after commas

---

## 🧪 Test CORS is Working

```powershell
# Test preflight request
curl -X OPTIONS http://localhost:8000/api/v1/applications `
  -H "Origin: http://localhost:3002" `
  -H "Access-Control-Request-Method: POST" `
  -I
```

**Expected headers:**
```
Access-Control-Allow-Origin: http://localhost:3002
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH
```

---

## 🔍 Where CORS is Configured

1. **Environment Variable** (`.env`):
   ```env
   API_CORS_ORIGINS=http://localhost:3000,http://localhost:3002
   ```

2. **Config Loading** (`planproof/config.py` lines 77-80):
   ```python
   api_cors_origins: list[str] = Field(
       default=["http://localhost:3000", "http://localhost:3001", 
                "http://localhost:3002", "http://localhost:8501"],
       alias="API_CORS_ORIGINS"
   )
   ```

3. **FastAPI Middleware** (`planproof/api/main.py` lines 45-55):
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

---

## 🎯 Development vs Production

### Development (Local)
```env
API_CORS_ORIGINS=http://localhost:3000,http://localhost:3002,http://localhost:8501
```

### Production
```env
API_CORS_ORIGINS=https://planproof.yourdomain.com,https://app.yourdomain.com
```

**⚠️ NEVER use `*` in production!**

---

## 🆘 Still Not Working?

1. **Check backend logs** for startup errors
2. **Verify port** - frontend must match CORS origin
3. **Clear browser cache** and hard reload (Ctrl+Shift+R)
4. **Check firewall** - Windows Firewall may block port 8000
5. **Read full guide**: [CORS_FIX_GUIDE.md](CORS_FIX_GUIDE.md)

---

## 📞 Quick Commands Reference

```powershell
# Check if backend is running
Get-Process | Where-Object {$_.ProcessName -like "*python*"}

# Test health endpoint
curl http://localhost:8000/api/v1/health

# Check what's on port 8000
netstat -ano | findstr :8000

# Stop all Python processes
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process

# Start backend
python run_api.py

# Run diagnostics
.\fix-cors.ps1

# Check .env has CORS config
Select-String -Path .env -Pattern "API_CORS_ORIGINS"
```

---

## 📚 Related Documentation

- **Full Guide**: [CORS_FIX_GUIDE.md](CORS_FIX_GUIDE.md)
- **API Documentation**: [docs/API_INTEGRATION_GUIDE.md](docs/API_INTEGRATION_GUIDE.md)
- **General Troubleshooting**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

**Last Updated:** 2026-01-03

