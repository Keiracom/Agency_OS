#!/usr/bin/env python3
"""
Batch YouTube Transcript Fetcher
Uses Webshare proxies to avoid IP blocks.

Usage:
    python3 scripts/batch_transcript.py video_ids.txt output.json
    python3 scripts/batch_transcript.py --video-id VIDEO_ID
"""

import json
import sys
import random
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

def load_proxies():
    """Load proxies from cache."""
    cache_file = Path(__file__).parent.parent / ".config" / "proxy_list.json"
    if cache_file.exists():
        with open(cache_file) as f:
            data = json.load(f)
            return data.get("proxies", [])
    return []

def get_proxy_url(proxy: dict) -> str:
    """Convert proxy dict to URL."""
    return f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"

def fetch_transcript(video_id: str, proxies: list, max_retries: int = 3) -> dict:
    """Fetch transcript for a single video with proxy rotation."""
    for attempt in range(max_retries):
        proxy = random.choice(proxies)
        proxy_url = get_proxy_url(proxy)
        
        try:
            ytt = YouTubeTranscriptApi(proxy_config=GenericProxyConfig(
                http_url=proxy_url,
                https_url=proxy_url
            ))
            transcript = ytt.fetch(video_id)
            text = " ".join([t.text for t in transcript])
            
            return {
                "video_id": video_id,
                "success": True,
                "transcript": text,
                "word_count": len(text.split())
            }
        except Exception as e:
            if attempt == max_retries - 1:
                return {
                    "video_id": video_id,
                    "success": False,
                    "error": str(e)
                }
    
    return {"video_id": video_id, "success": False, "error": "Max retries exceeded"}

def batch_fetch(video_ids: list[str], output_file: str = None) -> list[dict]:
    """Fetch transcripts for multiple videos."""
    proxies = load_proxies()
    if not proxies:
        print("ERROR: No proxies loaded", file=sys.stderr)
        return []
    
    print(f"Loaded {len(proxies)} proxies", file=sys.stderr)
    results = []
    
    for i, video_id in enumerate(video_ids):
        print(f"[{i+1}/{len(video_ids)}] Fetching {video_id}...", file=sys.stderr)
        result = fetch_transcript(video_id, proxies)
        results.append(result)
        
        if result["success"]:
            print(f"  ✓ {result['word_count']} words", file=sys.stderr)
        else:
            print(f"  ✗ {result['error'][:50]}", file=sys.stderr)
    
    if output_file:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved to {output_file}", file=sys.stderr)
    
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    if sys.argv[1] == "--video-id":
        # Single video mode
        video_id = sys.argv[2]
        proxies = load_proxies()
        result = fetch_transcript(video_id, proxies)
        print(json.dumps(result, indent=2))
    else:
        # Batch mode
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "transcripts.json"
        
        with open(input_file) as f:
            video_ids = [line.strip() for line in f if line.strip()]
        
        batch_fetch(video_ids, output_file)
