# 🐳 Docker Setup for Windows - Step by Step

**Complete guide to install Docker and run PlanProof**

---

## 📋 Part 1: Install Docker Desktop (One-Time Setup)

### Step 1: Download Docker Desktop

1. Go to: https://www.docker.com/products/docker-desktop/
2. Click **"Download for Windows"**
3. Wait for `Docker Desktop Installer.exe` to download (~500MB)

### Step 2: Install Docker Desktop

1. **Run the installer** (`Docker Desktop Installer.exe`)
2. **Accept** the license agreement
3. **Keep default settings**:
   - ✅ Use WSL 2 instead of Hyper-V (recommended)
   - ✅ Add shortcut to desktop
4. Click **"Install"**
5. Wait for installation to complete (~5 minutes)
6. Click **"Close and restart"** when prompted

### Step 3: Start Docker Desktop

1. **After restart**, Docker Desktop should start automatically
2. If not, search for **"Docker Desktop"** in Start Menu and open it
3. **Wait for Docker to start** (you'll see "Docker Desktop is running" in the system tray)
4. Accept the **Docker Subscription Service Agreement** if prompted

### Step 4: Verify Docker is Working

Open PowerShell and run:

```powershell
docker --version
docker-compose --version
```

Expected output:
```
Docker version 24.x.x, build xxxxxxx
Docker Compose version v2.x.x
```

✅ **Docker is ready!** You only need to do this once.

---

## 🚀 Part 2: Run PlanProof with Docker

### Quick Commands (Copy & Paste)

Open PowerShell in your PlanProof directory:

```powershell
# Navigate to project
cd "D:\Aathira Docs\PlanProof"

# Build and start containers (first time takes 5-10 minutes to download images)
docker-compose up -d

# Watch the logs (Ctrl+C to stop watching, containers keep running)
docker-compose logs -f
```

### What's Happening?

1. **First run** (5-10 minutes):
   - Downloads Python base image (~400MB)
   - Downloads Node.js image (~300MB)
   - Downloads Nginx image (~50MB)
   - Builds backend container
   - Builds frontend container
   - Starts both containers

2. **Subsequent runs** (<30 seconds):
   - Uses cached images
   - Just starts containers

### Access Your Application

Once containers are running (look for "Application startup complete" in logs):

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 📊 Useful Docker Commands

### Check Status

```powershell
# See running containers
docker-compose ps

# Check health status
docker ps

# See resource usage
docker stats
```

Expected output for `docker-compose ps`:
```
NAME                    STATUS
planproof-frontend      Up 2 minutes (healthy)
planproof-backend       Up 2 minutes (healthy)
```

### View Logs

```powershell
# All logs
docker-compose logs

# Follow logs (live updates)
docker-compose logs -f

# Just backend logs
docker-compose logs -f backend

# Just frontend logs
docker-compose logs -f frontend

# Last 50 lines
docker-compose logs --tail=50
```

### Stop & Start

```powershell
# Stop containers (keeps data)
docker-compose down

# Start again
docker-compose up -d

# Restart everything
docker-compose restart

# Restart just backend
docker-compose restart backend
```

### Clean Restart

```powershell
# Stop and remove everything
docker-compose down -v

# Rebuild from scratch
docker-compose build --no-cache

# Start fresh
docker-compose up -d
```

---

## 🔍 Troubleshooting

### Problem: "docker: command not found"

**Solution**: Docker Desktop is not running.

1. Open **Docker Desktop** from Start Menu
2. Wait for "Docker Desktop is running" in system tray
3. Try command again

### Problem: "port is already allocated"

**Solution**: Port 3000 or 8000 is in use.

```powershell
# Check what's using port 8000
netstat -ano | findstr :8000

# Kill process (replace 1234 with actual PID)
Stop-Process -Id 1234 -Force

# Or change port in docker-compose.yml
# ports:
#   - "8001:8000"  # Uses port 8001 instead
```

### Problem: Containers keep restarting

**Solution**: Check logs for errors.

```powershell
docker-compose logs backend

# Common issues:
# - Missing .env file
# - Invalid DATABASE_URL
# - Azure credentials expired
```

### Problem: "Cannot connect to Docker daemon"

**Solution**: Docker Desktop is not fully started.

1. Open Docker Desktop
2. Wait for "Engine running" status (bottom left)
3. Try command again

### Problem: Build takes forever

**Solution**: First build downloads large images.

- Python image: ~400MB
- Node image: ~300MB
- Total time: 5-10 minutes (one-time only)
- Subsequent builds: <1 minute

### Problem: Frontend can't reach backend

**Solution**: Check backend health.

```powershell
# Test backend directly
curl http://localhost:8000/health

# Should return: {"status":"healthy"}

# If not working, check backend logs
docker-compose logs backend
```

---

## 🧪 Testing the Setup

### 1. Check Docker is Running

```powershell
docker --version
```

### 2. Start Containers

```powershell
cd "D:\Aathira Docs\PlanProof"
docker-compose up -d
```

### 3. Wait for Startup

```powershell
# Watch logs until you see "Application startup complete"
docker-compose logs -f backend
```

Press `Ctrl+C` when you see startup complete.

### 4. Check Health

```powershell
# Backend health
curl http://localhost:8000/health

# Container status
docker-compose ps
```

### 5. Open Browser

Open: http://localhost:3000

You should see the PlanProof application!

### 6. Test API

Open: http://localhost:8000/docs

You should see the Swagger API documentation.

---

## 🔄 Development Workflow

### Option A: Production Mode (Optimized)

```powershell
# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

**When to use**: Testing, demos, production-like environment

### Option B: Development Mode (Hot Reload)

```powershell
# Start with hot reload
docker-compose -f docker-compose.dev.yml up

# Make code changes - they reload automatically!

# Stop with Ctrl+C
```

**When to use**: Active development, code changes auto-reload

---

## 📝 Summary Checklist

- [ ] Docker Desktop installed
- [ ] Docker Desktop running (system tray icon)
- [ ] `.env` file exists with Azure credentials
- [ ] PowerShell open in project directory
- [ ] Run: `docker-compose up -d`
- [ ] Wait for containers to start (~2-5 minutes)
- [ ] Check: http://localhost:3000
- [ ] Check: http://localhost:8000/docs

---

## 🆘 Need Help?

### Quick Diagnostics

```powershell
# Run this to check everything
docker --version
docker ps
docker-compose ps
netstat -ano | findstr ":8000 :3000"
```

Paste the output if you need help!

### Common Commands Cheat Sheet

```powershell
# Start
docker-compose up -d

# Logs
docker-compose logs -f

# Status
docker-compose ps

# Stop
docker-compose down

# Restart
docker-compose restart

# Clean restart
docker-compose down -v && docker-compose up -d --build

# Shell access
docker exec -it planproof-backend bash
docker exec -it planproof-frontend sh
```

---

## 🎯 What's Next?

Once Docker is running:

1. ✅ Frontend available at: http://localhost:3000
2. ✅ Backend API at: http://localhost:8000
3. ✅ Try uploading a PDF
4. ✅ Test the validation workflow
5. ✅ Check [DOCKER_SETUP.md](./DOCKER_SETUP.md) for advanced usage

**Your manual setup issues are now gone!** 🎉
