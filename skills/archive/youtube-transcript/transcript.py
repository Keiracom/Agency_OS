#!/usr/bin/env python3
"""
Fetch YouTube transcripts using Apify.
Works from cloud IPs where direct YouTube API access is blocked.
"""

import argparse
import json
import os
import re
import sys
import html
from pathlib import Path
import urllib.request
import urllib.error

def load_api_key():
    """Load Apify API key from environment or config file."""
    api_key = os.environ.get('APIFY_API_KEY')
    if api_key:
        return api_key
    
    env_file = Path.home() / '.config/agency-os/.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith('APIFY_API_KEY='):
                    return line.split('=', 1)[1].strip().strip('"\'')
    
    raise ValueError("APIFY_API_KEY not found in environment or ~/.config/agency-os/.env")

def extract_video_id(url_or_id: str) -> str:
    """Extract video ID from YouTube URL or return as-is if already an ID."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return url_or_id

def get_transcript(url: str, api_key: str) -> dict:
    """Fetch transcript using Apify karamelo~youtube-transcripts actor."""
    # Start the actor run
    run_url = f"https://api.apify.com/v2/acts/karamelo~youtube-transcripts/runs?token={api_key}&waitForFinish=120"
    
    data = json.dumps({"urls": [url]}).encode('utf-8')
    req = urllib.request.Request(run_url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            result = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(f"Apify API error: {error_body}")
    
    if 'error' in result:
        raise RuntimeError(f"Apify error: {result['error'].get('message', result['error'])}")
    
    # Get dataset ID
    dataset_id = result.get('data', {}).get('defaultDatasetId')
    if not dataset_id:
        raise RuntimeError("Failed to get dataset ID from Apify response")
    
    # Fetch results
    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={api_key}"
    with urllib.request.urlopen(items_url, timeout=30) as response:
        items = json.loads(response.read().decode())
    
    if not items:
        raise RuntimeError("No transcript found for this video")
    
    return items[0]

def clean_text(text: str) -> str:
    """Clean HTML entities from text."""
    return html.unescape(text)

def main():
    parser = argparse.ArgumentParser(description='Fetch YouTube transcripts')
    parser.add_argument('url', nargs='?', help='YouTube URL or video ID')
    parser.add_argument('--video-id', '-v', help='YouTube video ID')
    parser.add_argument('--json', '-j', action='store_true', help='Output full JSON')
    args = parser.parse_args()
    
    # Get URL/ID from args
    video_input = args.video_id or args.url
    if not video_input:
        parser.print_help()
        sys.exit(1)
    
    video_id = extract_video_id(video_input)
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        api_key = load_api_key()
        result = get_transcript(url, api_key)
        
        if args.json:
            # Clean captions and output JSON
            result['captions'] = [clean_text(c) for c in result.get('captions', [])]
            print(json.dumps(result, indent=2))
        else:
            # Output plain text
            captions = result.get('captions', [])
            text = ' '.join(clean_text(c) for c in captions)
            print(text)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
