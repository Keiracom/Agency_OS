#!/usr/bin/env python3
"""
Content Master Tool - Unified content scraping interface.

Consolidates: youtube, youtube-transcript, rss-feeds, arxiv

Usage:
    python3 tools/content_master.py <action> <source> [query] [options]
"""

import argparse
import json
import sys
import re
from urllib.request import urlopen, Request
from urllib.parse import quote_plus, urlencode
from urllib.error import HTTPError
import xml.etree.ElementTree as ET

# ============================================
# YOUTUBE
# ============================================

def youtube_search(query: str, limit: int = 10) -> list[dict]:
    """Search YouTube via Invidious API (no auth required)."""
    
    instances = [
        "https://inv.nadeko.net",
        "https://invidious.nerdvpn.de",
        "https://yt.artemislena.eu",
    ]
    
    for instance in instances:
        try:
            url = f"{instance}/api/v1/search?q={quote_plus(query)}&type=video"
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            
            with urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode())
            
            results = []
            for video in data[:limit]:
                results.append({
                    "title": video.get("title"),
                    "channel": video.get("author"),
                    "views": video.get("viewCount", 0),
                    "duration": video.get("lengthSeconds", 0),
                    "url": f"https://youtube.com/watch?v={video.get('videoId')}",
                    "videoId": video.get("videoId"),
                })
            return results
        except Exception:
            continue
    
    return [{"error": "No Invidious instances available"}]


def youtube_transcript(video_id: str) -> dict:
    """Get YouTube transcript - requires yt-dlp or API."""
    return {
        "note": f"For transcript, use: yt-dlp --write-auto-sub --skip-download https://youtube.com/watch?v={video_id}",
        "videoId": video_id,
    }


# ============================================
# RSS FEEDS
# ============================================

def rss_fetch(url: str, limit: int = 20) -> list[dict]:
    """Fetch and parse RSS/Atom feed."""
    
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (RSS Reader)"})
    
    try:
        with urlopen(req, timeout=15) as response:
            content = response.read().decode()
        
        root = ET.fromstring(content)
        results = []
        
        # Handle RSS 2.0
        items = root.findall(".//item")
        if items:
            for item in items[:limit]:
                results.append({
                    "title": item.findtext("title", ""),
                    "link": item.findtext("link", ""),
                    "date": item.findtext("pubDate", ""),
                    "description": (item.findtext("description", "") or "")[:200],
                })
        
        # Handle Atom
        else:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall(".//atom:entry", ns) or root.findall(".//entry")
            for entry in entries[:limit]:
                link = entry.find("atom:link", ns) or entry.find("link")
                href = link.get("href") if link is not None else ""
                results.append({
                    "title": entry.findtext("atom:title", ns) or entry.findtext("title", ""),
                    "link": href,
                    "date": entry.findtext("atom:published", ns) or entry.findtext("published", ""),
                })
        
        return results
    except Exception as e:
        return [{"error": f"RSS fetch failed: {e}"}]


# ============================================
# ARXIV
# ============================================

def arxiv_search(query: str, limit: int = 10, category: str = None) -> list[dict]:
    """Search arXiv papers."""
    
    search_query = quote_plus(query)
    if category:
        search_query = f"cat:{category}+AND+{search_query}"
    
    url = f"http://export.arxiv.org/api/query?search_query=all:{search_query}&start=0&max_results={limit}&sortBy=submittedDate&sortOrder=descending"
    
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urlopen(req, timeout=15) as response:
            content = response.read().decode()
        
        root = ET.fromstring(content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        
        results = []
        for entry in root.findall("atom:entry", ns):
            # Get PDF link
            pdf_link = ""
            for link in entry.findall("atom:link", ns):
                if link.get("title") == "pdf":
                    pdf_link = link.get("href", "")
                    break
            
            results.append({
                "title": entry.findtext("atom:title", ns, "").replace("\n", " ").strip(),
                "authors": [a.findtext("atom:name", ns, "") for a in entry.findall("atom:author", ns)][:3],
                "summary": entry.findtext("atom:summary", ns, "")[:300].replace("\n", " "),
                "published": entry.findtext("atom:published", ns, "")[:10],
                "url": entry.findtext("atom:id", ns, ""),
                "pdf": pdf_link,
            })
        
        return results
    except Exception as e:
        return [{"error": f"arXiv search failed: {e}"}]


# ============================================
# ROUTER
# ============================================

def route(action: str, source: str, query: str = None, **kwargs) -> list[dict]:
    """Route to appropriate content handler."""
    
    limit = kwargs.get("limit", 10)
    url = kwargs.get("url")
    video_id = kwargs.get("video_id")
    category = kwargs.get("category")
    
    if source == "youtube":
        if action == "search":
            return youtube_search(query, limit)
        elif action == "transcript":
            vid = video_id or query
            return [youtube_transcript(vid)]
        else:
            return [{"error": f"Unknown action for youtube: {action}"}]
    
    elif source == "rss":
        if action == "fetch":
            if not url:
                return [{"error": "url required for rss fetch"}]
            return rss_fetch(url, limit)
        else:
            return [{"error": f"Unknown action for rss: {action}"}]
    
    elif source == "arxiv":
        if action == "search":
            return arxiv_search(query, limit, category)
        else:
            return [{"error": f"Unknown action for arxiv: {action}"}]
    
    else:
        return [{"error": f"Unknown source: {source}"}]


def format_results(results: list[dict], source: str) -> str:
    """Format results for display."""
    
    if not results:
        return "No results found."
    
    if "error" in results[0]:
        return f"❌ Error: {results[0]['error']}"
    
    output = [f"📚 {source.upper()} Results ({len(results)} items)", "=" * 50, ""]
    
    for i, item in enumerate(results, 1):
        title = item.get("title", "")[:80]
        url = item.get("url") or item.get("link", "")
        
        if source == "youtube":
            output.append(f"[{i}] {title}")
            output.append(f"    📺 {item.get('channel', '?')} | 👁️ {item.get('views', 0):,}")
        elif source == "arxiv":
            authors = ", ".join(item.get("authors", [])[:2])
            output.append(f"[{i}] {title}")
            output.append(f"    👤 {authors} | 📅 {item.get('published', '')}")
        else:
            output.append(f"[{i}] {title}")
            output.append(f"    📅 {item.get('date', '')[:20]}")
        
        if url:
            output.append(f"    🔗 {url[:70]}...")
        output.append("")
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Content Master Tool")
    parser.add_argument("action", choices=["search", "fetch", "transcript"])
    parser.add_argument("source", choices=["youtube", "rss", "arxiv"])
    parser.add_argument("query", nargs="?", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--url", help="RSS feed URL")
    parser.add_argument("--video-id", help="YouTube video ID")
    parser.add_argument("--category", help="arXiv category (e.g., cs.AI)")
    parser.add_argument("--json", action="store_true")
    
    args = parser.parse_args()
    
    results = route(
        action=args.action,
        source=args.source,
        query=args.query,
        limit=args.limit,
        url=args.url,
        video_id=args.video_id,
        category=args.category,
    )
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_results(results, args.source))


if __name__ == "__main__":
    main()
