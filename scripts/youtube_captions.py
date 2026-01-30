#!/usr/bin/env python3
"""
YouTube Caption Fetcher

Fetches video transcripts using YouTube Data API v3 with OAuth authentication.
Works from cloud IPs where direct scraping is blocked.

Usage:
    # Get transcript as plain text
    python youtube_captions.py "https://www.youtube.com/watch?v=VIDEO_ID"
    
    # Get transcript with timestamps (JSON)
    python youtube_captions.py VIDEO_ID --json
    
    # Specify language preference
    python youtube_captions.py VIDEO_ID --lang en
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

# Import OAuth manager from same directory
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from youtube_oauth import get_valid_access_token, load_env

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


@dataclass
class CaptionTrack:
    """Represents a caption track."""
    id: str
    name: str
    language: str
    track_kind: str  # 'standard' or 'ASR' (auto-generated)
    is_auto: bool
    is_translatable: bool


@dataclass
class Caption:
    """A single caption entry."""
    start: float
    duration: float
    text: str


def extract_video_id(url_or_id: str) -> str:
    """Extract video ID from YouTube URL or return as-is if already an ID."""
    # Already an ID
    if re.match(r"^[a-zA-Z0-9_-]{11}$", url_or_id):
        return url_or_id
    
    # Various YouTube URL formats
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    raise ValueError(f"Could not extract video ID from: {url_or_id}")


def api_request(endpoint: str, params: dict, access_token: str) -> dict:
    """Make authenticated request to YouTube API."""
    url = f"{YOUTUBE_API_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get("error", {}).get("message", error_body)
        except json.JSONDecodeError:
            error_msg = error_body
        raise RuntimeError(f"YouTube API error ({e.code}): {error_msg}")


def get_video_info(video_id: str, access_token: str) -> dict:
    """Get video title and channel info."""
    result = api_request("videos", {
        "part": "snippet",
        "id": video_id
    }, access_token)
    
    if not result.get("items"):
        raise ValueError(f"Video not found: {video_id}")
    
    snippet = result["items"][0]["snippet"]
    return {
        "title": snippet.get("title", "Unknown"),
        "channel": snippet.get("channelTitle", "Unknown"),
        "video_id": video_id
    }


def list_caption_tracks(video_id: str, access_token: str) -> list[CaptionTrack]:
    """List available caption tracks for a video."""
    result = api_request("captions", {
        "part": "snippet",
        "videoId": video_id
    }, access_token)
    
    tracks = []
    for item in result.get("items", []):
        snippet = item["snippet"]
        tracks.append(CaptionTrack(
            id=item["id"],
            name=snippet.get("name", ""),
            language=snippet.get("language", "unknown"),
            track_kind=snippet.get("trackKind", "standard"),
            is_auto=snippet.get("trackKind") == "ASR",
            is_translatable=snippet.get("isTranslatable", False)
        ))
    
    return tracks


def download_caption_track(track_id: str, access_token: str) -> str:
    """Download caption track content."""
    # The captions.download endpoint requires special handling
    url = f"{YOUTUBE_API_BASE}/captions/{track_id}?tfmt=ttml"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 403:
            # This is common - many videos don't allow caption download
            raise PermissionError(
                "Caption download not allowed for this video. "
                "The video owner has disabled caption downloads."
            )
        error_body = e.read().decode()
        raise RuntimeError(f"Failed to download captions ({e.code}): {error_body}")


def parse_ttml_captions(ttml_content: str) -> list[Caption]:
    """Parse TTML format captions."""
    captions = []
    
    try:
        root = ET.fromstring(ttml_content)
    except ET.ParseError as e:
        raise ValueError(f"Failed to parse caption XML: {e}")
    
    # Handle namespace
    ns = {"tt": "http://www.w3.org/ns/ttml"}
    
    # Find all <p> elements (each contains a caption)
    body = root.find(".//tt:body", ns) or root.find(".//body")
    if body is None:
        # Try without namespace
        body = root.find(".//body")
    
    if body is None:
        return captions
    
    for p in body.iter():
        if p.tag.endswith("}p") or p.tag == "p":
            begin = p.get("begin", "0s")
            end = p.get("end", "0s")
            dur = p.get("dur")
            
            start_sec = parse_time(begin)
            if dur:
                duration = parse_time(dur)
            else:
                duration = parse_time(end) - start_sec
            
            # Get text content (including nested elements)
            text = "".join(p.itertext()).strip()
            text = text.replace("\n", " ").strip()
            
            if text:
                captions.append(Caption(
                    start=start_sec,
                    duration=duration,
                    text=text
                ))
    
    return captions


def parse_time(time_str: str) -> float:
    """Parse TTML time format to seconds."""
    # Handle formats: "1.5s", "00:01:30.500", "1500ms"
    time_str = time_str.strip()
    
    if time_str.endswith("ms"):
        return float(time_str[:-2]) / 1000
    if time_str.endswith("s"):
        return float(time_str[:-1])
    
    # HH:MM:SS.mmm format
    parts = time_str.replace(",", ".").split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    
    return float(time_str)


def select_best_track(
    tracks: list[CaptionTrack],
    preferred_lang: str = "en"
) -> Optional[CaptionTrack]:
    """Select the best caption track (prefer manual over auto-generated)."""
    if not tracks:
        return None
    
    # Sort by preference: manual first, then by language match
    def track_score(track: CaptionTrack) -> tuple[int, int, int]:
        is_manual = 0 if track.is_auto else 1
        lang_match = 1 if track.language.startswith(preferred_lang) else 0
        is_english = 1 if track.language.startswith("en") else 0
        return (is_manual, lang_match, is_english)
    
    tracks_sorted = sorted(tracks, key=track_score, reverse=True)
    return tracks_sorted[0]


def get_transcript(
    video_id: str,
    access_token: str,
    preferred_lang: str = "en"
) -> tuple[dict, list[Caption]]:
    """Get transcript for a video.
    
    Returns:
        Tuple of (video_info, captions)
    """
    # Get video info
    video_info = get_video_info(video_id, access_token)
    
    # List caption tracks
    tracks = list_caption_tracks(video_id, access_token)
    
    if not tracks:
        raise ValueError(
            f"No captions available for video: {video_id}\n"
            f"Title: {video_info['title']}"
        )
    
    # Select best track
    track = select_best_track(tracks, preferred_lang)
    
    video_info["caption_language"] = track.language
    video_info["caption_type"] = "auto-generated" if track.is_auto else "manual"
    
    # Download captions
    ttml_content = download_caption_track(track.id, access_token)
    
    # Parse captions
    captions = parse_ttml_captions(ttml_content)
    
    return video_info, captions


def format_plain_text(captions: list[Caption]) -> str:
    """Format captions as plain text."""
    return "\n".join(c.text for c in captions)


def format_json(video_info: dict, captions: list[Caption]) -> str:
    """Format as JSON with timestamps."""
    output = {
        **video_info,
        "captions": [
            {
                "start": c.start,
                "duration": c.duration,
                "text": c.text
            }
            for c in captions
        ]
    }
    return json.dumps(output, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch YouTube video transcripts using OAuth"
    )
    parser.add_argument(
        "video",
        help="YouTube video URL or video ID"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON with timestamps"
    )
    parser.add_argument(
        "--lang",
        default="en",
        help="Preferred caption language (default: en)"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show video info and available caption tracks"
    )
    
    args = parser.parse_args()
    
    try:
        # Extract video ID
        video_id = extract_video_id(args.video)
        
        # Get access token
        access_token = get_valid_access_token()
        
        if args.info:
            # Just show info
            video_info = get_video_info(video_id, access_token)
            tracks = list_caption_tracks(video_id, access_token)
            
            print(f"\nVideo: {video_info['title']}")
            print(f"Channel: {video_info['channel']}")
            print(f"ID: {video_id}")
            print(f"\nCaption Tracks ({len(tracks)}):")
            for track in tracks:
                auto_tag = " [AUTO]" if track.is_auto else ""
                print(f"  - {track.language}: {track.name or '(default)'}{auto_tag}")
            return
        
        # Get transcript
        video_info, captions = get_transcript(video_id, access_token, args.lang)
        
        # Output
        if args.json:
            print(format_json(video_info, captions))
        else:
            # Print header as comment
            print(f"# {video_info['title']}")
            print(f"# {video_info['channel']}")
            print(f"# Captions: {video_info['caption_type']} ({video_info['caption_language']})")
            print()
            print(format_plain_text(captions))
        
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
