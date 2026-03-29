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

    # ── Helpers ──────────────────────────────────────────────────────────────

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
        return stats

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
            abn_data = await self._match_abn(domain, website_data.get("title"), state_hint)
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

    async def _scrape_website(self, domain: str) -> dict[str, Any]:
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
        self, domain: str, title: str | None, state_hint: str | None
    ) -> dict[str, Any]:
        result: dict[str, Any] = {"abn_matched": False}

        if title and len(title.strip()) > 3:
            search_name = re.sub(r"\s*[\|\u2013\-]\s*.+$", "", title.strip()).strip()
        else:
            search_name = domain.split(".")[0].replace("-", " ").replace("_", " ")

        if len(search_name) < 3:
            return result

        search_lower = search_name.lower()

        # Try local abn_registry table
        try:
            rows = await self._conn.fetch(
                "SELECT abn, legal_name, trading_name, gst_registered, "
                "entity_type, registration_date, state "
                "FROM abn_registry "
                "WHERE LOWER(trading_name) LIKE $1 OR LOWER(legal_name) LIKE $1 "
                "LIMIT 5",
                f"%{search_lower}%",
            )
            if rows:
                match = rows[0]
                if state_hint and len(rows) > 1:
                    for row in rows:
                        if (row.get("state") or "").upper() == state_hint.upper():
                            match = row
                            break
                api_name = match.get("trading_name") or match.get("legal_name") or ""
                confidence = self._abn_confidence(search_name, api_name)
                return {
                    "abn_matched": True,
                    "gst_registered": match["gst_registered"],
                    "entity_type": match["entity_type"],
                    "registration_date": match["registration_date"],
                    "abn_confidence": confidence,
                }
        except Exception as exc:
            self._logger.warning("ABN registry query failed for %s: %s", domain, exc)

        # Fallback: live ABN API
        try:
            from src.config.settings import settings
            from src.integrations.abn_client import ABNClient

            async with ABNClient(guid=settings.ABN_LOOKUP_GUID) as abn:
                api_results = await abn.search_by_name(search_name)
            if api_results and isinstance(api_results, list) and api_results[0]:
                r = api_results[0]
                api_name = r.get("legal_name") or r.get("trading_name") or ""
                confidence = self._abn_confidence(search_name, api_name)
                return {
                    "abn_matched": True,
                    "gst_registered": r.get("gst_registered", False),
                    "entity_type": r.get("entity_type"),
                    "registration_date": r.get("registration_date"),
                    "abn_confidence": confidence,
                }
        except Exception as exc:
            self._logger.warning("ABN API fallback failed for %s: %s", domain, exc)

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
