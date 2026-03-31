"""
Contract: src/pipeline/mobile_waterfall.py
Purpose: 3-tier mobile number discovery waterfall for DM prospects.
         Short-circuits on first find. Tracks source and cost.
Layer: 4 - orchestration
Directive: #300-FIX Issue 11

TIERS:
  Layer 1: Website regex on cached HTML (free)
           Run during scrape stage on every domain — result in contact_data.
  Layer 2: Leadmagic mobile ($0.077/lookup)
           Run on all DM-found prospects where Layer 1 failed.
  Layer 3: Bright Data LinkedIn profile ($0.00075/lookup)
           Run on all where Layer 2 failed.

Mobile runs on ALL DM-found prospects (260 from Stage 6), not just STRUGGLING.
Stage 8 integration test will run on all 260 DM-found domains.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

# ── Mobile regex patterns ─────────────────────────────────────────────────────
_MOBILE_AU_RE    = re.compile(r'04\d{2}[\s.\-]?\d{3}[\s.\-]?\d{3}')
_MOBILE_INTL_RE  = re.compile(r'\+614\d{2}[\s.\-]?\d{3}[\s.\-]?\d{3}')
_MOBILE_CLEAN_RE = re.compile(r'[\s.\-]')

# ── Costs ─────────────────────────────────────────────────────────────────────
COST_LAYER2_LEADMAGIC  = Decimal("0.077")
COST_LAYER3_BRIGHTDATA = Decimal("0.00075")


@dataclass
class MobileResult:
    mobile: str | None = None
    source: str | None = None        # "html_regex" | "leadmagic" | "brightdata" | None
    cost_usd: Decimal = field(default_factory=Decimal)
    tier_used: int | None = None
    error: str | None = None


def extract_mobile_from_html(html: str) -> str | None:
    """Layer 1: regex scan of already-scraped HTML. Free."""
    if not html:
        return None
    for pattern in (_MOBILE_INTL_RE, _MOBILE_AU_RE):
        m = pattern.search(html)
        if m:
            raw = m.group(0)
            clean = _MOBILE_CLEAN_RE.sub("", raw)
            # Normalise: +614XXXXXXXX → 04XXXXXXXX for consistency
            if clean.startswith("+614"):
                clean = "0" + clean[3:]
            return clean
    return None


async def run_mobile_waterfall(
    domain: str,
    dm_linkedin_url: str | None,
    contact_data: dict | None,
    leadmagic_client: Any | None = None,
    brightdata_client: Any | None = None,
    sem_paid: asyncio.Semaphore | None = None,
) -> MobileResult:
    """
    Run the 3-tier mobile discovery waterfall for a single domain.

    Args:
        domain: The business domain.
        dm_linkedin_url: LinkedIn profile URL from DM identification stage.
        contact_data: Free contact signals extracted during scrape (may contain mobile).
        leadmagic_client: Optional LeadmagicClient for Layer 2 ($0.077).
        brightdata_client: Optional BrightDataLinkedInClient for Layer 3 ($0.00075).
        sem_paid: Optional semaphore to gate paid calls.

    Returns:
        MobileResult with mobile number, source, cost, and tier used.
    """
    # ── Layer 1: HTML regex (already extracted — check contact_data) ──────────
    if contact_data and contact_data.get("mobile"):
        return MobileResult(
            mobile=contact_data["mobile"],
            source="html_regex",
            cost_usd=Decimal("0"),
            tier_used=1,
        )

    # ── Layer 2: Leadmagic mobile lookup ──────────────────────────────────────
    if leadmagic_client is not None and dm_linkedin_url:
        try:
            async with (sem_paid if sem_paid else contextlib.nullcontext()):
                result = await leadmagic_client.find_mobile(
                    linkedin_url=dm_linkedin_url,
                )
            if result and result.get("mobile"):
                return MobileResult(
                    mobile=result["mobile"],
                    source="leadmagic",
                    cost_usd=COST_LAYER2_LEADMAGIC,
                    tier_used=2,
                )
        except Exception as exc:
            logger.warning("mobile_waterfall Layer 2 failed for %s: %s", domain, exc)

    # ── Layer 3: Bright Data LinkedIn profile ─────────────────────────────────
    if brightdata_client is not None and dm_linkedin_url:
        try:
            async with (sem_paid if sem_paid else contextlib.nullcontext()):
                profile = await brightdata_client.get_profile(
                    linkedin_url=dm_linkedin_url,
                )
            if profile and profile.get("mobile"):
                return MobileResult(
                    mobile=profile["mobile"],
                    source="brightdata",
                    cost_usd=COST_LAYER3_BRIGHTDATA,
                    tier_used=3,
                )
        except Exception as exc:
            logger.warning("mobile_waterfall Layer 3 failed for %s: %s", domain, exc)

    return MobileResult(mobile=None, source=None, cost_usd=Decimal("0"), tier_used=None)
