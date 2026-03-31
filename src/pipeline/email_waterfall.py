"""
Contract: src/pipeline/email_waterfall.py
Purpose: 4-layer email discovery waterfall for pipeline v7.
         Runs after DM identification. Finds and verifies deliverable email
         addresses for decision makers before reachability scoring.
Layer: 3 - pipeline
Directive: #299

Waterfall layers (short-circuit — returns on first verified hit):
  Layer 1: Website HTML scrape (free) — mailto: links, email regex on cached HTML
  Layer 2: Pattern generation (free) — first.last@, first@, flast@, firstl@
            + MX record check to confirm domain accepts mail
  Layer 3: Leadmagic email finder ($0.015 USD) — API lookup by name + domain
  Layer 4: Bright Data LinkedIn enrichment ($0.00075 USD) — profile → email

Semaphore: GLOBAL_SEM_LEADMAGIC (10 concurrent) added to global pool.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# ── Lazy-imported clients (at module level for patchability) ─────────────────
try:
    from src.integrations.leadmagic import LeadmagicClient
except ImportError:
    LeadmagicClient = None  # type: ignore

try:
    from src.integrations.brightdata_client import BrightDataLinkedInClient
except ImportError:
    BrightDataLinkedInClient = None  # type: ignore

# ── Global semaphore for Leadmagic API calls ──────────────────────────────────
# Added to global pool alongside GLOBAL_SEM_SONNET / GLOBAL_SEM_HAIKU
GLOBAL_SEM_LEADMAGIC = asyncio.Semaphore(10)

# Email regex — matches standard email formats
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Pattern templates: (format_name, template)
# {f} = first name, {l} = last name, {fi} = first initial, {li} = last initial
_PATTERN_TEMPLATES = [
    ("first.last", "{f}.{l}"),
    ("first", "{f}"),
    ("flast", "{fi}{l}"),
    ("firstl", "{f}{li}"),
    ("last", "{l}"),
]

# Cost constants (USD)
COST_LEADMAGIC = 0.015
COST_BRIGHTDATA = 0.00075


@dataclass
class EmailResult:
    """Result from email waterfall discovery."""
    email: str | None
    verified: bool
    source: str  # "website" | "pattern" | "leadmagic" | "brightdata" | "none"
    confidence: str  # "high" | "medium" | "low"
    cost_usd: float

    def to_dict(self) -> dict:
        return {
            "dm_email": self.email,
            "dm_email_verified": self.verified,
            "dm_email_source": self.source,
            "dm_email_confidence": self.confidence,
            "email_cost_usd": self.cost_usd,
        }


# ── Name parsing ──────────────────────────────────────────────────────────────

def _parse_name(dm_name: str) -> tuple[str, str]:
    """Split 'Michael Chen' → ('michael', 'chen'). Handles middle names."""
    parts = dm_name.strip().split()
    if not parts:
        return "", ""
    first = parts[0].lower()
    last = parts[-1].lower() if len(parts) > 1 else ""
    return first, last


def _generate_patterns(first: str, last: str, domain: str) -> list[str]:
    """Generate candidate email patterns from name + domain."""
    if not first or not last or not domain:
        return []
    fi = first[0] if first else ""
    li = last[0] if last else ""
    candidates = []
    for _, template in _PATTERN_TEMPLATES:
        try:
            local = template.format(f=first, l=last, fi=fi, li=li)
            candidates.append(f"{local}@{domain}")
        except KeyError:
            pass
    return candidates


# ── Layer 1: Website HTML scrape ──────────────────────────────────────────────

def _extract_emails_from_html(html: str, domain: str, dm_name: str) -> EmailResult | None:
    """
    Layer 1: Extract emails from cached website HTML.
    Prefers emails that match the DM's name parts.
    """
    if not html:
        return None

    found = _EMAIL_RE.findall(html)
    if not found:
        return None

    # Filter to emails on the same domain (or subdomain)
    _d = domain.lower()
    domain_clean = _d[4:] if _d.startswith("www.") else _d
    domain_emails = [e for e in found if domain_clean in e.lower().split("@")[-1]]
    all_emails = domain_emails or found[:5]  # fallback to any email if no domain match

    if not all_emails:
        return None

    # Score by name match
    first, last = _parse_name(dm_name)
    name_parts = [p for p in [first, last] if len(p) >= 3]
    best = None
    best_score = -1

    for email in all_emails:
        local = email.split("@")[0].lower()
        score = sum(1 for p in name_parts if p in local)
        if score > best_score:
            best_score = score
            best = email

    if best:
        confidence = "high" if best_score >= 2 else ("medium" if best_score == 1 else "low")
        return EmailResult(
            email=best,
            verified=False,  # not SMTP-verified, just found in HTML
            source="website",
            confidence=confidence,
            cost_usd=0.0,
        )
    return None


# ── Layer 2: Pattern generation + MX check ───────────────────────────────────

async def _check_mx(domain: str) -> bool:
    """Check if domain has MX records (accepts mail). Returns False on error."""
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 5.0
        resolver.resolve(domain, "MX")
        return True
    except Exception:
        return False


async def _try_patterns(first: str, last: str, domain: str) -> EmailResult | None:
    """
    Layer 2: Generate patterns + confirm MX record exists.
    Does NOT do SMTP probing — that's Layer 3's job.
    Returns the most likely pattern with medium confidence if MX passes.
    """
    if not first or not last or not domain:
        return None

    has_mx = await _check_mx(domain)
    if not has_mx:
        return None

    candidates = _generate_patterns(first, last, domain)
    if not candidates:
        return None

    # Return first.last@domain as best guess (most common professional pattern)
    best = candidates[0]
    return EmailResult(
        email=best,
        verified=False,
        source="pattern",
        confidence="medium",
        cost_usd=0.0,
    )


# ── Layer 3: Leadmagic email finder ──────────────────────────────────────────

async def _leadmagic_lookup(
    first: str,
    last: str,
    domain: str,
    company_name: str | None = None,
) -> EmailResult | None:
    """
    Layer 3: Leadmagic /email-finder — $0.015/call.
    Returns verified email with confidence score.
    """
    if not first or not last or not domain:
        return None

    async with GLOBAL_SEM_LEADMAGIC:
        try:
            from src.config.settings import settings
            if LeadmagicClient is None:
                return None

            async with LeadmagicClient(api_key=settings.leadmagic_api_key) as client:
                result = await client.find_email(
                    first_name=first.capitalize(),
                    last_name=last.capitalize(),
                    domain=domain,
                    company=company_name,
                )

            if result.found and result.email:
                confidence = (
                    "high" if result.confidence >= 80
                    else "medium" if result.confidence >= 50
                    else "low"
                )
                return EmailResult(
                    email=result.email,
                    verified=True,  # Leadmagic verifies via SMTP
                    source="leadmagic",
                    confidence=confidence,
                    cost_usd=COST_LEADMAGIC,
                )
        except Exception as exc:
            logger.warning("email_waterfall layer3 leadmagic failed domain=%s: %s", domain, exc)
    return None


# ── Layer 4: Bright Data LinkedIn enrichment ─────────────────────────────────

async def _brightdata_lookup(
    dm_linkedin: str | None,
    domain: str,
    company_name: str | None = None,
) -> EmailResult | None:
    """
    Layer 4: Bright Data LinkedIn profile → email ($0.00075/record).
    Only runs if dm_linkedin URL is available.
    """
    if not dm_linkedin:
        return None

    try:
        if BrightDataLinkedInClient is None:
            return None

        client = BrightDataLinkedInClient()
        people = await client.lookup_company_people(
            company_name=company_name or domain,
            linkedin_url=dm_linkedin,
        )

        for person in people or []:
            email = person.get("email") or person.get("email_address")
            if email and "@" in email:
                return EmailResult(
                    email=email,
                    verified=False,  # LinkedIn profile data, not SMTP-verified
                    source="brightdata",
                    confidence="medium",
                    cost_usd=COST_BRIGHTDATA,
                )
    except Exception as exc:
        logger.warning("email_waterfall layer4 brightdata failed domain=%s: %s", domain, exc)
    return None


# ── Main entry point ─────────────────────────────────────────────────────────

async def discover_email(
    domain: str,
    dm_name: str,
    dm_linkedin: str | None = None,
    html: str | None = None,
    company_name: str | None = None,
    skip_layers: list[int] | None = None,
    contact_data: dict | None = None,
) -> EmailResult:
    """
    4-layer email discovery waterfall.

    Short-circuits on first verified/found email. Layers:
      1: Website HTML (free)
      2: Pattern generation + MX check (free)
      3: Leadmagic finder ($0.015)
      4: Bright Data LinkedIn ($0.00075)

    Args:
        domain: Business domain (e.g. "dentist.com.au")
        dm_name: Decision maker full name (e.g. "Michael Chen")
        dm_linkedin: LinkedIn URL if available from DM waterfall
        html: Cached website HTML from scrape stage
        company_name: Company name for API lookup context
        skip_layers: List of layer numbers to skip (e.g. [3,4] to skip paid)

    Returns:
        EmailResult with email, verified flag, source, confidence, cost_usd.
    """
    skip = set(skip_layers or [])
    # Strip www. prefix so patterns like first.last@www.domain.com.au don't occur
    domain = domain[4:] if domain.startswith("www.") else domain
    first, last = _parse_name(dm_name)

    # Layer 0: contact registry — check company_email from HTML scrape (free)
    if contact_data and (contact_data.get("company_email") or contact_data.get("email")):
        email_val = contact_data.get("company_email") or contact_data.get("email")
        return EmailResult(
            email=email_val,
            verified=False,
            source="contact_registry",
            confidence="low",  # company email, not DM-specific
            cost_usd=0.0,
        )

    # Layer 1: Website HTML
    if 1 not in skip:
        result = _extract_emails_from_html(html or "", domain, dm_name)
        if result and result.email:
            logger.info("email_waterfall L1 hit domain=%s email=%s", domain, result.email)
            return result

    # Layer 2: Pattern + MX
    if 2 not in skip and first and last:
        result = await _try_patterns(first, last, domain)
        if result and result.email:
            logger.info("email_waterfall L2 hit domain=%s email=%s", domain, result.email)
            return result

    # Layer 3: Leadmagic
    if 3 not in skip and first and last:
        result = await _leadmagic_lookup(first, last, domain, company_name)
        if result and result.email:
            logger.info("email_waterfall L3 hit domain=%s email=%s confidence=%s",
                        domain, result.email, result.confidence)
            return result

    # Layer 4: Bright Data
    if 4 not in skip:
        result = await _brightdata_lookup(dm_linkedin, domain, company_name)
        if result and result.email:
            logger.info("email_waterfall L4 hit domain=%s email=%s", domain, result.email)
            return result

    # No email found
    logger.debug("email_waterfall miss domain=%s", domain)
    return EmailResult(
        email=None,
        verified=False,
        source="none",
        confidence="low",
        cost_usd=0.0,
    )
