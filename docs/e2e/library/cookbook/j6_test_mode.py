"""
Skill: J6.1 — TEST_MODE Verification
Journey: J6 - LinkedIn Outreach
Checks: 4

Purpose: Ensure TEST_MODE redirects all LinkedIn actions to test recipient.
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
# LINKEDIN-SPECIFIC CONSTANTS
# =============================================================================

LINKEDIN_LIMITS = {
    "connection_requests_per_day": 80,  # Unipile recommended limit
    "messages_per_day": 100,  # Unipile recommended limit
    "profile_views_per_day": 150,
    "connection_note_max_chars": 300,
}

UNIPILE_CONFIG = {
    "api_base": "https://api.unipile.com/api/v1",
    "webhook_events": ["message.received", "connection.accepted", "connection.rejected"],
    "auth_flow": "hosted",  # Unipile handles OAuth
}

TEST_MODE_CONFIG = {
    "env_var": "TEST_MODE",
    "recipient_var": "TEST_LINKEDIN_RECIPIENT",
    "default_test_profile": "https://linkedin.com/in/test-recipient",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J6.1.1",
        "part_a": "Read `src/config/settings.py` — verify `TEST_LINKEDIN_RECIPIENT`",
        "part_b": "Check Railway env var",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Settings has TEST_LINKEDIN_RECIPIENT field",
            "expect": {
                "code_contains": ["TEST_LINKEDIN_RECIPIENT", "test_linkedin_recipient"]
            }
        }
    },
    {
        "id": "J6.1.2",
        "part_a": "Read `src/engines/linkedin.py` — verify redirect logic in send method",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "LinkedIn engine redirects to test recipient when TEST_MODE=true",
            "expect": {
                "code_contains": ["TEST_MODE", "test_linkedin_recipient", "settings"]
            }
        }
    },
    {
        "id": "J6.1.3",
        "part_a": "Verify redirect happens BEFORE API call",
        "part_b": "Trigger action, check logs",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/linkedin/test-mode-check",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_field": "test_mode"
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/linkedin/test-mode-check' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J6.1.4",
        "part_a": "Verify original LinkedIn URL preserved in logs",
        "part_b": "Check activity record",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, lead_id, action, metadata
                FROM activity
                WHERE channel = 'linkedin'
                  AND metadata->>'test_mode' = 'true'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "has_field": "metadata",
                "metadata_contains": ["original_recipient", "test_mode"]
            }
        }
    }
]

PASS_CRITERIA = [
    "TEST_MODE setting exists in config",
    "TEST_LINKEDIN_RECIPIENT configured in Railway",
    "Redirect happens before Unipile API call",
    "Original recipient preserved in activity metadata"
]

KEY_FILES = [
    "src/config/settings.py",
    "src/engines/linkedin.py"
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
    lines.append("### LinkedIn Limits (Unipile)")
    for key, value in LINKEDIN_LIMITS.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### TEST_MODE Configuration")
    for key, value in TEST_MODE_CONFIG.items():
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
            if lt.get("curl_command"):
                lines.append(f"  curl: {lt['curl_command'][:50]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
