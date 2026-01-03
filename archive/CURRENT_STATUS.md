# PlanProof - Current Status & Setup Guide

**Last Updated**: 2026-01-02
**Branch**: `claude/fix-app-screen-ui-LW99P`

---

## ✅ WHAT'S WORKING

### Backend (Port 8000)
- ✅ FastAPI server running
- ✅ Health endpoint: `http://localhost:8000/api/v1/health`
- ✅ CORS configured for localhost:3000
- ✅ All API routes working
- ✅ Dependencies installed

### Frontend (Port 3000)
- ✅ Vite dev server running
- ✅ React app loads without errors
- ✅ Proxy configured (`/api` → `http://localhost:8000`)
- ✅ No CORS errors (requests go through proxy)
- ✅ All UI components working
- ✅ Per-file upload tracking
- ✅ Backend health monitoring
- ✅ File validation
- ✅ Error handling with retry

### Fixed Issues
- ✅ Backend server configuration
- ✅ CORS errors resolved
- ✅ React Router warnings fixed
- ✅ useEffect/useState bug fixed
- ✅ API client timeout added
- ✅ Enhanced error messages
- ✅ 28 total bugs fixed

---

## ⚠️ KNOWN LIMITATIONS

### Database Connection
**Status**: ❌ Not Working
**Error**: `failed to resolve host 'planproof-dev-pgflex-8016.postgres.database.azure.com'`

**Cause**: Azure PostgreSQL database is not accessible from this network environment.

**Impact**:
- ❌ Cannot create applications
- ❌ Cannot upload documents
- ❌ Cannot store validation results

**Workaround Options**:
1. **VPN/Network Access**: Connect to network with access to Azure PostgreSQL
2. **Local PostgreSQL**: Set up local PostgreSQL instance
3. **Mock Mode**: Disable database writes in config (not fully implemented)

**To Fix**:
```bash
# Option 1: Change DATABASE_URL to local PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost:5432/planproof

# Option 2: Set up local PostgreSQL
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=pass -e POSTGRES_DB=planproof postgres:13
```

---

## 🚀 HOW TO START SERVERS

### Option 1: Automated Script (Recommended)
```bash
cd /home/user/PlanProof
bash start_servers.sh
```

This will:
- Start backend on port 8000
- Start frontend on port 3000
- Check health of both
- Show server PIDs and log locations

### Option 2: Manual Start

**Backend**:
```bash
cd /home/user/PlanProof
python run_api.py
# Runs on http://localhost:8000
```

**Frontend**:
```bash
cd /home/user/PlanProof/frontend
cp .env.example .env  # If not already done
npm install           # If not already done
npm run dev
# Runs on http://localhost:3000
```

---

## 📋 ENVIRONMENT SETUP

### Backend `.env` (Root directory)
```bash
# Already configured with:
- Azure storage credentials
- Azure Document Intelligence
- Azure OpenAI
- PostgreSQL database URL
- CORS origins
- Feature flags
```

### Frontend `.env` (frontend/ directory)
```bash
# Copy the example:
cp frontend/.env.example frontend/.env

# Contents:
VITE_API_URL=/api
```

**Why `/api`?**
- Routes through Vite dev proxy
- Avoids CORS errors
- Proxy forwards to http://localhost:8000

---

## 🧪 TESTING

### 1. Check Servers are Running
```bash
# Backend health
curl http://localhost:8000/api/v1/health
# Should return: {"status":"healthy",...}

# Frontend (via proxy)
curl http://localhost:3000/api/v1/health
# Should return same as above

# Frontend page
curl http://localhost:3000
# Should return HTML with <title>PlanProof</title>
```

### 2. Run Automated Tests
```bash
bash test_ui_automated.sh
```

Expected results:
- ✅ Backend health check
- ✅ CORS headers
- ⚠️ Application create (fails due to database)
- ⚠️ File upload (fails due to database)

### 3. Manual UI Testing
1. Open http://localhost:3000/new-application
2. Expected:
   - ✅ Green "Backend connected" alert
   - ✅ Form fields working
   - ✅ File drag & drop working
   - ❌ Upload fails with database error (expected)

---

## 🐛 TROUBLESHOOTING

### "Cannot connect to backend server"
**Symptoms**: Red alert in UI, CORS errors

**Fix**:
```bash
# Check if backend is running
ps aux | grep uvicorn

# If not, start it
python run_api.py &

# Verify
curl http://localhost:8000/api/v1/health
```

