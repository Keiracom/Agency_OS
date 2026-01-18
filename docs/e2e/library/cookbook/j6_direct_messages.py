"""
Skill: J6.7 — Direct Messages
Journey: J6 - LinkedIn Outreach
Checks: 3

Purpose: Verify direct message functionality via Unipile.
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
# DIRECT MESSAGE CONSTANTS
# =============================================================================

MESSAGE_CONFIG = {
    "action_type": "message",
    "activity_action": "message_sent",
    "requires_connection": True,  # Must be connected to send DM
}

UNIPILE_MESSAGE_ENDPOINT = {
    "path": "/linkedin/message",
    "method": "POST",
    "required_fields": ["account_id", "recipient_id", "message"],
    "optional_fields": [],
}

LINKEDIN_LIMITS = {
    "messages_per_day": 100,  # Unipile recommended limit
    "message_max_chars": 8000,  # LinkedIn DM limit
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J6.7.1",
        "part_a": "Verify `action=\"message\"` flow in LinkedIn engine",
        "part_b": "Check code path",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Message action routes to send_message in Unipile",
            "expect": {
                "code_contains": ["message", "send_message", "content"]
            }
        }
    },
    {
        "id": "J6.7.2",
        "part_a": "Verify activity logged as `message_sent`",
        "part_b": "Check action field",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, lead_id, action, channel, content_snapshot
                FROM activity
                WHERE action = 'message_sent'
                  AND channel = 'linkedin'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "action": "message_sent",
                "channel": "linkedin",
                "has_content_snapshot": True
            }
        }
    },
    {
        "id": "J6.7.3",
        "part_a": "Send test direct message",
        "part_b": "Verify sent via Unipile (requires TEST_MODE=true)",
        "key_files": [],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/linkedin/message",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "message": "Hi [Name], following up on our connection..."
            },
            "expect": {
                "status": 200,
                "body_has_field": "success"
            },
            "warning": "Requires TEST_MODE=true and existing connection",
            "curl_command": """curl -X POST '{api_url}/api/v1/linkedin/message' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "TEST_LEAD_ID", "message": "Test message"}'"""
        }
    }
]

PASS_CRITERIA = [
    "Direct messages work via Unipile API",
    "Activity logged with action=message_sent",
    "Content snapshot stored for analytics",
    "TEST_MODE redirects to test recipient"
]

KEY_FILES = [
    "src/engines/linkedin.py",
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
    lines.append("### Message Configuration")
    for key, value in MESSAGE_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### LinkedIn Limits")
    for key, value in LINKEDIN_LIMITS.items():
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
                lines.append(f"  curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
