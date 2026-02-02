---
name: youtube-transcript
description: Use when extracting YouTube video transcripts via OAuth API. Get captions with timestamps, works from cloud servers. Triggers on "youtube transcript", "video captions", "what did they say in", extracting spoken content from videos.
metadata: {"clawdbot":{"emoji":"📜"}}
---

# YouTube Transcript Skill

Fetch transcripts from YouTube videos using YouTube Data API v3 with OAuth authentication.
Works from cloud servers where direct YouTube scraping is blocked.

## First-Time Setup

Before using, you must authorize access to YouTube captions.

### On a machine with browser:
```bash
cd /home/elliotbot/clawd/scripts
python3 youtube_oauth.py --setup
```

### On a headless server (e.g., Vultr):
```bash
cd /home/elliotbot/clawd/scripts
python3 youtube_oauth.py --setup --headless
```
This shows an auth URL. Open it in any browser, authorize, then paste the redirect URL back.

After authorizing:
- Tokens stored in `~/.config/agency-os/youtube_tokens.json`
- Tokens auto-refresh (no need to re-authorize)

Check status anytime:
```bash
python3 youtube_oauth.py --status
```

## Usage

### Get Transcript (Plain Text)
```bash
python youtube_captions.py "https://www.youtube.com/watch?v=VIDEO_ID"
# or just the video ID
python youtube_captions.py VIDEO_ID
```

### Get Transcript with Timestamps (JSON)
```bash
python youtube_captions.py VIDEO_ID --json
```

### Check Available Captions
```bash
python youtube_captions.py VIDEO_ID --info
```

### Specify Language
```bash
python youtube_captions.py VIDEO_ID --lang es
```

## Options

| Flag | Description |
|------|-------------|
| `--json` | Output JSON with timestamps |
| `--lang LANG` | Preferred language code (default: en) |
| `--info` | Show video info and available caption tracks |

## Output Formats

### Plain Text (default)
```
# Video Title
# Channel Name
# Captions: manual (en)

First line of transcript...
Second line of transcript...
```

### JSON (`--json`)
```json
{
  "title": "Video Title",
  "channel": "Channel Name",
  "video_id": "ABC123xyz",
  "caption_language": "en",
  "caption_type": "manual",
  "captions": [
    {"start": 0.0, "duration": 2.5, "text": "Hello world"},
    {"start": 2.5, "duration": 3.0, "text": "Next caption"}
  ]
}
```

## Caption Selection Logic

1. **Manual captions** preferred over auto-generated
2. **Requested language** (`--lang`) preferred
3. **English** preferred as fallback

## Error Handling

| Error | Meaning |
|-------|---------|
| "No captions available" | Video has no captions (try a different video) |
| "Caption download not allowed" | Video owner disabled caption downloads |
| "Video not found" | Invalid video ID |
| "No tokens found" | Run `--setup` first |

## Requirements

- OAuth credentials in `~/.config/agency-os/.env`:
  - `GOOGLE_GMAIL_CLIENT_ID`
  - `GOOGLE_GMAIL_CLIENT_SECRET`
- Python 3.10+
- No external dependencies (uses stdlib only)

## How It Works

1. Uses YouTube Data API v3 (requires OAuth)
2. Lists available caption tracks for video
3. Downloads caption in TTML format
4. Parses to plain text or structured JSON

## Limitations

- Only works for videos with captions (manual or auto-generated)
- Some videos have captions disabled for download by owner
- Requires one-time OAuth setup (interactive browser flow)

## Files

| File | Purpose |
|------|---------|
| `scripts/youtube_oauth.py` | OAuth token manager |
| `scripts/youtube_captions.py` | Caption fetcher |
| `~/.config/agency-os/youtube_tokens.json` | Stored OAuth tokens |
