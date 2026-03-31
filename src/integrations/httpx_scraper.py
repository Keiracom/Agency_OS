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

_MOBILE_AU_RE   = re.compile(r'04\d{2}[\s.\-]?\d{3}[\s.\-]?\d{3}')
_MOBILE_INTL_RE = re.compile(r'\+614\d{2}[\s.\-]?\d{3}[\s.\-]?\d{3}')
_LANDLINE_RE    = re.compile(r'0[2378][\s.\-]?\d{4}[\s.\-]?\d{4}')
_EMAIL_RE       = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
_LINKEDIN_RE    = re.compile(r'linkedin\.com/(?:in|company)/[\w\-]+')
_MOBILE_CLEAN   = re.compile(r'[\s.\-]')

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class HttpxScraper:
    """Raw-HTML scraper using httpx AsyncClient. No JS rendering."""

    def _extract_contact_data(self, html: str) -> dict:
        """
        Extract free contact signals from scraped HTML.
        Returns contact_data dict with mobile, landline, email, linkedin fields.
        All fields are None if not found. Never raises.
        """
        contact: dict = {
            "mobile": None,
            "landline": None,
            "email": None,
            "linkedin": None,
        }
        if not html:
            return contact
        # Mobile (intl pattern takes priority — normalise to 04XXXXXXXX)
        m = _MOBILE_INTL_RE.search(html)
        if m:
            raw = _MOBILE_CLEAN.sub("", m.group(0))
            contact["mobile"] = "0" + raw[3:]   # +614 → 04
        else:
            m = _MOBILE_AU_RE.search(html)
            if m:
                contact["mobile"] = _MOBILE_CLEAN.sub("", m.group(0))
        # Landline
        m = _LANDLINE_RE.search(html)
        if m:
            contact["landline"] = _MOBILE_CLEAN.sub("", m.group(0))
        # Email (first non-generic)
        emails = _EMAIL_RE.findall(html)
        GENERIC = {"noreply", "info", "support", "admin", "webmaster", "hello", "contact"}
        for email in emails:
            local = email.split("@")[0].lower()
            if local not in GENERIC and not email.endswith(".png") and not email.endswith(".jpg"):
                contact["email"] = email.lower()
                break
        # LinkedIn profile or company URL
        m = _LINKEDIN_RE.search(html)
        if m:
            contact["linkedin"] = "https://www." + m.group(0)
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
        contact_data = self._extract_contact_data(html)

        return {
            "status_code": resp.status_code,
            "html": html,
            "title": title,
            "content_length": len(html),
            "contact_data": contact_data,
        }
