"""
Contract: src/integrations/httpx_scraper.py
Purpose: Lightweight raw-HTML website scraper using httpx (no JS rendering)
Layer: 2 - integrations
Imports: httpx only
Consumers: src/pipeline/free_enrichment.py
Directive: #295
"""

from __future__ import annotations

import re

import httpx

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class HttpxScraper:
    """Raw-HTML scraper using httpx AsyncClient. No JS rendering."""

    async def scrape(self, domain: str, timeout: float = 10.0) -> dict | None:
        """
        Fetch https://{domain} and return a result dict.

        Returns:
            dict with keys: status_code (int), html (str), title (str | None),
            content_length (int)
        Returns None on timeout, connection error, or non-200 status.
        """
        url = f"https://{domain}"
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={"User-Agent": _UA},
                timeout=timeout,
            ) as client:
                resp = await client.get(url)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError):
            return None

        if resp.status_code != 200:
            return None

        html = resp.text
        title_match = _TITLE_RE.search(html)
        title = title_match.group(1).strip() if title_match else None

        return {
            "status_code": resp.status_code,
            "html": html,
            "title": title,
            "content_length": len(html),
        }
