# YouTube Video Analysis Skill

Extract transcripts with timestamps from YouTube videos.

## Usage

```bash
source /home/elliotbot/clawd/.venv/bin/activate
python /home/elliotbot/clawd/scripts/youtube_transcript.py "<youtube_url_or_id>" [language] [--json]
```

## Examples

**Get transcript with timestamps:**
```bash
python /home/elliotbot/clawd/scripts/youtube_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

**Get JSON output (for programmatic use):**
```bash
python /home/elliotbot/clawd/scripts/youtube_transcript.py "VIDEO_ID" --json
```

**Get transcript in specific language:**
```bash
python /home/elliotbot/clawd/scripts/youtube_transcript.py "VIDEO_ID" de
```

## Output Format

**Human-readable (default):**
```
[00:01] First line of transcript
[00:05] Second line of transcript
[01:23] And so on...
```

**JSON (--json flag):**
```json
[
  {"text": "First line", "start": 1.0, "duration": 3.5},
  {"text": "Second line", "start": 5.2, "duration": 2.1}
]
```

## Supported URL Formats

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://youtube.com/embed/VIDEO_ID`
- Just the video ID: `VIDEO_ID`

## How to Use This

When given a YouTube link:

1. Run the transcript script to get full content with timestamps
2. Analyze/summarize the content as needed
3. Reference specific timestamps when discussing parts of the video

## Dependencies

Requires the `youtube-transcript-api` package (installed in venv).

## Limitations

- Only works if video has captions (auto-generated or manual)
- Some videos have captions disabled
- Private/unlisted videos may not be accessible
