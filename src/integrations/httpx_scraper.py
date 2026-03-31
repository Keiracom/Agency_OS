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

_TITLE_RE      = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_MOBILE_AU_RE  = re.compile(r'04\d{2}[\s.\-]?\d{3}[\s.\-]?\d{3}')
_MOBILE_INT_RE = re.compile(r'\+614\d{2}[\s.\-]?\d{3}[\s.\-]?\d{3}')
_LANDLINE_RE   = re.compile(r'0[2378][\s.\-]?\d{4}[\s.\-]?\d{4}')
_EMAIL_RE      = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
_LINKEDIN_RE   = re.compile(r'linkedin\.com/(?:in|company)/[\w\-]+')
_CLEAN_RE      = re.compile(r'[\s.\-]')
_GENERIC_EMAIL = frozenset({"noreply", "info", "support", "admin", "webmaster", "hello", "contact", "enquiries", "enquiry"})
_PLACEHOLDER_EMAIL_RE = re.compile(
    r"(example\.|yourdomain\.|placeholder|test@|you@|your@|user@)",
    re.IGNORECASE,
)
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

    def _extract_contact_data(self, html: str) -> dict:
        """
        Extract free contact signals from scraped HTML.
        Returns separated company_* and dm/linkedin fields.
        Never raises.
        """
        contact: dict = {
            "company_email":   None,   # from website mailto/contact page
            "company_phone":   None,   # landline: 0[2378]XXXXXXXX
            "company_mobile":  None,   # 04XX mobile from website
            "linkedin_company": None,  # company LinkedIn page URL
            "linkedin_dm":     None,   # person LinkedIn profile URL (/in/)
            # DM fields (populated by paid waterfalls, not scrape)
            "dm_email":        None,
            "dm_email_verified": False,
            "dm_mobile":       None,
        }
        if not html:
            return contact
        # Company mobile (04XX — intl takes priority)
        m = _MOBILE_INT_RE.search(html)
        if m:
            raw = _CLEAN_RE.sub("", m.group(0))
            contact["company_mobile"] = "0" + raw[3:]  # +614 → 04
        else:
            m = _MOBILE_AU_RE.search(html)
            if m:
                contact["company_mobile"] = _CLEAN_RE.sub("", m.group(0))
        # Company landline
        m = _LANDLINE_RE.search(html)
        if m:
            contact["company_phone"] = _CLEAN_RE.sub("", m.group(0))
        # Company email (first non-generic)
        for email in _EMAIL_RE.findall(html):
            local = email.split("@")[0].lower()
            if (local not in _GENERIC_EMAIL
                    and not email.endswith((".png", ".jpg", ".gif"))
                    and not _PLACEHOLDER_EMAIL_RE.search(email)):
                contact["company_email"] = email.lower()
                break
        # LinkedIn — split company vs person
        for m in _LINKEDIN_RE.finditer(html):
            url = "https://www." + m.group(0)
            if "/in/" in url and not contact["linkedin_dm"]:
                contact["linkedin_dm"] = url
            elif "/company/" in url and not contact["linkedin_company"]:
                contact["linkedin_company"] = url
        return contact

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
            "contact_data": self._extract_contact_data(html),
        }
