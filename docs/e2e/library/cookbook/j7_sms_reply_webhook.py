"""
Skill: J7.2 — SMS Reply Webhook (Twilio)
Journey: J7 - Reply Handling
Checks: 5

Purpose: Verify SMS replies are received and processed via Twilio.
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
# SMS REPLY CONSTANTS
# =============================================================================

WEBHOOK_ENDPOINTS = {
    "twilio_inbound": "/webhooks/twilio/inbound",
    "twilio_status": "/webhooks/twilio/status"
}

TWILIO_PARAMS = {
    "from_field": "From",
    "to_field": "To",
    "body_field": "Body",
    "message_sid": "MessageSid",
    "account_sid": "AccountSid"
}

SMS_ACTIVITY_TYPES = {
    "reply_received": "replied",
    "sms_sent": "sms_sent",
    "sms_delivered": "sms_delivered"
}

SIGNATURE_VALIDATION = {
    "header": "X-Twilio-Signature",
    "validation_required": True
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.2.1",
        "part_a": "Read `webhooks.py` — verify `/webhooks/twilio/inbound` endpoint (line 474)",
        "part_b": "Send test SMS reply",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Twilio inbound webhook endpoint exists",
            "expect": {
                "code_contains": ["/webhooks/twilio/inbound", "async def", "twilio"]
            }
        }
    },
    {
        "id": "J7.2.2",
        "part_a": "Verify Twilio signature validation (lines 90-113)",
        "part_b": "Check validation passes",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Twilio signature validation implemented",
            "expect": {
                "code_contains": ["X-Twilio-Signature", "validate", "RequestValidator", "TWILIO_AUTH_TOKEN"]
            }
        }
    },
    {
        "id": "J7.2.3",
        "part_a": "Verify `twilio.parse_inbound_webhook` call (line 511)",
        "part_b": "Check parsing",
        "key_files": ["src/api/routes/webhooks.py", "src/integrations/twilio.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/webhooks/twilio/inbound",
            "auth": False,
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            "body": {
                "From": "+61400000000",
                "To": "+61457543392",
                "Body": "Yes, I am interested",
                "MessageSid": "SM_test_message_sid_001",
                "AccountSid": "test_account_sid"
            },
            "expect": {
                "status": 200,
                "content_type": "text/xml"
            },
            "curl_command": """curl -X POST '{api_url}/webhooks/twilio/inbound' \\
  -H 'Content-Type: application/x-www-form-urlencoded' \\
  -d 'From=%2B61400000000&To=%2B61457543392&Body=Test%20reply&MessageSid=SM_test'"""
        }
    },
    {
        "id": "J7.2.4",
        "part_a": "Verify lead matched by phone number",
        "part_b": "Check lead found",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.phone, l.first_name, l.status
                FROM leads l
                WHERE l.phone LIKE '%{test_phone_suffix}%'
                LIMIT 1;
            """,
            "test_values": {
                "test_phone_suffix": "457543392"
            },
            "expect": {
                "required_fields": ["id", "phone"]
            }
        }
    },
    {
        "id": "J7.2.5",
        "part_a": "Verify `closer.process_reply` called (line 535)",
        "part_b": "Check activity created",
        "key_files": ["src/api/routes/webhooks.py", "src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.lead_id, a.action, a.channel, a.intent, a.created_at
                FROM activities a
                WHERE a.action = 'replied'
                AND a.channel = 'sms'
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
    "Twilio inbound webhook endpoint exists",
    "Signature validation implemented",
    "Payload parsed correctly",
    "Lead matched by phone"
]

KEY_FILES = [
    "src/api/routes/webhooks.py",
    "src/integrations/twilio.py",
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
    lines.append("### Twilio Payload Fields")
    for name, field in TWILIO_PARAMS.items():
        lines.append(f"  {name}: {field}")
    lines.append("")
    lines.append("### Signature Validation")
    lines.append(f"  Header: {SIGNATURE_VALIDATION['header']}")
    lines.append(f"  Required: {SIGNATURE_VALIDATION['validation_required']}")
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
