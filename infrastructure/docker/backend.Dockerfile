# Multi-stage build for production-ready backend

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

LABEL maintainer="team@planproof.com"
LABEL description="PlanProof - AI-powered planning application validation system"
LABEL version="1.0.0"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /usr/local

# Copy application code
COPY backend/planproof/ ./planproof/
COPY backend/alembic/ ./alembic/
COPY backend/alembic.ini .
COPY backend/main.py .
COPY backend/run_api.py .
COPY backend/pyproject.toml .

# Create necessary directories
RUN mkdir -p runs data && chmod 777 runs data

# Copy entry point script first (before user creation)
COPY backend/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create non-root user
RUN useradd -m -u 1000 planproof && \
    chown -R planproof:planproof /app

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Switch to non-root user
USER planproof

ENTRYPOINT ["/bin/bash", "/usr/local/bin/docker-entrypoint.sh"]

# Default command: run FastAPI with uvicorn
CMD ["uvicorn", "planproof.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
