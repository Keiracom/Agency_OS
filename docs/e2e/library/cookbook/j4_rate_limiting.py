"""
Skill: J4.5 — Rate Limiting
Journey: J4 - SMS Outreach
Checks: 5

Purpose: Verify 100/day/number limit is enforced (Rule 17).
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
    "test_phone": "+61457543392"
}

# =============================================================================
# SMS DOMAIN CONSTANTS
# =============================================================================

SMS_LIMITS = {
    "daily_per_number": 100,
    "reset_time_utc": "00:00",
    "rate_limit_key_format": "sms_limit:{phone}:{date}",
    "error_class": "ResourceRateLimitError"
}

REDIS_CONFIG = {
    "rate_limiter_key_prefix": "rate_limit:",
    "ttl_seconds": 86400,  # 24 hours
    "upstash_url": "{{UPSTASH_REDIS_URL}}"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J4.5.1",
        "part_a": "Read `SMS_DAILY_LIMIT_PER_NUMBER` constant",
        "part_b": "Verify value = 100",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "code_verify",
            "check": "SMS_DAILY_LIMIT_PER_NUMBER constant equals 100",
            "expect": {
                "code_contains": ["SMS_DAILY_LIMIT_PER_NUMBER = 100", "DAILY_LIMIT = 100"]
            }
        }
    },
    {
        "id": "J4.5.2",
        "part_a": "Verify `rate_limiter.check_and_increment` call",
        "part_b": "Check sms.py rate limit logic",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Rate limiter check_and_increment is called before send",
            "expect": {
                "code_contains": ["rate_limiter", "check_and_increment", "increment"]
            }
        }
    },
    {
        "id": "J4.5.3",
        "part_a": "Verify Redis used for rate limiting",
        "part_b": "Check redis.py rate limiter implementation",
        "key_files": ["src/integrations/redis.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Redis-based rate limiter implementation exists",
            "expect": {
                "code_contains": ["RateLimiter", "redis", "incr", "expire", "ttl"]
            }
        }
    },
    {
        "id": "J4.5.4",
        "part_a": "Verify ResourceRateLimitError raised when limit exceeded",
        "part_b": "Test hitting limit (send 101 SMS, verify 101st blocked)",
        "key_files": ["src/engines/sms.py", "src/exceptions.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/sms/send",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "message": "Rate limit test"
            },
            "note": "To test limit: send 101 messages to same number, verify 101st returns 429",
            "expect": {
                "on_limit_exceeded": {
                    "status": 429,
                    "error_type": "ResourceRateLimitError",
                    "body_contains": "rate limit exceeded"
                }
            },
            "curl_command": """# Send SMS repeatedly to test limit:
for i in {1..101}; do
  curl -X POST '{api_url}/api/v1/sms/send' \\
    -H 'Authorization: Bearer {token}' \\
    -H 'Content-Type: application/json' \\
    -d '{"lead_id": "{test_lead_id}", "message": "Test $i"}'
  echo "Sent $i"
done"""
        }
    },
    {
        "id": "J4.5.5",
        "part_a": "Verify remaining quota returned in response",
        "part_b": "Check EngineResult metadata",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/sms/send",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "message": "Quota check test"
            },
            "expect": {
                "status": 200,
                "body_has_fields": ["remaining_quota", "daily_limit"],
                "response_structure": {
                    "metadata": {
                        "remaining_quota": "integer",
                        "daily_limit": 100
                    }
                }
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/sms/send' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{test_lead_id}", "message": "Test"}' | jq '.metadata'"""
        }
    }
]

PASS_CRITERIA = [
    "Limit is 100/day/number",
    "Redis tracks counts",
    "101st SMS blocked with ResourceRateLimitError",
    "Remaining quota returned in response",
    "Rate limit resets daily"
]

KEY_FILES = [
    "src/engines/sms.py",
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
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### SMS Rate Limits")
    for key, value in SMS_LIMITS.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Redis Configuration")
    for key, value in REDIS_CONFIG.items():
        lines.append(f"  {key}: {value}")
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
            if lt.get("check"):
                lines.append(f"  Check: {lt['check']}")
            if lt.get("note"):
                lines.append(f"  Note: {lt['note']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
