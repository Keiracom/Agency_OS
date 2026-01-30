#!/bin/bash
# Quick Claude API chat
# Usage: anthropic-chat.sh "message" [model]

set -euo pipefail

MESSAGE="${1:-Hello}"
MODEL="${2:-claude-sonnet-4-5-20250514}"
MAX_TOKENS="${3:-1024}"

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "Error: ANTHROPIC_API_KEY not set" >&2
  exit 1
fi

# Escape message for JSON
MESSAGE_ESCAPED=$(echo "$MESSAGE" | jq -Rs '.')

curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"max_tokens\": $MAX_TOKENS,
    \"messages\": [{\"role\": \"user\", \"content\": $MESSAGE_ESCAPED}]
  }" | jq -r '.content[0].text // .error.message // .'
