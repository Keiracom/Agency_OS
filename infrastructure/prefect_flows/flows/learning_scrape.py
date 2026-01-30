"""
Elliot Daily Learning Scrape Flow
=================================
Automated knowledge acquisition from HackerNews, ProductHunt, GitHub Trending,
YouTube, and Reddit.

Rate-limited to 1 request per 5 seconds. Writes to elliot_knowledge table.
Includes relevance scoring to prioritize Agency OS-relevant content.

Enhanced with:
- YouTube: Specific tech/AI/SaaS channels via Apify
- HackerNews: Show HN, Ask HN sections
- ProductHunt: Today's launches with descriptions
- GitHub: Language filters (Python, TypeScript) + Collections
- Reddit: r/SaaS, r/Entrepreneur, r/sales, r/startups
"""

import asyncio
import hashlib
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path

import httpx
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from supabase import create_client, Client


# ============================================
# Relevance Scoring System
# ============================================

# Keyword patterns with their score boosts
SCORING_CONFIG = {
    # HIGH RELEVANCE (0.3-0.5 boost) - Agency OS Stack
    "high_stack": {
        "boost": 0.45,
        "patterns": [
            r'\b(fastapi|fast-api|fast api)\b',
            r'\b(nextjs|next\.js|next js)\b',
            r'\bsupabase\b',
            r'\bprefect\b',
            r'\brailway\b',
            r'\bvercel\b',
        ]
    },
    # HIGH RELEVANCE - AI/LLM Tools
    "high_ai": {
        "boost": 0.40,
        "patterns": [
            r'\b(anthropic|claude|sonnet|opus|haiku)\b',
            r'\b(openai|gpt-4|gpt4|chatgpt|gpt-3|gpt3)\b',
            r'\b(llm|llms|large language model)\b',
            r'\b(langchain|langsmith|langgraph)\b',
            r'\b(rag|retrieval augmented|vector database|embedding)\b',
            r'\b(ai agent|ai agents|agentic|multi-agent)\b',
            r'\b(mcp|model context protocol)\b',
        ]
    },
    # HIGH RELEVANCE - Outreach/Automation
    "high_outreach": {
        "boost": 0.40,
        "patterns": [
            r'\b(cold email|email outreach|outbound|lead gen|lead generation)\b',
            r'\b(sales automation|crm|pipeline|prospecting)\b',
            r'\b(linkedin automation|linkedin outreach)\b',
            r'\b(workflow automation|n8n|zapier|make\.com)\b',
            r'\b(twilio|sendgrid|resend|email api)\b',
        ]
    },
    # HIGH RELEVANCE - SaaS/Agency Business
    "high_business": {
        "boost": 0.35,
        "patterns": [
            r'\b(saas|software as a service)\b',
            r'\b(agency|agencies|white label|whitelabel)\b',
            r'\b(mrr|arr|churn|retention|pricing|monetization)\b',
            r'\b(b2b|enterprise sales|smb)\b',
        ]
    },
    # HIGH RELEVANCE - Enterprise/Advanced Architecture
    "high_enterprise": {
        "boost": 0.45,
        "patterns": [
            r'\b(production|enterprise|scale|architecture|infrastructure)\b',
            r'\b(multi-agent|orchestration|autonomous agent)\b',
            r'\b(thought leader|deep dive|novel approach|research)\b',
            r'\b(system design|distributed|high availability|fault tolerant)\b',
        ]
    },
    # HIGH RELEVANCE - Competitive Intel (Instantly, Smartlead, Apollo)
    "high_competitive": {
        "boost": 0.50,
        "patterns": [
            r'\b(instantly|smartlead|apollo\.io|lemlist|woodpecker)\b',
            r'\b(outreach\.io|salesloft|outplay|reply\.io)\b',
            r'\b(competitor|versus|alternative|comparison|benchmark)\b',
            r'\b(market leader|disrupting|challenging|overtaking)\b',
        ]
    },
    # MEDIUM RELEVANCE (0.1-0.2 boost) - Dev Tools
    "medium_dev": {
        "boost": 0.15,
        "patterns": [
            r'\b(python|typescript|javascript|rust|go)\b',
            r'\b(docker|kubernetes|k8s|terraform|aws|gcp|azure)\b',
            r'\b(postgres|postgresql|redis|mongodb)\b',
            r'\b(api|rest|graphql|grpc)\b',
            r'\b(github|gitlab|ci/cd|devops)\b',
        ]
    },
    # MEDIUM RELEVANCE - Productivity & Business
    "medium_productivity": {
        "boost": 0.18,
        "patterns": [
            r'\b(productivity|efficiency|automation)\b',
            r'\b(startup|founder|entrepreneur|bootstrap)\b',
            r'\b(remote work|async|team management)\b',
            r'\b(analytics|metrics|dashboard|monitoring)\b',
            r'\b(machine learning|ml|deep learning|neural network)\b',
        ]
    },
}

