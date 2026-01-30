"""
Elliot Daily Learning Scrape Flow
=================================
Automated knowledge acquisition from HackerNews, ProductHunt, GitHub,
YouTube, Reddit, and Twitter/X.

All scrapers run in PARALLEL using asyncio.gather() to avoid timeouts.
Each scraper uses TARGETED KEYWORD SEARCHES for maximum relevance.
Writes to elliot_knowledge table with relevance scoring.

Scrapers use keyword-based searches:
- HackerNews: Algolia API with 5 targeted keywords (ALL TIME)
- GitHub: Search API with 5 keywords sorted by stars
- Reddit: Search across subreddits with 5 keywords (ALL TIME)
- YouTube: Search queries with 5 keywords + target channels
- ProductHunt: Search for AI/automation/sales tools
- Twitter/X: Keyword searches + thought leader accounts

Rate Limiting Strategy (to prevent bans):
- HackerNews (Algolia): 1 req/sec
- Reddit: 1 req/2sec (they ban aggressively)
- GitHub API: 1 req/2sec (30/min authenticated)
- ProductHunt: 1 req/3sec (gentle)
- ArXiv: 1 req/3sec (their policy)
- Dev.to: 1 req/sec (30/min limit)
- Indie Hackers: 1 req/5sec (no official API)
- RSS feeds: 1 req/2sec (standard courtesy)
- YouTube/Twitter via Apify: Actor handles limits
"""

import asyncio
import hashlib
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path
from functools import wraps

import httpx
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from supabase import create_client, Client


# ============================================
# Rate Limiting Infrastructure
# ============================================

# User-Agent header for all requests
HEADERS = {
    'User-Agent': 'ElliotBot/1.0 (Research; https://github.com/elliot-agent)'
}


