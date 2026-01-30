"""
Elliot Daily Learning Scrape Flow
=================================
Automated knowledge acquisition from HackerNews, ProductHunt, GitHub,
YouTube, Reddit, and Twitter/X.

All scrapers run in PARALLEL using asyncio.gather() to avoid timeouts.
Each scraper uses TARGETED KEYWORD SEARCHES for maximum relevance.
Writes to elliot_knowledge table with relevance scoring.

Scrapers use keyword-based searches:
- HackerNews: Algolia API with 15 targeted keywords (ALL TIME)
- GitHub: Search API with 15 keywords sorted by stars
- Reddit: Search across subreddits with 10 keywords (ALL TIME)
- YouTube: Search queries with 10 keywords + target channels
- ProductHunt: Search for AI/automation/sales tools
- Twitter/X: Keyword searches + thought leader accounts
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
# Keywords Configuration
# ============================================

# HackerNews Keywords (15) - Searched via Algolia ALL TIME
HACKERNEWS_KEYWORDS = [
    "cold email",
    "sales automation",
    "AI agents",
    "LLM memory",
    "autonomous agents",
    "SaaS pricing",
    "outbound sales",
    "CRM automation",
    "lead generation",
    "multi-agent",
    "RAG",
    "vector database",
    "Claude",
    "GPT-4",
    "email deliverability",
]

# GitHub Keywords (15) - Searched via Search API sorted by stars
GITHUB_KEYWORDS = [
    "ai-agents",
    "sales-automation",
    "cold-email",
    "llm-memory",
    "multi-agent",
    "autonomous-agent",
    "rag",
    "langchain",
    "email-automation",
    "crewai",
    "autogen",
    "vector-database",
    "claude",
    "outbound",
    "lead-generation",
]

# Reddit Keywords (10) - Searched ALL TIME across subreddits
REDDIT_KEYWORDS = [
    "AI agents",
    "cold email automation",
    "sales automation",
    "LLM memory",
    "autonomous agents",
    "SaaS tools",
    "multi-agent",
    "outbound sales",
    "lead gen",
    "Claude",
]

# Reddit Subreddits (includes r/ClaudeAI)
REDDIT_SUBREDDITS = [
    "SaaS",
    "Entrepreneur",
    "sales",
    "startups",
    "automation",
    "LocalLLaMA",
    "ChatGPT",
    "ClaudeAI",
    "webdev",
    "smallbusiness",
]

# YouTube Keywords (10) - Search queries
YOUTUBE_KEYWORDS = [
    "AI agent tutorial",
    "cold email automation",
    "LLM memory architecture",
    "sales automation demo",
    "multi-agent system",
    "autonomous AI",
    "RAG tutorial",
    "Claude coding",
    "GPT automation",
    "SaaS growth",
]

# ProductHunt Search Terms
PRODUCTHUNT_KEYWORDS = [
    "AI",
    "automation",
    "sales",
    "email",
    "CRM",
    "agent",
    "LLM",
    "outreach",
]

# Twitter/X Keywords
TWITTER_KEYWORDS = [
    "AI agents",
    "cold email",
    "sales automation",
    "LLM memory",
    "multi-agent",
    "autonomous AI",
    "RAG",
    "Claude AI",
    "SaaS tools",
    "email deliverability",
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

RATE_LIMIT_SECONDS = 2  # Reduced for faster scraping
REQUEST_TIMEOUT = 30

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
APIFY_API_KEY = os.environ.get("APIFY_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # For higher rate limits

# Target YouTube channels for tech/AI/SaaS content
YOUTUBE_CHANNELS = [
    {"name": "Y Combinator", "handle": "@ycombinator", "url": "https://www.youtube.com/@ycombinator/videos"},
    {"name": "Lex Fridman", "handle": "@lexfridman", "url": "https://www.youtube.com/@lexfridman/videos"},
    {"name": "My First Million", "handle": "@MyFirstMillionPod", "url": "https://www.youtube.com/@MyFirstMillionPod/videos"},
    {"name": "All-In Podcast", "handle": "@alaboringpodcast", "url": "https://www.youtube.com/@alaboringpodcast/videos"},
    {"name": "Lenny's Podcast", "handle": "@LennysPodcast", "url": "https://www.youtube.com/@LennysPodcast/videos"},
    {"name": "Greg Isenberg", "handle": "@gregisenberg", "url": "https://www.youtube.com/@gregisenberg/videos"},
]

# Twitter/X thought leader accounts
TWITTER_ACCOUNTS = [
    "levelsio",       # Pieter Levels - indie hacker legend
    "marckohlbrugge", # Marc Köhlbrugge - WIP founder
    "gregisenberg",   # Greg Isenberg - Late Checkout
    "ycombinator",    # Y Combinator
    "paulg",          # Paul Graham
    "sama",           # Sam Altman
    "AnthropicAI",    # Anthropic
    "OpenAI",         # OpenAI
]

# ============================================
# Rate Limiter
# ============================================

class RateLimiter:
    """Simple async rate limiter."""
    
    def __init__(self, min_interval: float = 2.0):
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

@task(retries=2, retry_delay_seconds=10)
async def scrape_hackernews(limit_per_keyword: int = 100) -> list[dict]:
    """
    Scrape HackerNews using Algolia API with targeted keyword searches.
    Searches ALL TIME for comprehensive coverage.
    
    Args:
        limit_per_keyword: Max results per keyword (100)
    """
    logger = get_run_logger()
    logger.info(f"Scraping HackerNews via Algolia API with {len(HACKERNEWS_KEYWORDS)} keywords...")
    
    insights = []
    seen_ids = set()
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for keyword in HACKERNEWS_KEYWORDS:
            await rate_limiter.wait()
            try:
                # Algolia API - search ALL TIME (no date filter)
                params = {
                    "query": keyword,
                    "tags": "story",
                    "hitsPerPage": limit_per_keyword,
                }
                response = await client.get(
                    "http://hn.algolia.com/api/v1/search",
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
async def scrape_github(limit_per_keyword: int = 50) -> list[dict]:
    """
    Scrape GitHub using Search API with targeted keyword searches.
    Sorted by stars for quality signal.
    
    Args:
        limit_per_keyword: Max results per keyword (50)
    """
    logger = get_run_logger()
    logger.info(f"Scraping GitHub via Search API with {len(GITHUB_KEYWORDS)} keywords...")
    
    insights = []
    seen_repos = set()
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Elliot-Learning-Bot/1.0"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for keyword in GITHUB_KEYWORDS:
            await rate_limiter.wait()
            try:
                params = {
                    "q": keyword,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": min(limit_per_keyword, 100),  # GitHub max is 100
                }
                response = await client.get(
                    "https://api.github.com/search/repositories",
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
async def scrape_reddit(limit_per_search: int = 50) -> list[dict]:
    """
    Scrape Reddit using search API across subreddits with keyword searches.
    Searches ALL TIME for comprehensive coverage.
    
    Args:
        limit_per_search: Max results per subreddit/keyword combo
    """
    logger = get_run_logger()
    logger.info(f"Scraping Reddit with {len(REDDIT_KEYWORDS)} keywords across {len(REDDIT_SUBREDDITS)} subreddits...")
    
    insights = []
    seen_ids = set()
    
    headers = {
        "User-Agent": "Elliot-Learning-Bot/1.0 (by /u/elliot_agent)"
    }
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for subreddit in REDDIT_SUBREDDITS:
            for keyword in REDDIT_KEYWORDS:
                await rate_limiter.wait()
                try:
                    # Reddit search API - ALL TIME
                    url = f"https://www.reddit.com/r/{subreddit}/search.json"
                    params = {
                        "q": keyword,
                        "sort": "relevance",
                        "t": "all",  # ALL TIME
                        "limit": limit_per_search,
                        "restrict_sr": "on",  # Restrict to subreddit
                    }
                    response = await client.get(url, params=params, headers=headers)
                    
                    if response.status_code == 429:
                        logger.warning(f"Reddit rate limit hit, waiting...")
                        await asyncio.sleep(60)
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
    
    logger.info(f"Scraped {len(insights)} unique Reddit posts (from {len(REDDIT_SUBREDDITS)} subreddits x {len(REDDIT_KEYWORDS)} keywords)")
    return insights


@task(retries=2, retry_delay_seconds=30)
async def scrape_youtube(limit_per_keyword: int = 20) -> list[dict]:
    """
    Scrape YouTube using Apify with keyword searches + target channels.
    
    Args:
        limit_per_keyword: Max results per search query
    """
    logger = get_run_logger()
    logger.info(f"Scraping YouTube with {len(YOUTUBE_KEYWORDS)} keywords + {len(YOUTUBE_CHANNELS)} channels...")
    
    if not APIFY_API_KEY:
        logger.warning("APIFY_API_KEY not set, skipping YouTube scrape")
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
        await rate_limiter.wait()
        
        try:
            # Use streamers/youtube-scraper actor
            run_response = await client.post(
                "https://api.apify.com/v2/acts/streamers~youtube-scraper/runs",
                headers={"Authorization": f"Bearer {APIFY_API_KEY}"},
                json={
                    "startUrls": start_urls,
                    "maxResults": total_limit,
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
            
            # Poll for completion (max 300 seconds for larger scrape)
            for _ in range(60):
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
                logger.warning("YouTube scraper timed out after 300s")
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
async def scrape_producthunt(limit: int = 100) -> list[dict]:
    """
    Scrape ProductHunt for AI, automation, sales, and email tools.
    Uses web scraping for search results.
    
    Args:
        limit: Total max products to scrape
    """
    logger = get_run_logger()
    logger.info(f"Scraping ProductHunt with {len(PRODUCTHUNT_KEYWORDS)} keyword searches...")
    
    insights = []
    seen_slugs = set()
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        # First get RSS feed for today's launches
        await rate_limiter.wait()
        try:
            response = await client.get(
                "https://www.producthunt.com/feed",
                headers={"User-Agent": "Elliot-Learning-Bot/1.0"}
            )
            response.raise_for_status()
            content = response.text
            
            # Parse RSS feed
            items = re.findall(
                r'<item>.*?<title><!\[CDATA\[(.*?)\]\]></title>.*?<link>(.*?)</link>.*?<description><!\[CDATA\[(.*?)\]\]></description>.*?</item>',
                content,
                re.DOTALL
            )
            
            for title, url, description in items:
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
                
                if is_relevant or len(insights) < 20:  # Always include top 20
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
        
        # Also search for specific keywords on ProductHunt
        for keyword in PRODUCTHUNT_KEYWORDS[:4]:  # Top 4 keywords
            await rate_limiter.wait()
            try:
                search_url = f"https://www.producthunt.com/search?q={keyword}"
                response = await client.get(
                    search_url,
                    headers={
                        "User-Agent": "Elliot-Learning-Bot/1.0",
                        "Accept": "text/html"
                    },
                    follow_redirects=True
                )
                # Note: ProductHunt search requires JavaScript, so limited results via HTML scraping
                # The RSS feed above provides better coverage
            except Exception as e:
                logger.warning(f"ProductHunt search failed for '{keyword}': {e}")
                continue
    
    logger.info(f"Scraped {len(insights)} ProductHunt products")
    return insights


@task(retries=2, retry_delay_seconds=30)
async def scrape_twitter(limit_per_keyword: int = 50) -> list[dict]:
    """
    Scrape Twitter/X using Apify with keyword searches + thought leader accounts.
    Uses apidojo/tweet-scraper actor which supports searchTerms.
    
    Args:
        limit_per_keyword: Max tweets per search term
    """
    logger = get_run_logger()
    logger.info(f"Scraping Twitter/X with {len(TWITTER_KEYWORDS)} keywords + {len(TWITTER_ACCOUNTS)} accounts...")
    
    if not APIFY_API_KEY:
        logger.warning("APIFY_API_KEY not set, skipping Twitter scrape")
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
        await rate_limiter.wait()
        
        try:
            # Use apidojo/tweet-scraper actor (Tweet Scraper V2)
            run_response = await client.post(
                "https://api.apify.com/v2/acts/apidojo~tweet-scraper/runs",
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
                logger.warning(f"Twitter scraper start failed: {run_response.status_code} - {run_response.text[:200]}")
                return []
            
            run_data = run_response.json()
            run_id = run_data.get("data", {}).get("id")
            
            if not run_id:
                return []
            
            logger.info(f"Twitter scraper started: run_id={run_id}")
            
            # Poll for completion (max 300 seconds)
            for _ in range(60):
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
                headers={"Authorization": f"Bearer {APIFY_API_KEY}"}
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
    hn_limit_per_keyword: int = 100,
    gh_limit_per_keyword: int = 50,
    reddit_limit_per_search: int = 50,
    yt_limit_per_keyword: int = 20,
    ph_limit: int = 100,
    twitter_limit_per_keyword: int = 50
):
    """
    Main flow: Scrape multiple sources with targeted keyword searches and store insights.
    
    This is a BIG INITIAL SCRAPE - higher limits to build comprehensive knowledge base.
    
    Args:
        hn_limit_per_keyword: HackerNews results per keyword (100 x 15 keywords)
        gh_limit_per_keyword: GitHub repos per keyword (50 x 15 keywords)
        reddit_limit_per_search: Reddit posts per subreddit/keyword combo
        yt_limit_per_keyword: YouTube videos per keyword (20 x 10 keywords)
        ph_limit: ProductHunt products total
        twitter_limit_per_keyword: Tweets per keyword/account (50 x 18 terms)
    """
    logger = get_run_logger()
    logger.info("Starting targeted keyword learning scrape (BIG INITIAL SCRAPE)...")
    logger.info(f"Keywords: HN={len(HACKERNEWS_KEYWORDS)}, GH={len(GITHUB_KEYWORDS)}, Reddit={len(REDDIT_KEYWORDS)}, YT={len(YOUTUBE_KEYWORDS)}, Twitter={len(TWITTER_KEYWORDS)}")
    
    # Run all scrapers in parallel
    logger.info("Launching all scrapers in parallel...")
    results = await asyncio.gather(
        scrape_hackernews(hn_limit_per_keyword),
        scrape_github(gh_limit_per_keyword),
        scrape_reddit(reddit_limit_per_search),
        scrape_youtube(yt_limit_per_keyword),
        scrape_producthunt(ph_limit),
        scrape_twitter(twitter_limit_per_keyword),
        return_exceptions=True
    )
    
    # Unpack results, handling any exceptions
    scraper_names = ["hackernews", "github", "reddit", "youtube", "producthunt", "twitter"]
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
    
    logger.info(f"Targeted keyword scrape complete: {stored_count} new insights stored")
    
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
        }
    }


# ============================================
# Deployment Helper
# ============================================

if __name__ == "__main__":
    # For local testing
    import asyncio
    asyncio.run(daily_learning_scrape())