### "Network Error" in UI
**Symptoms**: Error on file upload

**Possible Causes**:
1. **Backend not running**: Start backend
2. **Frontend not using proxy**: Check `frontend/.env` has `VITE_API_URL=/api`
3. **Database error**: Expected - see "Database Connection" section above

**Check**:
```bash
# Should see this in frontend/.env
cat frontend/.env
# Output: VITE_API_URL=/api

# Test proxy
curl http://localhost:3000/api/v1/health
```

### CORS Errors
**Should not happen anymore**, but if you see them:

1. Check `.env` has CORS configured:
```bash
grep CORS .env
# Should show: API_CORS_ORIGINS=["http://localhost:3000",...]
```

2. Check frontend is using `/api` not direct URL:
```bash
cat frontend/.env
# Should show: VITE_API_URL=/api
```

3. Restart both servers:
```bash
# Kill existing
pkill -f uvicorn
pkill -f vite

# Restart
bash start_servers.sh
```

---

## 📁 KEY FILES

### Configuration
- `.env` - Backend configuration
- `frontend/.env` - Frontend configuration (gitignored)
- `frontend/.env.example` - Template for frontend .env

### Source Code
- `frontend/src/pages/NewApplication.tsx` - Main upload UI (567 lines, rewritten)
- `frontend/src/api/client.ts` - API client with timeout & error handling
- `frontend/src/main.tsx` - React Router with v7 flags
- `planproof/api/main.py` - FastAPI app with CORS
- `planproof/api/routes/documents.py` - File upload endpoint

### Scripts
- `start_servers.sh` - Start both servers
- `test_ui_automated.sh` - Automated test suite
- `run_api.py` - Backend startup script

### Documentation
- `FIXES_SUMMARY.md` - Complete list of all 28 fixes
- `CURRENT_STATUS.md` - This file
- `README.md` - Project overview

---

## 📊 CURRENT SERVER STATUS

Run this to check what's running:
```bash
echo "=== Backend ==="
curl -s http://localhost:8000/api/v1/health 2>&1 | head -1

echo -e "\n=== Frontend ==="
curl -s http://localhost:3000 2>&1 | grep -o "<title>.*</title>"

echo -e "\n=== Processes ==="
ps aux | grep -E "uvicorn|vite" | grep -v grep
```

---

## 🎯 NEXT STEPS

### To Make Fully Functional:

1. **Fix Database Access**:
   - Set up VPN/network access to Azure PostgreSQL, OR
   - Set up local PostgreSQL instance, OR
   - Use mock/development mode without database

2. **Once Database is Accessible**:
   - Application creation will work
   - File uploads will work
   - Validation will run
   - Results will be stored

3. **Production Deployment**:
   - Build frontend: `cd frontend && npm run build`
   - Configure production environment variables
   - Set up proper PostgreSQL connection
   - Deploy to Azure/cloud platform

---

## ✅ WHAT YOU CAN TEST NOW (Without Database)

Even without database access, you can verify:

1. ✅ **UI Loads**: Open http://localhost:3000/new-application
2. ✅ **Backend Connection**: See green "Backend connected" alert
3. ✅ **Form Validation**: Try invalid application references
4. ✅ **File Validation**: Try uploading non-PDF, empty files, duplicates
5. ✅ **Error Handling**: See specific error messages
6. ✅ **No CORS Errors**: All requests go through proxy

The only thing that fails is the actual upload (due to database), but you can see:
- ✅ File selection working
- ✅ Progress bars appearing
- ✅ Error handling with retry buttons
- ✅ Clear error messages ("failed to resolve host...")

---

## 📞 SUPPORT

### Logs
- Backend: `/tmp/planproof_backend.log`
- Frontend: `/tmp/planproof_frontend.log`

### Check Status
```bash
# Health checks
curl http://localhost:8000/api/v1/health
curl http://localhost:3000/api/v1/health

# View logs
tail -f /tmp/planproof_backend.log
tail -f /tmp/planproof_frontend.log
```

### Stop Servers
```bash
# If you used start_servers.sh, it shows PIDs
kill <backend_pid> <frontend_pid>

# Or kill all
pkill -f uvicorn
pkill -f vite
```

---

**All Fixes Committed**: ✅
**Branch**: `claude/fix-app-screen-ui-LW99P`
**Ready for PR**: ✅
