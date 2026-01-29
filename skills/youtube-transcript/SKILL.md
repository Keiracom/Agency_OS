# YouTube Transcript Skill

Fetch transcripts from YouTube videos reliably from cloud servers (bypasses IP bans).

## Usage

### Shell Script
```bash
./get-transcript.sh "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Python
```bash
python3 transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Options
- `--json` - Output raw JSON with timestamps (Python only)
- `--video-id VIDEO_ID` - Use video ID directly instead of URL

## Output
- Default: Plain text transcript
- With `--json`: Full JSON with title, channel, captions array

## Dependencies
- Apify API key (from `~/.config/agency-os/.env`)
- Uses `karamelo~youtube-transcripts` actor ($0.007/transcript)

## Examples
```bash
# Get transcript as text
./get-transcript.sh "https://www.youtube.com/watch?v=rPAKq2oQVBs"

# Get full JSON output
python3 transcript.py "https://www.youtube.com/watch?v=rPAKq2oQVBs" --json

# Just video ID
python3 transcript.py --video-id rPAKq2oQVBs
```

## Notes
- Works from cloud IPs (Vultr, AWS, etc.) where direct YouTube APIs are blocked
- Supports auto-generated and manual captions
- Average response time: 5-10 seconds
