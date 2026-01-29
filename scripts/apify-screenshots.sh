#!/bin/bash
source ~/.config/agency-os/.env

# Use Apify's screenshot actor with residential proxies
take_screenshot() {
    local url=$1
    local name=$2
    
    echo "Capturing: $url -> $name"
    
    # Use Apify's website content crawler with screenshot
    RUN_RESPONSE=$(curl -s -X POST "https://api.apify.com/v2/acts/apify~website-content-crawler/runs?token=$APIFY_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"startUrls\": [{\"url\": \"$url\"}],
            \"maxCrawlPages\": 1,
            \"saveScreenshots\": true,
            \"proxyConfiguration\": {
                \"useApifyProxy\": true,
                \"apifyProxyGroups\": [\"RESIDENTIAL\"]
            }
        }")
    
    RUN_ID=$(echo $RUN_RESPONSE | jq -r '.data.id')
    echo "  Run ID: $RUN_ID"
    
    # Wait for completion (max 60 seconds)
    for i in {1..12}; do
        sleep 5
        STATUS=$(curl -s "https://api.apify.com/v2/actor-runs/$RUN_ID?token=$APIFY_API_KEY" | jq -r '.data.status')
        echo "  Status: $STATUS"
        if [ "$STATUS" = "SUCCEEDED" ]; then
            break
        fi
        if [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "ABORTED" ]; then
            echo "  Failed!"
            return 1
        fi
    done
    
    # Get screenshot from key-value store
    KV_STORE_ID=$(curl -s "https://api.apify.com/v2/actor-runs/$RUN_ID?token=$APIFY_API_KEY" | jq -r '.data.defaultKeyValueStoreId')
    
    # List keys and find screenshot
    KEYS=$(curl -s "https://api.apify.com/v2/key-value-stores/$KV_STORE_ID/keys?token=$APIFY_API_KEY" | jq -r '.data.items[].key' | grep -i screenshot | head -1)
    
    if [ -n "$KEYS" ]; then
        curl -s "https://api.apify.com/v2/key-value-stores/$KV_STORE_ID/records/$KEYS?token=$APIFY_API_KEY" \
            -o "/home/elliotbot/clawd/competitive/screenshots/${name}-residential.png"
        echo "  Saved: ${name}-residential.png"
    else
        echo "  No screenshot found"
    fi
}

# G2 product pages
take_screenshot "https://www.g2.com/products/artisan-ai/reviews" "artisan-g2"
take_screenshot "https://www.g2.com/products/aisdr/reviews" "aisdr-g2"
take_screenshot "https://www.g2.com/products/instantly/reviews" "instantly-g2"

echo "Done!"
