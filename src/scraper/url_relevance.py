"""
URL relevance classifier for S2 page filtering.

Matches discovered URLs against keyword categories to select
the most valuable pages for Sonnet comprehension.

Categories:
  contact  — contact details, address, phone, email
  about    — about us, our story, company info
  services — services offered, what we do
  team     — team, staff, our people, practitioners

Ratified: 2026-04-13. Pipeline E S2 discover-filter-scrape-comprehend.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse


# Category → URL keyword patterns (matched against path segments)
CATEGORY_PATTERNS: dict[str, list[re.Pattern]] = {
    "contact": [
        re.compile(r"contact", re.I),
        re.compile(r"get-in-touch", re.I),
        re.compile(r"enquir", re.I),
        re.compile(r"find-us", re.I),
        re.compile(r"location", re.I),
    ],
    "about": [
        re.compile(r"about", re.I),
        re.compile(r"our-story", re.I),
        re.compile(r"who-we-are", re.I),
        re.compile(r"company", re.I),
        re.compile(r"our-practice", re.I),
        re.compile(r"our-clinic", re.I),
    ],
    "services": [
        re.compile(r"service", re.I),
        re.compile(r"what-we-do", re.I),
        re.compile(r"treatments", re.I),
        re.compile(r"capabilities", re.I),
        re.compile(r"solutions", re.I),
        re.compile(r"practice-area", re.I),
        re.compile(r"areas-of-law", re.I),
    ],
    "team": [
        re.compile(r"team", re.I),
        re.compile(r"staff", re.I),
        re.compile(r"our-people", re.I),
        re.compile(r"practitioners", re.I),
        re.compile(r"dentist", re.I),
        re.compile(r"our-vet", re.I),
        re.compile(r"our-lawyer", re.I),
        re.compile(r"meet-", re.I),
    ],
}

# Paths to always skip (never relevant)
SKIP_PATTERNS = [
    re.compile(r"\.(jpg|jpeg|png|gif|svg|pdf|css|js|woff|ico|xml)$", re.I),
    re.compile(r"(wp-content|wp-admin|wp-includes|wp-json)", re.I),
    re.compile(r"(cart|checkout|login|signup|register|account)", re.I),
    re.compile(r"(privacy|terms|disclaimer|cookie|sitemap\.xml)", re.I),
    re.compile(r"(tag/|category/|author/|page/\d)", re.I),
    re.compile(r"#", re.I),
]


def classify_url(url: str) -> list[str]:
    """Return list of matching categories for a URL. Empty if no match."""
    path = urlparse(url).path.lower()
    if any(p.search(path) for p in SKIP_PATTERNS):
        return []
    categories = []
    for cat, patterns in CATEGORY_PATTERNS.items():
        if any(p.search(path) for p in patterns):
            categories.append(cat)
    return categories


# Canonical paths to ALWAYS try regardless of discovery (Bug A fix)
CANONICAL_PATHS: dict[str, list[str]] = {
    "contact": ["/contact", "/contact-us"],
    "about": ["/about", "/about-us"],
}


def filter_urls(
    urls: list[str],
    base_domain: str,
    max_per_category: int = 2,
    max_total: int = 5,
) -> dict[str, list[str]]:
    """
    Filter discovered URLs into category buckets.
    Returns dict of category → list of URLs (max_per_category each).
    Total across all categories capped at max_total.
    Homepage (/) always included separately.

    Bug A fix: sort by path length (shorter = more canonical) before filtering.
    Canonical paths (/contact, /about) always included as fallback.
    """
    parsed_base = urlparse(f"https://{base_domain}").netloc.replace("www.", "")
    base_url = f"https://{base_domain}"
    buckets: dict[str, list[str]] = {cat: [] for cat in CATEGORY_PATTERNS}
    total = 0

    # Sort by path length — shorter paths are more likely canonical
    same_domain = []
    for url in urls:
        parsed = urlparse(url)
        url_domain = parsed.netloc.replace("www.", "")
        if url_domain and url_domain != parsed_base:
            continue
        same_domain.append(url)
    same_domain.sort(key=lambda u: len(urlparse(u).path))

    for url in same_domain:
        if total >= max_total:
            break
        cats = classify_url(url)
        for cat in cats:
            if len(buckets[cat]) < max_per_category and total < max_total:
                buckets[cat].append(url)
                total += 1
                break

    # Bug A fix: ensure canonical paths are always in buckets
    for cat, paths in CANONICAL_PATHS.items():
        if not buckets.get(cat) and total < max_total:
            for path in paths:
                canonical = f"{base_url}{path}"
                if canonical not in [u for urls in buckets.values() for u in urls]:
                    buckets.setdefault(cat, []).append(canonical)
                    total += 1
                    break

    return {k: v for k, v in buckets.items() if v}
