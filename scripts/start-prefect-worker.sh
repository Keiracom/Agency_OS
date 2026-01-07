#!/bin/bash
# FILE: scripts/start-prefect-worker.sh
# PURPOSE: Start Prefect worker to execute flows
# PHASE: 5 (Orchestration)
# TASK: ORC-012

set -e

echo "Starting Prefect worker..."

# Verify PREFECT_API_URL is set
if [ -z "$PREFECT_API_URL" ]; then
    echo "ERROR: PREFECT_API_URL not set. Set it to your Prefect server URL."
    echo "Example: https://prefect-server-production-xxxx.up.railway.app/api"
    exit 1
fi

echo "Connecting to Prefect server at: $PREFECT_API_URL"

# Wait for Prefect server to be ready
echo "Waiting for Prefect server..."
MAX_RETRIES=30
RETRY_COUNT=0
until curl -sf "$PREFECT_API_URL/health" > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "ERROR: Prefect server not reachable after $MAX_RETRIES attempts"
        exit 1
    fi
    echo "Waiting for Prefect server... (attempt $RETRY_COUNT/$MAX_RETRIES)"
    sleep 5
done

echo "Prefect server is ready!"

# Create work pool if it doesn't exist
echo "Ensuring work pool exists..."
prefect work-pool create agency-os-pool --type process 2>/dev/null || echo "Work pool already exists"

# Deploy flows from prefect.yaml
echo "Deploying flows..."
echo "Current directory: $(pwd)"
echo "Checking prefect.yaml exists..."
if [ ! -f prefect.yaml ]; then
    echo "ERROR: prefect.yaml not found!"
    exit 1
fi

echo "Running prefect deploy --all..."
if ! prefect deploy --all; then
    echo "ERROR: Flow deployment failed!"
    echo "Check the error details above."
    echo "Common issues:"
    echo "  - Missing dependencies in requirements.txt"
    echo "  - Syntax errors in flow files"
    echo "  - Invalid prefect.yaml configuration"
    exit 1
fi
echo "All flows deployed successfully!"

# Start the worker
echo "Starting worker for pool: agency-os-pool"
exec prefect worker start --pool agency-os-pool --name "railway-worker-$(hostname)"
