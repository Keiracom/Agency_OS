"""
Skill: J10.13 — Rate Limits Page
Journey: J10 - Admin Dashboard
Checks: 3

Purpose: Verify API rate limit monitoring and display.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "test_admin": {
        "email": "david.stephens@keiracom.com",
        "role": "admin"
    }
}

# =============================================================================
# RATE LIMIT CONSTANTS
# =============================================================================

RATE_LIMITS = [
    {"api": "Apollo", "limit": "10,000/month", "reset": "Monthly", "current_usage_field": "apollo_credits_used"},
    {"api": "Salesforge", "limit": "Based on mailboxes", "reset": "Daily", "current_usage_field": "emails_sent_today"},
    {"api": "Unipile", "limit": "Varies by plan", "reset": "Daily", "current_usage_field": "linkedin_actions_today"},
    {"api": "Anthropic", "limit": "Based on tier", "reset": "Per minute/day", "current_usage_field": "claude_tokens_used"},
    {"api": "Twilio", "limit": "Account dependent", "reset": "Per second", "current_usage_field": "sms_sent_today"}
]

WARNING_THRESHOLDS = {
    "caution": 0.5,   # 50% - show usage
    "warning": 0.8,   # 80% - yellow warning
    "critical": 0.95  # 95% - red alert
}

RATE_LIMIT_ACTIONS = {
    "approaching_limit": "Slow down outreach pace",
    "at_limit": "Pause outreach until reset",
    "over_limit": "Switch to backup provider or wait"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.13.1",
        "part_a": "Read `frontend/app/admin/system/rate-limits/page.tsx` — verify display",
        "part_b": "Load rate limits page, verify data renders",
        "key_files": ["frontend/app/admin/system/rate-limits/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/admin/system/rate-limits",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["Rate Limits", "Usage", "Limit"]
            },
            "manual_steps": [
                "1. Login as admin user",
                "2. Navigate to {frontend_url}/admin/system/rate-limits",
                "3. Verify rate limits page loads",
                "4. Check all API providers are listed"
            ]
        }
    },
    {
        "id": "J10.13.2",
        "part_a": "Verify rate limit status for each API",
        "part_b": "Check Apollo, Salesforge, Unipile limits display",
        "key_files": ["frontend/app/admin/system/rate-limits/page.tsx", "src/api/routes/admin.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/rate-limits",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["api", "limit", "used", "remaining", "reset_at"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/rate-limits' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/system/rate-limits page, review each API row",
                "2. Verify Apollo shows: credits used / total credits",
                "3. Verify Salesforge shows: emails sent today / daily limit",
                "4. Verify Unipile shows: LinkedIn actions / daily limit",
                "5. Check progress bars match usage percentages"
            ]
        }
    },
    {
        "id": "J10.13.3",
        "part_a": "Verify rate limit warnings display",
        "part_b": "Check warning shows when approaching limit (>80%)",
        "key_files": ["frontend/app/admin/system/rate-limits/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. On /admin/system/rate-limits page, identify usage levels",
                "2. For APIs at <50% usage: verify green/normal indicator",
                "3. For APIs at 50-80% usage: verify yellow caution indicator",
                "4. For APIs at 80-95% usage: verify orange warning indicator",
                "5. For APIs at >95% usage: verify red critical indicator",
                "6. Check warning messages display for high usage APIs"
            ],
            "expect": {
                "color_coding_accurate": True,
                "warnings_at_threshold": True,
                "reset_time_shown": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Rate limits page loads correctly",
    "All API rate limits display",
    "Warnings show at threshold"
]

KEY_FILES = [
    "frontend/app/admin/system/rate-limits/page.tsx",
    "src/api/routes/admin.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_frontend_url(path: str) -> str:
    """Get full frontend URL for live testing."""
    base = LIVE_CONFIG["frontend_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append(f"- Rate Limits Page: {LIVE_CONFIG['frontend_url']}/admin/system/rate-limits")
    lines.append("")
    lines.append("### Rate Limits by API")
    for rl in RATE_LIMITS:
        lines.append(f"  - {rl['api']}: {rl['limit']} (reset: {rl['reset']})")
    lines.append("")
    lines.append("### Warning Thresholds")
    for level, threshold in WARNING_THRESHOLDS.items():
        lines.append(f"  - {level}: {threshold*100}%")
    lines.append("")
    lines.append("### Rate Limit Actions")
    for status, action in RATE_LIMIT_ACTIONS.items():
        lines.append(f"  - {status}: {action}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("type"):
            lines.append(f"  Live Test Type: {lt['type']}")
        if lt.get("curl_command"):
            lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
