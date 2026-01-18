"""
Skill: J6.6 — Connection Requests
Journey: J6 - LinkedIn Outreach
Checks: 4

Purpose: Verify connection request functionality via Unipile.
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
# CONNECTION REQUEST CONSTANTS
# =============================================================================

CONNECTION_CONFIG = {
    "note_max_chars": 300,  # LinkedIn limit for connection notes
    "action_type": "connection",
    "activity_action": "connection_sent",
}

UNIPILE_CONNECTION_ENDPOINT = {
    "path": "/linkedin/connection-request",
    "method": "POST",
    "required_fields": ["account_id", "profile_url"],
    "optional_fields": ["note"],
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J6.6.1",
        "part_a": "Verify `action=\"connection\"` flow in LinkedIn engine",
        "part_b": "Check code path",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Connection action routes to send_connection_request in Unipile",
            "expect": {
                "code_contains": ["connection", "send_connection_request", "note"]
            }
        }
    },
    {
        "id": "J6.6.2",
        "part_a": "Verify message limit (300 chars) enforced",
        "part_b": "Check Unipile integration",
        "key_files": ["src/integrations/unipile.py", "src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Note length validated before sending",
            "expect": {
                "code_contains": ["300", "len(", "note"]
            }
        }
    },
    {
        "id": "J6.6.3",
        "part_a": "Verify activity logged as `connection_sent`",
        "part_b": "Check action field",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, lead_id, action, channel, created_at
                FROM activity
                WHERE action = 'connection_sent'
                  AND channel = 'linkedin'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "action": "connection_sent",
                "channel": "linkedin"
            }
        }
    },
    {
        "id": "J6.6.4",
        "part_a": "Send test connection request",
        "part_b": "Verify sent via Unipile (requires TEST_MODE=true)",
        "key_files": [],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/linkedin/connection",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "note": "Hi, I'd like to connect regarding [topic]."
            },
            "expect": {
                "status": 200,
                "body_has_field": "success"
            },
            "warning": "Requires TEST_MODE=true on Railway to avoid real outreach",
            "curl_command": """curl -X POST '{api_url}/api/v1/linkedin/connection' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "TEST_LEAD_ID", "note": "Test connection"}'"""
        }
    }
]

PASS_CRITERIA = [
    "Connection requests work via Unipile API",
    "300 character limit enforced for connection notes",
    "Activity logged with action=connection_sent",
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
    lines.append("### Connection Request Configuration")
    for key, value in CONNECTION_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Unipile Connection Endpoint")
    for key, value in UNIPILE_CONNECTION_ENDPOINT.items():
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
