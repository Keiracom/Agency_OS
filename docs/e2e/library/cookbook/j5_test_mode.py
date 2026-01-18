"""
Skill: J5.1 — TEST_MODE Verification
Journey: J5 - Voice Outreach
Checks: 4

Purpose: Ensure TEST_MODE redirects all voice calls to test recipient.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "test_voice_recipient": "+61457543392",  # CEO test phone
    "client_id": "81dbaee6-4e71-48ad-be40-fa915fae66e0",
    "user_id": "a60bcdbd-4a31-43e7-bcc8-3ab998c44ac2",
    "test_email": "david.stephens@keiracom.com",
    "test_phone": "+61457543392",
    "warning": "Voice calls cost money - ensure TEST_MODE=true before testing"
}

# =============================================================================
# VOICE TEST MODE CONSTANTS
# =============================================================================

VOICE_TEST_MODE = {
    "env_var": "TEST_MODE",
    "recipient_env_var": "TEST_VOICE_RECIPIENT",
    "expected_behavior": "All calls redirect to TEST_VOICE_RECIPIENT when TEST_MODE=true",
    "original_phone_logging": "Original phone number preserved in activity metadata"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.1.1",
        "part_a": "Read `src/config/settings.py` — verify `TEST_VOICE_RECIPIENT` exists",
        "part_b": "Check Railway env var for TEST_VOICE_RECIPIENT",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Settings has TEST_VOICE_RECIPIENT field",
            "expect": {
                "code_contains": ["TEST_VOICE_RECIPIENT", "TEST_MODE"]
            }
        }
    },
    {
        "id": "J5.1.2",
        "part_a": "Read `src/engines/voice.py` lines 173-177 — verify redirect logic",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Voice engine redirects to test recipient when TEST_MODE=true",
            "expect": {
                "code_contains": ["TEST_MODE", "TEST_VOICE_RECIPIENT", "redirect"]
            }
        }
    },
    {
        "id": "J5.1.3",
        "part_a": "Verify redirect happens BEFORE call initiation",
        "part_b": "Trigger call, check logs for redirect message",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/voice/test-call",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "campaign_id": "{test_campaign_id}"
            },
            "expect": {
                "status": 200,
                "body_has_field": "redirected_to",
                "redirected_to_matches": "+61457543392"
            },
            "warning": "Initiates actual call - CEO approval required",
            "curl_command": """curl -X POST '{api_url}/api/v1/voice/test-call' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{lead_id}", "campaign_id": "{campaign_id}"}'"""
        }
    },
    {
        "id": "J5.1.4",
        "part_a": "Verify original phone preserved in logs/activity",
        "part_b": "Check activity record for original phone number",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, channel, metadata->>'original_phone' as original_phone,
                       metadata->>'redirected_to' as redirected_to
                FROM activity
                WHERE channel = 'voice'
                ORDER BY created_at DESC
                LIMIT 1;
            """,
            "expect": {
                "required_fields": ["original_phone", "redirected_to"],
                "redirected_to_equals": "+61457543392"
            }
        }
    }
]

PASS_CRITERIA = [
    "TEST_MODE setting exists",
    "TEST_VOICE_RECIPIENT configured",
    "Redirect happens before call",
    "Original phone logged for reference"
]

KEY_FILES = [
    "src/config/settings.py",
    "src/engines/voice.py"
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
    lines.append(f"- Test Voice Recipient: {LIVE_CONFIG['test_voice_recipient']}")
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### Voice Test Mode")
    for key, value in VOICE_TEST_MODE.items():
        lines.append(f"  {key}: {value}")
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
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