class SourceRateLimiter:
    """
    Per-source rate limiter to prevent bans.
    Conservative delays based on each source's policies.
    """
    
    def __init__(self):
        self.last_request: dict[str, float] = defaultdict(float)
        self.delays = {
            'hackernews': 1.0,      # Algolia is generous but be safe
            'reddit': 2.0,           # They ban aggressively
            'github': 2.0,           # 30/min authenticated = 2sec/req
            'producthunt': 3.0,      # Be gentle
            'arxiv': 3.0,            # Their policy
            'devto': 1.0,            # 30/min limit
            'indiehackers': 5.0,     # Very gentle, no official API
            'rss': 2.0,              # Standard RSS courtesy
            'substack': 2.0,         # Standard RSS courtesy
            'aiblogs': 2.0,          # Standard RSS courtesy
            # YouTube and Twitter via Apify - actor handles it
            'apify': 0.0,            # Let Apify manage
        }
        self._lock = asyncio.Lock()
    
    async def wait(self, source: str):
        """Wait until rate limit allows next request for source."""
        async with self._lock:
            delay = self.delays.get(source.lower(), 2.0)
            if delay == 0:
                return
            
            now = time.time()
            elapsed = now - self.last_request[source]
            if elapsed < delay:
                wait_time = delay - elapsed
                logger = get_run_logger()
                logger.debug(f"Rate limiting {source}: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            self.last_request[source] = time.time()


class RequestTracker:
    """
    Track total requests per scrape run.
    Enforces max request cap to prevent runaway scraping.
    """
    
    def __init__(self, max_requests: int = 500):
        self.max_requests = max_requests
        self.request_count = 0
        self.rate_limit_hits = 0
        self.server_errors = 0
        self._lock = asyncio.Lock()
    
    async def increment(self) -> bool:
        """
        Increment request count. Returns False if cap exceeded.
        """
        async with self._lock:
            if self.request_count >= self.max_requests:
                return False
            self.request_count += 1
            return True
    
    async def record_rate_limit(self):
        """Record a rate limit hit (429)."""
        async with self._lock:
            self.rate_limit_hits += 1
    
    async def record_server_error(self):
        """Record a server error (5xx)."""
        async with self._lock:
            self.server_errors += 1
    
    def get_stats(self) -> dict:
        """Get current stats."""
        return {
            "total_requests": self.request_count,
            "max_requests": self.max_requests,
            "rate_limit_hits": self.rate_limit_hits,
            "server_errors": self.server_errors,
        }
    
    @property
    def can_continue(self) -> bool:
        """Check if we can continue making requests."""
        return self.request_count < self.max_requests


# Global instances
rate_limiter = SourceRateLimiter()
request_tracker = RequestTracker(max_requests=500)


async def make_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    source: str,
    **kwargs
) -> httpx.Response:
    """
    Make an HTTP request with rate limiting, retries, and tracking.
    
    Args:
        client: httpx client
        method: HTTP method (GET, POST)
        url: URL to request
        source: Source name for rate limiting
        **kwargs: Additional request arguments
    
    Returns:
        httpx.Response
    
    Raises:
        Exception if cap exceeded or all retries fail
    """
    logger = get_run_logger()
    
    # Check if we can make more requests
    if not await request_tracker.increment():
        raise Exception(f"Request cap exceeded ({request_tracker.max_requests})")
    
    # Wait for rate limit
    await rate_limiter.wait(source)
    
    # Merge headers
    headers = {**HEADERS, **kwargs.pop('headers', {})}
    
    # Retry logic with exponential backoff
    max_retries = 2
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            if method.upper() == 'GET':
                response = await client.get(url, headers=headers, **kwargs)
            else:
                response = await client.post(url, headers=headers, **kwargs)
            
            # Handle rate limiting (429)
            if response.status_code == 429:
                await request_tracker.record_rate_limit()
                if attempt < max_retries:
                    wait_time = 60  # Wait 60s on rate limit
                    logger.warning(f"Rate limited (429) on {source}, waiting {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Rate limited (429) on {source}, max retries exceeded")
                    raise httpx.HTTPStatusError(
                        f"Rate limited after {max_retries} retries",
                        request=response.request,
                        response=response
                    )
            
            # Handle server errors (5xx)
            if 500 <= response.status_code < 600:
                await request_tracker.record_server_error()
                if attempt < max_retries:
                    wait_time = 10 * (attempt + 1)  # 10s, 20s backoff
                    logger.warning(f"Server error ({response.status_code}) on {source}, waiting {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Server error ({response.status_code}) on {source}, max retries exceeded")
            
            return response
            
        except httpx.TimeoutException as e:
            last_error = e
            if attempt < max_retries:
                wait_time = 5 * (attempt + 1)
                logger.warning(f"Timeout on {source}, waiting {wait_time}s (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)
                continue
            else:
                raise
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(f"Request error on {source}: {e}, retrying...")
                await asyncio.sleep(2)
                continue
            else:
                raise
    
    raise last_error or Exception(f"Request failed after {max_retries} retries")


# ============================================
# Keywords Configuration (Conservative - 5-10 per source)
# ============================================

# HackerNews Keywords (5) - Searched via Algolia ALL TIME
# Reduced from 15 to prevent rate limiting
HACKERNEWS_KEYWORDS = [
    "AI agents",
    "sales automation",
    "cold email",
    "multi-agent",
    "SaaS",
]

# GitHub Keywords (5) - Searched via Search API sorted by stars
# Reduced from 15 to stay under 30/min rate limit
GITHUB_KEYWORDS = [
    "ai-agents",
    "sales-automation",
    "cold-email",
    "multi-agent",
    "langchain",
]

# Reddit Keywords (5) - Searched ALL TIME across subreddits
# Reduced from 10 to prevent bans
REDDIT_KEYWORDS = [
    "AI agents",
    "cold email automation",
    "sales automation",
    "SaaS tools",
    "Claude",
]

# Reddit Subreddits (5) - Reduced from 10
REDDIT_SUBREDDITS = [
    "SaaS",
    "Entrepreneur",
    "sales",
    "LocalLLaMA",
    "ClaudeAI",
]

# YouTube Keywords (5) - Search queries
# Reduced from 10 - Apify handles limits but be conservative
YOUTUBE_KEYWORDS = [
    "AI agent tutorial",
    "cold email automation",
    "sales automation demo",
    "multi-agent system",
    "SaaS growth",
]

# ProductHunt Search Terms (5)
# Reduced from 8
PRODUCTHUNT_KEYWORDS = [
    "AI",
    "automation",
    "sales",
    "email",
    "agent",
]

# Twitter/X Keywords (5)
# Reduced from 10 - Apify handles limits but be conservative
TWITTER_KEYWORDS = [
    "AI agents",
    "cold email",
    "sales automation",
    "multi-agent",
    "SaaS",
]

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

REQUEST_TIMEOUT = 30
MAX_REQUESTS_PER_RUN = 500  # Total request cap per scrape run

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
APIFY_API_KEY = os.environ.get("APIFY_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # For higher rate limits

# Target YouTube channels for tech/AI/SaaS content (reduced from 6 to 3)
YOUTUBE_CHANNELS = [
    {"name": "Y Combinator", "handle": "@ycombinator", "url": "https://www.youtube.com/@ycombinator/videos"},
    {"name": "My First Million", "handle": "@MyFirstMillionPod", "url": "https://www.youtube.com/@MyFirstMillionPod/videos"},
    {"name": "Greg Isenberg", "handle": "@gregisenberg", "url": "https://www.youtube.com/@gregisenberg/videos"},
]

# Twitter/X thought leader accounts (reduced from 8 to 5)
TWITTER_ACCOUNTS = [
    "levelsio",       # Pieter Levels - indie hacker legend
    "gregisenberg",   # Greg Isenberg - Late Checkout
    "paulg",          # Paul Graham
    "AnthropicAI",    # Anthropic
    "OpenAI",         # OpenAI
]

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

@task(retries=2, retry_delay_seconds=10)
async def scrape_hackernews(limit_per_keyword: int = 50) -> list[dict]:
    """
    Scrape HackerNews using Algolia API with targeted keyword searches.
    Searches ALL TIME for comprehensive coverage.
    
    Rate limit: 1 req/sec (conservative for Algolia)
    
    Args:
        limit_per_keyword: Max results per keyword (50, reduced from 100)
    """
    logger = get_run_logger()
    logger.info(f"Scraping HackerNews via Algolia API with {len(HACKERNEWS_KEYWORDS)} keywords...")
    
    insights = []
    seen_ids = set()
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for keyword in HACKERNEWS_KEYWORDS:
            # Check request cap before making request
            if not request_tracker.can_continue:
                logger.warning("Request cap reached, stopping HackerNews scrape")
                break
                
            try:
                # Algolia API - search ALL TIME (no date filter)
                params = {
                    "query": keyword,
                    "tags": "story",
                    "hitsPerPage": limit_per_keyword,
                }
                response = await make_request(
                    client, 'GET',
                    "https://hn.algolia.com/api/v1/search",
                    source='hackernews',
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                hits = data.get("hits", [])
                logger.info(f"  [{keyword}] Found {len(hits)} stories")
                
                for hit in hits:
                    story_id = hit.get("objectID")
                    if story_id in seen_ids:
                        continue
                    seen_ids.add(story_id)
                    
                    title = hit.get("title", "")
                    url = hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
                    score = hit.get("points", 0) or 0
                    num_comments = hit.get("num_comments", 0) or 0
                    created_at = hit.get("created_at", "")
                    author = hit.get("author", "")
                    
                    if not title:
                        continue
                    
                    # Confidence based on engagement
                    confidence = min(0.95, 0.4 + (score / 500) + (num_comments / 200))
                    category = categorize_content(title)
                    
                    insights.append({
                        "category": category,
                        "content": f"[HN {score}pts] {title}",
                        "summary": f"{title} (by {author}, {num_comments} comments)",
                        "source_url": url,
                        "source_type": "hackernews",
                        "confidence_score": round(confidence, 2),
                        "metadata": {
                            "hn_id": story_id,
                            "score": score,
                            "comments": num_comments,
                            "author": author,
                            "keyword": keyword,
                            "created_at": created_at,
                        }
                    })
                    
            except Exception as e:
                logger.warning(f"HN search failed for keyword '{keyword}': {e}")
                continue
    
    logger.info(f"Scraped {len(insights)} unique HackerNews stories (from {len(HACKERNEWS_KEYWORDS)} keywords)")
    return insights


@task(retries=2, retry_delay_seconds=10)
async def scrape_github(limit_per_keyword: int = 30) -> list[dict]:
    """
    Scrape GitHub using Search API with targeted keyword searches.
    Sorted by stars for quality signal.
    
    Rate limit: 1 req/2sec (30/min authenticated)
    
    Args:
        limit_per_keyword: Max results per keyword (30, reduced from 50)
    """
    logger = get_run_logger()
    logger.info(f"Scraping GitHub via Search API with {len(GITHUB_KEYWORDS)} keywords...")
    
    insights = []
    seen_repos = set()
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for keyword in GITHUB_KEYWORDS:
            # Check request cap before making request
            if not request_tracker.can_continue:
                logger.warning("Request cap reached, stopping GitHub scrape")
                break
                
            try:
                params = {
                    "q": keyword,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": min(limit_per_keyword, 100),  # GitHub max is 100
                }
                response = await make_request(
                    client, 'GET',
                    "https://api.github.com/search/repositories",
                    source='github',
                    params=params,
                    headers=headers
                )
                
                if response.status_code == 403:
                    logger.warning(f"GitHub rate limit hit for keyword '{keyword}'")
                    await asyncio.sleep(60)  # Wait a minute
                    continue
                    
                response.raise_for_status()
                data = response.json()
                
                items = data.get("items", [])
                logger.info(f"  [{keyword}] Found {len(items)} repos")
                
                for repo in items:
                    full_name = repo.get("full_name", "")
                    if full_name in seen_repos:
                        continue
                    seen_repos.add(full_name)
                    
                    name = repo.get("name", "")
                    description = (repo.get("description") or "")[:300]
                    stars = repo.get("stargazers_count", 0)
                    url = repo.get("html_url", "")
                    language = repo.get("language", "")
                    topics = repo.get("topics", [])
                    updated_at = repo.get("updated_at", "")
                    
                    if not name or not url:
                        continue
                    
                    # Minimum stars threshold
                    if stars < 10:
                        continue
                    
                    # Confidence based on stars
                    confidence = min(0.95, 0.5 + (stars / 5000))
                    category = categorize_content(f"{name} {description}")
                    
                    insights.append({
                        "category": category,
                        "content": f"[GitHub ⭐{stars:,}] {full_name}",
                        "summary": f"{full_name}: {description}" if description else f"GitHub repo: {full_name}",
                        "source_url": url,
                        "source_type": "github",
                        "confidence_score": round(confidence, 2),
                        "metadata": {
                            "repo": full_name,
                            "stars": stars,
                            "language": language,
                            "topics": topics[:5],
                            "keyword": keyword,
                            "updated_at": updated_at,
                        }
                    })
                    
            except Exception as e:
                logger.warning(f"GitHub search failed for keyword '{keyword}': {e}")
                continue
    
    logger.info(f"Scraped {len(insights)} unique GitHub repos (from {len(GITHUB_KEYWORDS)} keywords)")
    return insights


@task(retries=2, retry_delay_seconds=10)
async def scrape_reddit(limit_per_search: int = 25) -> list[dict]:
    """
    Scrape Reddit using search API across subreddits with keyword searches.
    Searches ALL TIME for comprehensive coverage.
    Uses old.reddit.com with browser User-Agent to avoid 403 blocks.
    
    Rate limit: 1 req/2sec (Reddit bans aggressively)
    
    Args:
        limit_per_search: Max results per subreddit/keyword combo (25, reduced from 50)
    """
    logger = get_run_logger()
    logger.info(f"Scraping Reddit with {len(REDDIT_KEYWORDS)} keywords across {len(REDDIT_SUBREDDITS)} subreddits...")
    
    insights = []
    seen_ids = set()
    
    # Reddit requires browser-like User-Agent to avoid 403
    reddit_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for subreddit in REDDIT_SUBREDDITS:
            for keyword in REDDIT_KEYWORDS:
                # Check request cap before making request
                if not request_tracker.can_continue:
                    logger.warning("Request cap reached, stopping Reddit scrape")
                    break
                    
                try:
                    # Use old.reddit.com with browser UA to avoid 403 blocks
                    url = f"https://old.reddit.com/r/{subreddit}/search.json"
                    params = {
                        "q": keyword,
                        "sort": "relevance",
                        "t": "all",  # ALL TIME
                        "limit": limit_per_search,
                        "restrict_sr": "on",  # Restrict to subreddit
                    }
                    response = await make_request(
                        client, 'GET', url,
                        source='reddit',
                        params=params,
                        headers=reddit_headers
                    )
                    
                    if response.status_code == 403:
                        logger.warning(f"Reddit 403 forbidden for r/{subreddit} - skipping")
                        continue
                    
                    if response.status_code == 429:
                        logger.warning(f"Reddit rate limit hit (will be handled by retry logic)")
                        continue
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    posts = data.get("data", {}).get("children", [])
                    
                    for post_wrapper in posts:
                        post = post_wrapper.get("data", {})
                        post_id = post.get("id", "")
                        
                        if post_id in seen_ids:
                            continue
                        seen_ids.add(post_id)
                        
                        title = post.get("title", "")
                        selftext = (post.get("selftext") or "")[:500]
                        score = post.get("score", 0)
                        num_comments = post.get("num_comments", 0)
                        permalink = post.get("permalink", "")
                        post_url = f"https://reddit.com{permalink}" if permalink else ""
                        created_utc = post.get("created_utc", 0)
                        author = post.get("author", "")
                        
                        if not title or not post_url:
                            continue
                        
                        # Minimum score threshold
                        if score < 5:
                            continue
                        
                        # Confidence based on score and comments
                        confidence = min(0.95, 0.4 + (score / 500) + (num_comments / 100))
                        category = categorize_content(f"{title} {selftext}")
                        
                        insights.append({
                            "category": category,
                            "content": f"[r/{subreddit} {score}pts] {title}",
                            "summary": f"{title}. {selftext[:200]}" if selftext else title,
                            "source_url": post_url,
                            "source_type": "reddit",
                            "confidence_score": round(confidence, 2),
                            "metadata": {
                                "subreddit": subreddit,
                                "score": score,
                                "comments": num_comments,
                                "author": author,
                                "keyword": keyword,
                                "created_utc": created_utc,
                            }
                        })
                        
                except Exception as e:
                    logger.warning(f"Reddit search failed for r/{subreddit} '{keyword}': {e}")
                    continue
            
            # Check cap after each subreddit
            if not request_tracker.can_continue:
                break
    
    logger.info(f"Scraped {len(insights)} unique Reddit posts (from {len(REDDIT_SUBREDDITS)} subreddits x {len(REDDIT_KEYWORDS)} keywords)")
    return insights


@task(retries=2, retry_delay_seconds=30)
async def scrape_youtube(limit_per_keyword: int = 15) -> list[dict]:
    """
    Scrape YouTube using Apify with keyword searches + target channels.
    
    Rate limit: Apify handles internal rate limits
    
    Args:
        limit_per_keyword: Max results per search query (15, reduced from 20)
    """
    logger = get_run_logger()
    logger.info(f"Scraping YouTube with {len(YOUTUBE_KEYWORDS)} keywords + {len(YOUTUBE_CHANNELS)} channels...")
    
    if not APIFY_API_KEY:
        logger.warning("APIFY_API_KEY not set, skipping YouTube scrape")
        return []
    
    # Check request cap (Apify calls count as requests)
    if not request_tracker.can_continue:
        logger.warning("Request cap reached, skipping YouTube scrape")
        return []
    
    insights = []
    
    # Build start URLs from keywords and channels
    start_urls = []
    
    # Add keyword search URLs
    for keyword in YOUTUBE_KEYWORDS:
        encoded_query = keyword.replace(" ", "+")
        # No date filter to get ALL TIME best results
        start_urls.append({"url": f"https://www.youtube.com/results?search_query={encoded_query}"})
    
    # Add channel URLs (recent videos from target channels)
    for channel in YOUTUBE_CHANNELS:
        start_urls.append({"url": channel["url"]})
    
    total_limit = limit_per_keyword * len(YOUTUBE_KEYWORDS) + 10 * len(YOUTUBE_CHANNELS)
    
    async with httpx.AsyncClient(timeout=300) as client:
        try:
            # Use streamers/youtube-scraper actor (Apify handles rate limits)
            run_response = await make_request(
                client, 'POST',
                "https://api.apify.com/v2/acts/streamers~youtube-scraper/runs",
                source='apify',
                headers={"Authorization": f"Bearer {APIFY_API_KEY}"},
                json={
                    "startUrls": start_urls,
                    "maxResults": total_limit,
                    "maxResultsShorts": 0,  # Skip shorts
                    "proxy": {"useApifyProxy": True},
                }
            )
            
            if run_response.status_code != 201:
                error_text = run_response.text[:200] if run_response.text else ""
                # Check for Apify billing/limit errors
                if run_response.status_code == 402 or "limit" in error_text.lower() or "exceeded" in error_text.lower():
                    logger.warning(f"YouTube scraper: Apify monthly limit exceeded - returning empty results")
                    return []
                logger.warning(f"YouTube scraper start failed: {run_response.status_code} - {error_text}")
                return []
            
            run_data = run_response.json()
            run_id = run_data.get("data", {}).get("id")
            
            if not run_id:
                return []
            
            logger.info(f"YouTube scraper started: run_id={run_id}")
            
            # Poll for completion (max 300 seconds for larger scrape)
            for _ in range(60):
                await asyncio.sleep(5)
                
                # Don't count polling as requests toward cap
                status_response = await client.get(
                    f"https://api.apify.com/v2/actor-runs/{run_id}",
                    headers={**HEADERS, "Authorization": f"Bearer {APIFY_API_KEY}"}
                )
                status_data = status_response.json()
                status = status_data.get("data", {}).get("status")
                
                if status == "SUCCEEDED":
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    logger.warning(f"YouTube scraper run failed: {status}")
                    return []
            else:
                logger.warning("YouTube scraper timed out after 300s")
                return []
            
            # Get results
            dataset_id = status_data.get("data", {}).get("defaultDatasetId")
            if not dataset_id:
                return []
            
            results_response = await client.get(
                f"https://api.apify.com/v2/datasets/{dataset_id}/items",
                headers={**HEADERS, "Authorization": f"Bearer {APIFY_API_KEY}"}
            )
            
            videos = results_response.json() if results_response.status_code == 200 else []
            seen_ids = set()
            
            for video in videos:
                video_id = video.get("id") or video.get("videoId", "")
                if video_id in seen_ids:
                    continue
                seen_ids.add(video_id)
                
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
                
                # Minimum views threshold
                if view_count < 1000:
                    continue
                
                # Confidence based on views and channel
                confidence = min(0.95, 0.5 + (view_count / 100000))
                # Boost confidence for known channels
                if any(ch["name"].lower() in channel.lower() for ch in YOUTUBE_CHANNELS):
                    confidence = min(0.95, confidence + 0.1)
                
                category = categorize_content(f"{title} {description}")
                from_target_channel = any(ch["name"].lower() in channel.lower() for ch in YOUTUBE_CHANNELS)
                
                insights.append({
                    "category": category,
                    "content": f"[YouTube {view_count:,} views] {title}",
                    "summary": f"{title} by {channel}. {description[:200]}",
                    "source_url": url,
                    "source_type": "youtube",
                    "confidence_score": round(confidence, 2),
                    "metadata": {
                        "video_id": video_id,
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


@task(retries=2, retry_delay_seconds=10)
async def scrape_producthunt(limit: int = 50) -> list[dict]:
    """
    Scrape ProductHunt for AI, automation, sales, and email tools.
    Uses RSS feed (JavaScript search is limited).
    
    Rate limit: 1 req/3sec (gentle)
    
    Args:
        limit: Total max products to scrape (50, reduced from 100)
    """
    logger = get_run_logger()
    logger.info(f"Scraping ProductHunt via RSS feed...")
    
    # Check request cap
    if not request_tracker.can_continue:
        logger.warning("Request cap reached, skipping ProductHunt scrape")
        return []
    
    insights = []
    seen_slugs = set()
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        # Get RSS feed for today's launches
        try:
            response = await make_request(
                client, 'GET',
                "https://www.producthunt.com/feed",
                source='producthunt'
            )
            response.raise_for_status()
            content = response.text
            
            # Parse RSS feed - try multiple patterns for flexibility
            # Pattern 1: CDATA wrapped content
            items = re.findall(
                r'<item>.*?<title><!\[CDATA\[(.*?)\]\]></title>.*?<link>(.*?)</link>.*?<description><!\[CDATA\[(.*?)\]\]></description>.*?</item>',
                content,
                re.DOTALL
            )
            
            # Pattern 2: Non-CDATA wrapped (fallback)
            if not items:
                items = re.findall(
                    r'<item>.*?<title>([^<]+)</title>.*?<link>([^<]+)</link>.*?<description>([^<]*)</description>.*?</item>',
                    content,
                    re.DOTALL
                )
            
            # Pattern 3: guid as link fallback
            if not items:
                items = re.findall(
                    r'<item>.*?<title>(?:<!\[CDATA\[)?([^\]<]+)(?:\]\]>)?</title>.*?<guid[^>]*>([^<]+)</guid>.*?</item>',
                    content,
                    re.DOTALL
                )
                items = [(t, u, "") for t, u in items]  # Add empty description
            
            logger.info(f"ProductHunt RSS parsed {len(items)} items from feed")
            
            for title, url, description in items[:limit]:
                title = title.strip()
                url = url.strip()
                description = re.sub(r'<[^>]+>', '', description.strip()[:500])
                
                # Extract slug from URL for dedup
                slug = url.split("/posts/")[-1] if "/posts/" in url else url
                if slug in seen_slugs:
                    continue
                seen_slugs.add(slug)
                
                # Check if relevant to our keywords
                text_to_check = f"{title} {description}".lower()
                is_relevant = any(kw.lower() in text_to_check for kw in PRODUCTHUNT_KEYWORDS)
                
                if is_relevant or len(insights) < 15:  # Always include top 15
                    insights.append({
                        "category": "tool_discovery",
                        "content": f"[ProductHunt] {title}",
                        "summary": f"{title}: {description[:200]}" if description else title[:200],
                        "source_url": url,
                        "source_type": "producthunt",
                        "confidence_score": 0.75 if is_relevant else 0.60,
                        "metadata": {
                            "slug": slug,
                            "tagline": description[:100] if description else "",
                            "matched_keywords": [kw for kw in PRODUCTHUNT_KEYWORDS if kw.lower() in text_to_check],
                        }
                    })
                    
        except Exception as e:
            logger.warning(f"ProductHunt RSS failed: {e}")
    
    logger.info(f"Scraped {len(insights)} ProductHunt products")
    return insights


@task(retries=2, retry_delay_seconds=30)
async def scrape_twitter(limit_per_keyword: int = 25) -> list[dict]:
    """
    Scrape Twitter/X using Apify with keyword searches + thought leader accounts.
    Uses apidojo/tweet-scraper actor which supports searchTerms.
    
    Rate limit: Apify handles internal rate limits
    
    Args:
        limit_per_keyword: Max tweets per search term (25, reduced from 50)
    """
    logger = get_run_logger()
    logger.info(f"Scraping Twitter/X with {len(TWITTER_KEYWORDS)} keywords + {len(TWITTER_ACCOUNTS)} accounts...")
    
    if not APIFY_API_KEY:
        logger.warning("APIFY_API_KEY not set, skipping Twitter scrape")
        return []
    
    # Check request cap
    if not request_tracker.can_continue:
        logger.warning("Request cap reached, skipping Twitter scrape")
        return []
    
    insights = []
    
    # Build search terms - keywords + account searches
    search_terms = []
    
    # Add keyword searches
    for keyword in TWITTER_KEYWORDS:
        search_terms.append(keyword)
    
    # Add account searches (from:username gets their tweets)
    for account in TWITTER_ACCOUNTS:
        search_terms.append(f"from:{account}")
    
    total_limit = limit_per_keyword * (len(TWITTER_KEYWORDS) + len(TWITTER_ACCOUNTS))
    
    async with httpx.AsyncClient(timeout=300) as client:
        try:
            # Use apidojo/tweet-scraper actor (Tweet Scraper V2)
            run_response = await make_request(
                client, 'POST',
                "https://api.apify.com/v2/acts/apidojo~tweet-scraper/runs",
                source='apify',
                headers={"Authorization": f"Bearer {APIFY_API_KEY}"},
                json={
                    "searchTerms": search_terms,
                    "maxTweets": total_limit,
                    "sort": "Latest",
                    "tweetLanguage": "en",
                    "addUserInfo": True,
                    "proxy": {"useApifyProxy": True},
                }
            )
            
            if run_response.status_code != 201:
                error_text = run_response.text[:200] if run_response.text else ""
                # Check for Apify billing/limit errors
                if run_response.status_code == 402 or "limit" in error_text.lower() or "exceeded" in error_text.lower():
                    logger.warning(f"Twitter scraper: Apify monthly limit exceeded - returning empty results")
                    return []
                logger.warning(f"Twitter scraper start failed: {run_response.status_code} - {error_text}")
                return []
            
            run_data = run_response.json()
            run_id = run_data.get("data", {}).get("id")
            
            if not run_id:
                return []
            
            logger.info(f"Twitter scraper started: run_id={run_id}")
            
            # Poll for completion (max 300 seconds)
            # Don't count polling as requests toward cap
            for _ in range(60):
                await asyncio.sleep(5)
                status_response = await client.get(
                    f"https://api.apify.com/v2/actor-runs/{run_id}",
                    headers={**HEADERS, "Authorization": f"Bearer {APIFY_API_KEY}"}
                )
                status_data = status_response.json()
                status = status_data.get("data", {}).get("status")
                
                if status == "SUCCEEDED":
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    logger.warning(f"Twitter scraper run failed: {status}")
                    return []
            else:
                logger.warning("Twitter scraper timed out after 300s")
                return []
            
            # Get results
            dataset_id = status_data.get("data", {}).get("defaultDatasetId")
            if not dataset_id:
                return []
            
            results_response = await client.get(
                f"https://api.apify.com/v2/datasets/{dataset_id}/items",
                headers={**HEADERS, "Authorization": f"Bearer {APIFY_API_KEY}"}
            )
            
            tweets = results_response.json() if results_response.status_code == 200 else []
            seen_ids = set()
            
            for tweet in tweets:
                tweet_id = tweet.get("id") or tweet.get("id_str") or tweet.get("tweetId", "")
                
                if tweet_id in seen_ids:
                    continue
                seen_ids.add(tweet_id)
                
                text = tweet.get("text") or tweet.get("full_text") or tweet.get("tweet", "")
                author = tweet.get("author", {})
                username = author.get("username") or author.get("screen_name") or tweet.get("username", "")
                display_name = author.get("name") or tweet.get("name", username)
                
                # Engagement metrics
                likes = tweet.get("likeCount") or tweet.get("favorite_count") or tweet.get("likes", 0)
                retweets = tweet.get("retweetCount") or tweet.get("retweet_count") or tweet.get("retweets", 0)
                replies = tweet.get("replyCount") or tweet.get("reply_count") or 0
                
                # Tweet URL
                url = tweet.get("url") or tweet.get("tweetUrl", "")
                if not url and username and tweet_id:
                    url = f"https://x.com/{username}/status/{tweet_id}"
                
                created_at = tweet.get("createdAt") or tweet.get("created_at", "")
                
                if not text:
                    continue
                
                # Skip retweets
                if text.startswith("RT @"):
                    continue
                
                # Calculate engagement score
                engagement = likes + (retweets * 2) + replies
                is_target_account = username.lower() in [a.lower() for a in TWITTER_ACCOUNTS]
                
                # Minimum engagement threshold
                min_engagement = 5 if is_target_account else 10
                if engagement < min_engagement:
                    continue
                
                # Confidence based on engagement
                confidence = min(0.95, 0.4 + (engagement / 1000))
                if is_target_account:
                    confidence = min(0.95, confidence + 0.15)
                
                category = categorize_content(text)
                content_text = text[:200] + "..." if len(text) > 200 else text
                
                insights.append({
                    "category": category,
                    "content": f"[X @{username} {likes}❤️ {retweets}🔄] {content_text}",
                    "summary": f"@{username} ({display_name}): {text[:300]}",
                    "source_url": url,
                    "source_type": "twitter",
                    "confidence_score": round(confidence, 2),
                    "metadata": {
                        "tweet_id": tweet_id,
                        "username": username,
                        "display_name": display_name,
                        "likes": likes,
                        "retweets": retweets,
                        "replies": replies,
                        "engagement": engagement,
                        "is_target_account": is_target_account,
                        "created_at": created_at,
                    }
                })
                
        except Exception as e:
            logger.error(f"Twitter scrape failed: {e}")
    
    logger.info(f"Scraped {len(insights)} tweets from X/Twitter")
    return insights


# ============================================
# NEW SOURCES (No Apify Required)
# ============================================

# ArXiv categories for AI/ML research
ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.MA"]  # AI, ML, NLP, Multi-agent

# Dev.to tags for relevant content
DEVTO_TAGS = ["ai", "machinelearning", "automation", "saas", "python"]

# AI/Tech blogs RSS feeds
AI_BLOG_FEEDS = [
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
    {"name": "Anthropic Research", "url": "https://www.anthropic.com/research/rss.xml"},
    {"name": "LangChain Blog", "url": "https://blog.langchain.dev/rss/"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "The Batch (DeepLearning.AI)", "url": "https://www.deeplearning.ai/the-batch/feed/"},
]


@task(retries=2, retry_delay_seconds=10)
async def scrape_arxiv(limit_per_category: int = 25) -> list[dict]:
    """
    Scrape ArXiv for AI/ML research papers via their API.
    Uses direct Atom API - no Apify needed.
    
    Rate limit: 1 req/3sec (ArXiv policy)
    
    Args:
        limit_per_category: Max results per category (25)
    """
    logger = get_run_logger()
    logger.info(f"Scraping ArXiv with {len(ARXIV_CATEGORIES)} categories...")
    
    insights = []
    seen_ids = set()
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for category in ARXIV_CATEGORIES:
            if not request_tracker.can_continue:
                logger.warning("Request cap reached, stopping ArXiv scrape")
                break
                
            try:
                # ArXiv API query
                params = {
                    "search_query": f"cat:{category}",
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                    "max_results": limit_per_category,
                }
                response = await make_request(
                    client, 'GET',
                    "http://export.arxiv.org/api/query",
                    source='arxiv',
                    params=params
                )
                response.raise_for_status()
                content = response.text
                
                # Parse Atom feed entries
                entries = re.findall(
                    r'<entry>(.*?)</entry>',
                    content,
                    re.DOTALL
                )
                
                logger.info(f"  [{category}] Found {len(entries)} papers")
                
                for entry in entries:
                    # Extract paper ID
                    id_match = re.search(r'<id>([^<]+)</id>', entry)
                    paper_id = id_match.group(1) if id_match else ""
                    
                    if paper_id in seen_ids:
                        continue
                    seen_ids.add(paper_id)
                    
                    # Extract title (clean whitespace)
                    title_match = re.search(r'<title>([^<]+)</title>', entry, re.DOTALL)
                    title = re.sub(r'\s+', ' ', title_match.group(1).strip()) if title_match else ""
                    
                    # Extract summary/abstract
                    summary_match = re.search(r'<summary>([^<]+)</summary>', entry, re.DOTALL)
                    summary = re.sub(r'\s+', ' ', summary_match.group(1).strip())[:500] if summary_match else ""
                    
                    # Extract authors
                    authors = re.findall(r'<name>([^<]+)</name>', entry)
                    author_str = ", ".join(authors[:3])
                    if len(authors) > 3:
                        author_str += f" et al. ({len(authors)} authors)"
                    
                    # Extract published date
                    published_match = re.search(r'<published>([^<]+)</published>', entry)
                    published = published_match.group(1) if published_match else ""
                    
                    # Get abstract page URL
                    url = paper_id.replace("/abs/", "/abs/") if "/abs/" in paper_id else paper_id
                    
                    if not title:
                        continue
                    
                    category_str = categorize_content(f"{title} {summary}")
                    
                    insights.append({
                        "category": category_str,
                        "content": f"[ArXiv {category}] {title}",
                        "summary": f"{title} by {author_str}. {summary[:250]}",
                        "source_url": url,
                        "source_type": "arxiv",
                        "confidence_score": 0.80,  # Research papers are high quality
                        "metadata": {
                            "arxiv_id": paper_id,
                            "category": category,
                            "authors": authors[:5],
                            "published": published,
                        }
                    })
                    
            except Exception as e:
                logger.warning(f"ArXiv scrape failed for {category}: {e}")
                continue
    
    logger.info(f"Scraped {len(insights)} ArXiv papers")
    return insights


@task(retries=2, retry_delay_seconds=10)
async def scrape_devto(limit_per_tag: int = 20) -> list[dict]:
    """
    Scrape Dev.to for AI/automation articles via their public API.
    Uses direct API - no Apify needed.
    
    Rate limit: 1 req/sec (30/min limit)
    
    Args:
        limit_per_tag: Max results per tag (20)
    """
    logger = get_run_logger()
    logger.info(f"Scraping Dev.to with {len(DEVTO_TAGS)} tags...")
    
    insights = []
    seen_ids = set()
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for tag in DEVTO_TAGS:
            if not request_tracker.can_continue:
                logger.warning("Request cap reached, stopping Dev.to scrape")
                break
                
            try:
                # Dev.to public API
                response = await make_request(
                    client, 'GET',
                    f"https://dev.to/api/articles",
                    source='devto',
                    params={
                        "tag": tag,
                        "per_page": limit_per_tag,
                        "top": 30,  # Top articles from last 30 days
                    }
                )
                response.raise_for_status()
                articles = response.json()
                
                logger.info(f"  [{tag}] Found {len(articles)} articles")
                
                for article in articles:
                    article_id = article.get("id", "")
                    
                    if article_id in seen_ids:
                        continue
                    seen_ids.add(article_id)
                    
                    title = article.get("title", "")
                    description = article.get("description", "")[:300]
                    url = article.get("url", "")
                    reactions = article.get("positive_reactions_count", 0)
                    comments = article.get("comments_count", 0)
                    author = article.get("user", {}).get("username", "")
                    reading_time = article.get("reading_time_minutes", 0)
                    published = article.get("published_at", "")
                    tags = article.get("tag_list", [])
                    
                    if not title or not url:
                        continue
                    
                    # Minimum engagement
                    if reactions < 5:
                        continue
                    
                    # Confidence based on reactions
                    confidence = min(0.90, 0.5 + (reactions / 200))
                    category_str = categorize_content(f"{title} {description}")
                    
                    insights.append({
                        "category": category_str,
                        "content": f"[Dev.to {reactions}❤️] {title}",
                        "summary": f"{title} by @{author}. {description}",
                        "source_url": url,
                        "source_type": "devto",
                        "confidence_score": round(confidence, 2),
                        "metadata": {
                            "article_id": article_id,
                            "author": author,
                            "reactions": reactions,
                            "comments": comments,
                            "reading_time": reading_time,
                            "tags": tags[:5],
                            "published": published,
                        }
                    })
                    
            except Exception as e:
                logger.warning(f"Dev.to scrape failed for tag '{tag}': {e}")
                continue
    
    logger.info(f"Scraped {len(insights)} Dev.to articles")
    return insights


@task(retries=2, retry_delay_seconds=10)
async def scrape_ai_blogs(limit_per_feed: int = 15) -> list[dict]:
    """
    Scrape AI company blogs and newsletters via RSS.
    Uses direct RSS - no Apify needed.
    
    Rate limit: 1 req/2sec (standard RSS courtesy)
    
    Args:
        limit_per_feed: Max results per RSS feed (15)
    """
    logger = get_run_logger()
    logger.info(f"Scraping {len(AI_BLOG_FEEDS)} AI blog RSS feeds...")
    
    insights = []
    seen_urls = set()
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        for feed in AI_BLOG_FEEDS:
            if not request_tracker.can_continue:
                logger.warning("Request cap reached, stopping AI blogs scrape")
                break
                
            try:
                response = await make_request(
                    client, 'GET',
                    feed["url"],
                    source='aiblogs'
                )
                
                if response.status_code != 200:
                    logger.warning(f"  [{feed['name']}] HTTP {response.status_code}")
                    continue
                    
                content = response.text
                
                # Try multiple RSS/Atom patterns
                # Pattern 1: RSS item format
                items = re.findall(
                    r'<item>.*?<title>(?:<!\[CDATA\[)?([^\]<]+)(?:\]\]>)?</title>.*?<link>([^<]+)</link>.*?(?:<description>(?:<!\[CDATA\[)?([^\]<]*)(?:\]\]>)?</description>)?.*?</item>',
                    content,
                    re.DOTALL
                )
                
                # Pattern 2: Atom entry format
                if not items:
                    atom_entries = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL)
                    items = []
                    for entry in atom_entries:
                        title_match = re.search(r'<title[^>]*>(?:<!\[CDATA\[)?([^\]<]+)(?:\]\]>)?</title>', entry)
                        link_match = re.search(r'<link[^>]*href=["\']([^"\']+)["\']', entry)
                        summary_match = re.search(r'<(?:summary|content)[^>]*>(?:<!\[CDATA\[)?([^\]<]*)(?:\]\]>)?</(?:summary|content)>', entry, re.DOTALL)
                        if title_match and link_match:
                            items.append((
                                title_match.group(1).strip(),
                                link_match.group(1).strip(),
                                summary_match.group(1).strip() if summary_match else ""
                            ))
                
                logger.info(f"  [{feed['name']}] Found {len(items)} posts")
                
                for title, url, description in items[:limit_per_feed]:
                    title = re.sub(r'\s+', ' ', title.strip())
                    url = url.strip()
                    description = re.sub(r'<[^>]+>', '', description)[:300] if description else ""
                    
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    if not title or not url:
                        continue
                    
                    category_str = categorize_content(f"{title} {description}")
                    
                    insights.append({
                        "category": category_str,
                        "content": f"[{feed['name']}] {title}",
                        "summary": f"{title}. {description[:200]}" if description else title,
                        "source_url": url,
                        "source_type": "ai_blog",
                        "confidence_score": 0.85,  # Official blogs are high quality
                        "metadata": {
                            "blog_name": feed["name"],
                            "feed_url": feed["url"],
                        }
                    })
                    
            except Exception as e:
                logger.warning(f"AI blog scrape failed for {feed['name']}: {e}")
                continue
    
    logger.info(f"Scraped {len(insights)} AI blog posts")
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
    description="Scrape HackerNews, ProductHunt, GitHub, YouTube, Reddit, and X/Twitter with targeted keyword searches",
    retries=1,
    retry_delay_seconds=300,
    log_prints=True
)
async def daily_learning_scrape(
    hn_limit_per_keyword: int = 50,
    gh_limit_per_keyword: int = 30,
    reddit_limit_per_search: int = 25,
    yt_limit_per_keyword: int = 15,
    ph_limit: int = 50,
    twitter_limit_per_keyword: int = 25
):
    """
    Main flow: Scrape multiple sources with targeted keyword searches and store insights.
    
    Conservative rate limits to prevent bans:
    - Total request cap: 500 per run
    - Per-source delays (HN: 1s, Reddit: 2s, GitHub: 2s, etc.)
    - Retry with exponential backoff on 429/5xx
    - Reduced keyword counts (5 per source)
    
    Args:
        hn_limit_per_keyword: HackerNews results per keyword (50 x 5 keywords)
        gh_limit_per_keyword: GitHub repos per keyword (30 x 5 keywords)
        reddit_limit_per_search: Reddit posts per subreddit/keyword combo (25 x 5 x 5)
        yt_limit_per_keyword: YouTube videos per keyword (15 x 5 keywords)
        ph_limit: ProductHunt products total (50)
        twitter_limit_per_keyword: Tweets per keyword/account (25 x 10 terms)
    """
    logger = get_run_logger()
    
    # Reset request tracker for this run
    global request_tracker
    request_tracker = RequestTracker(max_requests=MAX_REQUESTS_PER_RUN)
    
    logger.info("Starting rate-limited learning scrape...")
    logger.info(f"Max requests: {MAX_REQUESTS_PER_RUN}")
    logger.info(f"Keywords: HN={len(HACKERNEWS_KEYWORDS)}, GH={len(GITHUB_KEYWORDS)}, Reddit={len(REDDIT_KEYWORDS)}, YT={len(YOUTUBE_KEYWORDS)}, Twitter={len(TWITTER_KEYWORDS)}")
    logger.info(f"New sources: ArXiv={len(ARXIV_CATEGORIES)} cats, Dev.to={len(DEVTO_TAGS)} tags, AI Blogs={len(AI_BLOG_FEEDS)} feeds")
    
    # Run all scrapers in parallel
    logger.info("Launching all scrapers in parallel...")
    results = await asyncio.gather(
        scrape_hackernews(hn_limit_per_keyword),
        scrape_github(gh_limit_per_keyword),
        scrape_reddit(reddit_limit_per_search),
        scrape_youtube(yt_limit_per_keyword),
        scrape_producthunt(ph_limit),
        scrape_twitter(twitter_limit_per_keyword),
        scrape_arxiv(25),         # NEW: ArXiv direct API
        scrape_devto(20),         # NEW: Dev.to direct API
        scrape_ai_blogs(15),      # NEW: AI blogs RSS
        return_exceptions=True
    )
    
    # Unpack results, handling any exceptions
    scraper_names = ["hackernews", "github", "reddit", "youtube", "producthunt", "twitter", "arxiv", "devto", "ai_blogs"]
    all_results = {name: [] for name in scraper_names}
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Scraper {scraper_names[i]} failed: {result}")
        else:
            all_results[scraper_names[i]] = result or []
            logger.info(f"Scraper {scraper_names[i]} returned {len(result or [])} insights")
    
    # Combine all insights
    all_insights = []
    for name in scraper_names:
        all_insights.extend(all_results[name])
    
    logger.info(f"Total raw insights: {len(all_insights)}")
    
    # Deduplicate
    unique_insights = await deduplicate_insights(all_insights)
    
    # Score for relevance
    scored_insights = await score_insights(unique_insights)
    
    # Store in Supabase
    stored_count = await store_insights(scored_insights)
    
    # Update stats
    await update_learning_stats(stored_count)
    
    # Calculate score distribution for return value
    high_relevance = len([i for i in scored_insights if i.get('relevance_score', 0) >= 0.8])
    medium_relevance = len([i for i in scored_insights if 0.5 <= i.get('relevance_score', 0) < 0.8])
    low_relevance = len([i for i in scored_insights if i.get('relevance_score', 0) < 0.5])
    
    # Get rate limiting stats
    rate_stats = request_tracker.get_stats()
    
    logger.info(f"Rate-limited scrape complete: {stored_count} new insights stored")
    logger.info(f"Request stats: {rate_stats}")
    
    return {
        "total_scraped": len(all_insights),
        "unique": len(unique_insights),
        "stored": stored_count,
        "relevance_distribution": {
            "high": high_relevance,
            "medium": medium_relevance,
            "low": low_relevance
        },
        "sources": {name: len(all_results[name]) for name in scraper_names},
        "keywords_used": {
            "hackernews": len(HACKERNEWS_KEYWORDS),
            "github": len(GITHUB_KEYWORDS),
            "reddit": len(REDDIT_KEYWORDS),
            "youtube": len(YOUTUBE_KEYWORDS),
            "twitter": len(TWITTER_KEYWORDS),
            "arxiv": len(ARXIV_CATEGORIES),
            "devto": len(DEVTO_TAGS),
            "ai_blogs": len(AI_BLOG_FEEDS),
        },
        "rate_limiting": rate_stats,
    }


# ============================================
# Deployment Helper
# ============================================

if __name__ == "__main__":
    # For local testing
    import asyncio
    asyncio.run(daily_learning_scrape())
