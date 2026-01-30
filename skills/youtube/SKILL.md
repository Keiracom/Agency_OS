# YouTube Scraping (Native, No API Key)

## 1. Overview

Native Python YouTube scraping without API key requirements.

| Library | Purpose | Cost |
|---------|---------|------|
| `youtube-search-python` | Search videos, channels, playlists | $0 |
| `youtube-transcript-api` | Extract video transcripts | $0 |

## 2. Installation

```bash
pip install youtube-search-python youtube-transcript-api
```

## 3. Search Videos

```python
from youtubesearchpython import VideosSearch, ChannelsSearch, PlaylistsSearch

# Basic search
search = VideosSearch("AI agents", limit=20)
results = search.result()['result']

# Get next page
search.next()
more_results = search.result()['result']

# Search with filters
search = VideosSearch("AI tutorial", limit=20, 
                      language='en', 
                      region='US')
```

## 4. Get Transcripts

```python
from youtube_transcript_api import YouTubeTranscriptApi

# Get transcript
transcript = YouTubeTranscriptApi.get_transcript("video_id")
full_text = " ".join([t['text'] for t in transcript])

# Get specific language
transcript = YouTubeTranscriptApi.get_transcript("video_id", languages=['en'])

# List available transcripts
transcript_list = YouTubeTranscriptApi.list_transcripts("video_id")
for t in transcript_list:
    print(t.language, t.is_generated)
```

## 5. Error Handling

```python
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

try:
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
except TranscriptsDisabled:
    # Video has transcripts disabled
    pass
except NoTranscriptFound:
    # No transcript in requested language
    pass
except VideoUnavailable:
    # Video doesn't exist or is private
    pass
```

## 6. Channel Videos

```python
from youtubesearchpython import Channel

channel = Channel("channel_id_or_url")
videos = channel.result['videos']
```

## 7. Rate Limits

| Concern | Recommendation |
|---------|----------------|
| No official limits | It's scraping, not API |
| Request spacing | 0.5-1 second between requests |
| IP blocking | Too fast = potential block |
| Heavy usage | Use proxies for large-scale scraping |

## 8. Response Structures

### Video Search Result

```python
{
    'id': 'video_id',
    'title': 'Video Title',
    'duration': '10:30',
    'viewCount': {'text': '1.2M views'},
    'publishedTime': '2 weeks ago',
    'channel': {'name': 'Channel Name', 'id': 'channel_id'},
    'descriptionSnippet': [{'text': '...'}],
    'thumbnails': [...]
}
```

### Transcript Result

```python
[
    {'text': 'Hello everyone', 'start': 0.0, 'duration': 2.5},
    {'text': 'today we will', 'start': 2.5, 'duration': 1.8},
    ...
]
```

## 9. Full Example

```python
from youtubesearchpython import VideosSearch
from youtube_transcript_api import YouTubeTranscriptApi

def search_and_transcribe(query: str, limit: int = 5):
    """Search YouTube and extract transcripts for matching videos."""
    results = []
    search = VideosSearch(query, limit=limit)
    
    for video in search.result()['result']:
        video_id = video['id']
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join([t['text'] for t in transcript])
        except Exception:
            text = None
        
        results.append({
            'title': video['title'],
            'url': f"https://youtube.com/watch?v={video_id}",
            'transcript': text
        })
    
    return results
```

## 10. Use Cases

- Extract tutorials for learning
- Scrape educational content
- Research competitor videos
- Build knowledge base from video content
- Analyze trending topics in a niche
- Generate summaries of video series
