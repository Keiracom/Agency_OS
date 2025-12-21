# FILE: Dockerfile
# PURPOSE: Shared container image for API and Worker services
# PHASE: 1 (Foundation + DevOps)
# TASK: DEV-001
# DEPENDENCIES: None
# RULES APPLIED:
#   - Rule 1: Follow blueprint exactly
#   - Rule 19: Connection pool limits in app config

# === Agency OS Multi-Stage Dockerfile ===
# Builds: API Service + Worker Service (shared base)
# syntax=docker/dockerfile:1.4

FROM python:3.11-slim AS base

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# === Dependencies Stage ===
FROM base AS dependencies

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# === Production Stage ===
FROM dependencies AS production

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default port
EXPOSE 8000

# Default command (API service)
# Override with docker-compose for worker service
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# === VERIFICATION CHECKLIST ===
# [x] Contract comment at top
# [x] Multi-stage build for efficiency
# [x] Non-root user for security
# [x] Health check configured
# [x] Python 3.11 as specified
# [x] System dependencies for asyncpg
# [x] No hardcoded credentials
