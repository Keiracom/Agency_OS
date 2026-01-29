#!/bin/bash
# Generate dashboard data JSON from Elliot's memory files
# Run this to update /home/elliotbot/clawd/dashboard-data.json

set -e

CLAWD_DIR="/home/elliotbot/clawd"
OUTPUT="$CLAWD_DIR/dashboard-data.json"

# Get current timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Function to safely read file content
read_file() {
    if [ -f "$1" ]; then
        cat "$1"
    else
        echo ""
    fi
}

# Function to escape JSON
escape_json() {
    python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))"
}

# Function to count items from markdown lists
count_items() {
    grep -c "^###\|^- " "$1" 2>/dev/null || echo "0"
}

# Read all memory files
LEARNINGS=$(read_file "$CLAWD_DIR/knowledge/LEARNINGS.md" | escape_json)
RULES=$(read_file "$CLAWD_DIR/knowledge/RULES.md" | escape_json)
DECISIONS=$(read_file "$CLAWD_DIR/knowledge/DECISIONS.md" | escape_json)
PATTERNS=$(read_file "$CLAWD_DIR/memory/PATTERNS.md" | escape_json)
MEMORY=$(read_file "$CLAWD_DIR/MEMORY.md" | escape_json)

# Read task files
BACKLOG=$(read_file "$CLAWD_DIR/tasks/BACKLOG.md" | escape_json)
IN_PROGRESS=$(read_file "$CLAWD_DIR/tasks/IN_PROGRESS.md" | escape_json)

# Get today's date
TODAY=$(date +"%Y-%m-%d")
YESTERDAY=$(date -d "yesterday" +"%Y-%m-%d" 2>/dev/null || date -v-1d +"%Y-%m-%d" 2>/dev/null || echo "")

# Read daily notes
DAILY_TODAY=$(read_file "$CLAWD_DIR/memory/daily/$TODAY.md" | escape_json)
DAILY_YESTERDAY=$(read_file "$CLAWD_DIR/memory/daily/$YESTERDAY.md" | escape_json)

# Count metrics
RULE_COUNT=$(grep -c "^### " "$CLAWD_DIR/knowledge/RULES.md" 2>/dev/null || echo "0")
LEARNING_COUNT=$(grep -c "^### " "$CLAWD_DIR/knowledge/LEARNINGS.md" 2>/dev/null || echo "0")
DECISION_COUNT=$(grep -c "^### " "$CLAWD_DIR/knowledge/DECISIONS.md" 2>/dev/null || echo "0")
PATTERN_COUNT=$(grep -c "^### " "$CLAWD_DIR/memory/PATTERNS.md" 2>/dev/null || echo "0")

# Count tasks by status
TASKS_TODO=$(grep -c "🔴 TODO" "$CLAWD_DIR/tasks/BACKLOG.md" 2>/dev/null || echo "0")
TASKS_BLOCKED=$(grep -c "🔴 BLOCKED" "$CLAWD_DIR/tasks/BACKLOG.md" 2>/dev/null || echo "0")
TASKS_RUNNING=$(grep -c "🟢 Running" "$CLAWD_DIR/tasks/IN_PROGRESS.md" 2>/dev/null || echo "0")

# Get recent activity (last 10 markdown files modified in memory/)
RECENT_FILES=$(find "$CLAWD_DIR/memory" "$CLAWD_DIR/knowledge" -name "*.md" -mtime -7 -type f 2>/dev/null | head -10 | while read f; do
    mtime=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null || echo "0")
    name=$(basename "$f")
    echo "{\"file\": \"$name\", \"mtime\": $mtime}"
done | paste -sd "," -)

# Get last boot time (from MEMORY.md first line containing date)
FIRST_BOOT=$(grep -o "202[0-9]-[0-9][0-9]-[0-9][0-9]" "$CLAWD_DIR/MEMORY.md" | head -1 || echo "unknown")

# Generate JSON output
cat > "$OUTPUT" << EOF
{
  "generated_at": "$TIMESTAMP",
  "metrics": {
    "rules": $RULE_COUNT,
    "learnings": $LEARNING_COUNT,
    "decisions": $DECISION_COUNT,
    "patterns": $PATTERN_COUNT,
    "tasks_todo": $TASKS_TODO,
    "tasks_blocked": $TASKS_BLOCKED,
    "tasks_running": $TASKS_RUNNING
  },
  "identity": {
    "name": "Elliot",
    "first_boot": "$FIRST_BOOT",
    "role": "CEO/Orchestrator"
  },
  "files": {
    "learnings": $LEARNINGS,
    "rules": $RULES,
    "decisions": $DECISIONS,
    "patterns": $PATTERNS,
    "memory": $MEMORY,
    "backlog": $BACKLOG,
    "in_progress": $IN_PROGRESS,
    "daily_today": $DAILY_TODAY,
    "daily_yesterday": $DAILY_YESTERDAY
  },
  "recent_activity": [$RECENT_FILES]
}
EOF

echo "Dashboard data generated at $OUTPUT"
echo "Metrics: $RULE_COUNT rules, $LEARNING_COUNT learnings, $DECISION_COUNT decisions, $PATTERN_COUNT patterns"
echo "Tasks: $TASKS_TODO TODO, $TASKS_BLOCKED blocked, $TASKS_RUNNING running"
