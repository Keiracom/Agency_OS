"""
Skill: J4.8 — Reply Detection
Journey: J4 - SMS Outreach
Checks: 4

Purpose: Verify SMS reply detection via Twilio inbound webhooks.
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
# SMS DOMAIN CONSTANTS
# =============================================================================

WEBHOOK_CONFIG = {
    "twilio_inbound_path": "/webhooks/sms/twilio/inbound",
    "twilio_status_path": "/webhooks/sms/twilio/status",
    "clicksend_delivery_path": "/webhooks/sms/clicksend/delivery",
    "content_type": "application/x-www-form-urlencoded"
}

TWILIO_INBOUND_FIELDS = {
    "required": ["From", "To", "Body", "MessageSid"],
    "optional": ["NumMedia", "SmsStatus", "AccountSid"]
}

REPLY_MATCHING_CONFIG = {
    "match_by": "phone_number",
    "phone_normalization": "+E.164",
    "activity_action": "sms_reply",
    "creates_notification": True
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J4.8.1",
        "part_a": "Read `parse_inbound_webhook` method in twilio.py",
        "part_b": "N/A",
        "key_files": ["src/integrations/twilio.py"],
        "live_test": {
            "type": "code_verify",
            "check": "parse_inbound_webhook method parses Twilio inbound SMS",
            "expect": {
                "code_contains": ["parse_inbound_webhook", "From", "Body", "MessageSid"]
            }
        }
    },
    {
        "id": "J4.8.2",
        "part_a": "Verify webhook endpoint `/webhooks/sms/twilio/inbound` exists",
        "part_b": "Check webhooks.py",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/webhooks/sms/twilio/inbound",
            "auth": False,
            "content_type": "application/x-www-form-urlencoded",
            "body": {
                "From": "+61400000000",
                "To": "+61400000001",
                "Body": "Test reply",
                "MessageSid": "SM_TEST_REPLY_123"
            },
            "expect": {
                "status": 200,
                "note": "Endpoint accepts and processes inbound webhook"
            },
            "curl_command": """curl -X POST '{api_url}/webhooks/sms/twilio/inbound' \\
  -H 'Content-Type: application/x-www-form-urlencoded' \\
  -d 'From=+61400000000&To=+61400000001&Body=Test&MessageSid=SM_TEST'"""
        }
    },
    {
        "id": "J4.8.3",
        "part_a": "Verify reply linked to original lead by phone number",
        "part_b": "Test reply matching logic",
        "key_files": ["src/api/routes/webhooks.py", "src/engines/sms.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.lead_id, a.action, a.content_preview,
                       l.phone, l.first_name
                FROM activity a
                JOIN leads l ON a.lead_id = l.id
                WHERE a.action = 'sms_reply'
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "has_rows": True,
                "lead_id_not_null": True,
                "phone_matches_sender": True
            }
        }
    },
    {
        "id": "J4.8.4",
        "part_a": "Verify reply creates activity record with action='sms_reply'",
        "part_b": "Check activity logging",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, lead_id, action, channel, content_preview,
                       metadata->>'from_phone' as from_phone,
                       metadata->>'message_sid' as message_sid
                FROM activity
                WHERE action = 'sms_reply'
                  AND channel = 'sms'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "has_rows": True,
                "action_value": "sms_reply",
                "channel_value": "sms",
                "required_metadata": ["from_phone", "message_sid"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Inbound webhook endpoint configured",
    "Reply parsed correctly (from, body, timestamp)",
    "Reply matched to original lead",
    "Activity record created for reply"
]

KEY_FILES = [
    "src/integrations/twilio.py",
    "src/api/routes/webhooks.py",
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
    lines.append("### Webhook Configuration")
    for key, value in WEBHOOK_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Twilio Inbound Fields")
    lines.append(f"  Required: {', '.join(TWILIO_INBOUND_FIELDS['required'])}")
    lines.append(f"  Optional: {', '.join(TWILIO_INBOUND_FIELDS['optional'])}")
    lines.append("")
    lines.append("### Reply Matching Configuration")
    for key, value in REPLY_MATCHING_CONFIG.items():
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
            if lt.get("check"):
                lines.append(f"  Check: {lt['check']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
