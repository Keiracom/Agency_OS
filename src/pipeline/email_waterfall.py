"""
Contract: src/pipeline/email_waterfall.py
Purpose: 4-layer email discovery waterfall for pipeline v7.
         Runs after DM identification. Finds and verifies deliverable email
         addresses for decision makers before reachability scoring.
Layer: 3 - pipeline
Directive: #299, #300-FIX-4

Waterfall layers (short-circuit — returns on first hit):
  Layer 0: Contact registry (free) — company_email from contact_data, unverified
  Layer 1: Website HTML scrape (free) — mailto: links, email regex on cached HTML, unverified
  Layer 2: Leadmagic email finder ($0.015 USD) — API lookup by name + domain, verified
  Layer 3: Bright Data LinkedIn enrichment ($0.00075 USD) — profile → email, unverified

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
    ("first.last",  "{f}.{l}"),
    ("first",       "{f}"),
    ("flast",       "{fi}{l}"),
    ("firstl",      "{f}{li}"),
    ("f.last",      "{fi}.{l}"),
    ("first_last",  "{f}_{l}"),
    ("last",        "{l}"),
    ("firstlast",   "{f}{l}"),
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

_NAME_PREFIXES = re.compile(
    r"^(Dr\.?\s*|Prof\.?\s*|Mr\.?\s*|Mrs\.?\s*|Ms\.?\s*|Miss\.?\s*|Sir\s+)",
    re.IGNORECASE,
)
_NAME_SUFFIXES = re.compile(
    r"\s*(OAM|AM|AO|PhD|MD|DDS|BDS|MBBS|FRCDS|FRACDS|Esq\.?)$",
    re.IGNORECASE,
)
# Strip LinkedIn noise: everything from " at ", " - ", " | ", " @ ", "of " onwards
_LINKEDIN_NOISE = re.compile(
    r"\s+(?:at|of|for|from|-|–|\|)\s+.+$",
    re.IGNORECASE,
)

_ROLE_WORDS = {
    "owner", "founder", "director", "manager", "principal",
    "partner", "associate", "consultant", "engineer", "head",
    "president", "ceo", "cto", "coo", "cfo",
}


def _parse_name(dm_name: str) -> tuple[str, str]:
    """
    Parse a DM name string into (first, last) for email pattern generation.

    Handles:
    - Prefixes: Dr., Prof., Mr., Mrs., Ms., Miss
    - Suffixes: OAM, AM, AO, PhD, MD, DDS, BDS
    - LinkedIn noise: "Owner at X", "Director - Y", "Founder of Z"
    - Single-word names: returns (name, "")

    Examples:
        "Dr. Harry Marget"                    → ("harry", "marget")
        "Dr. Teresa Sung"                     → ("teresa", "sung")
        "Prof. James Smith OAM"               → ("james", "smith")
        "Sam Carigliano"                      → ("sam", "carigliano")
        "Owner at VC Dental"                  → ("", "")  -- no real name
        "Dr. Harry Marget East Bentleigh..."  → ("harry", "marget")
    """
    if not dm_name:
        return "", ""

    name = dm_name.strip()

    # Strip LinkedIn noise first (e.g. "James Smith at Dental Co" → "James Smith")
    name = _LINKEDIN_NOISE.sub("", name).strip()

    # Strip title prefixes
    name = _NAME_PREFIXES.sub("", name).strip()

    # Strip honorific suffixes
    name = _NAME_SUFFIXES.sub("", name).strip()

    parts = name.split()
    if not parts:
        return "", ""

    # If first word is a known role word and no other distinguishing words, skip
    if len(parts) <= 2 and parts[0].lower() in _ROLE_WORDS:
        return "", ""

    first = parts[0].lower()
    last = parts[-1].lower() if len(parts) > 1 else ""

    # Sanity: reject if first or last look like non-names (numbers, single chars)
    if len(first) < 2:
        first = ""
    if len(last) < 2:
        last = ""

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
    contact_data: dict | None = None,
    skip_layers: list[int] | None = None,
) -> EmailResult:
    """
    Email discovery waterfall.
    Layers 0-1 return unverified emails.
    Layer 2 (Leadmagic) returns verified.
    Layer 3 (Bright Data) returns unverified.

    Args:
        domain: Business domain (e.g. "dentist.com.au")
        dm_name: Decision maker full name (e.g. "Michael Chen")
        dm_linkedin: LinkedIn URL if available from DM waterfall
        html: Cached website HTML from scrape stage
        company_name: Company name for API lookup context
        contact_data: Pre-scraped contact data dict (may contain company_email)
        skip_layers: List of layer numbers to skip (e.g. [2,3] to skip paid)

    Returns:
        EmailResult with email, verified flag, source, confidence, cost_usd.
    """
    skip = set(skip_layers or [])

    # Strip www. from domain for all pattern/lookup use
    clean_domain = domain[4:] if domain.startswith("www.") else domain

    first, last = _parse_name(dm_name)

    # Layer 0: contact_data company_email (free, unverified)
    # FIX (#300-FIX-8): name-match gate — only promote to dm_email if the email's
    # local part contains at least one name component from dm_name. If it doesn't
    # match (e.g. gavin.fawkes@ when dm_name is "Seymour Green"), the email is a
    # generic company/staff address and should NOT be returned as the DM's email.
    if 0 not in skip and contact_data:
        email_val = contact_data.get("company_email") or contact_data.get("email")
        if email_val and "@" in email_val:
            local = email_val.split("@")[0].lower()
            name_parts = [p for p in [first, last] if len(p) >= 3]
            name_match = any(p in local for p in name_parts) if name_parts else False
            if name_match:
                logger.info(
                    "email_waterfall L0 contact_registry domain=%s email=%s (name match)",
                    domain, email_val,
                )
                return EmailResult(
                    email=email_val,
                    verified=False,
                    source="contact_registry",
                    confidence="low",
                    cost_usd=0.0,
                )
            else:
                logger.debug(
                    "email_waterfall L0 contact_registry domain=%s email=%s SKIPPED "
                    "(name mismatch: dm=%r local=%r)",
                    domain, email_val, dm_name, local,
                )

    # Layer 1: Website HTML (free, unverified)
    if 1 not in skip:
        result = _extract_emails_from_html(html or "", clean_domain, dm_name)
        if result and result.email:
            logger.info("email_waterfall L1 website domain=%s email=%s", domain, result.email)
            return result

    # Layer 2: Leadmagic find_email (verified — Leadmagic finds real address)
    if 2 not in skip and first and last:
        result = await _leadmagic_lookup(first, last, clean_domain, company_name)
        if result and result.email:
            return result

    # Layer 3: Bright Data (unverified)
    if 3 not in skip:
        result = await _brightdata_lookup(dm_linkedin, clean_domain, company_name)
        if result and result.email:
            return result

    logger.debug("email_waterfall miss domain=%s", domain)
    return EmailResult(
        email=None,
        verified=False,
        source="none",
        confidence="low",
        cost_usd=0.0,
    )
