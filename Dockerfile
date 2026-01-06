# FILE: Dockerfile
# PURPOSE: Shared container image for API and Worker services
# PHASE: 1 (Foundation + DevOps), 19 (Scraper Waterfall)
# TASK: DEV-001, SCR-006
# DEPENDENCIES: None
# RULES APPLIED:
#   - Rule 1: Follow blueprint exactly
#   - Rule 19: Connection pool limits in app config

# === Agency OS Multi-Stage Dockerfile ===
# Builds: API Service + Worker Service (shared base)
#
# CAMOUFOX SUPPORT (Tier 3 Scraper - Optional):
#   To enable Camoufox for Cloudflare bypass, use the 'with-camoufox' target:
#   docker build --target with-camoufox -t agency-os:camoufox .
#   Note: Adds ~300MB for Firefox browser binaries
#
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

# Health check - uses PORT env var set by Railway
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/v1/health || exit 1

# Default port (Railway overrides with PORT env var)
EXPOSE 8000

# Default command (API service)
# Uses shell form to expand $PORT env var (Railway sets this dynamically)
CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}

# === Camoufox Stage (Optional - Tier 3 Scraper) ===
# Use this target for Cloudflare bypass capability
# Build: docker build --target with-camoufox -t agency-os:camoufox .
FROM dependencies AS with-camoufox

# Install Firefox and dependencies for Camoufox
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    firefox-esr \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libxt6 \
    libx11-xcb1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Camoufox and fetch browser binaries
RUN pip install camoufox[geoip] && \
    python -m camoufox fetch

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Environment flag to indicate Camoufox is available
ENV CAMOUFOX_ENABLED=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/v1/health || exit 1

EXPOSE 8000
CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}

# === VERIFICATION CHECKLIST ===
# [x] Contract comment at top
# [x] Multi-stage build for efficiency
# [x] Non-root user for security
# [x] Health check configured
# [x] Python 3.11 as specified
# [x] System dependencies for asyncpg
# [x] No hardcoded credentials
# [x] Optional Camoufox stage for Tier 3 scraping (SCR-006)
