#!/usr/bin/env python3
"""
YouTube Transcript Fetcher
Extracts transcripts with timestamps from YouTube videos.
"""

import sys
import re
import json
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(url_or_id):
    """Extract video ID from various YouTube URL formats or return as-is if already an ID."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return None

def format_timestamp(seconds):
    """Convert seconds to HH:MM:SS or MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def get_transcript(video_id, language='en'):
    """Fetch transcript for a video."""
    try:
        api = YouTubeTranscriptApi()
        
        # Try to get transcript - will auto-select best available
        transcript = api.fetch(video_id, languages=[language, 'en'])
        # Convert to list of dicts for consistency
        return [{"text": s.text, "start": s.start, "duration": s.duration} for s in transcript]
    except Exception as e:
        error_msg = str(e)
        if "disabled" in error_msg.lower():
            return {"error": "Transcripts are disabled for this video"}
        elif "not found" in error_msg.lower():
            return {"error": "No transcript found for this video"}
        elif "unavailable" in error_msg.lower():
            return {"error": "Video is unavailable"}
        else:
            return {"error": error_msg}

def main():
    if len(sys.argv) < 2:
        print("Usage: youtube_transcript.py <youtube_url_or_id> [language] [--json]")
        sys.exit(1)
    
    url_or_id = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else 'en'
    output_json = '--json' in sys.argv
    
    video_id = extract_video_id(url_or_id)
    if not video_id:
        print(f"Error: Could not extract video ID from '{url_or_id}'")
        sys.exit(1)
    
    result = get_transcript(video_id, language)
    
    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    
    if output_json:
        print(json.dumps(result, indent=2))
    else:
        # Human-readable format with timestamps
        for entry in result:
            timestamp = format_timestamp(entry['start'])
            text = entry['text'].replace('\n', ' ')
            print(f"[{timestamp}] {text}")

if __name__ == "__main__":
    main()
