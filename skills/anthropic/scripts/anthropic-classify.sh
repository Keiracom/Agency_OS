#!/bin/bash
# Fast classification with Haiku (cheapest model)
# Usage: anthropic-classify.sh "text" "category1,category2,category3"

set -euo pipefail

TEXT="${1:-}"
CATEGORIES="${2:-positive,negative,neutral}"

if [[ -z "$TEXT" ]]; then
  echo "Usage: anthropic-classify.sh \"text to classify\" \"cat1,cat2,cat3\"" >&2
  exit 1
fi

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "Error: ANTHROPIC_API_KEY not set" >&2
  exit 1
fi

TEXT_ESCAPED=$(echo "$TEXT" | jq -Rs '.')
SYSTEM="Classify the text into exactly one category: $CATEGORIES. Respond with ONLY the category name, nothing else."

curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d "{
    \"model\": \"claude-3-haiku-20240307\",
    \"max_tokens\": 50,
    \"temperature\": 0,
    \"system\": $(echo "$SYSTEM" | jq -Rs '.'),
    \"messages\": [{\"role\": \"user\", \"content\": $TEXT_ESCAPED}]
  }" | jq -r '.content[0].text // .error.message'
