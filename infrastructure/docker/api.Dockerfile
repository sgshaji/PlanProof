# FastAPI Backend Dockerfile
FROM python:3.11-slim

LABEL maintainer="team@planproof.com"
LABEL description="PlanProof FastAPI Backend"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY planproof/ ./planproof/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY artefacts/ ./artefacts/
COPY run_api.py .

# Create non-root user
RUN useradd -m -u 1000 apiuser && \
    chown -R apiuser:apiuser /app

# Switch to non-root user
USER apiuser

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the FastAPI application
CMD ["python3", "run_api.py"]