# Penalty patterns (reduce score)
PENALTY_PATTERNS = {
    # Gaming (penalty)
    "gaming": {
        "penalty": 0.30,
        "patterns": [
            r'\b(gaming|game|gamer|esports|playstation|xbox|nintendo|steam|twitch)\b',
            r'\b(fortnite|minecraft|valorant|league of legends|dota)\b',
        ]
    },
    # Crypto/Web3 (penalty)
    "crypto": {
        "penalty": 0.30,
        "patterns": [
            r'\b(crypto|cryptocurrency|bitcoin|btc|ethereum|eth|nft|web3|defi|blockchain)\b',
            r'\b(token|ico|airdrop|memecoin|shitcoin|hodl|moon)\b',
        ]
    },
    # Social/Entertainment (penalty)
    "social": {
        "penalty": 0.25,
        "patterns": [
            r'\b(tiktok|instagram|snapchat|influencer|viral|meme)\b',
            r'\b(celebrity|gossip|drama|reality tv)\b',
        ]
    },
    # Consumer/Unrelated (penalty)
    "consumer": {
        "penalty": 0.25,
        "patterns": [
            r'\b(recipe|cooking|fitness|workout|diet)\b',
            r'\b(dating|relationship|horoscope)\b',
        ]
    },
    # Beginner/Tutorial content (penalty) - We're building a unicorn
    "beginner": {
        "penalty": 0.35,
        "patterns": [
            r'\b(tutorial|beginner|getting started|how to start|for beginners)\b',
            r'\b(learn .* in \d+ minutes|crash course|101|basics)\b',
            r'\b(what is|introduction to|explained simply|easy guide)\b',
            r'\b(first steps|complete guide for beginners|no experience)\b',
        ]
    },
}

# Category boosts
CATEGORY_BOOSTS = {
    "tech_trend": 0.10,
    "tool_discovery": 0.15,
    "business_insight": 0.10,
    "competitor_intel": 0.15,
    "pattern_recognition": 0.10,
    "general": 0.0,
}


def score_knowledge_relevance(content: str, category: str = None) -> float:
    """
    Score content relevance 0.0-1.0 for Agency OS knowledge system.
    
    Scoring Tiers:
        HIGH (0.8-1.0): Agency OS stack, SaaS/agency, AI/LLM, outreach/automation
        MEDIUM (0.5-0.7): Dev tools, productivity, business insights
        LOW (0.0-0.4): Gaming, crypto, social, unrelated
    
    Args:
        content: Text content to score
        category: Optional category for additional boost
    
    Returns:
        Float score between 0.0 and 1.0
    """
    content_lower = (content or "").lower()
    base_score = 0.3
    keyword_boost = 0.0
    penalty = 0.0
    
    # Calculate keyword boosts
    for group_name, group_config in SCORING_CONFIG.items():
        for pattern in group_config["patterns"]:
            if re.search(pattern, content_lower, re.IGNORECASE):
                keyword_boost += group_config["boost"]
                break  # Only count once per group
    
    # Calculate penalties
    for group_name, group_config in PENALTY_PATTERNS.items():
        for pattern in group_config["patterns"]:
            if re.search(pattern, content_lower, re.IGNORECASE):
                penalty += group_config["penalty"]
                break  # Only count once per group
    
    # Category boost
    category_boost = CATEGORY_BOOSTS.get((category or "").lower(), 0.0)
    
    # Cap boosts and penalties
    keyword_boost = min(keyword_boost, 0.65)
    penalty = min(penalty, 0.50)
    
    # Calculate final score
    final_score = base_score + keyword_boost + category_boost - penalty
    return max(0.0, min(1.0, round(final_score, 2)))

# ============================================
# Configuration
# ============================================

# Load env from file if not already set
ENV_FILE = Path.home() / ".config" / "agency-os" / ".env"
if ENV_FILE.exists() and not os.environ.get("SUPABASE_URL"):
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

RATE_LIMIT_SECONDS = 5
REQUEST_TIMEOUT = 30

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
APIFY_API_KEY = os.environ.get("APIFY_API_KEY")

# Target YouTube channels for tech/AI/SaaS content
YOUTUBE_CHANNELS = [
    # Channel handles/URLs for specific tech channels
    {"name": "Y Combinator", "handle": "@ycombinator", "url": "https://www.youtube.com/@ycombinator/videos"},
    {"name": "Lex Fridman", "handle": "@lexfridman", "url": "https://www.youtube.com/@lexfridman/videos"},
    {"name": "My First Million", "handle": "@MyFirstMillionPod", "url": "https://www.youtube.com/@MyFirstMillionPod/videos"},
    {"name": "All-In Podcast", "handle": "@alaboringpodcast", "url": "https://www.youtube.com/@alaboringpodcast/videos"},
    {"name": "Lenny's Podcast", "handle": "@LennysPodcast", "url": "https://www.youtube.com/@LennysPodcast/videos"},
    {"name": "Greg Isenberg", "handle": "@gregisenberg", "url": "https://www.youtube.com/@gregisenberg/videos"},
]

