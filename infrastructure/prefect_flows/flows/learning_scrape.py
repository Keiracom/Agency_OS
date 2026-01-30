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
- Twitter/X: Native scraping via nitter RSS (no API key needed)

Rate Limiting Strategy (to prevent bans):
- HackerNews (Algolia): 1 req/sec
- Reddit: 1 req/2sec (they ban aggressively)
- GitHub API: 1 req/2sec (30/min authenticated)
- ProductHunt: 1 req/3sec (gentle)
- ArXiv: 1 req/3sec (their policy)
- Dev.to: 1 req/sec (30/min limit)
- Indie Hackers: 1 req/5sec (no official API)
- RSS feeds: 1 req/2sec (standard courtesy)
- Twitter/X: 1 req/sec via nitter RSS
- YouTube via Apify: Actor handles limits
"""

import asyncio
import hashlib
import os
import random
import re
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path
from functools import wraps

import feedparser
import httpx
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from supabase import create_client, Client

# Native YouTube scraping (no API key needed)
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript,
    RequestBlocked, IpBlocked
)


# ============================================
# Rate Limiting Infrastructure
# ============================================

# User-Agent header for all requests
HEADERS = {
    'User-Agent': 'ElliotBot/1.0 (Research; https://github.com/elliot-agent)'
}


# ============================================
# Anti-Ban Safety Measures
# ============================================

async def safe_delay(min_delay: float = 1.0, max_delay: float = 3.0):
    """
    Randomized delay to prevent detection patterns.
    Uses random interval instead of fixed delay.
    """
    delay = random.uniform(min_delay, max_delay)
    logger = get_run_logger()
    logger.debug(f"Rate limiting: waiting {delay:.1f}s before next request")
    await asyncio.sleep(delay)


def jittered_delay(base: float = 1.0, jitter: float = 0.5) -> float:
    """
    Add jitter to a base delay to avoid predictable patterns.
    
    Args:
        base: Base delay in seconds
        jitter: Maximum jitter (+/-) in seconds
    
    Returns:
        Delay with random jitter applied
    """
    return base + random.uniform(-jitter, jitter)


class BlockDetector:
    """
    Detects potential blocks/bans based on consecutive errors.
    Triggers graceful stop when threshold is reached.
    """
    
    def __init__(self, max_errors: int = 3, source_name: str = "scraper"):
        self.consecutive_errors = 0
        self.max_errors = max_errors
        self.blocked = False
        self.source_name = source_name
        self.total_errors = 0
        self.total_successes = 0
    
    def record_success(self):
        """Record a successful request, reset consecutive error count."""
        self.consecutive_errors = 0
        self.total_successes += 1
    
    def record_error(self, error: Exception):
        """
        Record an error. Check for block indicators.
        Triggers block detection after max consecutive errors.
        """
        self.consecutive_errors += 1
        self.total_errors += 1
        logger = get_run_logger()
        
        error_str = str(error).lower()
        
        # Check for explicit block indicators
        block_keywords = ["blocked", "captcha", "rate limit", "too many requests", 
                         "forbidden", "access denied", "bot detected", "429"]
        
        if any(kw in error_str for kw in block_keywords):
            self.blocked = True
            logger.warning(f"[{self.source_name}] Block indicator detected in error: {error}")
            return
        
        if self.consecutive_errors >= self.max_errors:
            self.blocked = True
            logger.warning(
                f"[{self.source_name}] Possible block detected after {self.max_errors} "
                f"consecutive errors. Stopping scraper."
            )
    
    def should_stop(self) -> bool:
        """Check if scraper should stop due to detected block."""
        return self.blocked
    
    def get_stats(self) -> dict:
        """Get detection statistics."""
        return {
            "source": self.source_name,
            "blocked": self.blocked,
            "total_successes": self.total_successes,
            "total_errors": self.total_errors,
            "consecutive_errors": self.consecutive_errors,
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
            'twitter': 1.0,          # Native scraping via nitter RSS
            # YouTube via Apify - actor handles it
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

# YouTube Keywords (10) - Search queries
# Native scraper: no Apify limits, but rate-limited to 0.5s between requests
YOUTUBE_KEYWORDS = [
    "AI agent tutorial",
    "LLM memory architecture", 
    "cold email automation",
    "sales automation SaaS",
    "multi-agent system",
    "Claude AI coding",
    "RAG tutorial",
    "autonomous AI agents",
    "prompt engineering",
    "SaaS growth strategies",
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

# Twitter/X Keywords (10) - Native scraper, no Apify
TWITTER_KEYWORDS = [
    "AI agents",
    "cold email automation",
    "SaaS growth",
    "LLM memory",
    "Claude AI",
    "sales automation",
    "multi-agent",
    "autonomous AI",
    "prompt engineering",
    "outbound sales",
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

# Twitter/X thought leader accounts (for nitter RSS)
TWITTER_ACCOUNTS = [
    "levelsio",       # Pieter Levels - indie hacker legend
    "sama",           # Sam Altman
    "AnthropicAI",    # Anthropic
    "OpenAI",         # OpenAI
    "LangChainAI",    # LangChain
    "gregisenberg",   # Greg Isenberg - Late Checkout
    "swyx",           # Shawn Wang - AI Engineer
]

# Nitter instances (public Twitter frontends with RSS) - ordered by reliability
# Note: Nitter instances frequently go down. This list should be updated periodically.
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.cz",
    "https://nitter.unixfox.eu",
    "https://n.opnxng.com",
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
async def scrape_youtube(limit_per_keyword: int = 10) -> list[dict]:
    """
    Scrape YouTube using native Python libraries (no API key needed).
    Uses yt-dlp for search and youtube-transcript-api for transcripts.
    
    Anti-ban safety measures:
    - Randomized delays (1-3s) instead of fixed delays
    - Block detection with graceful stop after 3 consecutive errors
    - Conservative limits (5 keywords × 10 videos = 50 max)
    - Detects RequestBlocked/IpBlocked exceptions
    
    Note: Transcripts may be unavailable from cloud IPs due to YouTube blocking.
    Video metadata (title, views, channel) is still captured.
    
    Args:
        limit_per_keyword: Max results per search query (10)
    """
    logger = get_run_logger()
    
    # Conservative limit: max 5 keywords for safety
    keywords_to_use = YOUTUBE_KEYWORDS[:5]
    logger.info(f"Scraping YouTube (native) with {len(keywords_to_use)} keywords (conservative limit)...")
    
    insights = []
    seen_ids = set()
    transcripts_found = 0
    transcripts_blocked = 0
    transcripts_unavailable = 0
    
    # Block detection for graceful stop
    detector = BlockDetector(max_errors=3, source_name="YouTube")
    
    # yt-dlp options for search
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,  # Don't download, just get metadata
        'ignoreerrors': True,
    }
    
    # Track if transcripts are being blocked (stop trying after 3 blocks)
    ip_blocked = False
    
    for keyword in keywords_to_use:
        # Check for block detection
        if detector.should_stop():
            logger.warning("YouTube scraper stopped due to possible block")
            break
            
        # Check request cap
        if not request_tracker.can_continue:
            logger.warning("Request cap reached, stopping YouTube scrape")
            break
            
        try:
            # Search YouTube using yt-dlp
            search_url = f"ytsearch{limit_per_keyword}:{keyword}"
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_result = ydl.extract_info(search_url, download=False)
            
            if not search_result or 'entries' not in search_result:
                logger.warning(f"  [{keyword}] No results")
                detector.record_error(Exception("No results returned"))
                await safe_delay(2.0, 4.0)  # Longer delay on empty results
                continue
            
            # Record success for search
            detector.record_success()
                
            videos = [e for e in search_result['entries'] if e]
            logger.info(f"  [{keyword}] Found {len(videos)} videos")
            
            for video in videos:
                # Check block detection between videos
                if detector.should_stop():
                    break
                    
                video_id = video.get('id') or video.get('url', '').split('=')[-1]
                if not video_id or video_id in seen_ids:
                    continue
                seen_ids.add(video_id)
                
                title = video.get('title', '')
                channel_name = video.get('channel', '') or video.get('uploader', '')
                view_count = video.get('view_count', 0) or 0
                duration = video.get('duration', 0)
                duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else ''
                
                # Try to get transcript (skip if IP is blocked)
                transcript_text = None
                if not ip_blocked:
                    try:
                        ytt_api = YouTubeTranscriptApi()
                        transcript = ytt_api.fetch(video_id)
                        transcript_text = " ".join([entry.text for entry in transcript])
                        # Truncate to reasonable size
                        if len(transcript_text) > 5000:
                            transcript_text = transcript_text[:5000] + "..."
                        transcripts_found += 1
                        detector.record_success()  # Transcript fetch succeeded
                    except (RequestBlocked, IpBlocked):
                        transcripts_blocked += 1
                        if transcripts_blocked >= 3:
                            ip_blocked = True
                            detector.blocked = True  # Also mark block detector
                            logger.warning("YouTube IP blocked - skipping transcript fetches for remaining videos")
                    except (TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript):
                        transcripts_unavailable += 1
                        # Not an error - just no transcript available
                    except Exception as e:
                        transcripts_unavailable += 1
                        error_str = str(e).lower()
                        # Check for block indicators in error message
                        if any(kw in error_str for kw in ["blocked", "captcha", "too many", "429"]):
                            detector.record_error(e)
                        logger.debug(f"Transcript error for {video_id}: {e}")
                
                # Get description as fallback
                description = (video.get('description') or '')[:500]
                
                # Use transcript if available, otherwise use description or title
                content_text = transcript_text or description or title
                
                # Minimum threshold - accept all videos with decent views
                # (transcripts unavailable from cloud, so don't penalize)
                if view_count < 1000:
                    continue
                
                # Confidence based on views and transcript availability
                confidence = min(0.95, 0.5 + (view_count / 100000))
                if transcript_text:
                    confidence = min(0.95, confidence + 0.1)
                
                # Check if from target channel
                from_target_channel = any(
                    ch["name"].lower() in channel_name.lower() 
                    for ch in YOUTUBE_CHANNELS
                )
                if from_target_channel:
                    confidence = min(0.95, confidence + 0.1)
                
                category = categorize_content(f"{title} {content_text[:500]}")
                
                insights.append({
                    "category": category,
                    "content": f"[YouTube {view_count:,} views] {title}",
                    "summary": f"{title} by {channel_name}. {content_text[:300]}",
                    "source_url": f"https://youtube.com/watch?v={video_id}",
                    "source_type": "youtube",
                    "confidence_score": round(confidence, 2),
                    "metadata": {
                        "video_id": video_id,
                        "channel": channel_name,
                        "view_count": view_count,
                        "duration": duration_str,
                        "has_transcript": transcript_text is not None,
                        "transcript_length": len(transcript_text) if transcript_text else 0,
                        "from_target_channel": from_target_channel,
                        "keyword": keyword,
                    }
                })
                
                # Randomized delay between requests (anti-ban)
                await safe_delay(1.0, 3.0)
                
        except Exception as e:
            detector.record_error(e)
            logger.warning(f"YouTube search failed for '{keyword}': {e}")
            if detector.should_stop():
                break
            # Extended delay after error
            delay = jittered_delay(3.0, 1.0)
            logger.info(f"Rate limiting: waiting {delay:.1f}s after error")
            await asyncio.sleep(delay)
            continue
        
        # Randomized delay between keywords
        await safe_delay(1.5, 3.5)
    
    # Log block detection stats
    stats = detector.get_stats()
    if stats["total_errors"] > 0:
        logger.info(f"YouTube block detector stats: {stats}")
    
    transcript_status = f"found={transcripts_found}, unavailable={transcripts_unavailable}"
    if transcripts_blocked > 0:
        transcript_status += f", blocked={transcripts_blocked} (cloud IP)"
    logger.info(f"Scraped {len(insights)} YouTube videos (transcripts: {transcript_status})")
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
async def scrape_twitter(limit_per_keyword: int = 20) -> list[dict]:
    """
    Native Twitter/X scraper using nitter RSS feeds (no API key needed).
    
    Anti-ban safety measures:
    - Randomized delays (1-3s) instead of fixed delays
    - Block detection with graceful stop after 3 consecutive errors
    - Conservative limits (5 accounts × 20 tweets = 100 max)
    - Graceful instance failover
    
    Strategy:
    1. Scrape target thought leader accounts via nitter RSS
    2. Try multiple nitter instances with fallback
    3. Rate limited with randomized delays between nitter calls
    
    Note: Native Twitter scraping is inherently unreliable due to:
    - Nitter instances frequently go down
    - Twitter/X actively blocks scrapers
    - No official public API without authentication
    
    This implementation gracefully fails if all methods are exhausted.
    
    Args:
        limit_per_keyword: Max tweets per account (20, conservative)
    """
    logger = get_run_logger()
    
    # Conservative limit: max 5 accounts for safety
    accounts_to_use = TWITTER_ACCOUNTS[:5]
    logger.info(f"Scraping Twitter/X natively with {len(accounts_to_use)} accounts (conservative limit)...")
    
    # Check request cap
    if not request_tracker.can_continue:
        logger.warning("Request cap reached, skipping Twitter scrape")
        return []
    
    insights = []
    seen_ids = set()
    working_instance = None
    
    # Block detection for graceful stop
    detector = BlockDetector(max_errors=3, source_name="Twitter")
    
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        # First, find a working nitter instance
        for instance in NITTER_INSTANCES:
            if not request_tracker.can_continue:
                break
            if detector.should_stop():
                break
            try:
                # Test with a known active account
                test_url = f"{instance}/OpenAI/rss"
                await rate_limiter.wait('twitter')
                
                response = await client.get(
                    test_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                    }
                )
                
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)
                    if feed.entries and len(feed.entries) > 0:
                        working_instance = instance
                        detector.record_success()
                        logger.info(f"Found working nitter instance: {instance}")
                        break
                    else:
                        logger.debug(f"Nitter {instance} returned empty feed")
                        detector.record_error(Exception("Empty feed"))
                elif response.status_code in [403, 429]:
                    detector.record_error(Exception(f"HTTP {response.status_code}"))
                    logger.debug(f"Nitter {instance} returned {response.status_code} (possible block)")
                else:
                    logger.debug(f"Nitter {instance} returned {response.status_code}")
                
                # Randomized delay between instance tests
                await safe_delay(1.0, 2.0)
                    
            except Exception as e:
                detector.record_error(e)
                logger.debug(f"Nitter {instance} failed: {type(e).__name__}: {e}")
                continue
        
        if not working_instance:
            logger.warning("No working nitter instance found - Twitter scrape returning empty")
            return []
        
        if detector.should_stop():
            logger.warning("Twitter scraper stopped due to possible block during instance discovery")
            return []
        
        # Reset detector for account scraping phase
        detector = BlockDetector(max_errors=3, source_name="Twitter-accounts")
        
        # Scrape each target account
        for account in accounts_to_use:
            # Check for block detection
            if detector.should_stop():
                logger.warning("Twitter scraper stopped due to possible block")
                break
                
            if not request_tracker.can_continue:
                logger.warning("Request cap reached, stopping Twitter scrape")
                break
                
            try:
                await rate_limiter.wait('twitter')
                
                feed_url = f"{working_instance}/{account}/rss"
                response = await client.get(
                    feed_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                    }
                )
                
                if response.status_code == 403 or response.status_code == 429:
                    detector.record_error(Exception(f"HTTP {response.status_code}"))
                    logger.warning(f"  [@{account}] HTTP {response.status_code} (possible block)")
                    if detector.should_stop():
                        break
                    # Extended delay after block-like response
                    delay = jittered_delay(5.0, 2.0)
                    logger.info(f"Rate limiting: waiting {delay:.1f}s after possible block")
                    await asyncio.sleep(delay)
                    continue
                
                if response.status_code != 200:
                    logger.warning(f"  [@{account}] HTTP {response.status_code}")
                    await safe_delay(1.0, 2.0)
                    continue
                
                feed = feedparser.parse(response.text)
                
                if not feed.entries:
                    logger.info(f"  [@{account}] No entries in feed")
                    await safe_delay(1.0, 2.0)
                    continue
                
                # Record success
                detector.record_success()
                logger.info(f"  [@{account}] Found {len(feed.entries)} tweets")
                
                for entry in feed.entries[:limit_per_keyword]:
                    # Extract tweet ID from link
                    # Nitter links look like: https://nitter.net/username/status/1234567890
                    link = entry.get("link", "")
                    tweet_id = link.split("/status/")[-1].split("#")[0] if "/status/" in link else ""
                    
                    if tweet_id in seen_ids:
                        continue
                    seen_ids.add(tweet_id)
                    
                    # Get title (usually the tweet text truncated)
                    title = entry.get("title", "")
                    
                    # Get full content from description/summary (HTML)
                    description = entry.get("description", "") or entry.get("summary", "")
                    # Strip HTML tags
                    text = re.sub(r'<[^>]+>', '', description).strip()
                    
                    # Get published date
                    published = entry.get("published", "")
                    
                    # Convert nitter URL to x.com URL
                    tweet_url = f"https://x.com/{account}/status/{tweet_id}" if tweet_id else link.replace(working_instance, "https://x.com")
                    
                    if not text:
                        continue
                    
                    # Skip retweets (nitter shows them as "RT by @username")
                    if text.startswith("RT by") or "RT @" in text[:20]:
                        continue
                    
                    # For nitter RSS, we don't have engagement metrics
                    # Set confidence based on being a target account
                    confidence = 0.70  # Base for target accounts
                    
                    category = categorize_content(text)
                    content_text = text[:200] + "..." if len(text) > 200 else text
                    
                    insights.append({
                        "category": category,
                        "content": f"[X @{account}] {content_text}",
                        "summary": f"@{account}: {text[:300]}",
                        "source_url": tweet_url,
                        "source_type": "twitter",
                        "confidence_score": round(confidence, 2),
                        "metadata": {
                            "tweet_id": tweet_id,
                            "username": account,
                            "display_name": account,
                            "is_target_account": True,
                            "published": published,
                            "scrape_method": "nitter_rss",
                            "nitter_instance": working_instance,
                        }
                    })
                
                # Randomized delay between accounts (anti-ban)
                await safe_delay(1.5, 3.5)
                    
            except Exception as e:
                detector.record_error(e)
                logger.warning(f"Twitter scrape failed for @{account}: {type(e).__name__}: {e}")
                if detector.should_stop():
                    break
                # Extended delay after error
                delay = jittered_delay(3.0, 1.0)
                logger.info(f"Rate limiting: waiting {delay:.1f}s after error")
                await asyncio.sleep(delay)
                continue
    
    # Log block detection stats
    stats = detector.get_stats()
    if stats["total_errors"] > 0:
        logger.info(f"Twitter block detector stats: {stats}")
    
    logger.info(f"Scraped {len(insights)} tweets from X/Twitter (native, no API)")
    return insights

# ============================================
# NEW SOURCES (No Apify Required)
# ============================================

# ArXiv categories for AI/ML research
ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.MA"]  # AI, ML, NLP, Multi-agent

# Dev.to tags for relevant content
DEVTO_TAGS = ["ai", "machinelearning", "automation", "saas", "python"]

# AI/Tech blogs RSS feeds (from skills/rss-feeds/SKILL.md)
AI_BLOG_FEEDS = [
    # AI Company Blogs
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
    {"name": "LangChain Blog", "url": "https://blog.langchain.dev/rss/"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    # Key Newsletters (from skill documentation)
    {"name": "Latent Space", "url": "https://www.latent.space/feed"},
    {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/"},
    {"name": "Lenny's Newsletter", "url": "https://www.lennysnewsletter.com/feed"},
    {"name": "One Useful Thing", "url": "https://www.oneusefulthing.org/feed"},
    {"name": "Pragmatic Engineer", "url": "https://newsletter.pragmaticengineer.com/feed"},
]
# Note: Anthropic has no public RSS feed per skill documentation


@task(retries=2, retry_delay_seconds=10)
async def scrape_arxiv(limit_per_category: int = 25) -> list[dict]:
    """
    Scrape ArXiv for AI/ML research papers via their API.
    Uses feedparser for reliable Atom XML parsing per skills/arxiv/SKILL.md.
    
    Rate limit: 1 req/3sec (ArXiv policy - be a good citizen)
    
    Args:
        limit_per_category: Max results per category (25)
    """
    logger = get_run_logger()
    logger.info(f"Scraping ArXiv with {len(ARXIV_CATEGORIES)} categories...")
    
    insights = []
    seen_ids = set()
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        for category in ARXIV_CATEGORIES:
            if not request_tracker.can_continue:
                logger.warning("Request cap reached, stopping ArXiv scrape")
                break
                
            try:
                # ArXiv API query per skill documentation
                # Format: search_query=cat:{category}&sortBy=submittedDate&sortOrder=descending
                # Note: ArXiv now redirects HTTP to HTTPS, so use HTTPS directly
                params = {
                    "search_query": f"cat:{category}",
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                    "max_results": limit_per_category,
                }
                response = await make_request(
                    client, 'GET',
                    "https://export.arxiv.org/api/query",
                    source='arxiv',
                    params=params
                )
                response.raise_for_status()
                content = response.text
                
                # Parse Atom feed using feedparser (per skill recommendation)
                feed = feedparser.parse(content)
                
                if feed.bozo:
                    logger.warning(f"  [{category}] Parse warning: {feed.bozo_exception}")
                
                logger.info(f"  [{category}] Found {len(feed.entries)} papers")
                
                for entry in feed.entries:
                    # Extract paper ID from entry.id (format: http://arxiv.org/abs/2401.12345v1)
                    paper_id = entry.get("id", "")
                    arxiv_id = paper_id.split("/abs/")[-1] if "/abs/" in paper_id else paper_id
                    
                    if paper_id in seen_ids:
                        continue
                    seen_ids.add(paper_id)
                    
                    # Extract title (clean whitespace)
                    title = re.sub(r'\s+', ' ', entry.get("title", "").strip())
                    
                    # Extract summary/abstract
                    summary = re.sub(r'\s+', ' ', entry.get("summary", "").strip())[:500]
                    
                    # Extract authors (feedparser provides entry.authors list)
                    authors = [a.get("name", "") for a in entry.get("authors", [])]
                    author_str = ", ".join(authors[:3])
                    if len(authors) > 3:
                        author_str += f" et al. ({len(authors)} authors)"
                    
                    # Extract published date
                    published = entry.get("published", "")
                    
                    # Get abstract page URL (entry.link or construct from ID)
                    url = entry.get("link", paper_id)
                    
                    # Get PDF URL (from links with title='pdf')
                    pdf_url = None
                    for link in entry.get("links", []):
                        if link.get("title") == "pdf":
                            pdf_url = link.get("href")
                            break
                    
                    # Get primary category from arxiv:primary_category or tags
                    primary_cat = category
                    tags = [t.get("term", "") for t in entry.get("tags", [])]
                    
                    if not title:
                        continue
                    
                    category_str = categorize_content(f"{title} {summary}")
                    
                    insights.append({
                        "category": category_str,
                        "content": f"[ArXiv {primary_cat}] {title}",
                        "summary": f"{title} by {author_str}. {summary[:250]}",
                        "source_url": url,
                        "source_type": "arxiv",
                        "confidence_score": 0.80,  # Research papers are high quality
                        "metadata": {
                            "arxiv_id": arxiv_id,
                            "category": primary_cat,
                            "categories": tags[:5],
                            "authors": authors[:5],
                            "published": published,
                            "pdf_url": pdf_url,
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
    Uses feedparser for reliable RSS/Atom parsing per skills/rss-feeds/SKILL.md.
    
    Rate limit: 1 req/2sec (standard RSS courtesy per skill documentation)
    
    Args:
        limit_per_feed: Max results per RSS feed (15)
    """
    logger = get_run_logger()
    logger.info(f"Scraping {len(AI_BLOG_FEEDS)} AI blog RSS feeds...")
    
    insights = []
    seen_urls = set()
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        for feed_config in AI_BLOG_FEEDS:
            if not request_tracker.can_continue:
                logger.warning("Request cap reached, stopping AI blogs scrape")
                break
                
            try:
                response = await make_request(
                    client, 'GET',
                    feed_config["url"],
                    source='aiblogs'
                )
                
                if response.status_code != 200:
                    logger.warning(f"  [{feed_config['name']}] HTTP {response.status_code}")
                    continue
                    
                content = response.text
                
                # Parse RSS/Atom using feedparser (handles both formats automatically)
                feed = feedparser.parse(content)
                
                if feed.bozo:
                    # Parse error occurred but may still have partial data
                    logger.warning(f"  [{feed_config['name']}] Parse warning: {feed.bozo_exception}")
                
                if not feed.entries:
                    logger.warning(f"  [{feed_config['name']}] No entries found")
                    continue
                
                logger.info(f"  [{feed_config['name']}] Found {len(feed.entries)} posts")
                
                for entry in feed.entries[:limit_per_feed]:
                    # Extract fields using .get() for missing fields (per skill recommendation)
                    title = entry.get("title", "")
                    title = re.sub(r'\s+', ' ', title.strip()) if title else ""
                    
                    url = entry.get("link", "")
                    
                    # Get summary/description - try multiple fields
                    summary = entry.get("summary", "")
                    if not summary and entry.get("content"):
                        # Some feeds put content in content[0].value
                        summary = entry.get("content", [{}])[0].get("value", "")
                    # Strip HTML tags and truncate
                    summary = re.sub(r'<[^>]+>', '', summary)[:300] if summary else ""
                    
                    # Get author
                    author = entry.get("author", "Unknown")
                    
                    # Get published date
                    published = entry.get("published", "")
                    
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    if not title or not url:
                        continue
                    
                    category_str = categorize_content(f"{title} {summary}")
                    
                    insights.append({
                        "category": category_str,
                        "content": f"[{feed_config['name']}] {title}",
                        "summary": f"{title}. {summary[:200]}" if summary else title,
                        "source_url": url,
                        "source_type": "ai_blog",
                        "confidence_score": 0.85,  # Official blogs are high quality
                        "metadata": {
                            "blog_name": feed_config["name"],
                            "feed_url": feed_config["url"],
                            "author": author,
                            "published": published,
                        }
                    })
                    
            except Exception as e:
                logger.warning(f"AI blog scrape failed for {feed_config['name']}: {e}")
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
    # TODO: Add HTML sanitization with bleach before storing scraped content
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
