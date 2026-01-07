#!/bin/bash
# FILE: scripts/start-prefect-server.sh
# PURPOSE: Start Prefect server with Railway's dynamic port
# PHASE: 5 (Orchestration)
# TASK: ORC-012

set -e

# Use Railway's PORT or default to 4200
PORT=${PORT:-4200}

echo "Starting Prefect server on port $PORT..."

# Configure Prefect server
export PREFECT_SERVER_API_HOST=0.0.0.0
export PREFECT_SERVER_API_PORT=$PORT

# If database URL provided, use PostgreSQL; otherwise use SQLite
if [ -n "$PREFECT_API_DATABASE_CONNECTION_URL" ]; then
    echo "Using PostgreSQL database for Prefect metadata"
else
    echo "Using SQLite database for Prefect metadata (not recommended for production)"
fi

# Start the Prefect server
exec prefect server start --host 0.0.0.0 --port $PORT