# ============================================
# Rate Limiter
# ============================================

class RateLimiter:
    """Simple async rate limiter."""
    
    def __init__(self, min_interval: float = 5.0):
        self.min_interval = min_interval
        self.last_request = 0
    
    async def wait(self):
        """Wait until rate limit allows next request."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self.last_request
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_request = asyncio.get_event_loop().time()

rate_limiter = RateLimiter(RATE_LIMIT_SECONDS)

# ============================================
# Supabase Client
# ============================================

def get_supabase() -> Client:
    """Get authenticated Supabase client."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ============================================
# Scraping Tasks
# ============================================

@task(
    retries=2,
    retry_delay_seconds=10,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=6) if 'timedelta' in dir() else None
)
async def scrape_hackernews(limit: int = 30) -> list[dict]:
    """
    Scrape HackerNews front page, Show HN, and Ask HN stories.
    Uses official HN API (free, no auth required).
    
    Enhanced to capture:
    - Top stories (main page)
    - Show HN posts (product launches, demos)
    - Ask HN posts (questions, patterns, advice)
    """
    logger = get_run_logger()
    logger.info(f"Scraping HackerNews (top + Show HN + Ask HN) limit: {limit}...")
    
    insights = []
    
    # Define story sources with their endpoints and types
    story_sources = [
        ("topstories", "hackernews", limit),
        ("showstories", "hackernews_show", limit // 2),  # Show HN
        ("askstories", "hackernews_ask", limit // 2),    # Ask HN
    ]
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for endpoint, source_type, source_limit in story_sources:
            await rate_limiter.wait()
            try:
                response = await client.get(f"https://hacker-news.firebaseio.com/v0/{endpoint}.json")
                response.raise_for_status()
                story_ids = response.json()[:source_limit]
                
                for story_id in story_ids:
                    await rate_limiter.wait()
                    try:
                        story_response = await client.get(
                            f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                        )
                        story_response.raise_for_status()
                        story = story_response.json()
                        
                        if not story or story.get("type") != "story":
                            continue
                        
                        title = story.get("title", "")
                        url = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
                        score = story.get("score", 0)
                        text = story.get("text", "")  # Ask HN posts have text body
                        
                        # Calculate confidence based on engagement
                        confidence = min(0.95, 0.4 + (score / 500))
                        
                        # Categorize based on title keywords and source
                        category = categorize_content(title)
                        
                        # Add prefix based on source type
                        if source_type == "hackernews_show":
                            prefix = "[Show HN"
                        elif source_type == "hackernews_ask":
                            prefix = "[Ask HN"
                        else:
                            prefix = "[HN"
                        
                        insights.append({
                            "category": category,
                            "content": f"{prefix} {score}pts] {title}",
                            "summary": text[:300] if text else title[:200],
                            "source_url": url,
                            "source_type": source_type,
                            "confidence_score": round(confidence, 2),
                            "metadata": {
                                "hn_id": story_id,
                                "score": score,
                                "comments": story.get("descendants", 0),
                                "hn_type": endpoint.replace("stories", "")
                            }
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to fetch HN story {story_id}: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"Failed to fetch HN {endpoint}: {e}")
                continue
    
    logger.info(f"Scraped {len(insights)} HackerNews stories (top + Show HN + Ask HN)")
    return insights


@task(retries=2, retry_delay_seconds=10)
async def scrape_producthunt(limit: int = 10) -> list[dict]:
    """
    Scrape ProductHunt today's launches with descriptions.
    Uses web scraping (no API key required for basic data).
    
    Enhanced to capture:
    - Today's launches specifically
    - Product descriptions/taglines
    - Vote counts
    """
    logger = get_run_logger()
    logger.info(f"Scraping ProductHunt today's launches (limit: {limit})...")
    
    insights = []
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        await rate_limiter.wait()
        
        try:
            # ProductHunt RSS feed for today's posts
            response = await client.get(
                "https://www.producthunt.com/feed",
                headers={"User-Agent": "Elliot-Learning-Bot/1.0"}
            )
            response.raise_for_status()
            
            content = response.text
            
            # Parse RSS feed - extract title, link, and description
            # Pattern matches: <item>...<title>...</title>...<link>...</link>...<description>...</description>...</item>
            items = re.findall(
                r'<item>.*?<title><!\[CDATA\[(.*?)\]\]></title>.*?<link>(.*?)</link>.*?<description><!\[CDATA\[(.*?)\]\]></description>.*?</item>',
                content,
                re.DOTALL
            )[:limit]
            
            for title, url, description in items:
                title = title.strip()
                url = url.strip()
                description = description.strip()[:500]  # Truncate long descriptions
                
                # Clean up HTML from description
                description = re.sub(r'<[^>]+>', '', description)
                
                insights.append({
                    "category": "tool_discovery",
                    "content": f"[ProductHunt Today] {title}",
                    "summary": f"{title}: {description[:200]}" if description else title[:200],
                    "source_url": url,
                    "source_type": "producthunt",
                    "confidence_score": 0.7,
                    "metadata": {
                        "scraped_from": "rss_feed",
                        "tagline": description[:100] if description else "",
                        "launch_type": "today"
                    }
                })
                
        except Exception as e:
            logger.warning(f"ProductHunt RSS failed: {e}")
            
    logger.info(f"Scraped {len(insights)} ProductHunt products")
    return insights


@task(retries=2, retry_delay_seconds=10)
async def scrape_github_trending(limit: int = 15) -> list[dict]:
    """
    Scrape GitHub Trending repositories with language filters.
    Uses web scraping (no API key required).
    
    Enhanced to capture:
    - Python trending repos
    - TypeScript trending repos
    - Collections (curated lists)
    """
    logger = get_run_logger()
    logger.info(f"Scraping GitHub Trending (Python + TypeScript + Collections) limit: {limit}...")
    
    insights = []
    
    # Define language filters and sources
    sources = [
        ("https://github.com/trending/python?since=daily", "python", limit // 3),
        ("https://github.com/trending/typescript?since=daily", "typescript", limit // 3),
        ("https://github.com/trending?since=daily", "all", limit // 3),
    ]
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for url, language, source_limit in sources:
            await rate_limiter.wait()
            
            try:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Elliot-Learning-Bot/1.0",
                        "Accept": "text/html"
                    }
                )
                response.raise_for_status()
                content = response.text
                
                # Parse trending repos - look for repo links in article elements
                # Pattern: href="/owner/repo" followed by description
                repo_pattern = r'<article[^>]*>.*?<h2[^>]*>.*?<a href="(/[^/]+/[^"]+)"[^>]*>.*?</h2>.*?<p[^>]*>(.*?)</p>'
                matches = re.findall(repo_pattern, content, re.DOTALL)
                
                # Fallback to simpler pattern if no matches
                if not matches:
                    repos = re.findall(r'href="(/[^/]+/[^"]+)"[^>]*class="[^"]*Link[^"]*"', content)
                    matches = [(repo, "") for repo in repos]
                
                seen = set()
                count = 0
                
                for repo_path, description in matches:
                    if repo_path.startswith('/trending') or repo_path.count('/') != 2:
                        continue
                    if repo_path in seen:
                        continue
                    seen.add(repo_path)
                    
                    if count >= source_limit:
                        break
                    
                    repo_name = repo_path.strip('/')
                    repo_url = f"https://github.com{repo_path}"
                    desc = re.sub(r'<[^>]+>', '', description).strip()[:200] if description else ""
                    
                    # Determine category based on repo name/description
                    category = "tool_discovery"
                    text_to_check = f"{repo_name} {desc}".lower()
                    if any(kw in text_to_check for kw in ['ai', 'ml', 'llm', 'gpt', 'agent']):
                        category = "tech_trend"
                    
                    insights.append({
                        "category": category,
                        "content": f"[GitHub Trending {language.upper()}] {repo_name}",
                        "summary": f"{repo_name}: {desc}" if desc else f"Trending repo: {repo_name}",
                        "source_url": repo_url,
                        "source_type": "github",
                        "confidence_score": 0.75,
                        "metadata": {
                            "repo": repo_name,
                            "language": language,
                            "description": desc
                        }
                    })
                    count += 1
                    
            except Exception as e:
                logger.warning(f"GitHub trending scrape failed for {language}: {e}")
        
        # Also scrape GitHub Collections
        await rate_limiter.wait()
        try:
            collections_response = await client.get(
                "https://github.com/collections",
                headers={
                    "User-Agent": "Elliot-Learning-Bot/1.0",
                    "Accept": "text/html"
                }
            )
            collections_response.raise_for_status()
            collections_content = collections_response.text
            
            # Extract collection links and titles
            collection_pattern = r'<a[^>]*href="(/collections/[^"]+)"[^>]*>.*?<h3[^>]*>(.*?)</h3>'
            collections = re.findall(collection_pattern, collections_content, re.DOTALL)[:5]
            
            for collection_path, collection_title in collections:
                collection_title = re.sub(r'<[^>]+>', '', collection_title).strip()
                collection_url = f"https://github.com{collection_path}"
                
                insights.append({
                    "category": "tool_discovery",
                    "content": f"[GitHub Collection] {collection_title}",
                    "summary": f"Curated collection: {collection_title}",
                    "source_url": collection_url,
                    "source_type": "github_collection",
                    "confidence_score": 0.65,
                    "metadata": {
                        "collection_name": collection_title,
                        "type": "collection"
                    }
                })
                
        except Exception as e:
            logger.warning(f"GitHub collections scrape failed: {e}")
    
    logger.info(f"Scraped {len(insights)} GitHub trending repos and collections")
    return insights


@task(retries=2, retry_delay_seconds=30)
async def scrape_youtube(limit: int = 30) -> list[dict]:
    """
    Scrape YouTube for AI/SaaS videos from specific tech channels using Apify.
    
    Target channels:
    - Y Combinator
    - Lex Fridman (AI guests)
    - My First Million (SaaS)
    - All-In Podcast
    - Lenny's Podcast
    - Greg Isenberg
    
    Also includes search queries for AI/automation topics.
    """
    logger = get_run_logger()
    logger.info(f"Scraping YouTube channels and AI/automation videos (limit: {limit})...")
    
    if not APIFY_API_KEY:
        logger.warning("APIFY_API_KEY not set, skipping YouTube scrape")
        return []
    
    insights = []
    
    # Build start URLs from both channels and search queries
    start_urls = []
    
    # Add channel URLs (recent videos)
    for channel in YOUTUBE_CHANNELS:
        start_urls.append({"url": channel["url"]})
    
    # Add search URLs for AI/automation topics (filtered by upload date)
    search_queries = [
        "AI agent architecture",
        "autonomous agent frameworks",
        "multi-agent orchestration",
        "LLM production deployment",
        "enterprise AI infrastructure",
        "agentic AI research",
        "AI-first SaaS architecture",
        "cold email AI automation",
        "AI sales automation enterprise",
    ]
    
    for query in search_queries:
        # sp=EgQIAxAB filters to "This week" and sorts by view count
        encoded_query = query.replace(" ", "+")
        start_urls.append({"url": f"https://www.youtube.com/results?search_query={encoded_query}&sp=EgQIAxAB"})
    
    async with httpx.AsyncClient(timeout=300) as client:
        await rate_limiter.wait()
        
        try:
            # Use streamers/youtube-scraper actor
            run_response = await client.post(
                "https://api.apify.com/v2/acts/streamers~youtube-scraper/runs",
                headers={"Authorization": f"Bearer {APIFY_API_KEY}"},
                json={
                    "startUrls": start_urls,
                    "maxResults": limit,
                    "maxResultsShorts": 0,  # Skip shorts
                    "proxy": {"useApifyProxy": True},
                }
            )
            
            if run_response.status_code != 201:
                logger.warning(f"YouTube scraper start failed: {run_response.status_code} - {run_response.text[:200]}")
                return []
            
            run_data = run_response.json()
            run_id = run_data.get("data", {}).get("id")
            
            if not run_id:
                return []
            
            logger.info(f"YouTube scraper started: run_id={run_id}")
            
            # Poll for completion (max 180 seconds for multiple channels)
            for _ in range(36):
                await asyncio.sleep(5)
                status_response = await client.get(
                    f"https://api.apify.com/v2/actor-runs/{run_id}",
                    headers={"Authorization": f"Bearer {APIFY_API_KEY}"}
                )
                status_data = status_response.json()
                status = status_data.get("data", {}).get("status")
                
                if status == "SUCCEEDED":
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    logger.warning(f"YouTube scraper run failed: {status}")
                    return []
            else:
                logger.warning("YouTube scraper timed out after 180s")
                return []
            
            # Get results
            dataset_id = status_data.get("data", {}).get("defaultDatasetId")
            if not dataset_id:
                return []
            
            results_response = await client.get(
                f"https://api.apify.com/v2/datasets/{dataset_id}/items",
                headers={"Authorization": f"Bearer {APIFY_API_KEY}"}
            )
            
            videos = results_response.json() if results_response.status_code == 200 else []
            
            for video in videos:
                title = video.get("title", "")
                description = (video.get("description") or video.get("text") or "")[:500]
                channel = video.get("channelName") or video.get("author", {}).get("name", "")
                view_count = video.get("viewCount") or video.get("views", 0)
                url = video.get("url") or video.get("link", "")
                published = video.get("uploadDate") or video.get("date", "")
                
                # Handle view count as string with commas
                if isinstance(view_count, str):
                    view_count = int(view_count.replace(",", "").replace(" views", "").strip() or 0)
                
                if not title or not url:
                    continue
                
                # Filter by minimum views (500+ for channel videos, 1000+ for search)
                min_views = 500 if any(ch["name"].lower() in channel.lower() for ch in YOUTUBE_CHANNELS) else 1000
                if view_count < min_views:
                    continue
                
                # Confidence based on views and channel
                confidence = min(0.95, 0.5 + (view_count / 100000))
                # Boost confidence for known channels
                if any(ch["name"].lower() in channel.lower() for ch in YOUTUBE_CHANNELS):
                    confidence = min(0.95, confidence + 0.1)
                
                category = categorize_content(f"{title} {description}")
                
                # Determine if from target channel
                from_target_channel = any(ch["name"].lower() in channel.lower() for ch in YOUTUBE_CHANNELS)
                
                insights.append({
                    "category": category,
                    "content": f"[YouTube {view_count:,} views] {title}",
                    "summary": f"{title} by {channel}. {description[:200]}",
                    "source_url": url,
                    "source_type": "youtube",
                    "confidence_score": round(confidence, 2),
                    "metadata": {
                        "channel": channel,
                        "view_count": view_count,
                        "published": published,
                        "from_target_channel": from_target_channel,
                    }
                })
                
        except Exception as e:
            logger.error(f"YouTube scrape failed: {e}")
    
    logger.info(f"Scraped {len(insights)} YouTube videos")
    return insights


@task(retries=2, retry_delay_seconds=30)
async def scrape_reddit(limit: int = 50) -> list[dict]:
    """
    Scrape Reddit for relevant posts using Apify.
    Uses trudax/reddit-scraper-lite actor.
    
    Enhanced subreddits:
    - r/SaaS - SaaS business discussions
    - r/Entrepreneur - Business/startup insights
    - r/sales - Sales strategies and tools
    - r/startups - Startup community
    - r/automation - Automation tools and workflows
    - r/LocalLLaMA - Local LLM developments
    - r/ChatGPT - AI/LLM trends
    - r/webdev - Web development trends
    """
    logger = get_run_logger()
    logger.info(f"Scraping Reddit (expanded subreddits) limit: {limit}...")
    
    if not APIFY_API_KEY:
        logger.warning("APIFY_API_KEY not set, skipping Reddit scrape")
        return []
    
    insights = []
    
    # Enhanced subreddit list with top posts from today
    subreddit_urls = [
        # Business/SaaS
        {"url": "https://www.reddit.com/r/SaaS/top/?t=day"},
        {"url": "https://www.reddit.com/r/Entrepreneur/top/?t=day"},
        {"url": "https://www.reddit.com/r/sales/top/?t=day"},
        {"url": "https://www.reddit.com/r/startups/top/?t=day"},
        # Tech/AI
        {"url": "https://www.reddit.com/r/automation/top/?t=day"},
        {"url": "https://www.reddit.com/r/LocalLLaMA/top/?t=day"},
        {"url": "https://www.reddit.com/r/ChatGPT/top/?t=day"},
        {"url": "https://www.reddit.com/r/webdev/top/?t=day"},
        # Additional valuable subreddits
        {"url": "https://www.reddit.com/r/smallbusiness/top/?t=day"},
        {"url": "https://www.reddit.com/r/agency/top/?t=day"},
    ]
    
    async with httpx.AsyncClient(timeout=180) as client:
        await rate_limiter.wait()
        
        try:
            # Start Apify actor run using reddit-scraper-lite
            run_response = await client.post(
                "https://api.apify.com/v2/acts/trudax~reddit-scraper-lite/runs",
                headers={"Authorization": f"Bearer {APIFY_API_KEY}"},
                json={
                    "startUrls": subreddit_urls,
                    "maxItems": limit,
                    "proxy": {"useApifyProxy": True},
                }
            )
            
            if run_response.status_code != 201:
                logger.warning(f"Reddit scraper start failed: {run_response.status_code} - {run_response.text[:200]}")
                return []
            
            run_data = run_response.json()
            run_id = run_data.get("data", {}).get("id")
            
            if not run_id:
                return []
            
            # Poll for completion (max 120 seconds)
            for _ in range(24):
                await asyncio.sleep(5)
                status_response = await client.get(
                    f"https://api.apify.com/v2/actor-runs/{run_id}",
                    headers={"Authorization": f"Bearer {APIFY_API_KEY}"}
                )
                status_data = status_response.json()
                status = status_data.get("data", {}).get("status")
                
                if status == "SUCCEEDED":
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    logger.warning(f"Reddit scraper run failed: {status}")
                    return []
            else:
                logger.warning("Reddit scraper timed out")
                return []
            
            # Get results
            dataset_id = status_data.get("data", {}).get("defaultDatasetId")
            if not dataset_id:
                return []
            
            results_response = await client.get(
                f"https://api.apify.com/v2/datasets/{dataset_id}/items",
                headers={"Authorization": f"Bearer {APIFY_API_KEY}"}
            )
            
            posts = results_response.json() if results_response.status_code == 200 else []
            
            for post in posts:
                # Handle reddit-scraper-lite field names
                title = post.get("title") or post.get("parsedTitle", "")
                body = (post.get("body") or post.get("text") or "")[:500]
                subreddit = (post.get("communityName") or post.get("parsedCommunityName", "")).replace("r/", "")
                score = post.get("score") or post.get("upVotes", 0)
                url = post.get("url", "")
                
                # Skip comments (only want posts)
                if post.get("category") == "comment" or post.get("parentId"):
                    continue
                
                if not title:
                    continue
                
                # Ensure URL is complete
                if url and not url.startswith("http"):
                    url = f"https://reddit.com{url}"
                
                # Different score thresholds for different subreddits
                # Business subreddits typically have lower engagement
                business_subs = ['saas', 'entrepreneur', 'sales', 'startups', 'smallbusiness', 'agency']
                min_score = 20 if subreddit.lower() in business_subs else 50
                
                if score < min_score:
                    continue
                
                # Confidence based on score
                confidence = min(0.95, 0.5 + (score / 1000))
                category = categorize_content(f"{title} {body}")
                
                insights.append({
                    "category": category,
                    "content": f"[r/{subreddit} {score}pts] {title}",
                    "summary": f"{title}. {body[:200]}" if body else title,
                    "source_url": url,
                    "source_type": "reddit",
                    "confidence_score": round(confidence, 2),
                    "metadata": {
                        "subreddit": subreddit,
                        "score": score,
                    }
                })
                
        except Exception as e:
            logger.error(f"Reddit scrape failed: {e}")
    
    logger.info(f"Scraped {len(insights)} Reddit posts")
    return insights


# ============================================
# Processing Tasks
# ============================================

def categorize_content(text: str) -> str:
    """Categorize content based on keywords."""
    text_lower = text.lower()
    
    if any(kw in text_lower for kw in ['ai', 'llm', 'gpt', 'claude', 'machine learning', 'neural']):
        return "tech_trend"
    elif any(kw in text_lower for kw in ['startup', 'funding', 'vc', 'acquisition', 'ipo']):
        return "business_insight"
    elif any(kw in text_lower for kw in ['tool', 'app', 'launch', 'released', 'introducing']):
        return "tool_discovery"
    elif any(kw in text_lower for kw in ['pattern', 'architecture', 'design', 'best practice']):
        return "pattern_recognition"
    elif any(kw in text_lower for kw in ['competitor', 'versus', 'alternative', 'comparison']):
        return "competitor_intel"
    else:
        return "general"


def generate_content_hash(content: str, source_url: str) -> str:
    """Generate deduplication hash."""
    return hashlib.sha256(f"{content}:{source_url}".encode()).hexdigest()[:16]


@task
async def deduplicate_insights(insights: list[dict]) -> list[dict]:
    """Remove duplicate insights based on content hash."""
    logger = get_run_logger()
    
    seen_hashes = set()
    unique = []
    
    for insight in insights:
        content_hash = generate_content_hash(
            insight.get("content", ""),
            insight.get("source_url", "")
        )
        
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            insight["metadata"] = insight.get("metadata", {})
            insight["metadata"]["content_hash"] = content_hash
            unique.append(insight)
    
    logger.info(f"Deduplicated {len(insights)} -> {len(unique)} insights")
    return unique


@task
async def score_insights(insights: list[dict]) -> list[dict]:
    """
    Apply relevance scoring to all insights.
    Adds relevance_score field to each insight.
    """
    logger = get_run_logger()
    
    scored = []
    high_count = 0
    medium_count = 0
    low_count = 0
    
    for insight in insights:
        # Combine content and summary for scoring
        text_to_score = f"{insight.get('content', '')} {insight.get('summary', '')}"
        category = insight.get('category')
        
        score = score_knowledge_relevance(text_to_score, category)
        insight['relevance_score'] = score
        
        # Track distribution
        if score >= 0.8:
            high_count += 1
        elif score >= 0.5:
            medium_count += 1
        else:
            low_count += 1
        
        scored.append(insight)
    
    logger.info(
        f"Scored {len(scored)} insights: "
        f"HIGH={high_count}, MEDIUM={medium_count}, LOW={low_count}"
    )
    
    return scored


@task
async def store_insights(insights: list[dict]) -> int:
    """Store insights in Supabase elliot_knowledge table."""
    logger = get_run_logger()
    
    if not insights:
        logger.info("No insights to store")
        return 0
    
    supabase = get_supabase()
    
    # Get existing content hashes to avoid duplicates
    hashes = [i.get("metadata", {}).get("content_hash") for i in insights if i.get("metadata", {}).get("content_hash")]
    
    if hashes:
        # Query existing records and extract hashes in Python
        existing = supabase.table("elliot_knowledge").select("metadata").execute()
        existing_hashes = set()
        for r in (existing.data or []):
            if r.get("metadata") and r["metadata"].get("content_hash"):
                existing_hashes.add(r["metadata"]["content_hash"])
        insights = [i for i in insights if i.get("metadata", {}).get("content_hash") not in existing_hashes]
    
    if not insights:
        logger.info("All insights already exist")
        return 0
    
    # Batch insert
    try:
        result = supabase.table("elliot_knowledge").insert(insights).execute()
        stored_count = len(result.data) if result.data else 0
        logger.info(f"Stored {stored_count} new insights")
        return stored_count
    except Exception as e:
        logger.error(f"Failed to store insights: {e}")
        raise


@task
async def update_learning_stats(stored_count: int):
    """Update learning statistics in session state."""
    logger = get_run_logger()
    
    supabase = get_supabase()
    
    try:
        # Get current stats
        result = supabase.table("elliot_session_state").select("value").eq("key", "elliot:learning_stats").single().execute()
        stats = result.data.get("value", {}) if result.data else {}
        
        # Update stats
        stats["total_learned"] = stats.get("total_learned", 0) + stored_count
        stats["last_scrape"] = datetime.now(timezone.utc).isoformat()
        stats["last_scrape_count"] = stored_count
        
        # Upsert
        supabase.table("elliot_session_state").upsert({
            "key": "elliot:learning_stats",
            "value": stats
        }).execute()
        
        logger.info(f"Updated learning stats: total={stats['total_learned']}")
        
    except Exception as e:
        logger.warning(f"Failed to update learning stats: {e}")


# ============================================
# Main Flow
# ============================================

@flow(
    name="daily_learning_scrape",
    description="Scrape HackerNews, ProductHunt, GitHub Trending, YouTube, and Reddit for insights",
    retries=1,
    retry_delay_seconds=300,
    log_prints=True
)
async def daily_learning_scrape(
    hn_limit: int = 50,
    ph_limit: int = 10,
    gh_limit: int = 15,
    yt_limit: int = 30,
    reddit_limit: int = 50
):
    """
    Main flow: Scrape multiple sources and store insights.
    
    Args:
        hn_limit: Number of HackerNews stories to scrape (top + Show HN + Ask HN)
        ph_limit: Number of ProductHunt products to scrape
        gh_limit: Number of GitHub trending repos to scrape
        yt_limit: Number of YouTube videos to scrape
        reddit_limit: Number of Reddit posts to scrape
    """
    logger = get_run_logger()
    logger.info("Starting daily learning scrape...")
    
    # Run scrapers (sequentially to respect rate limits)
    hn_insights = await scrape_hackernews(hn_limit)
    ph_insights = await scrape_producthunt(ph_limit)
    gh_insights = await scrape_github_trending(gh_limit)
    yt_insights = await scrape_youtube(yt_limit)
    reddit_insights = await scrape_reddit(reddit_limit)
    
    # Combine all insights
    all_insights = hn_insights + ph_insights + gh_insights + yt_insights + reddit_insights
    logger.info(f"Total raw insights: {len(all_insights)}")
    
    # Deduplicate
    unique_insights = await deduplicate_insights(all_insights)
    
    # Score for relevance
    scored_insights = await score_insights(unique_insights)
    
    # Store in Supabase (DB trigger will also score, but we include for logging)
    stored_count = await store_insights(scored_insights)
    
    # Update stats
    await update_learning_stats(stored_count)
    
    # Calculate score distribution for return value
    high_relevance = len([i for i in scored_insights if i.get('relevance_score', 0) >= 0.8])
    medium_relevance = len([i for i in scored_insights if 0.5 <= i.get('relevance_score', 0) < 0.8])
    low_relevance = len([i for i in scored_insights if i.get('relevance_score', 0) < 0.5])
    
    logger.info(f"Daily learning scrape complete: {stored_count} new insights stored")
    
    return {
        "total_scraped": len(all_insights),
        "unique": len(unique_insights),
        "stored": stored_count,
        "relevance_distribution": {
            "high": high_relevance,
            "medium": medium_relevance,
            "low": low_relevance
        },
        "sources": {
            "hackernews": len(hn_insights),
            "producthunt": len(ph_insights),
            "github": len(gh_insights),
            "youtube": len(yt_insights),
            "reddit": len(reddit_insights)
        }
    }


# ============================================
# Deployment Helper
# ============================================

if __name__ == "__main__":
    # For local testing
    import asyncio
    asyncio.run(daily_learning_scrape())
