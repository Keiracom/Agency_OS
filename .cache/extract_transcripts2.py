#!/usr/bin/env python3
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
import json
import sys

videos = [
    ("ssYt09bCgUY", "Fireship: The wild rise of OpenClaw"),
    ("qJle6Bki4Og", "Fireship: How to make vibe coding not suck"),
    ("1WImBwiA7RA", "AI Jason: Claude Skills - the SOP for your agent"),
    ("MW3t6jP9AOs", "AI Jason: .agent folder is making claude code 10x better"),
    ("LCYBVpSB0Wo", "AI Jason: I was using sub-agents wrong"),
    ("UZb0if-7wGE", "AI Jason: I was using Claude Code wrong... The Ultimate Workflow"),
]

with open('/home/elliotbot/clawd/.config/proxy_list.json') as f:
    data = json.load(f)

# Load existing results if any
try:
    with open('/home/elliotbot/clawd/.cache/transcripts_batch1.json') as f:
        results = json.load(f)
        done_ids = {r['video_id'] for r in results if r.get('status') == 'success'}
except:
    results = []
    done_ids = set()

sys.stdout.flush()

for i, (video_id, title) in enumerate(videos):
    if video_id in done_ids:
        print(f"[{i+1}/6] SKIP (already done): {title}")
        sys.stdout.flush()
        continue
        
    proxy_idx = 200 + i * 20  # Use different proxies: 200, 220, 240, etc.
    p = data['proxies'][proxy_idx]
    proxy_url = f"http://{p['username']}:{p['password']}@{p['host']}:{p['port']}"
    
    print(f"[{i+1}/6] Fetching: {title} ({video_id}) via proxy {proxy_idx}...")
    sys.stdout.flush()
    
    try:
        ytt = YouTubeTranscriptApi(proxy_config=GenericProxyConfig(http_url=proxy_url, https_url=proxy_url))
        transcript = ytt.fetch(video_id)
        text = ' '.join([t.text for t in transcript])
        results.append({
            "video_id": video_id,
            "title": title,
            "transcript": text,
            "status": "success"
        })
        print(f"    ✓ Got {len(text)} chars")
        sys.stdout.flush()
        
        # Save after each success
        with open('/home/elliotbot/clawd/.cache/transcripts_batch1.json', 'w') as f:
            json.dump(results, f, indent=2)
            
    except Exception as e:
        print(f"    ✗ Error: {e}")
        sys.stdout.flush()
        results.append({
            "video_id": video_id,
            "title": title,
            "transcript": None,
            "status": f"error: {str(e)}"
        })

with open('/home/elliotbot/clawd/.cache/transcripts_batch1.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nDone. {sum(1 for r in results if r.get('status') == 'success')}/6 successful.")
sys.stdout.flush()
