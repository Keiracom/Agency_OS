"""
Skill: J3.4 - Rate Limiting
Journey: J3 - Email Outreach
Checks: 5

Purpose: Verify 50/day/domain limit is enforced (Rule 17).
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
}

# =============================================================================
# RATE LIMITING CONSTANTS
# =============================================================================

RATE_LIMITS = {
    "email_daily_per_domain": 50,
    "redis_key_prefix": "email_rate_limit",
    "ttl_seconds": 86400,  # 24 hours
    "rule_reference": "Rule 17 - 50/day/domain limit",
}

REDIS_CONFIG = {
    "key_pattern": "email_rate_limit:{domain}:{date}",
    "increment_on_send": True,
    "check_before_send": True,
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J3.4.1",
        "part_a": "Read `EMAIL_DAILY_LIMIT_PER_DOMAIN` constant - verify value is 50",
        "part_b": "Verify constant in email.py line 53",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "code_verify",
            "check": "EMAIL_DAILY_LIMIT_PER_DOMAIN constant equals 50",
            "expect": {
                "code_contains": ["EMAIL_DAILY_LIMIT_PER_DOMAIN", "50"]
            }
        }
    },
    {
        "id": "J3.4.2",
        "part_a": "Verify `rate_limiter.check_and_increment` call in email send flow",
        "part_b": "Check email.py lines 158-171 for rate limit check",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Rate limiter check called before sending email",
            "expect": {
                "code_contains": ["rate_limiter", "check", "domain", "limit"]
            }
        }
    },
    {
        "id": "J3.4.3",
        "part_a": "Verify domain extraction logic from from_email address",
        "part_b": "Test with various email formats (user@domain.com, etc.)",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Domain extracted correctly from email address",
            "expect": {
                "code_contains": ["@", "split", "domain", "from_email"]
            },
            "manual_steps": [
                "1. Check email.py for domain extraction logic",
                "2. Verify it handles: user@domain.com -> domain.com",
                "3. Verify it handles: Name <user@domain.com> -> domain.com",
                "4. Verify edge cases like subdomains"
            ]
        }
    },
    {
        "id": "J3.4.4",
        "part_a": "Verify Redis is used for rate limiting via redis.py",
        "part_b": "Check Redis keys after sending test email",
        "key_files": ["src/integrations/redis.py", "src/engines/email.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/rate-limits",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["limits", "current_usage"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/rate-limits' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. Send test email via API",
                "2. Check Redis for rate limit key",
                "3. Key format: email_rate_limit:{domain}:{date}",
                "4. Verify counter incremented"
            ]
        }
    },
    {
        "id": "J3.4.5",
        "part_a": "Verify ResourceRateLimitError raised when limit exceeded",
        "part_b": "Attempt to send 51st email, verify it is blocked with correct error",
        "key_files": ["src/engines/email.py", "src/exceptions.py"],
        "live_test": {
            "type": "code_verify",
            "check": "ResourceRateLimitError exception exists and is raised when limit exceeded",
            "expect": {
                "code_contains": ["ResourceRateLimitError", "raise", "limit", "exceeded"]
            },
            "manual_steps": [
                "1. Check src/exceptions.py for ResourceRateLimitError class",
                "2. Check email.py for where this exception is raised",
                "3. Verify error message includes domain and limit info",
                "4. Test by temporarily lowering limit and sending emails"
            ],
            "note": "Do NOT actually send 51 emails - verify code path exists"
        }
    }
]

PASS_CRITERIA = [
    "Limit is 50/day/domain",
    "Redis tracks counts correctly",
    "51st email blocked with ResourceRateLimitError",
    "Remaining quota returned in response",
    "Domain extracted correctly from email address"
]

KEY_FILES = [
    "src/engines/email.py",
    "src/integrations/redis.py",
    "src/exceptions.py"
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
    lines.append(f"- API URL: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend URL: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase URL: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect URL: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Rate Limiting Configuration")
    lines.append(f"  Daily Limit Per Domain: {RATE_LIMITS['email_daily_per_domain']}")
    lines.append(f"  Redis Key Prefix: {RATE_LIMITS['redis_key_prefix']}")
    lines.append(f"  TTL: {RATE_LIMITS['ttl_seconds']} seconds (24 hours)")
    lines.append(f"  Rule: {RATE_LIMITS['rule_reference']}")
    lines.append("")
    lines.append("### Redis Key Pattern")
    lines.append(f"  {REDIS_CONFIG['key_pattern']}")
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
            if lt.get("note"):
                lines.append(f"  Note: {lt['note']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
