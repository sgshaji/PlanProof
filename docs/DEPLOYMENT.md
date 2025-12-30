# PlanProof Deployment Guide

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Local Development Deployment](#local-development-deployment)
- [Docker Deployment](#docker-deployment)
- [Azure Deployment](#azure-deployment)
- [Production Considerations](#production-considerations)
- [Monitoring & Maintenance](#monitoring--maintenance)

---

## Overview

This guide covers deploying PlanProof in various environments, from local development to production Azure infrastructure.

**Deployment Options**:
1. **Local Development** - Direct Python with local PostgreSQL
2. **Docker Compose** - Containerized for testing
3. **Azure App Service** - Managed PaaS deployment
4. **Azure Container Instances** - Simple container hosting
5. **Azure Kubernetes Service** - Enterprise-scale orchestration

---

## Prerequisites

### Required Services

- ✅ **PostgreSQL 13+** with PostGIS extension
- ✅ **Azure Blob Storage** account
- ✅ **Azure Document Intelligence** resource
- ✅ **Azure OpenAI** resource with deployed model
- ⚠️ **SMTP Server** (optional, for email notifications)

### Required Tools

```bash
# Azure CLI
az --version

# Docker (for container deployments)
docker --version
docker-compose --version

# Kubernetes CLI (for AKS)
kubectl version --client
```

---

## Local Development Deployment

### Step 1: Environment Setup

```bash
# Clone repository
git clone <repo-url>
cd PlanProof

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

Required `.env` variables:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/planproof
AZURE_STORAGE_CONNECTION_STRING=...
AZURE_DOCINTEL_ENDPOINT=...
AZURE_DOCINTEL_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_KEY=...
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
```

### Step 3: Initialize Database

```bash
# Create database
createdb planproof

# Enable PostGIS
psql -d planproof -c "CREATE EXTENSION postgis;"

# Run migrations
alembic upgrade head
```

### Step 4: Start Application

```bash
# Start Streamlit UI
python run_ui.py

# Or use CLI
python main.py --help
```

Application will be available at: `http://localhost:8501`

---

## Docker Deployment

### Using Docker Compose (Recommended)

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  postgres:
    image: postgis/postgis:13-3.1
    environment:
      POSTGRES_DB: planproof
      POSTGRES_USER: planproof
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U planproof"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    environment:
      DATABASE_URL: postgresql://planproof:${DB_PASSWORD}@postgres:5432/planproof
      AZURE_STORAGE_CONNECTION_STRING: ${AZURE_STORAGE_CONNECTION_STRING}
      AZURE_DOCINTEL_ENDPOINT: ${AZURE_DOCINTEL_ENDPOINT}
      AZURE_DOCINTEL_KEY: ${AZURE_DOCINTEL_KEY}
      AZURE_OPENAI_ENDPOINT: ${AZURE_OPENAI_ENDPOINT}
      AZURE_OPENAI_KEY: ${AZURE_OPENAI_KEY}
      AZURE_OPENAI_DEPLOYMENT_NAME: ${AZURE_OPENAI_DEPLOYMENT_NAME}
    ports:
      - "8501:8501"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./runs:/app/runs
    restart: unless-stopped

volumes:
  postgres_data:
```

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run migrations and start app
CMD alembic upgrade head && streamlit run planproof/ui/main.py --server.port 8501 --server.address 0.0.0.0
```

**Deployment**:
```bash
# Create .env file with secrets
cp .env.example .env
# Edit .env

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

---

## Azure Deployment

### Option 1: Azure App Service

**Step 1: Create Resources**

```bash
# Login to Azure
az login

# Create resource group
az group create --name planproof-rg --location uksouth

# Create App Service Plan
az appservice plan create \
  --name planproof-plan \
  --resource-group planproof-rg \
  --sku B2 \
  --is-linux

# Create Web App
az webapp create \
  --resource-group planproof-rg \
  --plan planproof-plan \
  --name planproof-app \
  --runtime "PYTHON:3.11"
```

**Step 2: Configure Application**

```bash
# Set environment variables
az webapp config appsettings set \
  --resource-group planproof-rg \
  --name planproof-app \
  --settings \
    DATABASE_URL="postgresql://..." \
    AZURE_STORAGE_CONNECTION_STRING="..." \
    AZURE_DOCINTEL_ENDPOINT="..." \
    AZURE_DOCINTEL_KEY="..." \
    AZURE_OPENAI_ENDPOINT="..." \
    AZURE_OPENAI_KEY="..." \
    AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o-mini"

# Configure startup command
az webapp config set \
  --resource-group planproof-rg \
  --name planproof-app \
  --startup-file "streamlit run planproof/ui/main.py --server.port 8000 --server.address 0.0.0.0"
```

**Step 3: Deploy**

```bash
# Deploy from local Git
git remote add azure <deployment-url>
git push azure main

# Or deploy ZIP
az webapp deployment source config-zip \
  --resource-group planproof-rg \
  --name planproof-app \
  --src planproof.zip
```

### Option 2: Azure Container Registry + Container Instances

**Step 1: Create Container Registry**

```bash
# Create ACR
az acr create \
  --resource-group planproof-rg \
  --name planproofacr \
  --sku Basic

# Login to ACR
az acr login --name planproofacr
```

**Step 2: Build and Push Image**

```bash
# Build image
docker build -t planproof:latest .

# Tag for ACR
docker tag planproof:latest planproofacr.azurecr.io/planproof:latest

# Push to ACR
docker push planproofacr.azurecr.io/planproof:latest
```

**Step 3: Deploy to Container Instances**

```bash
# Create container instance
az container create \
  --resource-group planproof-rg \
  --name planproof-container \
  --image planproofacr.azurecr.io/planproof:latest \
  --cpu 2 \
  --memory 4 \
  --registry-login-server planproofacr.azurecr.io \
  --registry-username $(az acr credential show --name planproofacr --query username -o tsv) \
  --registry-password $(az acr credential show --name planproofacr --query passwords[0].value -o tsv) \
  --dns-name-label planproof \
  --ports 8501 \
  --environment-variables \
    DATABASE_URL="postgresql://..." \
    AZURE_STORAGE_CONNECTION_STRING="..." \
    AZURE_DOCINTEL_ENDPOINT="..." \
    AZURE_DOCINTEL_KEY="..."

# Get FQDN
az container show \
  --resource-group planproof-rg \
  --name planproof-container \
  --query ipAddress.fqdn
```

### Option 3: Azure Kubernetes Service (AKS)

**Step 1: Create AKS Cluster**

```bash
# Create AKS cluster
az aks create \
  --resource-group planproof-rg \
  --name planproof-aks \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-managed-identity \
  --attach-acr planproofacr

# Get credentials
az aks get-credentials --resource-group planproof-rg --name planproof-aks
```

**Step 2: Create Kubernetes Manifests**

**deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: planproof
spec:
  replicas: 3
  selector:
    matchLabels:
      app: planproof
  template:
    metadata:
      labels:
        app: planproof
    spec:
      containers:
      - name: planproof
        image: planproofacr.azurecr.io/planproof:latest
        ports:
        - containerPort: 8501
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: planproof-secrets
              key: database-url
        - name: AZURE_STORAGE_CONNECTION_STRING
          valueFrom:
            secretKeyRef:
              name: planproof-secrets
              key: storage-connection-string
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: planproof-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8501
  selector:
    app: planproof
```

**Step 3: Deploy to AKS**

```bash
# Create secrets
kubectl create secret generic planproof-secrets \
  --from-literal=database-url="postgresql://..." \
  --from-literal=storage-connection-string="..."

# Apply deployment
kubectl apply -f deployment.yaml

# Get service IP
kubectl get service planproof-service

# View logs
kubectl logs -l app=planproof -f
```

---

## Production Considerations

### Security

1. **Environment Variables**
   - Use Azure Key Vault for secrets
   - Never commit `.env` to version control
   - Rotate keys regularly

2. **Network Security**
   - Configure firewall rules
   - Use VNet integration
   - Enable HTTPS/TLS

3. **Database Security**
   - Use managed PostgreSQL (Azure Database)
   - Enable SSL connections
   - Configure access policies

### Performance

1. **Scaling**
   - Horizontal scaling for UI (multiple instances)
   - Vertical scaling for pipeline processing
   - Consider Azure Functions for background jobs

2. **Caching**
   - Redis for session state
   - CDN for static assets
   - Database query caching

3. **Optimization**
   - Connection pooling (SQLAlchemy)
   - Async processing for long-running tasks
   - Blob storage CDN integration

### Backup & Recovery

```bash
# Database backup
pg_dump -h <host> -U <user> -d planproof > backup.sql

# Restore
psql -h <host> -U <user> -d planproof < backup.sql

# Azure Blob backup
az storage blob download-batch \
  --source planproof-documents \
  --destination ./backup \
  --account-name <storage-account>
```

### High Availability

- **Database**: Azure PostgreSQL with read replicas
- **Storage**: Geo-redundant blob storage (GRS)
- **Compute**: Multi-region deployment with Traffic Manager
- **Monitoring**: Azure Application Insights

---

## Monitoring & Maintenance

### Logging

```python
# Application logs
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Application Insights

```bash
# Install SDK
pip install opencensus-ext-azure

# Configure in code
from opencensus.ext.azure.log_exporter import AzureLogHandler

logger.addHandler(AzureLogHandler(
    connection_string='InstrumentationKey=...'
))
```

### Health Checks

- **Streamlit Health**: `http://localhost:8501/_stcore/health`
- **Database**: Verify PostgreSQL connection
- **Azure Services**: Check blob/docintel/openai connectivity

### Maintenance Tasks

```bash
# Database vacuum
psql -d planproof -c "VACUUM ANALYZE;"

# Clean old runs (older than 90 days)
find runs/ -type d -mtime +90 -exec rm -rf {} \;

# Update dependencies
pip list --outdated
pip install --upgrade <package>

# Database migrations
alembic upgrade head
```

---

## Troubleshooting

### Common Issues

**Issue**: Streamlit won't start
```bash
# Check port availability
netstat -an | grep 8501

# Try different port
streamlit run planproof/ui/main.py --server.port 8502
```

**Issue**: Database connection fails
```bash
# Test connection
psql -h <host> -U <user> -d planproof

# Check firewall rules
az postgres server firewall-rule list \
  --resource-group planproof-rg \
  --server-name planproof-db
```

**Issue**: Azure service authentication fails
```bash
# Verify credentials
az account show

# Test blob storage
az storage blob list \
  --container-name planproof-documents \
  --connection-string "..."
```

For more troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Additional Resources

- [Azure App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [Azure Kubernetes Service](https://docs.microsoft.com/azure/aks/)
- [PostgreSQL Azure](https://docs.microsoft.com/azure/postgresql/)
- [Streamlit Deployment](https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app)
