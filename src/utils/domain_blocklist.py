"""
Domain blocklist for S1 discovery pipeline.
Domains in this set are never inserted into business_universe.
Directive #267
"""

from __future__ import annotations

BLOCKED_DOMAINS: frozenset[str] = frozenset(
    {
        # Social platforms
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "tiktok.com",
        "pinterest.com",
        "snapchat.com",
        "reddit.com",
        "youtube.com",
        "linkedin.com",
        "threads.net",
        # Search / tech giants
        "google.com",
        "google.com.au",
        "bing.com",
        "yahoo.com",
        "apple.com",
        "microsoft.com",
        "amazon.com",
        "amazon.com.au",
        # Website builders / platforms
        "wordpress.com",
        "wix.com",
        "squarespace.com",
        "shopify.com",
        "webflow.com",
        "weebly.com",
        "blogger.com",
        # Hosting / infra
        "godaddy.com",
        "cloudflare.com",
        "github.com",
        "gitlab.com",
        "stackoverflow.com",
        "medium.com",
        # Government / non-business
        "gov.au",
        "nsw.gov.au",
        "vic.gov.au",
        "qld.gov.au",
        "sa.gov.au",
        "wa.gov.au",
        "tas.gov.au",
        "act.gov.au",
        "nt.gov.au",
        "health.gov.au",
    }
)


def is_blocked(domain: str | None) -> bool:
    """Return True if domain should be excluded from business_universe."""
    if not domain:
        return True
    d = domain.lower().strip()
    if not d:
        return True
    # Exact match
    if d in BLOCKED_DOMAINS:
        return True
    # Subdomain of blocked domain (e.g. rfs.nsw.gov.au)
    return any(d.endswith("." + blocked) for blocked in BLOCKED_DOMAINS)
