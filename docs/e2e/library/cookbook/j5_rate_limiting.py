"""
Skill: J5.7 — Rate Limiting
Journey: J5 - Voice Outreach
Checks: 4

Purpose: Verify call rate limits are enforced.
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
    "warning": "Rate limit tests should not hit actual limits in production"
}

# =============================================================================
# VOICE RATE LIMITS
# =============================================================================

VOICE_RATE_LIMITS = {
    "calls_per_day_per_number": 50,
    "concurrent_calls_max": 10,
    "cooldown_between_calls_seconds": 30,
    "retry_after_rate_limit_seconds": 3600,
    "redis_key_pattern": "voice:rate_limit:{phone_number}:{date}",
    "rate_limit_window": "24h"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.7.1",
        "part_a": "Check rate limit constant in voice.py — should be 50/day/number",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Rate limit constant is 50 calls per day per number",
            "expect": {
                "code_contains": ["50", "rate_limit", "RATE_LIMIT", "daily"]
            }
        }
    },
    {
        "id": "J5.7.2",
        "part_a": "Verify rate_limiter.check_and_increment called in send method",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Rate limiter check happens before call",
            "expect": {
                "code_contains": ["check_and_increment", "rate_limit"]
            }
        }
    },
    {
        "id": "J5.7.3",
        "part_a": "Verify Redis used for rate limiting — check redis.py",
        "part_b": "N/A",
        "key_files": ["src/integrations/redis.py", "src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Redis integration used for rate limiting",
            "expect": {
                "code_contains": ["redis", "Redis", "incr", "expire"]
            }
        }
    },
    {
        "id": "J5.7.4",
        "part_a": "N/A",
        "part_b": "Test hitting limit — make 51 calls, verify 51st blocked",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Note: This test should NOT be run in production",
                "2. In test environment, simulate 50 calls",
                "3. Attempt 51st call",
                "4. Verify rate limit error returned",
                "5. Check Redis key for count"
            ],
            "expect": {
                "status_on_51st": 429,
                "error_message_contains": "rate limit"
            },
            "warning": "Do NOT run this test in production - will exhaust daily limit"
        }
    }
]

PASS_CRITERIA = [
    "Rate limit enforced",
    "Redis tracks counts",
    "Excess calls blocked"
]

KEY_FILES = [
    "src/engines/voice.py",
    "src/integrations/redis.py"
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
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### Voice Rate Limits")
    lines.append(f"  Calls/Day/Number: {VOICE_RATE_LIMITS['calls_per_day_per_number']}")
    lines.append(f"  Max Concurrent: {VOICE_RATE_LIMITS['concurrent_calls_max']}")
    lines.append(f"  Cooldown Between Calls: {VOICE_RATE_LIMITS['cooldown_between_calls_seconds']}s")
    lines.append(f"  Redis Key Pattern: {VOICE_RATE_LIMITS['redis_key_pattern']}")
    lines.append(f"  Rate Limit Window: {VOICE_RATE_LIMITS['rate_limit_window']}")
    lines.append("")
    lines.append("### Checks")
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
