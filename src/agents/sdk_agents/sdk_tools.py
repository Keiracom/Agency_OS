"""
Contract: src/agents/sdk_agents/sdk_tools.py
Purpose: Tool definitions and implementations for SDK agents
Layer: Agents
Consumers: sdk_brain.py, all sdk_agents

Tools available:
- web_search: Search the web using Serper API
- web_fetch: Fetch and parse webpage content
- linkedin_posts: Fetch LinkedIn posts via Apify
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable, Coroutine
from html import unescape
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


# ============================================
# TOOL DEFINITIONS (for Claude)
# ============================================

WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web for information. Use for finding company news, funding announcements, press releases, job postings, and general research. Returns titles, snippets, and URLs of relevant results.",
    "input_schema": {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query. Be specific - include company names, topics, timeframes when relevant."
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (1-10). Default is 5.",
                "default": 5,
                "minimum": 1,
                "maximum": 10
            }
        }
    }
}

WEB_FETCH_TOOL = {
    "name": "web_fetch",
    "description": "Fetch and read the content of a specific webpage. Use for reading company websites (about pages, careers pages), blog posts, press releases, or any URL you found via web_search. Returns the text content of the page.",
    "input_schema": {
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {
                "type": "string",
                "description": "Full URL to fetch (must include https://)"
            }
        }
    }
}

LINKEDIN_POSTS_TOOL = {
    "name": "linkedin_posts",
    "description": "Fetch recent LinkedIn posts from a person's profile. Use for finding what topics they've been discussing, their professional interests, and potential conversation starters. Requires a LinkedIn profile URL.",
    "input_schema": {
        "type": "object",
        "required": ["linkedin_url"],
        "properties": {
            "linkedin_url": {
                "type": "string",
                "description": "LinkedIn profile URL (e.g., https://linkedin.com/in/username)"
            },
            "max_posts": {
                "type": "integer",
                "description": "Maximum number of posts to return (1-10). Default is 5.",
                "default": 5,
                "minimum": 1,
                "maximum": 10
            }
        }
    }
}

# All available tools
ALL_TOOLS = [WEB_SEARCH_TOOL, WEB_FETCH_TOOL, LINKEDIN_POSTS_TOOL]

# Tools for specific agent types
ICP_TOOLS = [WEB_SEARCH_TOOL, WEB_FETCH_TOOL]  # ICP extraction uses search + fetch
ENRICHMENT_TOOLS = [WEB_SEARCH_TOOL, WEB_FETCH_TOOL, LINKEDIN_POSTS_TOOL]
EMAIL_TOOLS = []  # Email agent doesn't need tools - uses enrichment data
VOICE_KB_TOOLS = []  # Voice KB agent doesn't need tools - uses enrichment data
OBJECTION_TOOLS = []  # Objection agent doesn't need tools


# ============================================
# TOOL IMPLEMENTATIONS
# ============================================


async def web_search(
    query: str,
    num_results: int = 5,
    serper_api_key: str | None = None,
) -> str:
    """
    Execute web search using Serper API.

    Args:
        query: Search query
        num_results: Number of results (1-10)
        serper_api_key: Serper API key (uses settings if not provided)

    Returns:
        Formatted search results as string
    """
    api_key = serper_api_key or getattr(settings, "serper_api_key", None)

    if not api_key:
        return "Error: Serper API key not configured"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "q": query,
                    "num": num_results,
                }
            )
            response.raise_for_status()
            data = response.json()

        # Format results
        results = []
        for item in data.get("organic", [])[:num_results]:
            title = item.get("title", "No title")
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            date = item.get("date", "")

            result_text = f"**{title}**"
            if date:
                result_text += f" ({date})"
            result_text += f"\n{snippet}"
            result_text += f"\nURL: {link}"
            results.append(result_text)

        if not results:
            return f"No results found for: {query}"

        return "\n\n---\n\n".join(results)

    except httpx.TimeoutException:
        return f"Error: Search timed out for: {query}"
    except httpx.HTTPStatusError as e:
        return f"Error: Search API error ({e.response.status_code})"
    except Exception as e:
        logger.error(f"Web search error: {e}", exc_info=True)
        return f"Error: Search failed - {str(e)}"


async def web_fetch(
    url: str,
    max_length: int = 8000,
) -> str:
    """
    Fetch and parse webpage content.

    Args:
        url: URL to fetch
        max_length: Maximum content length to return

    Returns:
        Cleaned text content from the page
    """
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AgencyOS/1.0; +https://agencyos.com)"
            }
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return f"Error: URL returned non-text content ({content_type})"

            html = response.text

        # Clean HTML to text
        text = _html_to_text(html)

        # Truncate if needed
        if len(text) > max_length:
            text = text[:max_length] + "\n\n[Content truncated...]"

        if not text.strip():
            return f"Error: No readable content found at {url}"

        return text

    except httpx.TimeoutException:
        return f"Error: Request timed out for {url}"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} for {url}"
    except Exception as e:
        logger.error(f"Web fetch error: {e}", exc_info=True)
        return f"Error: Failed to fetch {url} - {str(e)}"


def _html_to_text(html: str) -> str:
    """Convert HTML to clean text."""
    # Remove scripts and styles
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML comments
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    # Convert common elements to text equivalents
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<p[^>]*>', '\n\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</p>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<h[1-6][^>]*>', '\n\n## ', html, flags=re.IGNORECASE)
    html = re.sub(r'</h[1-6]>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<li[^>]*>', '\n- ', html, flags=re.IGNORECASE)

    # Remove remaining tags
    html = re.sub(r'<[^>]+>', ' ', html)

    # Decode HTML entities
    text = unescape(html)

    # Clean whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()

    return text


async def linkedin_posts(
    linkedin_url: str,
    max_posts: int = 5,
    apify_token: str | None = None,
) -> str:
    """
    Fetch LinkedIn posts via Apify.

    Args:
        linkedin_url: LinkedIn profile URL
        max_posts: Maximum posts to return
        apify_token: Apify API token

    Returns:
        Formatted posts as string
    """
    token = apify_token or getattr(settings, "apify_token", None)

    if not token:
        return "Error: Apify token not configured"

    # Extract profile ID from URL
    profile_id = _extract_linkedin_id(linkedin_url)
    if not profile_id:
        return f"Error: Invalid LinkedIn URL format: {linkedin_url}"

    try:
        # Use Apify's LinkedIn Post Scraper
        actor_id = "supreme_coder/linkedin-post"

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Start actor run
            run_response = await client.post(
                f"https://api.apify.com/v2/acts/{actor_id}/runs",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "profileUrls": [linkedin_url],
                    "maxPosts": max_posts,
                }
            )
            run_response.raise_for_status()
            run_data = run_response.json()
            run_id = run_data["data"]["id"]

            # Wait for completion (poll)
            for _ in range(30):  # Max 30 seconds
                await asyncio.sleep(1)
                status_response = await client.get(
                    f"https://api.apify.com/v2/actor-runs/{run_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                status_data = status_response.json()
                status = status_data["data"]["status"]

                if status == "SUCCEEDED":
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    return f"Error: LinkedIn scrape {status.lower()}"

            # Get results
            dataset_id = status_data["data"]["defaultDatasetId"]
            results_response = await client.get(
                f"https://api.apify.com/v2/datasets/{dataset_id}/items",
                headers={"Authorization": f"Bearer {token}"}
            )
            posts = results_response.json()

        if not posts:
            return f"No posts found for {linkedin_url}"

        # Format posts
        formatted = []
        for post in posts[:max_posts]:
            text = post.get("text", "")[:500]  # Truncate long posts
            date = post.get("postedDate", "Unknown date")
            likes = post.get("numLikes", 0)
            comments = post.get("numComments", 0)

            formatted.append(
                f"**Post ({date})**\n"
                f"{text}\n"
                f"Engagement: {likes} likes, {comments} comments"
            )

        return "\n\n---\n\n".join(formatted)

    except httpx.TimeoutException:
        return f"Error: LinkedIn scrape timed out for {linkedin_url}"
    except Exception as e:
        logger.error(f"LinkedIn posts error: {e}", exc_info=True)
        return f"Error: Failed to fetch LinkedIn posts - {str(e)}"


def _extract_linkedin_id(url: str) -> str | None:
    """Extract LinkedIn profile ID from URL."""
    patterns = [
        r"linkedin\.com/in/([^/\?]+)",
        r"linkedin\.com/pub/([^/\?]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


# ============================================
# TOOL REGISTRY
# ============================================

# Maps tool names to implementation functions
TOOL_REGISTRY: dict[str, Callable[..., Coroutine[Any, Any, str]]] = {
    "web_search": web_search,
    "web_fetch": web_fetch,
    "linkedin_posts": linkedin_posts,
}


# ============================================
# HELPER FUNCTIONS
# ============================================


def get_tools_for_agent(agent_type: str) -> list[dict]:
    """Get tool definitions for a specific agent type."""
    tools_map = {
        "icp_extraction": ICP_TOOLS,
        "enrichment": ENRICHMENT_TOOLS,
        "email": EMAIL_TOOLS,
        "voice_kb": VOICE_KB_TOOLS,
        "objection": OBJECTION_TOOLS,
    }
    return tools_map.get(agent_type, [])


async def execute_tool(name: str, **kwargs) -> str:
    """Execute a tool by name with given arguments."""
    if name not in TOOL_REGISTRY:
        return f"Error: Unknown tool '{name}'"

    tool_fn = TOOL_REGISTRY[name]
    return await tool_fn(**kwargs)
