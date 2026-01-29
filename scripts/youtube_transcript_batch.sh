#!/bin/bash
# YouTube Transcript Batch Extractor via Apify
# Uses starvibe/youtube-video-transcript actor (cheaper at $0.005/video)

source ~/.config/agency-os/.env

# Configuration
ACTOR="starvibe~youtube-video-transcript"
OUTPUT_DIR="${1:-./transcripts}"
VIDEO_LIST="${2:-./video_ids.txt}"

mkdir -p "$OUTPUT_DIR"

# Function to extract transcript for a single video
extract_transcript() {
    local video_id="$1"
    local output_file="$OUTPUT_DIR/${video_id}.json"
    
    echo "Processing: $video_id"
    
    # Start the run
    run_response=$(curl -s -X POST "https://api.apify.com/v2/acts/$ACTOR/runs?waitForFinish=120" \
        -H "Authorization: Bearer $APIFY_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"youtube_url\": \"https://www.youtube.com/watch?v=$video_id\", \"language\": \"en\", \"include_transcript_text\": true}")
    
    # Check status
    status=$(echo "$run_response" | jq -r '.data.status // "FAILED"')
    
    if [ "$status" == "SUCCEEDED" ]; then
        dataset_id=$(echo "$run_response" | jq -r '.data.defaultDatasetId')
        
        # Fetch results
        curl -s "https://api.apify.com/v2/datasets/$dataset_id/items?format=json" \
            -H "Authorization: Bearer $APIFY_API_KEY" > "$output_file"
        
        echo "  ✓ Saved to $output_file"
    else
        echo "  ✗ Failed: $status"
        echo "$run_response" | jq '.error // .data.status' >> "$OUTPUT_DIR/errors.log"
    fi
}

# Process video IDs from file or command line
if [ -f "$VIDEO_LIST" ]; then
    while read -r video_id; do
        [ -z "$video_id" ] && continue
        [ "${video_id:0:1}" == "#" ] && continue
        extract_transcript "$video_id"
        sleep 1  # Rate limiting
    done < "$VIDEO_LIST"
else
    echo "Usage: $0 [output_dir] [video_ids.txt]"
    echo "Or pipe video IDs: echo 'CBNbcbMs_Lc' | $0"
    
    # Read from stdin if piped
    while read -r video_id; do
        [ -z "$video_id" ] && continue
        extract_transcript "$video_id"
    done
fi

echo "Done! Transcripts saved to $OUTPUT_DIR"
