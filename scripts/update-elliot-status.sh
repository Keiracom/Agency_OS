#!/bin/bash
# Update Elliot status for mobile app

cd /tmp/elliot-status || exit 1

# Get current session status from clawdbot
STATUS=$(clawdbot status 2>/dev/null || echo "")

# Extract context percentage
CONTEXT=$(echo "$STATUS" | grep -oP 'Context: \K[0-9]+' || echo "0")

# Get current timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Create updated status.json
cat > status.json << EOF
{
  "lastUpdated": "$TIMESTAMP",
  "scoreboard": {
    "tasksCompletedToday": ${TASKS_TODAY:-0},
    "needsAttention": ${NEEDS_ATTENTION:-0},
    "health": "${HEALTH:-green}",
    "currentlyWorkingOn": ${WORKING_ON:-'["Ready for tasks"]'},
    "recentWins": ${RECENT_WINS:-'[]'},
    "blockers": []
  },
  "metrics": {
    "contextPercent": $CONTEXT,
    "tokens": {"input": 0, "output": 0, "costEstimate": 0},
    "sessions": {"count": 1, "uptimeHours": 0},
    "model": "claude-opus-4-5",
    "memory": {"dailyLogCount": 0, "patternCount": 0, "lastMaintenance": null},
    "cronJobs": [],
    "responseTime": {"avg": 0, "p95": 0, "unit": "seconds"}
  }
}
EOF

# Push to GitHub
git add status.json
git commit -m "Update status: $TIMESTAMP" --allow-empty
git push origin main

echo "Status updated at $TIMESTAMP"
