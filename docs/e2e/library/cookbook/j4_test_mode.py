"""
Skill: J4.1 — TEST_MODE Verification
Journey: J4 - SMS Outreach
Checks: 4

Purpose: Ensure TEST_MODE redirects all SMS to test recipient.
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

SMS_TEST_CONFIG = {
    "test_sms_recipient": "+61457543392",
    "test_mode_env_var": "TEST_MODE",
    "test_sms_recipient_env_var": "TEST_SMS_RECIPIENT",
    "expected_log_prefix": "[TEST_MODE]"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J4.1.1",
        "part_a": "Read `src/config/settings.py` — verify `TEST_SMS_RECIPIENT` setting exists",
        "part_b": "Check Railway env var for TEST_SMS_RECIPIENT",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "TEST_SMS_RECIPIENT setting exists in settings.py",
            "expect": {
                "code_contains": ["TEST_SMS_RECIPIENT", "TEST_MODE"]
            },
            "curl_command": """# Check Railway env vars via CLI:
railway variables --service agency-os --kv | grep -E "(TEST_MODE|TEST_SMS_RECIPIENT)\""""
        }
    },
    {
        "id": "J4.1.2",
        "part_a": "Read `src/engines/sms.py` lines 137-141 — verify redirect logic",
        "part_b": "N/A",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Redirect logic swaps phone number when TEST_MODE=true",
            "expect": {
                "code_contains": ["TEST_MODE", "TEST_SMS_RECIPIENT", "redirect"],
                "logic": "if TEST_MODE: phone = TEST_SMS_RECIPIENT"
            }
        }
    },
    {
        "id": "J4.1.3",
        "part_a": "Verify redirect happens BEFORE send (not after)",
        "part_b": "Trigger send, check logs for redirect message",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/sms/send",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "message": "Test SMS redirect verification"
            },
            "expect": {
                "status": 200,
                "body_has_field": "success",
                "logs_contain": "[TEST_MODE] Redirecting SMS"
            },
            "warning": "Sends real SMS to test number - costs apply",
            "curl_command": """curl -X POST '{api_url}/api/v1/sms/send' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{test_lead_id}", "message": "Test redirect"}'"""
        }
    },
    {
        "id": "J4.1.4",
        "part_a": "Verify original phone preserved in logs/activity",
        "part_b": "Check activity record for original_phone field",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, lead_id, action, metadata->>'original_phone' as original_phone,
                       metadata->>'actual_recipient' as actual_recipient
                FROM activity
                WHERE action = 'sms_sent'
                  AND metadata->>'test_mode' = 'true'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "has_rows": True,
                "required_fields": ["original_phone", "actual_recipient"]
            }
        }
    }
]

PASS_CRITERIA = [
    "TEST_MODE setting exists in settings.py",
    "TEST_SMS_RECIPIENT configured (+61457543392)",
    "Redirect happens before send",
    "Original phone logged for reference"
]

KEY_FILES = [
    "src/config/settings.py",
    "src/engines/sms.py"
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
    lines.append("### SMS Test Configuration")
    for key, value in SMS_TEST_CONFIG.items():
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
            if lt.get("url"):
                lines.append(f"  URL: {lt['url']}")
            if lt.get("warning"):
                lines.append(f"  Warning: {lt['warning']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
