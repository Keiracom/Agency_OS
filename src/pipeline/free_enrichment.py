"""
Contract: src/pipeline/free_enrichment.py
Purpose: Zero-cost enrichment for business_universe — DNS, website scrape, ABN match
Layer: 4 - orchestration (uses asyncpg connection directly)
Imports: asyncpg, httpx, dns.resolver, src.integrations (ABN fallback)
Consumers: orchestration flows
Directive: #282
"""

from __future__ import annotations

import asyncio
import difflib
import json
import logging
import os
import re
from enum import Enum
from typing import Any

import asyncpg
import dns.resolver
import httpx

SPIDER_API_URL = "https://api.spider.cloud/scrape"
BATCH_SIZE = 50
DNS_TIMEOUT = 5
SPIDER_MAX_CREDITS_PER_PAGE = 50

# ── Ad tag detection regexes ─────────────────────────────────────────────────
AW_TAG_RE = re.compile(
    r'gtag\s*\(\s*["\']config["\']\s*,\s*["\']AW-|googleadservices\.com/pagead/conversion',
    re.IGNORECASE,
)
GADS_RMK_RE = re.compile(
    r'google_remarketing_only|google_conversion_id|googleads\.g\.doubleclick\.net',
    re.IGNORECASE,
)
META_PIXEL_RE = re.compile(
    r'connect\.facebook\.net|fbq\s*\(|facebook-jssdk',
    re.IGNORECASE,
)

# ── ABN multi-strategy matching constants ────────────────────────────────────
_ABN_STOPWORDS: frozenset[str] = frozenset({
    "at", "and", "the", "of", "in", "for", "by", "to", "a", "an",
    "my", "your", "our", "its", "with", "from", "on", "is", "as", "or",
})
_RE_ABN_ENTITY_SUFFIXES = re.compile(
    r"\s*(PTY\.?\s*LTD\.?|PROPRIETARY\s+LIMITED|PTY\s+LIMITED|LIMITED"
    r"|LTD\.?|TRUST|TRADING\s+AS|T/A|ABN)\s*$",
    re.IGNORECASE,
)
_RE_ABN_ENTITY_PREFIXES = re.compile(
    r"^(THE\s+TRUSTEE\s+FOR\s+THE\s+|THE\s+TRUSTEE\s+FOR\s+"
    r"|THE\s+TRUST\s+OF\s+|TRUSTEE\s+FOR\s+THE\s+|TRUSTEE\s+FOR\s+)",
    re.IGNORECASE,
)
_RE_ABN_TITLE_CLEANUP = re.compile(
    r"^\s*(Home\s*[\|\u2013\-]|Welcome\s+to|About\s*[\|\u2013\-]|Contact)\s*",
    re.IGNORECASE,
)

CMS_PATTERNS = {
    "wp-content/": "wordpress",
    "wp-includes/": "wordpress",
    "/cdn.shopify.com": "shopify",
    "squarespace.com/universal": "squarespace",
    "wix.com": "wix",
    "webflow.com": "webflow",
    ".ghost.io": "ghost",
    "drupal.org": "drupal",
}

TECH_PATTERNS = {
    "jquery": "jquery",
    "react": "react",
    "/vue": "vue",
    "angular": "angular",
    "next": "nextjs",
    "nuxt": "nuxtjs",
    "gatsby": "gatsby",
    "bootstrap": "bootstrap",
    "tailwind": "tailwind",
}

MX_PROVIDER_MAP = {
    "google": "google",
    "gmail": "google",
    "outlook": "microsoft365",
    "microsoft": "microsoft365",
    "zoho": "zoho",
    "mimecast": "mimecast",
    "proofpoint": "proofpoint",
}

