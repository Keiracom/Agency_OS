"""
Skill: J6.10 — Reply Detection
Journey: J6 - LinkedIn Outreach
Checks: 3

Purpose: Verify LinkedIn replies are detected via Unipile webhooks or polling.
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
# REPLY DETECTION CONSTANTS
# =============================================================================

UNIPILE_WEBHOOK_EVENTS = {
    "message.received": "New message received from LinkedIn contact",
    "connection.accepted": "Connection request was accepted",
    "connection.rejected": "Connection request was rejected/withdrawn",
}

REPLY_DETECTION_CONFIG = {
    "method": "webhook",  # webhook or polling
    "webhook_endpoint": "/api/v1/webhooks/unipile",
    "polling_interval_seconds": 300,  # 5 minutes if polling
}

REPLY_PROCESSING = {
    "creates_activity": True,
    "activity_action": "message_received",
    "triggers_lead_update": True,
    "updates_stage": "replied",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J6.10.1",
        "part_a": "Verify webhook handler for Unipile events",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py", "src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Webhook endpoint handles message.received events",
            "expect": {
                "code_contains": ["unipile", "webhook", "message.received"]
            }
        }
    },
    {
        "id": "J6.10.2",
        "part_a": "Verify reply creates activity with message_received action",
        "part_b": "Check implementation",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, lead_id, action, channel, content_snapshot
                FROM activity
                WHERE action = 'message_received'
                  AND channel = 'linkedin'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "action": "message_received",
                "channel": "linkedin"
            }
        }
    },
    {
        "id": "J6.10.3",
        "part_a": "Test reply detection flow",
        "part_b": "Send test webhook or check Unipile dashboard",
        "key_files": [],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/webhooks/unipile",
            "auth": False,
            "body": {
                "event": "message.received",
                "data": {
                    "account_id": "test_account",
                    "sender_id": "test_sender",
                    "message": "Test reply message",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            },
            "expect": {
                "status": 200
            },
            "note": "Webhook should be validated with Unipile signature in production",
            "curl_command": """curl -X POST '{api_url}/api/v1/webhooks/unipile' \\
  -H 'Content-Type: application/json' \\
  -d '{"event": "message.received", "data": {...}}'"""
        }
    }
]

PASS_CRITERIA = [
    "Webhook endpoint receives Unipile events",
    "New replies create activity records",
    "Reply content captured in content_snapshot",
    "Lead stage updated on reply (if configured)"
]

KEY_FILES = [
    "src/api/routes/webhooks.py",
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
    lines.append("### Unipile Webhook Events")
    for event, description in UNIPILE_WEBHOOK_EVENTS.items():
        lines.append(f"  {event}: {description}")
    lines.append("")
    lines.append("### Reply Detection Configuration")
    for key, value in REPLY_DETECTION_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Reply Processing")
    for key, value in REPLY_PROCESSING.items():
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
            if lt.get("note"):
                lines.append(f"  Note: {lt['note']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
