"""
Skill: J7.1 — Email Reply Webhook (Postmark)
Journey: J7 - Reply Handling
Checks: 5

Purpose: Verify email replies are received and processed via Postmark.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app"
}

# =============================================================================
# REPLY DETECTION CONSTANTS
# =============================================================================

WEBHOOK_ENDPOINTS = {
    "postmark_inbound": "/webhooks/postmark/inbound",
    "postmark_bounce": "/webhooks/postmark/bounce",
    "postmark_spam": "/webhooks/postmark/spam"
}

EMAIL_HEADERS = {
    "in_reply_to": "In-Reply-To",
    "references": "References",
    "message_id": "Message-ID"
}

ACTIVITY_TYPES = {
    "reply_received": "replied",
    "reply_processed": "reply_processed"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.1.1",
        "part_a": "Read `webhooks.py` — verify `/webhooks/postmark/inbound` endpoint",
        "part_b": "Send test email reply",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Postmark inbound webhook endpoint exists",
            "expect": {
                "code_contains": ["/webhooks/postmark/inbound", "async def", "postmark"]
            }
        }
    },
    {
        "id": "J7.1.2",
        "part_a": "Verify `postmark.parse_inbound_webhook` call (line 277)",
        "part_b": "Check logs for parsing",
        "key_files": ["src/api/routes/webhooks.py", "src/integrations/postmark.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/webhooks/postmark/inbound",
            "auth": False,
            "body": {
                "FromName": "Test Sender",
                "From": "test@example.com",
                "To": "reply@agency.com",
                "Subject": "Re: Meeting Request",
                "TextBody": "Yes, I am interested in learning more.",
                "MessageID": "test-message-id-001",
                "Headers": [{"Name": "In-Reply-To", "Value": "<original-message-id@agency.com>"}]
            },
            "expect": {
                "status": 200,
                "body_contains": ["success", "processed"]
            },
            "curl_command": """curl -X POST '{api_url}/webhooks/postmark/inbound' \\
  -H 'Content-Type: application/json' \\
  -d '{"FromName": "Test", "From": "test@example.com", "TextBody": "Test reply"}'"""
        }
    },
    {
        "id": "J7.1.3",
        "part_a": "Verify lead matched by email address",
        "part_b": "Check lead found",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.email, l.first_name, l.status
                FROM leads l
                WHERE l.email = '{test_email}'
                LIMIT 1;
            """,
            "test_values": {
                "test_email": "david.stephens@keiracom.com"
            },
            "expect": {
                "required_fields": ["id", "email"]
            }
        }
    },
    {
        "id": "J7.1.4",
        "part_a": "Verify `closer.process_reply` called (line 300)",
        "part_b": "Check activity created",
        "key_files": ["src/api/routes/webhooks.py", "src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.lead_id, a.action, a.channel, a.intent, a.created_at
                FROM activities a
                WHERE a.action = 'replied'
                AND a.channel = 'email'
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "lead_id", "action", "channel"]
            }
        }
    },
    {
        "id": "J7.1.5",
        "part_a": "Verify `in_reply_to` header extracted",
        "part_b": "Check thread linking",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "In-Reply-To header extraction implemented",
            "expect": {
                "code_contains": ["in_reply_to", "In-Reply-To", "Headers", "message_id"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Postmark webhook endpoint exists",
    "Payload parsed correctly",
    "Lead matched by email",
    "Reply processed via Closer engine"
]

KEY_FILES = [
    "src/api/routes/webhooks.py",
    "src/integrations/postmark.py",
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
    lines.append("### Email Headers Tracked")
    for name, header in EMAIL_HEADERS.items():
        lines.append(f"  {name}: {header}")
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
