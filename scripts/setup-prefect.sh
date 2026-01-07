#!/bin/bash
# FILE: scripts/setup-prefect.sh
# PURPOSE: Initialize Prefect work pool and deploy flows
# PHASE: 5 (Orchestration)
# TASK: ORC-012
#
# USAGE:
#   export PREFECT_API_URL=https://your-prefect-server.railway.app/api
#   ./scripts/setup-prefect.sh

set -e

echo "=========================================="
echo "Prefect Setup Script"
echo "=========================================="

# Check PREFECT_API_URL
if [ -z "$PREFECT_API_URL" ]; then
    echo "ERROR: PREFECT_API_URL not set"
    echo ""
    echo "Usage:"
    echo "  export PREFECT_API_URL=https://prefect-server-production-xxxx.up.railway.app/api"
    echo "  ./scripts/setup-prefect.sh"
    exit 1
fi

echo "Prefect API URL: $PREFECT_API_URL"
echo ""

# Test connection
echo "Testing connection to Prefect server..."
if ! curl -sf "$PREFECT_API_URL/health" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to Prefect server at $PREFECT_API_URL"
    exit 1
fi
echo "Connected successfully!"
echo ""

# Create work pool
echo "Creating work pool 'agency-os-pool'..."
python -m prefect work-pool create agency-os-pool --type process 2>/dev/null && echo "Work pool created!" || echo "Work pool already exists"
echo ""

# List work pools
echo "Current work pools:"
python -m prefect work-pool ls
echo ""

# Deploy flows
echo "Deploying flows from prefect.yaml..."
python -m prefect deploy --all
echo ""

# List deployments
echo "Current deployments:"
python -m prefect deployment ls
echo ""

echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start the worker: prefect worker start --pool agency-os-pool"
echo "2. Or deploy the worker service to Railway"
echo "3. Access Prefect UI at: ${PREFECT_API_URL%/api}"
