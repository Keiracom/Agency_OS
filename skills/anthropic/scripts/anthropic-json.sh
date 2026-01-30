#!/bin/bash
# Claude API with JSON output mode
# Usage: anthropic-json.sh "extract entities" "schema" [model]

set -euo pipefail

MESSAGE="${1:-Extract data}"
SCHEMA="${2:-{\"result\": \"string\"}}"
MODEL="${3:-claude-sonnet-4-5-20250514}"

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "Error: ANTHROPIC_API_KEY not set" >&2
  exit 1
fi

MESSAGE_ESCAPED=$(echo "$MESSAGE" | jq -Rs '.')
SYSTEM="Respond ONLY with valid JSON matching this schema: $SCHEMA"

curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"max_tokens\": 2048,
    \"system\": $(echo "$SYSTEM" | jq -Rs '.'),
    \"messages\": [
      {\"role\": \"user\", \"content\": $MESSAGE_ESCAPED},
      {\"role\": \"assistant\", \"content\": \"{\"}
    ]
  }" | jq -r '"{" + .content[0].text // .error.message // .'
