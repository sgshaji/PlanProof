# PlanProof - Local Setup Guide

**Choose your preferred setup method**

---

## 🐳 Option 1: Docker Setup (Recommended ⭐)

**Easiest and cleanest way - Everything runs in containers**

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Git
- Your `.env` file

### Quick Start

```bash
# Clone repository
git clone https://github.com/sgshaji/PlanProof.git
cd PlanProof

# Start everything with Docker
docker-compose up -d

# View logs
docker-compose logs -f
```

**Done!** 🎉

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs

### Development with Hot Reload

```bash
# Use dev configuration for auto-reload
docker-compose -f docker-compose.dev.yml up
```

Code changes automatically reload - no restart needed!

### Stop Services

```bash
docker-compose down
```

**📖 Full Docker Guide**: See [DOCKER_SETUP.md](./DOCKER_SETUP.md)

---

## 🔧 Option 2: Manual Setup

**For developers who prefer traditional setup**

---

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Git
- Python 3.11+
- Node.js 18+
- npm

---

## 📥 Step 1: Clone the Repository

```bash
git clone https://github.com/sgshaji/PlanProof.git
cd PlanProof

# Checkout the branch with all fixes
git checkout claude/fix-app-screen-ui-LW99P
```

---

## ⚙️ Step 2: Backend Setup

```bash
# Install Python dependencies
pip install -e .

# Create .env file (copy from repository)
cp .env.example .env

# Edit .env and add your Azure credentials:
# - AZURE_STORAGE_CONNECTION_STRING
# - AZURE_DOCINTEL_ENDPOINT + KEY
# - AZURE_OPENAI_ENDPOINT + KEY
# - DATABASE_URL

# Start backend
python run_api.py
```

Backend will run on: **http://localhost:8000**

---

## 🎨 Step 3: Frontend Setup

```bash
# In a new terminal
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Start frontend
npm run dev
```

Frontend will run on: **http://localhost:3000**

---

## 🌐 Step 4: Open in Browser

Open your browser to: **http://localhost:3000/new-application**

You should see:
- ✅ Green "Backend server is connected and healthy" alert
- ✅ Form for Application Reference
- ✅ File upload drag & drop area
- ✅ All UI features working

---

## ✅ What You'll Be Able to Test

### 1. Backend Connection Monitor
- Green/red status alerts
- Retry button when offline

### 2. Form Validation
- Try `AB` → Error: "at least 3 characters"
- Try `APP@123` → Error: "invalid characters"
- Try `APP-2025-001` → Accepted ✅

### 3. File Validation
- Upload .txt → Rejected "Only PDF files allowed"
- Upload PDF → Accepted ✅
- Add same file twice → "File already added"

### 4. Upload Flow
- See per-file progress bars
- Individual file tracking
- Error handling with retry
- Clear error messages

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
pip install -r requirements.txt
```

### Frontend won't start
```bash
# Check Node version
node --version  # Should be 18+

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### CORS errors
Check `frontend/.env` has:
```
VITE_API_URL=/api
```

### Database errors (expected)
If you get database connection errors, that's expected if you don't have access to the Azure PostgreSQL instance. The UI will still work perfectly - just the upload save will fail.

---

## 📊 All Fixes Included

This branch (`claude/fix-app-screen-ui-LW99P`) includes:

✅ **28 bugs fixed**:
- Backend server configuration
- CORS resolution
- Per-file progress tracking
- File validation (size, format, duplicates)
- Application reference validation
- Backend health monitoring
- Enhanced error messages
- Retry functionality
- React Router warnings fixed
- API timeout handling
- Visual feedback (icons, colors)
- Loading states

✅ **Documentation**:
- TESTING_GUIDE.md - Complete testing checklist
- FIXES_SUMMARY.md - All 28 fixes detailed
- CURRENT_STATUS.md - Status & troubleshooting

✅ **Scripts**:
- start_servers.sh - Auto-start both servers
- test_ui_automated.sh - Automated tests

---

## 🎯 Expected Behavior

### What Works ✅
- Page loads without errors
- Backend connection monitoring
- All form validation
- All file validation
- Progress tracking
- Error handling
- Retry functionality
- All visual feedback

### What Might Not Work ❌
- Database operations (if Azure DB not accessible)
- But this doesn't affect UI testing!

---

## 📸 What You Should See

### On Page Load:
```
┌─────────────────────────────────────────┐
│  New Planning Application               │
│                                         │
│  ✅ Backend server is connected        │
│     and healthy                         │
│                                         │
│  Application Reference *                │
│  [                                  ]   │
│                                         │
│  Applicant Name (Optional)             │
│  [                                  ]   │
│                                         │
│  Upload Documents                       │
│  ┌───────────────────────────────────┐ │
│  │   📤                              │ │
│  │   Drag & drop PDF files here      │ │
│  │   or click to browse              │ │
│  └───────────────────────────────────┘ │
│                                         │
│  [ Start Validation ] (disabled)        │
└─────────────────────────────────────────┘
```

### After Adding Files:
```
Selected Files (2)
┌──────────────────────────────────────┐
│ ✓ document.pdf        0.67 MB    ×  │
│ ✓ plan.pdf            0.29 MB    ×  │
└──────────────────────────────────────┘

[ Start Validation ] (enabled)
```

### During Upload:
```
Selected Files (2)
┌──────────────────────────────────────┐
│ 🔄 document.pdf       0.67 MB       │
│ ▓▓▓▓▓▓▓▓░░░░░░░ 45% uploaded       │
│                                      │
│ ⏸ plan.pdf            0.29 MB       │
│ ░░░░░░░░░░░░░░░ 0% pending         │
└──────────────────────────────────────┘
```

---

## 🎉 Success!

Once you can see the UI in your browser:
- All 28 bugs are fixed
- UI works perfectly
- You can test all features
- Clear documentation included

**The only limitation** is database access (which you may or may not have depending on your network).

---

**Enjoy testing the completely fixed UI!** 🚀