TRACKER_CHECKS: list[tuple[list[str], str]] = [
    (["gtag(", "g-", "ga-", "ua-"], "google_analytics"),
    (["gtm-"], "google_tag_manager"),
    (["fbq(", "facebook.net"], "facebook_pixel"),
    (["_linkedin_partner_id"], "linkedin_insight"),
    (["hs-script", "js.hubspot.com"], "hubspot"),
    (["hotjar"], "hotjar"),
    (["clarity.ms"], "clarity"),
]

DKIM_SELECTORS = ["google._domainkey", "selector1._domainkey", "default._domainkey"]

TEAM_SLUGS = ["/about", "/team", "/our-team", "/people", "/staff"]


class ABNMatchConfidence(str, Enum):
    EXACT   = "exact"    # >=90% similarity
    PARTIAL = "partial"  # 60-89% similarity
    LOW     = "low"      # <60% similarity


class EmailMaturity(str, Enum):
    PROFESSIONAL = "professional"   # custom domain MX + SPF
    WEBMAIL      = "webmail"        # has MX but no SPF
    NONE         = "none"           # no MX record


class FreeEnrichment:
    """
    Zero-cost enrichment pass for business_universe rows.

    Runs DNS pre-check, Spider website scrape, DNS enrichment, and ABN matching.
    Writes results back to business_universe and stamps free_enrichment_completed_at.
    """

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn
        self._spider_key = os.environ.get("SPIDER_API_KEY", "")
        self._logger = logging.getLogger(__name__)
        self._spider_fallback_count: int = 0

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _detect_ad_tags(html: str) -> dict[str, bool]:
        """Scan Spider-scraped HTML for advertising pixel/tag patterns.
        Free signal: no extra API calls, uses already-scraped content.
        Returns: has_google_ads_tag, has_meta_pixel, has_any_ad_tag
        """
        if not html:
            return {"has_google_ads_tag": False, "has_meta_pixel": False, "has_any_ad_tag": False}
        aw    = bool(AW_TAG_RE.search(html))
        rmk   = bool(GADS_RMK_RE.search(html))
        meta  = bool(META_PIXEL_RE.search(html))
        gads  = aw or rmk
        return {
            "has_google_ads_tag": gads,
            "has_meta_pixel": meta,
            "has_any_ad_tag": gads or meta,
        }

    def _abn_confidence(self, search_name: str, api_name: str) -> ABNMatchConfidence:
        """Compute name similarity between search term and ABN registry name."""
        ratio = difflib.SequenceMatcher(
            None, search_name.lower(), api_name.lower()
        ).ratio()
        if ratio >= 0.90:
            return ABNMatchConfidence.EXACT
        if ratio >= 0.60:
            return ABNMatchConfidence.PARTIAL
        return ABNMatchConfidence.LOW

    @staticmethod
    def _abn_clean_entity_name(name: str) -> str:
        """Strip common ABN registry suffixes/prefixes before similarity comparison.

        Examples:
            "DENTISTS@PYMBLE PTY LIMITED" → "DENTISTS@PYMBLE"
            "THE TRUSTEE FOR ABC TRUST" → "ABC TRUST"
        """
        name = _RE_ABN_ENTITY_PREFIXES.sub("", name).strip()
        name = _RE_ABN_ENTITY_SUFFIXES.sub("", name).strip()
        return name

    @staticmethod
    def _extract_domain_keywords(domain: str) -> list[str]:
        """Extract meaningful keywords from a domain name.

        Strips TLD, splits on hyphens/underscores, and splits concatenated
        words by removing stopwords.  Only splits on a stopword when both
        neighbouring sides have ≥ 5 non-space characters, preventing false
        splits on embedded stopword fragments (e.g. "is" inside "dentists").

        Examples:
            "dentistsatpymble.com.au" → ["dentists", "pymble"]
            "bright-smile-dental.com" → ["bright", "smile", "dental"]
            "brunswick-east-dental.com.au" → ["brunswick", "east", "dental"]
        """
        stem = domain.split(".")[0].lower()
        # Split on explicit separators first
        parts = re.split(r"[-_]", stem)
        if len(parts) == 1:
            # Concatenated word: inject spaces around stopwords only when both
            # neighbouring sides have ≥ 5 non-space characters.
            word = stem
            for sw in sorted(_ABN_STOPWORDS, key=len, reverse=True):
                buf: list[str] = []
                i = 0
                while i < len(word):
                    if word[i : i + len(sw)] == sw:
                        left_len = len("".join(buf).replace(" ", ""))
                        right_len = len(word[i + len(sw) :].replace(" ", ""))
                        if left_len >= 5 and right_len >= 5:
                            buf.append(" ")
                            i += len(sw)
                            buf.append(" ")
                            continue
                    buf.append(word[i])
                    i += 1
                word = "".join(buf)
            parts = word.split()
        return [w for w in parts if len(w) > 2 and w not in _ABN_STOPWORDS]

    async def _local_abn_match(
        self,
        keywords: list[str],
        state_hint: str | None = None,
    ) -> asyncpg.Record | None:
        """Search local abn_registry requiring ALL keywords to appear in legal/trading name.

        Uses AND-intersection so that e.g. ["dentists", "pymble"] only matches
        entities that contain BOTH words — avoiding broad false positives.
        """
        if not keywords:
            return None
        conditions: list[str] = []
        params: list[str] = []
        for kw in keywords[:4]:  # cap at 4 to avoid over-constraining
            idx = len(params) + 1
            conditions.append(
                f"(LOWER(legal_name) LIKE ${idx} OR LOWER(trading_name) LIKE ${idx})"
            )
            params.append(f"%{kw}%")
        sql = (
            "SELECT abn, legal_name, trading_name, gst_registered, "
            "entity_type, registration_date, state "
            f"FROM abn_registry WHERE {' AND '.join(conditions)} LIMIT 10"
        )
        rows = await self._conn.fetch(sql, *params)
        if not rows:
            return None
        if state_hint and len(rows) > 1:
            for r in rows:
                if (r.get("state") or "").upper() == state_hint.upper():
                    return r
        return rows[0]

    async def _local_abn_gst(self, abn_raw: str) -> tuple[bool | None, str | None, Any]:
        """Return (gst_registered, entity_type, registration_date) for a given ABN from local table."""
        if not abn_raw:
            return None, None, None
        try:
            row = await self._conn.fetchrow(
                "SELECT gst_registered, entity_type, registration_date "
                "FROM abn_registry WHERE abn = $1",
                abn_raw,
            )
            if row:
                return row["gst_registered"], row["entity_type"], row.get("registration_date")
        except Exception:
            pass
        return None, None, None

    def _abn_result_from_row(
        self,
        row: asyncpg.Record,
        search_name: str,
        strategy: str,
    ) -> dict[str, Any]:
        """Build the standard abn_matched result dict from a local DB row."""
        api_name = row.get("trading_name") or row.get("legal_name") or ""
        confidence = self._abn_confidence(
            search_name, self._abn_clean_entity_name(api_name)
        )
        return {
            "abn_matched": True,
            "gst_registered": row["gst_registered"],
            "entity_type": row["entity_type"],
            "registration_date": row.get("registration_date"),
            "abn_confidence": confidence,
            "_abn_strategy": strategy,
        }

    def _compute_email_maturity(
        self, mx_provider: str | None, has_spf: bool
    ) -> EmailMaturity:
        """Classify email infrastructure maturity from MX provider + SPF presence."""
        if mx_provider is None:
            return EmailMaturity.NONE
        if has_spf:
            return EmailMaturity.PROFESSIONAL
        return EmailMaturity.WEBMAIL

    def _extract_jsonld_address(self, html: str) -> dict[str, str | None] | None:
        """Extract structured address from JSON-LD schema.org blocks in HTML."""
        blocks = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        for block in blocks:
            try:
                data = json.loads(block)
            except (json.JSONDecodeError, ValueError):
                continue
            # Normalise to a list of items
            if isinstance(data, dict) and "@graph" in data:
                items = data["@graph"]
            elif isinstance(data, list):
                items = data
            else:
                items = [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                address = item.get("address")
                if not address:
                    continue
                if isinstance(address, dict):
                    return {
                        "street": address.get("streetAddress"),
                        "suburb": address.get("addressLocality"),
                        "state": address.get("addressRegion"),
                        "postcode": address.get("postalCode"),
                    }
        return None

    async def run(self, limit: int = 500) -> dict:
        rows = await self._conn.fetch(
            "SELECT id, domain, state FROM business_universe "
            "WHERE pipeline_stage >= 1 AND free_enrichment_completed_at IS NULL "
            "AND domain IS NOT NULL LIMIT $1",
            limit,
        )
        stats = {
            "total": len(rows),
            "completed": 0,
            "dns_skipped": 0,
            "spider_failed": 0,
            "abn_matched": 0,
            "abn_unmatched": 0,
            "errors": [],
        }
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            await asyncio.gather(*[self._process_domain(row, stats) for row in batch])
            self._logger.info(
                "FreeEnrichment: processed %d/%d",
                min(i + BATCH_SIZE, len(rows)),
                len(rows),
            )
        self._logger.info(
            "Spider fallbacks: %d/%d domains",
            self._spider_fallback_count,
            len(rows),
        )
        return stats

    async def enrich(self, domain: str) -> dict | None:
        """
        Single-domain enrichment for pipeline orchestration.
        Does NOT write to DB. Returns enrichment dict or None on failure.
        Used by PipelineOrchestrator.run().
        """
        try:
            domain_alive = self._dns_precheck(domain)
            website_data: dict = {}
            if domain_alive:
                website_data = await self._scrape_website(domain) or {}
            dns_data = self._enrich_dns(domain)
            suburb = (website_data.get("website_address") or {}).get("suburb")
            abn_data = await self._match_abn(
                domain,
                website_data.get("title"),
                state_hint=None,
            )
            title = website_data.get("title", "")
            company_name = (
                title.split("|")[0].split("-")[0].strip()[:60]
                or domain.split(".")[0].replace("-", " ").title()
            )
            return {
                **website_data,
                **dns_data,
                **abn_data,
                "company_name": company_name,
                "domain": domain,
            }
        except Exception as exc:
            self._logger.warning("enrich failed for %s: %s", domain, exc)
            return None

    async def scrape_website(self, domain: str) -> dict:
        """Public Spider scrape method for stage-parallel pipeline."""
        return await self._scrape_website(domain)

    async def enrich_from_spider(
        self,
        domain: str,
        spider_data: dict,
    ) -> dict | None:
        """
        DNS + ABN enrichment given pre-scraped Spider data.
        Used by stage-parallel PipelineOrchestrator where Spider runs as its own stage.
        Does NOT call _scrape_website(). Accepts pre-scraped output or empty dict.
        ABN uses asyncpg — caller must ensure only 1 concurrent call (sem=1) or pass
        sem_abn explicitly.
        """
        try:
            dns_data = self._enrich_dns(domain)
            title = spider_data.get("title", "")
            suburb = (spider_data.get("website_address") or {}).get("suburb")
            abn_data = await self._match_abn(
                domain,
                title or None,
                state_hint=None,
                suburb=suburb,
            )
            company_name = (
                title.split("|")[0].split("-")[0].strip()[:60]
                or domain.split(".")[0].replace("-", " ").title()
            )
            return {
                **spider_data,
                **dns_data,
                **abn_data,
                "company_name": company_name,
                "domain": domain,
            }
        except Exception as exc:
            self._logger.warning("enrich_from_spider failed for %s: %s", domain, exc)
            return None

    async def _process_domain(self, row: asyncpg.Record, stats: dict) -> None:
        domain = row["domain"]
        bu_id = row["id"]
        state_hint = row.get("state")
        try:
            domain_alive = self._dns_precheck(domain)
            website_data: dict[str, Any] = {}
            if domain_alive:
                website_data = await self._scrape_website(domain)
            else:
                stats["dns_skipped"] += 1
            dns_data = self._enrich_dns(domain)
            suburb = (website_data.get("website_address") or {}).get("suburb")
            abn_data = await self._match_abn(
                domain, website_data.get("title"), state_hint, suburb=suburb
            )
            if abn_data.get("abn_matched"):
                stats["abn_matched"] += 1
            else:
                stats["abn_unmatched"] += 1
            await self._write_results(bu_id, website_data, dns_data, abn_data)
            stats["completed"] += 1
        except Exception as exc:
            self._logger.error("FreeEnrichment error for %s: %s", domain, exc)
            stats["errors"].append({"domain": domain, "error": str(exc)})

    def _dns_precheck(self, domain: str) -> bool:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = float(DNS_TIMEOUT)
        for rdtype in ("A", "AAAA"):
            try:
                resolver.resolve(domain, rdtype)
                return True
            except dns.resolver.NXDOMAIN:
                return False
            except Exception:
                continue
        return False

    def _is_content_usable(self, content: str) -> bool:
        """Return False when content indicates a bot-challenge or empty page (trigger Spider fallback)."""
        if len(content) < 500:
            return False
        lower = content.lower()
        if "cf-browser-verification" in lower:
            return False
        if "just a moment" in lower and "cloudflare" in lower:
            return False
        if "<script" not in lower and len(content) < 2000:
            return False
        return True

    def _parse_html_content(self, html: str, base_url: str) -> dict[str, Any]:
        """Extract structured data from raw HTML — shared by httpx and Spider paths."""
        # Title from <title> tag
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        # Links from <a href="...">
        raw_links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE)
        links: list[str] = []
        for link in raw_links:
            link = link.strip()
            if link.startswith("//"):
                link = "https:" + link
            elif link.startswith("/"):
                link = base_url.rstrip("/") + link
            links.append(link)
        website_address = self._extract_jsonld_address(html)
        return {
            "title": title,
            "website_cms": self._extract_cms(html),
            "website_tech_stack": self._extract_tech_stack(html),
            "website_tracking_codes": self._extract_trackers(html),
            "website_team_names": self._extract_team_urls(links),
            "website_contact_emails": self._extract_emails(html, links),
            "website_address": website_address,
            **self._detect_ad_tags(html),
        }

    async def _scrape_website(self, domain: str) -> dict[str, Any]:
        url = f"https://{domain}"

        # Try httpx first (free)
        try:
            async with httpx.AsyncClient(
                timeout=20,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AgencyOS/1.0)"},
            ) as client:
                resp = await client.get(url)
                content = resp.text

            if self._is_content_usable(content):
                return self._parse_html_content(content, url)
        except Exception as exc:
            self._logger.debug("httpx failed for %s: %s", domain, exc)

        # Fall back to Spider for JS-heavy / blocked pages
        self._logger.debug("Falling back to Spider for %s", domain)
        return await self._spider_scrape(domain)

    async def _spider_scrape(self, domain: str) -> dict[str, Any]:
        """Call Spider Cloud API and parse the result — used as fallback when httpx fails."""
        self._spider_fallback_count += 1
        payload = {
            "url": f"https://{domain}",
            "return_format": "raw",
            "metadata": True,
            "return_page_links": True,
            "request": "smart",
            "limit": 1,
            "max_credits_per_page": SPIDER_MAX_CREDITS_PER_PAGE,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    SPIDER_API_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {self._spider_key}"},
                )
            if resp.status_code != 200:
                self._logger.warning("Spider %d for %s", resp.status_code, domain)
                return {}
            data = resp.json()
            if not data or not isinstance(data, list):
                return {}
            item = data[0]
            content: str = item.get("content") or ""
            links: list = item.get("links") or []
            metadata: dict = item.get("metadata") or {}
            if not content:
                return {}
            # JSON-LD address extraction (falls back to None — regex not used here)
            website_address = self._extract_jsonld_address(content)
            return {
                "title": metadata.get("title", ""),
                "website_cms": self._extract_cms(content),
                "website_tech_stack": self._extract_tech_stack(content),
                "website_tracking_codes": self._extract_trackers(content),
                "website_team_names": self._extract_team_urls(links),
                "website_contact_emails": self._extract_emails(content, links),
                "website_address": website_address,
                **self._detect_ad_tags(content),
            }
        except Exception as exc:
            self._logger.warning("Spider error for %s: %s", domain, exc)
            return {}

    def _extract_cms(self, html: str) -> str | None:
        gen = re.search(
            r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)',
            html,
            re.IGNORECASE,
        )
        if not gen:
            gen = re.search(
                r'content=["\']([^"\']*(?:wordpress|shopify|squarespace|wix|webflow|ghost|drupal)[^"\']*)["\']',
                html,
                re.IGNORECASE,
            )
        if gen:
            val = gen.group(1).lower()
            for kw, cms in [
                ("wordpress", "wordpress"),
                ("shopify", "shopify"),
                ("squarespace", "squarespace"),
                ("wix", "wix"),
                ("webflow", "webflow"),
                ("ghost", "ghost"),
                ("drupal", "drupal"),
            ]:
                if kw in val:
                    return cms
        for pattern, cms in CMS_PATTERNS.items():
            if pattern in html:
                return cms
        return None

    def _extract_tech_stack(self, html: str) -> list[str]:
        srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        src_text = " ".join(srcs).lower()
        inline = html.lower()
        techs: list[str] = []
        for pattern, tech in TECH_PATTERNS.items():
            if pattern in src_text or pattern in inline:
                if tech not in techs:
                    techs.append(tech)
        return techs

    def _extract_trackers(self, html: str) -> list[str]:
        lower = html.lower()
        trackers: list[str] = []
        for patterns, name in TRACKER_CHECKS:
            if any(p in lower for p in patterns):
                trackers.append(name)
        return trackers

    def _extract_team_urls(self, links: list) -> list[str]:
        found: list[str] = []
        for link in links:
            if isinstance(link, str) and any(slug in link.lower() for slug in TEAM_SLUGS):
                if link not in found:
                    found.append(link)
        return found

    def _extract_emails(self, html: str, links: list) -> list[str]:
        emails: set[str] = set()
        for link in links:
            if isinstance(link, str) and link.lower().startswith("mailto:"):
                email = link[7:].strip().lower()
                if email:
                    emails.add(email)
        for match in re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", html):
            emails.add(match.lower())
        result = sorted(emails)
        generics = {"noreply", "info"}
        specific = [e for e in result if not any(e.startswith(g + "@") for g in generics)]
        return specific if specific else result

    def _enrich_dns(self, domain: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "dns_mx_provider": None,
            "dns_has_spf": False,
            "dns_has_dkim": False,
        }
        resolver = dns.resolver.Resolver()
        resolver.lifetime = float(DNS_TIMEOUT)

        # MX
        try:
            mx_answers = resolver.resolve(domain, "MX")
            for mx in mx_answers:
                host = str(mx.exchange).lower()
                for kw, provider in MX_PROVIDER_MAP.items():
                    if kw in host:
                        result["dns_mx_provider"] = provider
                        break
                if result["dns_mx_provider"]:
                    break
            if not result["dns_mx_provider"] and mx_answers:
                result["dns_mx_provider"] = "other"
        except Exception:
            pass

        # SPF
        try:
            for txt in resolver.resolve(domain, "TXT"):
                if "v=spf1" in str(txt).lower():
                    result["dns_has_spf"] = True
                    break
        except Exception:
            pass

        # DKIM — collected for storage only; not used in maturity classification
        for selector in DKIM_SELECTORS:
            try:
                resolver.resolve(f"{selector}.{domain}", "TXT")
                result["dns_has_dkim"] = True
                break
            except Exception:
                continue

        # Email maturity classification from MX + SPF
        result["email_maturity"] = self._compute_email_maturity(
            result["dns_mx_provider"], result["dns_has_spf"]
        ).value

        return result

    async def _match_abn(
        self,
        domain: str,
        title: str | None = None,
        state_hint: str | None = None,
        suburb: str | None = None,
    ) -> dict[str, Any]:
        """Multi-strategy ABN matching waterfall.

        Tries 4 strategies in order, returning on the first EXACT or PARTIAL
        confidence match.  Tracks the best LOW-confidence result as a fallback.

        Strategy 1 — Domain keywords (local DB):
            Extract meaningful words from the domain stem and require ALL to
            appear in the ABN entity name.
            e.g. "dentistsatpymble.com.au" → keywords ["dentists","pymble"]
            Matches "Pymble Dental Loving Care Pty Limited" (PARTIAL).

        Strategy 2 — Title keywords (local DB):
            Clean the Spider page title, strip common nav suffixes, and use
            the remaining words as keyword intersection.
            e.g. "Dentists at Pymble | Family Dental" → ["dentists","pymble"]

        Strategy 3 — Suburb + first domain keyword (local DB):
            When a suburb is available from Spider JSON-LD address, combine it
            with the primary domain keyword for a tight two-word intersection.
            e.g. suburb="Pymble", keyword="dental" → finds dental practices in Pymble.

        Strategy 4 — Live ABN API fuzzy search:
            Falls back to the ABR XML API which performs full-text fuzzy search.
            On a match, the returned ABN is cross-referenced with the local table
            to retrieve gst_registered/entity_type (the search endpoint omits these).

        Returns:
            Dict with keys: abn_matched, gst_registered, entity_type,
            registration_date, abn_confidence, _abn_strategy (debug).
            abn_matched=False if nothing found.
        """
        result: dict[str, Any] = {"abn_matched": False}

        # ── Prepare candidate search terms ────────────────────────────────
        domain_keywords = self._extract_domain_keywords(domain)

        title_cleaned: str | None = None
        if title and len(title.strip()) > 3:
            t = _RE_ABN_TITLE_CLEANUP.sub("", title.strip())
            title_cleaned = re.sub(r"\s*[\|\u2013\-]\s*.+$", "", t).strip()
            if len(title_cleaned) < 3:
                title_cleaned = None

        best_low: dict[str, Any] | None = None

        def _keep(r: dict[str, Any]) -> dict[str, Any] | None:
            """Return r if EXACT/PARTIAL; stash as best_low if LOW; else None."""
            nonlocal best_low
            if r["abn_confidence"] in (ABNMatchConfidence.EXACT, ABNMatchConfidence.PARTIAL):
                return r
            if best_low is None:
                best_low = r
            return None

        # ── Strategy 1: Domain keyword intersection (local DB) ────────────
        if len(domain_keywords) >= 2:
            try:
                row = await self._local_abn_match(domain_keywords, state_hint)
                if row:
                    r = _keep(self._abn_result_from_row(
                        row, " ".join(domain_keywords), "domain_keywords"
                    ))
                    if r:
                        return r
            except Exception as exc:
                self._logger.debug("ABN strategy1 (domain) failed %s: %s", domain, exc)

        # ── Strategy 2: Title keyword intersection (local DB) ─────────────
        if title_cleaned:
            title_kw = [
                w for w in re.split(r"\s+", title_cleaned.lower())
                if len(w) > 2 and w not in _ABN_STOPWORDS
            ]
            if len(title_kw) >= 2:
                try:
                    row = await self._local_abn_match(title_kw, state_hint)
                    if row:
                        r = _keep(self._abn_result_from_row(row, title_cleaned, "title_keywords"))
                        if r:
                            return r
                except Exception as exc:
                    self._logger.debug("ABN strategy2 (title) failed %s: %s", domain, exc)

        # ── Strategy 3: Suburb + primary domain keyword (local DB) ────────
        if suburb and domain_keywords:
            suburb_kw = [suburb.lower().strip()] + domain_keywords[:1]
            if len(suburb_kw) >= 2:
                try:
                    row = await self._local_abn_match(suburb_kw, state_hint)
                    if row:
                        r = _keep(self._abn_result_from_row(
                            row, f"{suburb} {domain_keywords[0]}", "suburb_category"
                        ))
                        if r:
                            return r
                except Exception as exc:
                    self._logger.debug("ABN strategy3 (suburb) failed %s: %s", domain, exc)

        # ── Strategy 4: Live ABN API fuzzy search ─────────────────────────
        api_terms = [t for t in [title_cleaned, " ".join(domain_keywords) if domain_keywords else None]
                     if t and len(t) >= 3]
        for api_term in api_terms:
            try:
                from src.config.settings import settings
                from src.integrations.abn_client import ABNClient

                async with ABNClient(guid=settings.abn_lookup_guid) as abn_client:
                    api_results = await abn_client.search_by_name(api_term, limit=5)
                if not api_results:
                    continue
                best = api_results[0]
                api_name = best.get("business_name") or ""
                confidence = self._abn_confidence(
                    api_term, self._abn_clean_entity_name(api_name)
                )
                abn_raw = (best.get("abn") or "").replace(" ", "")
                gst, etype, reg_date = await self._local_abn_gst(abn_raw)
                candidate = {
                    "abn_matched": True,
                    "gst_registered": gst,
                    "entity_type": etype,
                    "registration_date": reg_date,
                    "abn_confidence": confidence,
                    "_abn_strategy": "live_api",
                }
                r = _keep(candidate)
                if r:
                    return r
            except Exception as exc:
                self._logger.warning("ABN strategy4 (api) failed %s: %s", domain, exc)

        # ── Return best LOW match if found, else no match ─────────────────
        if best_low:
            return best_low
        return result

    async def _write_results(
        self,
        bu_id: str,
        website_data: dict,
        dns_data: dict,
        abn_data: dict,
    ) -> None:
        await self._conn.execute(
            """
            UPDATE business_universe SET
                website_cms                   = $2,
                website_tech_stack            = $3::jsonb,
                website_tracking_codes        = $4::jsonb,
                website_team_names            = $5::jsonb,
                website_contact_emails        = $6::jsonb,
                dns_mx_provider               = $7,
                dns_has_spf                   = $8,
                dns_has_dkim                  = $9,
                abn_matched                   = $10,
                gst_registered                = COALESCE($11, gst_registered),
                entity_type                   = COALESCE($12, entity_type),
                registration_date             = COALESCE($13, registration_date),
                email_maturity                = $14,  -- column may need migration if not present
                free_enrichment_completed_at  = NOW()
            WHERE id = $1
            """,
            bu_id,
            website_data.get("website_cms"),
            json.dumps(website_data.get("website_tech_stack") or []),
            json.dumps(website_data.get("website_tracking_codes") or []),
            json.dumps(website_data.get("website_team_names") or []),
            json.dumps(website_data.get("website_contact_emails") or []),
            dns_data.get("dns_mx_provider"),
            dns_data.get("dns_has_spf", False),
            dns_data.get("dns_has_dkim", False),
            abn_data.get("abn_matched", False),
            abn_data.get("gst_registered"),
            abn_data.get("entity_type"),
            abn_data.get("registration_date"),
            dns_data.get("email_maturity"),
        )
