"""
Skill: J6.5 — LinkedIn URL Validation
Journey: J6 - LinkedIn Outreach
Checks: 3

Purpose: Verify LinkedIn URLs are validated before actions.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "client_id": "81dbaee6-4e71-48ad-be40-fa915fae66e0",
    "user_id": "a60bcdbd-4a31-43e7-bcc8-3ab998c44ac2",
    "test_email": "david.stephens@keiracom.com",
    "test_phone": "+61457543392",
}

# =============================================================================
# URL VALIDATION CONSTANTS
# =============================================================================

LINKEDIN_URL_PATTERNS = {
    "profile": r"https?://(www\.)?linkedin\.com/in/[\w\-]+/?",
    "company": r"https?://(www\.)?linkedin\.com/company/[\w\-]+/?",
    "sales_nav": r"https?://(www\.)?linkedin\.com/sales/lead/[\w\-,]+",
}

VALID_LINKEDIN_DOMAINS = [
    "linkedin.com",
    "www.linkedin.com",
]

URL_VALIDATION_ERRORS = {
    "missing": "LinkedIn URL is required for LinkedIn outreach",
    "invalid_format": "Invalid LinkedIn URL format",
    "not_profile": "URL must be a LinkedIn profile (linkedin.com/in/*)",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J6.5.1",
        "part_a": "Verify lead linkedin_url check in send method",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "LinkedIn URL validation before API call",
            "expect": {
                "code_contains": ["linkedin_url", "if not", "ValidationError"]
            }
        }
    },
    {
        "id": "J6.5.2",
        "part_a": "Verify URL format expected (linkedin.com/in/*)",
        "part_b": "Check regex or validation logic",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "URL validated against linkedin.com/in/ pattern",
            "expect": {
                "code_contains": ["linkedin.com", "/in/"]
            }
        }
    },
    {
        "id": "J6.5.3",
        "part_a": "Test missing LinkedIn URL",
        "part_b": "Verify error returned",
        "key_files": [],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/linkedin/send",
            "auth": True,
            "body": {
                "lead_id": "test-lead-no-linkedin",
                "action": "connection",
                "note": "Test connection request"
            },
            "expect": {
                "status": 400,
                "error_contains": "linkedin_url"
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/linkedin/send' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "test-lead-no-linkedin", "action": "connection"}'"""
        }
    }
]

PASS_CRITERIA = [
    "Missing LinkedIn URL rejected with clear error",
    "Invalid URL format rejected",
    "Only linkedin.com/in/* profiles accepted for outreach"
]

KEY_FILES = [
    "src/engines/linkedin.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def validate_linkedin_url(url: str) -> bool:
    """Check if URL is a valid LinkedIn profile URL."""
    import re
    pattern = LINKEDIN_URL_PATTERNS["profile"]
    return bool(re.match(pattern, url))

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### LinkedIn URL Patterns")
    for key, pattern in LINKEDIN_URL_PATTERNS.items():
        lines.append(f"  {key}: {pattern}")
    lines.append("")
    lines.append("### Validation Errors")
    for key, message in URL_VALIDATION_ERRORS.items():
        lines.append(f"  {key}: {message}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
            if lt.get("url"):
                lines.append(f"  URL: {lt['url']}")
            if lt.get("curl_command"):
                lines.append(f"  curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
