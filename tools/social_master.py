#!/usr/bin/env python3
"""
Social Master Tool - Unified social media scraping interface.

Consolidates: twitter, x-trends, reddit, hackernews, devto

Usage:
    python3 tools/social_master.py <action> <platform> [query] [options]
    
Actions:
    search    - Search posts/tweets by keyword
    trending  - Get trending topics/posts
    user      - Get posts from specific user
    top       - Get top posts from subreddit/topic

Platforms:
    twitter   - Twitter/X via snscrape
    reddit    - Reddit via old.reddit.com JSON
    hn        - HackerNews via Algolia API
    devto     - Dev.to articles

Examples:
    python3 tools/social_master.py search twitter "AI agents"
    python3 tools/social_master.py trending twitter
    python3 tools/social_master.py search reddit "python automation" --subreddit=automation
    python3 tools/social_master.py search hn "vector database"
    python3 tools/social_master.py top devto --tag=ai
"""

import argparse
import json
import sys
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.parse import quote_plus, urlencode
from urllib.error import HTTPError

# ============================================
# TWITTER/X
# ============================================

def twitter_search(query: str, limit: int = 20) -> list[dict]:
    """Search Twitter via snscrape (if installed) or return instructions."""
    try:
        import snscrape.modules.twitter as sntwitter
        
        results = []
        scraper = sntwitter.TwitterSearchScraper(query)
        
        for i, tweet in enumerate(scraper.get_items()):
            if i >= limit:
                break
            results.append({
                "text": tweet.rawContent,
                "user": tweet.user.username,
                "date": str(tweet.date),
                "likes": tweet.likeCount,
                "retweets": tweet.retweetCount,
                "url": tweet.url,
            })
        
        return results
    except ImportError:
        return [{"error": "snscrape not installed. Run: pip install snscrape"}]


def twitter_trending() -> list[dict]:
    """Get trending topics - requires nitter fallback or API."""
    # Nitter instances for trending
    nitter_instances = [
        "https://nitter.net",
        "https://nitter.privacydev.net",
    ]
    
    for instance in nitter_instances:
        try:
            url = f"{instance}/search?f=tweets&q=*&since=today"
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            # This is a placeholder - real trending needs proper scraping
            return [{"note": f"Check {instance} manually for trends"}]
        except Exception:
            continue
    
    return [{"error": "No Nitter instances available"}]


# ============================================
# REDDIT
# ============================================

def reddit_search(query: str, subreddit: str = None, limit: int = 20) -> list[dict]:
    """Search Reddit via old.reddit.com JSON API."""
    
    if subreddit:
        url = f"https://old.reddit.com/r/{subreddit}/search.json?q={quote_plus(query)}&restrict_sr=on&limit={limit}"
    else:
        url = f"https://old.reddit.com/search.json?q={quote_plus(query)}&limit={limit}"
    
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (social_master bot)"})
    
    try:
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        results = []
        for post in data.get("data", {}).get("children", []):
            p = post.get("data", {})
            results.append({
                "title": p.get("title"),
                "subreddit": p.get("subreddit"),
                "score": p.get("score"),
                "comments": p.get("num_comments"),
                "url": f"https://reddit.com{p.get('permalink')}",
                "author": p.get("author"),
            })
        
        return results
    except HTTPError as e:
        return [{"error": f"Reddit API error: {e.code}"}]


def reddit_top(subreddit: str, timeframe: str = "week", limit: int = 20) -> list[dict]:
    """Get top posts from subreddit."""
    
    url = f"https://old.reddit.com/r/{subreddit}/top.json?t={timeframe}&limit={limit}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (social_master bot)"})
    
    try:
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        results = []
        for post in data.get("data", {}).get("children", []):
            p = post.get("data", {})
            results.append({
                "title": p.get("title"),
                "score": p.get("score"),
                "comments": p.get("num_comments"),
                "url": f"https://reddit.com{p.get('permalink')}",
            })
        
        return results
    except HTTPError as e:
        return [{"error": f"Reddit API error: {e.code}"}]


# ============================================
# HACKERNEWS
# ============================================

def hn_search(query: str, limit: int = 20, story_type: str = "story") -> list[dict]:
    """Search HackerNews via Algolia API."""
    
    params = urlencode({
        "query": query,
        "tags": story_type,
        "hitsPerPage": limit,
    })
    url = f"https://hn.algolia.com/api/v1/search?{params}"
    
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        results = []
        for hit in data.get("hits", []):
            results.append({
                "title": hit.get("title"),
                "author": hit.get("author"),
                "points": hit.get("points"),
                "comments": hit.get("num_comments"),
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            })
        
        return results
    except HTTPError as e:
        return [{"error": f"HN API error: {e.code}"}]


def hn_trending(limit: int = 20) -> list[dict]:
    """Get front page stories (trending)."""
    
    url = f"https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage={limit}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        results = []
        for hit in data.get("hits", []):
            results.append({
                "title": hit.get("title"),
                "points": hit.get("points"),
                "comments": hit.get("num_comments"),
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            })
        
        return results
    except HTTPError as e:
        return [{"error": f"HN API error: {e.code}"}]


# ============================================
# DEV.TO
# ============================================

