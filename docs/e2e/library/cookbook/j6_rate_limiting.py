"""
Skill: J6.4 — Rate Limiting (LinkedIn Safety)
Journey: J6 - LinkedIn Outreach
Checks: 5

Purpose: Verify daily rate limits are enforced to protect LinkedIn accounts.

Note: Unipile recommends 80-100 connection requests/day vs HeyReach's 17/day limit.
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
# RATE LIMITING CONSTANTS
# =============================================================================

LINKEDIN_RATE_LIMITS = {
    "connection_requests_per_day": 80,  # Unipile recommended (conservative)
    "messages_per_day": 100,
    "profile_views_per_day": 150,
    "max_connection_requests_per_day": 100,  # Absolute max
}

RATE_LIMIT_KEYS = {
    "connection": "linkedin:connections:{account_id}:{date}",
    "message": "linkedin:messages:{account_id}:{date}",
    "profile_view": "linkedin:views:{account_id}:{date}",
}

REDIS_CONFIG = {
    "ttl_seconds": 86400,  # 24 hours
    "key_prefix": "linkedin:",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J6.4.1",
        "part_a": "Read `LINKEDIN_DAILY_LIMIT` or `DAILY_CONNECTION_LIMIT` constant",
        "part_b": "Verify limit is 80 (Unipile default)",
        "key_files": ["src/engines/linkedin.py", "src/integrations/unipile.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Daily connection limit constant exists and is set to 80",
            "expect": {
                "code_contains": ["DAILY_CONNECTION_LIMIT", "80"]
            }
        }
    },
    {
        "id": "J6.4.2",
        "part_a": "Verify rate limit check before API call",
        "part_b": "Check linkedin.py send method",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Rate limit checked before sending to Unipile",
            "expect": {
                "code_contains": ["rate_limit", "check", "ResourceRateLimitError"]
            }
        }
    },
    {
        "id": "J6.4.3",
        "part_a": "Verify limit keyed by `account_id` (not global)",
        "part_b": "Check rate limit key pattern",
        "key_files": ["src/engines/linkedin.py", "src/integrations/redis.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Rate limit is per-account, not global",
            "expect": {
                "code_contains": ["account_id", "rate_limit"]
            }
        }
    },
    {
        "id": "J6.4.4",
        "part_a": "Verify Redis used for rate limit tracking",
        "part_b": "Check redis.py rate limiter",
        "key_files": ["src/integrations/redis.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Redis rate limiter with increment and check methods",
            "expect": {
                "code_contains": ["incr", "expire", "get", "rate_limit"]
            }
        }
    },
    {
        "id": "J6.4.5",
        "part_a": "Test hitting rate limit",
        "part_b": "Send actions until limit reached, verify rejection",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Get current rate limit status via API",
                "2. If under limit, observe remaining count",
                "3. When at limit, verify ResourceRateLimitError returned",
                "4. Verify error message includes reset time"
            ],
            "expect": {
                "over_limit_rejected": True,
                "error_type": "ResourceRateLimitError"
            },
            "warning": "Do not actually exhaust the limit in production"
        }
    }
]

PASS_CRITERIA = [
    "Daily limit is 80 connection requests per account (Unipile default)",
    "Redis tracks counts per account with 24-hour TTL",
    "Rate limit checked BEFORE Unipile API call",
    "Clear error returned when limit exceeded"
]

KEY_FILES = [
    "src/engines/linkedin.py",
    "src/integrations/redis.py",
    "src/integrations/unipile.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### LinkedIn Rate Limits (Unipile)")
    for key, value in LINKEDIN_RATE_LIMITS.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Rate Limit Redis Keys")
    for key, pattern in RATE_LIMIT_KEYS.items():
        lines.append(f"  {key}: {pattern}")
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
            if lt.get("warning"):
                lines.append(f"  Warning: {lt['warning']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
