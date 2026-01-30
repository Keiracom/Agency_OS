#!/bin/bash
# yek-context.sh - Fast codebase context generator for LLM ingestion
# Usage: ./scripts/yek-context.sh [target] [max-size]
# Examples:
#   ./scripts/yek-context.sh agency-os 100K
#   ./scripts/yek-context.sh frontend 50K
#   ./scripts/yek-context.sh src/api 200K

set -e

TARGET="${1:-src}"
MAX_SIZE="${2:-100K}"
OUTPUT_DIR="/home/elliotbot/clawd/.context"

mkdir -p "$OUTPUT_DIR"

# Map common aliases to paths
case "$TARGET" in
  "agency-os"|"aos"|"backend")
    REPO="/home/elliotbot/clawd/Agency_OS"
    PATH_TARGET="src"
    OUTPUT_FILE="$OUTPUT_DIR/agency-os-backend.txt"
    ;;
  "frontend"|"fe"|"dashboard")
    REPO="/home/elliotbot/clawd/Agency_OS"
    PATH_TARGET="frontend/src"
    OUTPUT_FILE="$OUTPUT_DIR/agency-os-frontend.txt"
    ;;
  "mobile"|"app")
    REPO="/home/elliotbot/clawd/projects/elliot-mobile"
    PATH_TARGET="."
    OUTPUT_FILE="$OUTPUT_DIR/elliot-mobile.txt"
    ;;
  "clawd"|"workspace")
    REPO="/home/elliotbot/clawd"
    PATH_TARGET="."
    OUTPUT_FILE="$OUTPUT_DIR/clawd-workspace.txt"
    ;;
  *)
    # Direct path mode
    if [[ "$TARGET" == /* ]]; then
      REPO="$(dirname "$TARGET")"
      PATH_TARGET="$(basename "$TARGET")"
    else
      REPO="/home/elliotbot/clawd/Agency_OS"
      PATH_TARGET="$TARGET"
    fi
    OUTPUT_FILE="$OUTPUT_DIR/custom-context.txt"
    ;;
esac

echo "📦 Generating context..."
echo "   Repo: $REPO"
echo "   Path: $PATH_TARGET"
echo "   Max:  $MAX_SIZE"

cd "$REPO"
yek --max-size "$MAX_SIZE" --tree-header "$PATH_TARGET" > "$OUTPUT_FILE" 2>/dev/null

LINES=$(wc -l < "$OUTPUT_FILE")
SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)

echo "✅ Context ready: $OUTPUT_FILE"
echo "   Lines: $LINES | Size: $SIZE"
echo ""
echo "Quick read: cat $OUTPUT_FILE | head -500"
