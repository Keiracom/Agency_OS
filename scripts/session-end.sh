#!/bin/bash
# Session-end hook: regenerates dashboard data
# Call manually or hook into clawdbot session lifecycle

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(dirname "$SCRIPT_DIR")"

echo "🔄 Regenerating dashboard data..."
cd "$WORKSPACE"

if [[ -x "$SCRIPT_DIR/generate-dashboard-data.sh" ]]; then
    "$SCRIPT_DIR/generate-dashboard-data.sh"
    echo "✅ Dashboard data updated"
else
    echo "⚠️  generate-dashboard-data.sh not found or not executable"
    exit 1
fi

# Future hooks can go here:
# - Git commit memory changes
# - Sync to remote
# - Notify integrations

echo "✅ Session-end complete"
