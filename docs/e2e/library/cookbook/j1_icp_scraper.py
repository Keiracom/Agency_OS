"""
Skill: J1.8 — ICP Scraper Engine (Waterfall)
Journey: J1 - Signup & Onboarding
Checks: 7

Purpose: Verify ICP scraper implements full waterfall architecture.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "test_urls": {
        "static_site": "https://sparro.com.au",
        "js_heavy_site": "https://www.hubspot.com",
        "cloudflare_site": "https://www.cloudflare.com",
        "invalid_url": "not-a-valid-url"
    }
}

# =============================================================================
# WATERFALL TIERS
# =============================================================================

WATERFALL_TIERS = [
    {"tier": 0, "method": "URL Validation", "when": "Always first"},
    {"tier": 1, "method": "Apify Cheerio", "when": "Static HTML sites"},
    {"tier": 2, "method": "Apify Playwright", "when": "JS-rendered sites"},
    {"tier": 3, "method": "Camoufox", "when": "Cloudflare (future)"},
    {"tier": 4, "method": "Manual Fallback", "when": "When tiers 1-3 fail"},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.8.1",
        "part_a": "Read `src/engines/icp_scraper.py` — verify waterfall tiers",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/engines/icp_scraper.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Waterfall logic with tier fallbacks exists",
            "expect": {
                "code_contains": ["waterfall", "tier", "fallback", "cheerio", "playwright"]
            }
        }
    },
    {
        "id": "J1.8.2",
        "part_a": "Verify Tier 0: URL validation via `url_validator.validate_and_normalize()`",
        "part_b": "Submit invalid URL, verify error",
        "key_files": ["src/engines/url_validator.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/onboarding/analyze",
            "auth": True,
            "body": {"website_url": "not-a-valid-url"},
            "expect": {
                "status": 422,
                "body_contains": ["invalid", "URL"]
            },
            "curl_command": """curl -X POST 'https://agency-os-production.up.railway.app/api/v1/onboarding/analyze' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"website_url": "not-a-valid-url"}'"""
        }
    },
    {
        "id": "J1.8.3",
        "part_a": "Verify Tier 1: Apify Cheerio via `scrape_website_with_waterfall()`",
        "part_b": "Submit static site URL",
        "key_files": ["src/engines/icp_scraper.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/onboarding/analyze",
            "auth": True,
            "body": {"website_url": "https://sparro.com.au"},
            "expect": {
                "status": 202,
                "body_has_field": "job_id"
            },
            "verify_logs": "Check Prefect logs for 'Cheerio scraper succeeded'"
        }
    },
    {
        "id": "J1.8.4",
        "part_a": "Verify Tier 2: Apify Playwright fallback",
        "part_b": "Submit JS-heavy site URL",
        "key_files": ["src/engines/icp_scraper.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Submit JS-heavy site: https://www.hubspot.com",
                "2. Check Prefect logs",
                "3. Verify 'Cheerio failed, trying Playwright' in logs",
                "4. Verify extraction completes via Playwright"
            ],
            "expect": {
                "tier_used": 2,
                "log_contains": "Playwright"
            },
            "note": "May require APIFY_TOKEN with credits"
        }
    },
    {
        "id": "J1.8.5",
        "part_a": "Verify `needs_fallback=True` generates manual fallback URL",
        "part_b": "Submit Cloudflare-protected site",
        "key_files": ["src/engines/icp_scraper.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Submit Cloudflare-protected site",
                "2. Wait for extraction to fail tiers 1-2",
                "3. Check job result for 'needs_manual_entry' flag",
                "4. Verify redirect URL to /onboarding/manual-entry"
            ],
            "expect": {
                "needs_manual_entry": True
            }
        }
    },
    {
        "id": "J1.8.6",
        "part_a": "Verify portfolio page direct fetch via `_fetch_portfolio_pages()`",
        "part_b": "Check for /portfolio, /case-studies",
        "key_files": ["src/engines/icp_scraper.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Function attempts to fetch common portfolio paths",
            "expect": {
                "code_contains": ["portfolio", "case-studies", "work", "clients"]
            }
        }
    },
    {
        "id": "J1.8.7",
        "part_a": "Verify social links extraction via `_extract_social_links()`",
        "part_b": "Check scraped data includes social URLs",
        "key_files": ["src/engines/icp_scraper.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Complete extraction for https://sparro.com.au",
                "2. Check extracted data in icp_extraction_jobs table",
                "3. Verify social_links field populated"
            ],
            "expect": {
                "has_social_links": True,
                "social_platforms": ["linkedin", "twitter", "facebook"]
            }
        }
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

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Waterfall Tiers", ""]
    for tier in WATERFALL_TIERS:
        lines.append(f"  Tier {tier['tier']}: {tier['method']} — {tier['when']}")
    lines.append("")
    lines.append("### Test URLs")
    for name, url in LIVE_CONFIG['test_urls'].items():
        lines.append(f"  {name}: {url}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
