"""
Skill: J7.3 — LinkedIn Reply Webhook (Unipile)
Journey: J7 - Reply Handling
Checks: 4

Purpose: Verify LinkedIn replies are received and processed via Unipile.
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
# LINKEDIN REPLY CONSTANTS
# =============================================================================

WEBHOOK_ENDPOINTS = {
    "unipile_inbound": "/webhooks/unipile/inbound",
    "unipile_message": "/webhooks/unipile/message"
}

UNIPILE_EVENT_TYPES = {
    "message_received": "messaging.message_received",
    "connection_accepted": "connection.accepted",
    "inmail_received": "messaging.inmail_received"
}

LINKEDIN_ACTIVITY_TYPES = {
    "reply_received": "replied",
    "message_sent": "linkedin_message_sent",
    "connection_sent": "linkedin_connection_sent"
}

MESSAGE_FIELDS = {
    "sender_profile_url": "sender.profile_url",
    "message_content": "content",
    "message_id": "id",
    "conversation_id": "conversation_id",
    "timestamp": "timestamp"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.3.1",
        "part_a": "Read `webhooks.py` — verify `/webhooks/unipile/inbound` endpoint",
        "part_b": "Trigger test reply",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Unipile inbound webhook endpoint exists",
            "expect": {
                "code_contains": ["/webhooks/unipile", "async def", "unipile"]
            }
        }
    },
    {
        "id": "J7.3.2",
        "part_a": "Verify reply type check (message vs connection)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/webhooks/unipile/inbound",
            "auth": False,
            "body": {
                "event": "messaging.message_received",
                "data": {
                    "sender": {
                        "profile_url": "https://www.linkedin.com/in/test-user/"
                    },
                    "content": "Thanks for reaching out, I am interested!",
                    "id": "msg-test-001",
                    "conversation_id": "conv-test-001",
                    "timestamp": "2026-01-18T10:00:00Z"
                }
            },
            "expect": {
                "status": 200,
                "body_contains": ["success", "processed"]
            },
            "curl_command": """curl -X POST '{api_url}/webhooks/unipile/inbound' \\
  -H 'Content-Type: application/json' \\
  -d '{"event": "messaging.message_received", "data": {"content": "Test reply"}}'"""
        }
    },
    {
        "id": "J7.3.3",
        "part_a": "Verify lead matched by LinkedIn URL",
        "part_b": "Check lead found",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.linkedin_url, l.first_name, l.status
                FROM leads l
                WHERE l.linkedin_url IS NOT NULL
                AND l.linkedin_url != ''
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "linkedin_url"]
            }
        }
    },
    {
        "id": "J7.3.4",
        "part_a": "Verify `closer.process_reply` called",
        "part_b": "Check activity created",
        "key_files": ["src/api/routes/webhooks.py", "src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.lead_id, a.action, a.channel, a.intent, a.created_at
                FROM activities a
                WHERE a.action = 'replied'
                AND a.channel = 'linkedin'
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "lead_id", "action", "channel"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Unipile webhook endpoint exists",
    "Reply type filtered (not connections)",
    "Lead matched by LinkedIn URL",
    "Reply processed via Closer engine"
]

KEY_FILES = [
    "src/api/routes/webhooks.py",
    "src/integrations/unipile.py",
    "src/engines/closer.py"
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
    lines.append("### Webhook Endpoints")
    for name, endpoint in WEBHOOK_ENDPOINTS.items():
        lines.append(f"  {name}: {endpoint}")
    lines.append("")
    lines.append("### Unipile Event Types")
    for name, event in UNIPILE_EVENT_TYPES.items():
        lines.append(f"  {name}: {event}")
    lines.append("")
    lines.append("### Message Fields")
    for name, field in MESSAGE_FIELDS.items():
        lines.append(f"  {name}: {field}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
