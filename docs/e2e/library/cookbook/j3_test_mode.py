"""
Skill: J3.1 - TEST_MODE Verification
Journey: J3 - Email Outreach
Checks: 4

Purpose: Ensure TEST_MODE redirects all emails to test recipient.
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
# EMAIL OUTREACH CONSTANTS
# =============================================================================

EMAIL_LIMITS = {
    "daily_per_domain": 50,
    "max_batch_size": 10,
    "rate_limit_window_hours": 24,
}

TEST_MODE_CONFIG = {
    "env_var": "TEST_MODE",
    "expected_value": "true",
    "recipient_env_var": "TEST_EMAIL_RECIPIENT",
    "default_test_recipient": "david.stephens@keiracom.com",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J3.1.1",
        "part_a": "Read `src/config/settings.py` - verify `TEST_MODE` and `TEST_EMAIL_RECIPIENT` settings exist",
        "part_b": "Check Railway env var TEST_MODE is set to true",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Settings class contains TEST_MODE and TEST_EMAIL_RECIPIENT fields",
            "expect": {
                "code_contains": ["TEST_MODE", "TEST_EMAIL_RECIPIENT", "bool", "str"]
            },
            "manual_steps": [
                "1. Run: railway variables --service agency-os --kv | grep TEST_MODE",
                "2. Verify TEST_MODE=true",
                "3. Run: railway variables --service agency-os --kv | grep TEST_EMAIL_RECIPIENT",
                "4. Verify recipient email is set"
            ]
        }
    },
    {
        "id": "J3.1.2",
        "part_a": "Read `src/engines/email.py` lines 143-147 - verify redirect logic implementation",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Email engine redirects to test recipient when TEST_MODE is enabled",
            "expect": {
                "code_contains": ["TEST_MODE", "TEST_EMAIL_RECIPIENT", "original_email", "redirect"]
            }
        }
    },
    {
        "id": "J3.1.3",
        "part_a": "Verify redirect happens BEFORE send (not after) in email engine flow",
        "part_b": "Trigger send via Prefect flow, check logs for redirect message",
        "key_files": ["src/engines/email.py", "src/orchestration/flows/outreach_flow.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/outreach/send-test-email",
            "auth": True,
            "body": {
                "to_email": "fake@example.com",
                "subject": "TEST_MODE Verification",
                "body": "This should redirect to test recipient"
            },
            "expect": {
                "status": [200, 202],
                "logs_contain": ["TEST_MODE", "redirect", "original_email"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/outreach/send-test-email' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{\"to_email\": \"fake@example.com\", \"subject\": \"TEST_MODE Check\", \"body\": \"Test\"}'"""
        }
    },
    {
        "id": "J3.1.4",
        "part_a": "Verify original email preserved in logs/activity record metadata",
        "part_b": "Check activity record for original_email field after test send",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, channel, metadata->>'original_email' as original_email,
                       metadata->>'test_mode' as test_mode, created_at
                FROM activities
                WHERE channel = 'email' AND metadata->>'test_mode' = 'true'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "rows_exist": True,
                "original_email_preserved": True,
                "test_mode_flagged": True
            }
        }
    }
]

PASS_CRITERIA = [
    "TEST_MODE setting exists and is `true` in Railway",
    "TEST_EMAIL_RECIPIENT configured correctly",
    "Redirect happens before send (not after)",
    "Original email logged for reference"
]

KEY_FILES = [
    "src/config/settings.py",
    "src/engines/email.py",
    "src/orchestration/flows/outreach_flow.py"
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
    lines.append("### TEST_MODE Settings")
    lines.append(f"  Environment Variable: {TEST_MODE_CONFIG['env_var']}")
    lines.append(f"  Expected Value: {TEST_MODE_CONFIG['expected_value']}")
    lines.append(f"  Test Recipient: {TEST_MODE_CONFIG['default_test_recipient']}")
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
                lines.append(f"  Curl: {lt['curl_command'][:60]}...")
            if lt.get("manual_steps"):
                lines.append("  Manual Steps:")
                for step in lt["manual_steps"][:3]:
                    lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