def devto_search(query: str = None, tag: str = None, limit: int = 20) -> list[dict]:
    """Search Dev.to articles."""
    
    params = {"per_page": limit}
    if query:
        params["search"] = query
    if tag:
        params["tag"] = tag
    
    url = f"https://dev.to/api/articles?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        results = []
        for article in data:
            results.append({
                "title": article.get("title"),
                "author": article.get("user", {}).get("username"),
                "reactions": article.get("positive_reactions_count"),
                "comments": article.get("comments_count"),
                "url": article.get("url"),
                "tags": article.get("tag_list", []),
            })
        
        return results
    except HTTPError as e:
        return [{"error": f"Dev.to API error: {e.code}"}]


def devto_top(tag: str = None, limit: int = 20) -> list[dict]:
    """Get top Dev.to articles."""
    
    params = {"per_page": limit, "top": 7}  # Top from last 7 days
    if tag:
        params["tag"] = tag
    
    url = f"https://dev.to/api/articles?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        results = []
        for article in data:
            results.append({
                "title": article.get("title"),
                "author": article.get("user", {}).get("username"),
                "reactions": article.get("positive_reactions_count"),
                "url": article.get("url"),
            })
        
        return results
    except HTTPError as e:
        return [{"error": f"Dev.to API error: {e.code}"}]


# ============================================
# ROUTER
# ============================================

def route(action: str, platform: str, query: str = None, **kwargs) -> list[dict]:
    """Route to appropriate platform handler."""
    
    limit = kwargs.get("limit", 20)
    subreddit = kwargs.get("subreddit")
    tag = kwargs.get("tag")
    timeframe = kwargs.get("timeframe", "week")
    
    # Twitter
    if platform == "twitter":
        if action == "search":
            return twitter_search(query, limit)
        elif action == "trending":
            return twitter_trending()
        else:
            return [{"error": f"Unknown action for twitter: {action}"}]
    
    # Reddit
    elif platform == "reddit":
        if action == "search":
            return reddit_search(query, subreddit, limit)
        elif action == "top":
            if not subreddit:
                return [{"error": "subreddit required for top action"}]
            return reddit_top(subreddit, timeframe, limit)
        else:
            return [{"error": f"Unknown action for reddit: {action}"}]
    
    # HackerNews
    elif platform in ("hn", "hackernews"):
        if action == "search":
            return hn_search(query, limit)
        elif action == "trending":
            return hn_trending(limit)
        else:
            return [{"error": f"Unknown action for hn: {action}"}]
    
    # Dev.to
    elif platform == "devto":
        if action == "search":
            return devto_search(query, tag, limit)
        elif action == "top":
            return devto_top(tag, limit)
        else:
            return [{"error": f"Unknown action for devto: {action}"}]
    
    else:
        return [{"error": f"Unknown platform: {platform}"}]


def format_results(results: list[dict], platform: str) -> str:
    """Format results for display."""
    
    if not results:
        return "No results found."
    
    if "error" in results[0]:
        return f"❌ Error: {results[0]['error']}"
    
    output = [f"📊 {platform.upper()} Results ({len(results)} items)", "=" * 50, ""]
    
    for i, item in enumerate(results, 1):
        title = item.get("title") or item.get("text", "")[:80]
        url = item.get("url", "")
        
        # Platform-specific formatting
        if platform == "twitter":
            output.append(f"[{i}] @{item.get('user', '?')}: {title[:100]}...")
            output.append(f"    ❤️ {item.get('likes', 0)} | 🔄 {item.get('retweets', 0)}")
        elif platform == "reddit":
            output.append(f"[{i}] r/{item.get('subreddit', '?')}: {title[:80]}")
            output.append(f"    ⬆️ {item.get('score', 0)} | 💬 {item.get('comments', 0)}")
        elif platform in ("hn", "hackernews"):
            output.append(f"[{i}] {title[:80]}")
            output.append(f"    ⬆️ {item.get('points', 0)} | 💬 {item.get('comments', 0)}")
        elif platform == "devto":
            output.append(f"[{i}] {title[:80]}")
            output.append(f"    ❤️ {item.get('reactions', 0)} | 💬 {item.get('comments', 0)}")
        
        if url:
            output.append(f"    🔗 {url[:60]}...")
        output.append("")
    
    return "\n".join(output)


# ============================================
# CLI
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="Social Master Tool - Unified social media interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("action", choices=["search", "trending", "user", "top"],
                        help="Action to perform")
    parser.add_argument("platform", choices=["twitter", "reddit", "hn", "hackernews", "devto"],
                        help="Platform to query")
    parser.add_argument("query", nargs="?", default=None,
                        help="Search query (required for search action)")
    parser.add_argument("--limit", type=int, default=20,
                        help="Number of results (default: 20)")
    parser.add_argument("--subreddit", "-r",
                        help="Subreddit for Reddit queries")
    parser.add_argument("--tag", "-t",
                        help="Tag for Dev.to queries")
    parser.add_argument("--timeframe", choices=["day", "week", "month", "year", "all"],
                        default="week", help="Timeframe for top posts")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON")
    
    args = parser.parse_args()
    
    # Validate
    if args.action == "search" and not args.query:
        parser.error("search action requires a query")
    
    # Execute
    results = route(
        action=args.action,
        platform=args.platform,
        query=args.query,
        limit=args.limit,
        subreddit=args.subreddit,
        tag=args.tag,
        timeframe=args.timeframe,
    )
    
    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_results(results, args.platform))


if __name__ == "__main__":
    main()
