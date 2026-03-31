"""
Contract: src/integrations/httpx_scraper.py
Purpose: Lightweight raw-HTML website scraper using httpx (no JS rendering)
         Uses a persistent AsyncClient with connection pooling to reduce
         SSL handshake overhead on repeated calls.
Layer: 2 - integrations
Imports: httpx only
Consumers: src/pipeline/free_enrichment.py
Directive: #295, updated #300-FIX (Issue 9)
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
    """Raw-HTML scraper using a persistent httpx AsyncClient with connection pooling."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=15.0,
                limits=httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20,
                ),
                follow_redirects=True,
                headers={"User-Agent": _UA},
            )
        return self._client

    async def close(self) -> None:
        """Close the persistent client. Call when the scraper is no longer needed."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

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
            client = await self._get_client()
            resp = await client.get(url, timeout=timeout)
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
