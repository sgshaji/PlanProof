# Docker Development Environment

This guide explains how to run PlanProof using Docker for development with proper CORS configuration.

## Prerequisites

1. **Docker & Docker Compose** installed
2. **Environment file** (`.env`) in the project root with required variables:
   ```bash
   # Copy the example and fill in your credentials
   cp ../../config/production.env.example ../../.env
   ```

## Quick Start

1. **Navigate to the docker directory:**
   ```bash
   cd infrastructure/docker
   ```

2. **Start the services:**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

3. **Access the application:**
   | Service | URL | Description |
   |---------|-----|-------------|
   | Frontend | http://localhost:3001 | React app (Vite dev server) |
   | Backend API | http://localhost:8000 | FastAPI server |
   | API Docs | http://localhost:8000/api/docs | Swagger UI |

4. **View logs:**
   ```bash
   docker-compose -f docker-compose.dev.yml logs -f
   ```

## CORS Configuration Explained

### Frontend Configuration

The frontend uses **relative URLs** for API requests, which allows Vite's proxy to forward them to the backend:

- **`VITE_API_URL`**: Empty (uses relative URLs)
- **`DOCKER_ENV=true`**: Signals Vite to proxy to Docker network
- **`vite.config.ts`**: Proxy configuration routes `/api/*` requests
  - When running in Docker: Uses `http://backend:8000` (internal Docker network)
  - When running locally: Uses `http://localhost:8000`

### Backend Configuration

The backend allows specific origins via the `API_CORS_ORIGINS` environment variable in your `.env`:

```
API_CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002
```

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (http://localhost:3001)                                │
│  └── Makes API request to /api/v1/runs/...                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Frontend Container (Vite Dev Server)                           │
│  └── Proxy intercepts /api/* requests                          │
│  └── Forwards to http://backend:8000 (Docker network)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend Container (FastAPI)                                    │
│  └── Receives request, validates CORS origin                   │
│  └── Returns response with Access-Control-Allow-Origin header  │
└─────────────────────────────────────────────────────────────────┘
```

## Common Commands

### Start services in background
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### View logs
```bash
docker-compose -f docker-compose.dev.yml logs -f
```

### Stop services
```bash
docker-compose -f docker-compose.dev.yml down
```

### Rebuild after code changes
```bash
docker-compose -f docker-compose.dev.yml up --build
```

### Restart a single service
```bash
docker-compose -f docker-compose.dev.yml restart backend
docker-compose -f docker-compose.dev.yml restart frontend
```

## Troubleshooting CORS Issues

### Issue: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Solution:**
1. Verify `VITE_API_URL` is empty in `frontend/.env`
2. Ensure backend `API_CORS_ORIGINS` includes `http://localhost:3000`
3. Restart both services after configuration changes

### Issue: "Network error" or "Failed to fetch"

**Solution:**
1. Check backend is running: `curl http://localhost:8000/api/v1/health`
2. Check frontend proxy configuration in `vite.config.ts`
3. Verify Docker network is working: `docker network ls | grep planproof`

### Issue: Changes not reflected

**Solution:**
- **Backend changes**: Auto-reloads with mounted volumes
- **Frontend changes**: Auto-reloads with Vite HMR
- **Configuration changes**: Restart services:
  ```bash
  docker-compose -f docker-compose.dev.yml restart
  ```

## Environment Variables

Key environment variables for CORS configuration:

### Frontend
- `VITE_API_URL=` - Leave empty for development with proxy
- `DOCKER_ENV=true` - Signals to use Docker network hostnames

### Backend
- `API_CORS_ORIGINS` - Array of allowed origins (JSON format)
- `APP_ENV=development` - Enables debug logging

## Volume Mounts

The docker-compose file mounts source code for hot reloading:

### Backend
- `./planproof:/app/planproof` - Python source code
- `./runs:/app/runs` - Analysis results
- `./data:/app/data` - Sample data

### Frontend
- `./frontend:/app` - React source code
- `/app/node_modules` - Isolated npm dependencies

## Health Checks

The backend includes a health check endpoint:

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "azure_services": "configured"
}
```

## Next Steps

- See [../docs/QUICKSTART.md](../../docs/QUICKSTART.md) for usage guide
- See [../docs/TROUBLESHOOTING.md](../../docs/TROUBLESHOOTING.md) for more issues
- See [../docs/DEPLOYMENT.md](../../docs/DEPLOYMENT.md) for production deployment
