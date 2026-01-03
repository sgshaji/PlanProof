# 🐳 Docker Setup Guide - PlanProof

**The easiest and cleanest way to run PlanProof**

---

## 📋 Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac/Linux)
- Git
- Your `.env` file with Azure credentials

---

## 🚀 Quick Start (2 Commands!)

### 1. Clone & Configure

```bash
git clone https://github.com/sgshaji/PlanProof.git
cd PlanProof

# Make sure your .env file exists with Azure credentials
# (It's already there based on your setup!)
```

### 2. Start Everything

```bash
# Production mode (optimized builds)
docker-compose up -d

# OR Development mode (with hot reload)
docker-compose -f docker-compose.dev.yml up
```

**That's it!** 🎉

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 📦 What Gets Deployed?

### Production Mode (`docker-compose.yml`)
- ✅ **Backend**: FastAPI running with Uvicorn
- ✅ **Frontend**: React/Vite built and served with Nginx
- ✅ **Database**: Uses your Azure PostgreSQL
- ✅ **Storage**: Azure Blob Storage
- ✅ **AI**: Azure OpenAI + Document Intelligence

### Development Mode (`docker-compose.dev.yml`)
- 🔥 **Hot Reload**: Code changes auto-refresh
- 🐛 **Debug Mode**: Enhanced logging
- 📂 **Volume Mounts**: Source code mounted from host
- ⚡ **Fast Iteration**: No rebuild needed for code changes

---

## 🎯 Common Commands

### Start Services

```bash
# Production (builds once, optimized)
docker-compose up -d

# Development (hot reload)
docker-compose -f docker-compose.dev.yml up

# Rebuild and start (after dependency changes)
docker-compose up -d --build
```

### View Logs

```bash
# All services
docker-compose logs -f

# Just backend
docker-compose logs -f backend

# Just frontend
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100
```

### Stop Services

```bash
# Stop (preserves data)
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop development mode
docker-compose -f docker-compose.dev.yml down
```

### Check Status

```bash
# See running containers
docker-compose ps

# Check health
docker ps

# Check resource usage
docker stats
```

---

## 🔧 Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Mac/Linux

# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Maps host:8001 -> container:8000
```

### Container Won't Start

```bash
# Check logs for errors
docker-compose logs backend

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Database Connection Issues

```bash
# Verify DATABASE_URL in .env
cat .env | grep DATABASE_URL

# Test from container
docker exec -it planproof-backend curl http://localhost:8000/health
```

### Frontend Can't Reach Backend

```bash
# Check network
docker network inspect planproof_planproof-network

# Verify backend is healthy
curl http://localhost:8000/health
```

---

## 🔄 Development Workflow

### 1. Start Development Environment

```bash
docker-compose -f docker-compose.dev.yml up
```

### 2. Make Code Changes

Edit files in:
- `planproof/` - Backend Python code
- `frontend/src/` - Frontend React code

**Changes auto-reload!** ♻️

### 3. Add Dependencies

**Backend (Python):**
```bash
# Edit requirements.txt, then:
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml build backend
docker-compose -f docker-compose.dev.yml up
```

**Frontend (Node):**
```bash
# Edit frontend/package.json, then:
docker-compose -f docker-compose.dev.yml restart frontend
```

### 4. Database Migrations

```bash
# Run migrations
docker exec -it planproof-backend-dev alembic upgrade head

# Create new migration
docker exec -it planproof-backend-dev alembic revision --autogenerate -m "description"
```

---

## 📊 Health Checks

All services include health checks:

```bash
# Backend health
curl http://localhost:8000/health

# Frontend health (production only)
curl http://localhost:3000/health

# Check Docker health status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Expected output:
```
NAMES                    STATUS
planproof-frontend       Up 2 minutes (healthy)
planproof-backend        Up 2 minutes (healthy)
```

---

## 🌐 Accessing Services

### From Your Browser
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### From Host Machine (Terminal)
```bash
curl http://localhost:8000/health
curl http://localhost:3000
```

### Between Containers
Backend is accessible as `backend:8000` from frontend container.

---

## 🔐 Environment Variables

Your `.env` file is automatically loaded. Required variables:

```bash
# Azure PostgreSQL (already configured)
DATABASE_URL=postgresql://...

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=...
AZURE_STORAGE_CONTAINER_NAME=inbox

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini

# Azure Document Intelligence
AZURE_DOCINTEL_ENDPOINT=...
AZURE_DOCINTEL_KEY=...

# Authentication
JWT_SECRET_KEY=...
```

---

## 🚀 Production Deployment

### Build Production Images

```bash
# Build both services
docker-compose build

# Tag for registry
docker tag planproof_backend:latest myregistry/planproof-backend:v1.0
docker tag planproof_frontend:latest myregistry/planproof-frontend:v1.0

# Push to registry
docker push myregistry/planproof-backend:v1.0
docker push myregistry/planproof-frontend:v1.0
```

### Deploy to Azure Container Apps

```bash
# See docs/DEPLOYMENT.md for full instructions

az containerapp up \
  --name planproof-backend \
  --resource-group planproof-rg \
  --image myregistry/planproof-backend:v1.0 \
  --env-vars-file .env \
  --ingress external \
  --target-port 8000
```

---

## 💡 Benefits Over Manual Setup

| Manual Setup | Docker Setup |
|--------------|--------------|
| Install Python 3.11 | ✅ Included |
| Install Node.js 18 | ✅ Included |
| Setup virtual env | ✅ Automatic |
| Install PostgreSQL | ✅ Uses Azure |
| Manage processes | ✅ Docker handles |
| Port conflicts | ✅ Isolated |
| "Works on my machine" | ✅ Same everywhere |
| Setup time: ~20 min | ✅ Setup time: ~2 min |

---

## 📚 Next Steps

1. ✅ **Start Development**: `docker-compose -f docker-compose.dev.yml up`
2. 📝 **Check API Docs**: http://localhost:8000/docs
3. 🎨 **Open Frontend**: http://localhost:3000
4. 🧪 **Run Tests**: See [TESTING_GUIDE.md](../TESTING_GUIDE.md)
5. 🚀 **Deploy**: See [docs/DEPLOYMENT.md](./DEPLOYMENT.md)

---

## 🆘 Need Help?

- **Logs**: `docker-compose logs -f`
- **Shell Access**: `docker exec -it planproof-backend bash`
- **Restart**: `docker-compose restart`
- **Clean Start**: `docker-compose down -v && docker-compose up -d`

For more help, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
