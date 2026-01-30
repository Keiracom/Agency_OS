# YouTube TLDR Template

## Purpose
Extract transcript from a YouTube video and summarize the key points into a concise TLDR.

## Input Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `VIDEO_URL` | ✅ | Full YouTube URL (e.g., `https://www.youtube.com/watch?v=...`) |
| `SUMMARY_LENGTH` | ❌ | short/medium/detailed (default: medium) |
| `FOCUS_AREAS` | ❌ | Specific topics to emphasize (optional) |

## Instructions

### Step 1: Fetch Transcript via Apify
```bash
# Load API key
source ~/.config/agency-os/.env

# Call the YouTube transcript actor
curl -X POST "https://api.apify.com/v2/acts/crawlmaster~youtube-transcript-fetcher/runs?token=$APIFY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "VIDEO_URL", "lang": "en"}'
```

### Step 2: Wait for Run Completion
Poll the run status or use the sync endpoint:
```bash
curl -X POST "https://api.apify.com/v2/acts/crawlmaster~youtube-transcript-fetcher/run-sync-get-dataset-items?token=$APIFY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "VIDEO_URL", "lang": "en"}'
```

### Step 3: Analyze & Summarize
With the transcript text, identify:
1. **Main Topic** — What is this video about?
2. **Key Points** — 3-7 bullet points of main takeaways
3. **Notable Quotes** — Any memorable or quotable moments
4. **Action Items** — What should the viewer do after watching?

## Expected Output Format

```markdown
# 📺 TLDR: [Video Title]

**Channel:** [Channel Name]
**Duration:** [Length]
**URL:** [VIDEO_URL]

## 🎯 Main Topic
[1-2 sentence summary of what this video covers]

## 📌 Key Takeaways
- Point 1
- Point 2
- Point 3
- ...

## 💬 Notable Quotes
> "Quote 1" — [Timestamp if available]

## ✅ Action Items
- [ ] Action 1
- [ ] Action 2

## 🏷️ Tags
#topic1 #topic2 #topic3
```

## Example Usage
```
@elliot Use youtube-tldr template for https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

## Notes
- English transcripts only (lang=en)
- Auto-generated captions work but may have errors
- For long videos (>1hr), consider chunking the summary
