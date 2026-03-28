"""
Domain Parser Utility — Directive #260

Extracts a human-readable business name from a domain string.
Used by Stage 2 to build GMB search queries from discovered domains.

Examples:
  "acme-marketing.com.au" → "Acme Marketing"
  "www.best-plumbers.net.au" → "Best Plumbers"
  "digitalgrowth.co" → "Digitalgrowth"  (single word, keep as-is)
  "the-local-seo-agency.com" → "The Local Seo Agency"
"""

from __future__ import annotations

import re

# Multi-part TLDs to strip (order matters — longer first)
_MULTI_PART_TLDS = {
    ".com.au",
    ".net.au",
    ".org.au",
    ".edu.au",
    ".gov.au",
    ".co.nz",
    ".net.nz",
    ".org.nz",
    ".co.uk",
    ".org.uk",
    ".me.uk",
}
_SINGLE_TLDS = re.compile(r"\.[a-z]{2,6}$")


def extract_business_name(domain: str) -> str:
    """
    Extract a human-readable business name from a domain string.

    Args:
        domain: Raw domain, e.g. "www.acme-marketing.com.au"

    Returns:
        Title-cased business name, e.g. "Acme Marketing"
    """
    if not domain:
        return ""

    # Lowercase and strip leading protocol/www
    name = domain.lower().strip()
    name = re.sub(r"^https?://", "", name)
    name = re.sub(r"^www\.", "", name)

    # Strip subdomains (keep only second-level domain + TLD for stripping)
    # e.g. "app.acme.com.au" → "acme.com.au"
    # If more than 3 parts (sub.name.com.au = 4), drop leading subdomain(s)
    # We identify the TLD boundary by checking against known multi-part TLDs
    for tld in _MULTI_PART_TLDS:
        if name.endswith(tld):
            # Everything before the TLD is the domain name portion
            name = name[: -len(tld)]
            # If there are still dots, drop the leading subdomain(s)
            if "." in name:
                name = name.split(".")[-1]
            break
    else:
        # Strip single-part TLD
        name = _SINGLE_TLDS.sub("", name)
        # Drop leading subdomain if any
        if "." in name:
            name = name.split(".")[-1]

    # Split on hyphens and dots
    tokens = re.split(r"[-_.]", name)

    # Filter empty tokens
    tokens = [t for t in tokens if t]

    if not tokens:
        return domain  # fallback: return original

    # Title case
    return " ".join(t.title() for t in tokens)
