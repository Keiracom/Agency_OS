#!/bin/bash
# T2 GMB Batch Enrichment via Shell

cd /home/elliotbot/clawd
source .env

DATASET_ID="gd_m8ebnr0q2qlklc02fz"
BASE_URL="https://api.brightdata.com/datasets/v3"

# Leads to enrich
declare -A LEADS=(
    ["Zeemo"]="Melbourne"
    ["Think Creative Agency"]="Sydney"
    ["Defiant Digital"]="Sydney"
    ["McKenzie Partners"]="Sydney"
    ["Nous Company"]="Brisbane"
    ["Soak Creative"]="Brisbane"
    ["Nimbl"]="Melbourne"
    ["LittleBIG Marketing"]="Melbourne"
    ["Anchor Digital Marketing"]="Brisbane"
)

RESULTS_FILE="scripts/t2_gmb_results.jsonl"
> "$RESULTS_FILE"

for COMPANY in "${!LEADS[@]}"; do
    CITY="${LEADS[$COMPANY]}"
    KEYWORD="$COMPANY $CITY"
    
    echo "[$COMPANY] Triggering collection for '$KEYWORD'..."
    
    # Trigger
    RESPONSE=$(curl -s -X POST "$BASE_URL/trigger?dataset_id=$DATASET_ID&type=discover_new&discover_by=location&notify=false&include_errors=true" \
        -H "Authorization: Bearer $BRIGHTDATA_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"input\": [{\"country\": \"AU\", \"keyword\": \"$KEYWORD\", \"lat\": \"\"}]}")
    
    SNAPSHOT_ID=$(echo "$RESPONSE" | jq -r '.snapshot_id // empty')
    
    if [ -z "$SNAPSHOT_ID" ]; then
        echo "  ERROR: No snapshot_id. Response: $RESPONSE"
        echo "{\"company\": \"$COMPANY\", \"error\": \"trigger_failed\"}" >> "$RESULTS_FILE"
        continue
    fi
    
    echo "  Snapshot: $SNAPSHOT_ID - waiting for completion..."
    
    # Poll (max 3 min)
    for i in {1..18}; do
        sleep 10
        STATUS=$(curl -s "$BASE_URL/progress/$SNAPSHOT_ID" -H "Authorization: Bearer $BRIGHTDATA_API_KEY" | jq -r '.status // "unknown"')
        echo "    Poll $i: $STATUS"
        if [ "$STATUS" == "ready" ]; then
            break
        fi
        if [ "$STATUS" == "failed" ]; then
            echo "  ERROR: Collection failed"
            echo "{\"company\": \"$COMPANY\", \"error\": \"collection_failed\"}" >> "$RESULTS_FILE"
            continue 2
        fi
    done
    
    if [ "$STATUS" != "ready" ]; then
        echo "  ERROR: Timeout waiting for results"
        echo "{\"company\": \"$COMPANY\", \"error\": \"timeout\"}" >> "$RESULTS_FILE"
        continue
    fi
    
    # Fetch results
    RESULTS=$(curl -s "$BASE_URL/snapshot/$SNAPSHOT_ID?format=json" -H "Authorization: Bearer $BRIGHTDATA_API_KEY")
    
    # Extract first result (best match will be done in Python)
    echo "$RESULTS" | jq -c --arg company "$COMPANY" '{company: $company, results: .}' >> "$RESULTS_FILE"
    
    echo "  ✓ Results saved"
done

echo ""
echo "All results saved to $RESULTS_FILE"
