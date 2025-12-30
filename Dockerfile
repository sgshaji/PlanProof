# Multi-stage build for production-ready image

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
COPY requirements.txt .
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
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY planproof/ ./planproof/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY artefacts/ ./artefacts/
COPY main.py .
COPY run_ui.py .
COPY pyproject.toml .

# Create runs directory
RUN mkdir -p runs && chmod 777 runs

# Create non-root user
RUN useradd -m -u 1000 planproof && \
    chown -R planproof:planproof /app

# Switch to non-root user
USER planproof

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Entry point script
COPY --chown=planproof:planproof docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]

# Default command: run Streamlit UI
CMD ["streamlit", "run", "planproof/ui/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
