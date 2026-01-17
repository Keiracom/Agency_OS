"""
Skill: J1.8 — ICP Scraper Engine (Waterfall)
Journey: J1 - Signup & Onboarding
Checks: 7

Purpose: Verify ICP scraper implements full waterfall architecture.
"""

CHECKS = [
    {
        "id": "J1.8.1",
        "part_a": "Read `src/engines/icp_scraper.py` — verify waterfall tiers",
        "part_b": "N/A",
        "key_files": ["src/engines/icp_scraper.py"]
    },
    {
        "id": "J1.8.2",
        "part_a": "Verify Tier 0: URL validation via `url_validator.validate_and_normalize()`",
        "part_b": "Submit invalid URL, verify error",
        "key_files": ["src/engines/url_validator.py"]
    },
    {
        "id": "J1.8.3",
        "part_a": "Verify Tier 1: Apify Cheerio via `scrape_website_with_waterfall()`",
        "part_b": "Submit static site URL",
        "key_files": ["src/engines/icp_scraper.py"]
    },
    {
        "id": "J1.8.4",
        "part_a": "Verify Tier 2: Apify Playwright fallback",
        "part_b": "Submit JS-heavy site URL",
        "key_files": ["src/engines/icp_scraper.py"]
    },
    {
        "id": "J1.8.5",
        "part_a": "Verify `needs_fallback=True` generates manual fallback URL",
        "part_b": "Submit Cloudflare-protected site",
        "key_files": ["src/engines/icp_scraper.py"]
    },
    {
        "id": "J1.8.6",
        "part_a": "Verify portfolio page direct fetch via `_fetch_portfolio_pages()`",
        "part_b": "Check for /portfolio, /case-studies",
        "key_files": ["src/engines/icp_scraper.py"]
    },
    {
        "id": "J1.8.7",
        "part_a": "Verify social links extraction via `_extract_social_links()`",
        "part_b": "Check scraped data includes social URLs",
        "key_files": ["src/engines/icp_scraper.py"]
    }
]

PASS_CRITERIA = [
    "URL validation rejects invalid URLs",
    "Cheerio scrapes static sites",
    "Playwright handles JS sites",
    "Manual fallback URL generated on failure",
    "Social links extracted"
]

KEY_FILES = [
    "src/engines/icp_scraper.py",
    "src/engines/url_validator.py",
    "src/integrations/apify.py"
]

# Waterfall Tiers Reference
WATERFALL_TIERS = [
    {"tier": 0, "method": "URL Validation", "when": "Always first"},
    {"tier": 1, "method": "Apify Cheerio", "when": "Static HTML sites"},
    {"tier": 2, "method": "Apify Playwright", "when": "JS-rendered sites"},
    {"tier": 3, "method": "Camoufox", "when": "Cloudflare (future)"},
    {"tier": 4, "method": "Manual Fallback", "when": "When tiers 1-3 fail"},
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
