"""
src/utils/gmb_reviews.py
Best-effort GMB review text scraper via Google Maps HTML.
Free (httpx only). Falls back to empty list on any error.
Directive: #300-FIX Issue 4
"""

from __future__ import annotations

import re

import httpx

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def fetch_gmb_reviews(place_id: str, max_reviews: int = 20) -> list[str]:
    """
    Attempt to scrape review text for a GMB place_id from Google Maps HTML.
    Returns list of review text strings (up to max_reviews).
    Returns [] on any failure — caller handles gracefully.
    """
    if not place_id:
        return []
    url = f"https://www.google.com/maps/place/?q=place_id:{place_id}&hl=en"
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": _UA},
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return []
        html = resp.text
        reviews: list[str] = []
        # Pattern 1: span.wiI7pd content (GMB review text class)
        for m in re.finditer(r'class="wiI7pd"[^>]*>([^<]{20,500})<', html):
            text = m.group(1).strip()
            if text and len(text) >= 20:
                reviews.append(text)
        # Pattern 2: reviewText in JSON blobs
        if not reviews:
            for m in re.finditer(r'"reviewText"\s*:\s*"([^"]{20,500})"', html):
                text = m.group(1).strip()
                if text:
                    reviews.append(text)
        return reviews[:max_reviews]
    except Exception:
        return []
