#!/bin/bash
# Fetch YouTube transcript using Apify
# Usage: ./get-transcript.sh "https://www.youtube.com/watch?v=VIDEO_ID"

set -e

# Load API key
if [ -f ~/.config/agency-os/.env ]; then
    source ~/.config/agency-os/.env
fi

if [ -z "$APIFY_API_KEY" ]; then
    echo "Error: APIFY_API_KEY not set" >&2
    exit 1
fi

URL="$1"
if [ -z "$URL" ]; then
    echo "Usage: $0 <youtube-url>" >&2
    exit 1
fi

# Run the Apify actor and wait for completion
RESULT=$(curl -s -X POST "https://api.apify.com/v2/acts/karamelo~youtube-transcripts/runs?token=$APIFY_API_KEY&waitForFinish=120" \
    -H "Content-Type: application/json" \
    -d "{\"urls\": [\"$URL\"]}")

# Check for errors
if echo "$RESULT" | grep -q '"error"'; then
    echo "Error: $(echo "$RESULT" | jq -r '.error.message // .error')" >&2
    exit 1
fi

# Extract dataset ID and fetch results
DATASET_ID=$(echo "$RESULT" | jq -r '.data.defaultDatasetId')

if [ -z "$DATASET_ID" ] || [ "$DATASET_ID" = "null" ]; then
    echo "Error: Failed to get dataset ID" >&2
    exit 1
fi

# Fetch transcript and output as plain text
curl -s "https://api.apify.com/v2/datasets/$DATASET_ID/items?token=$APIFY_API_KEY" | \
    jq -r '.[0].captions | join(" ")' | \
    sed 's/&#39;/'"'"'/g; s/&quot;/"/g; s/&amp;/\&/g'
