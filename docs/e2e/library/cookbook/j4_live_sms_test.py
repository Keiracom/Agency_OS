"""
Skill: J4.12 — Live SMS Test
Journey: J4 - SMS Outreach
Checks: 6

Purpose: Verify SMS arrives on test phone with correct content.
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

TEST_PHONE_CONFIG = {
    "test_sms_recipient": "+61457543392",
    "test_mode_required": True,
    "env_var": "TEST_SMS_RECIPIENT"
}

TWILIO_SENDER_CONFIG = {
    "sender_type": "phone_number",
    "format": "+61XXXXXXXXX",
    "env_var": "TWILIO_PHONE_NUMBER",
    "display_name": None  # Phone number displays as sender
}

SMS_DELIVERY_STATUS = {
    "statuses": ["queued", "sent", "delivered", "failed", "undelivered"],
    "success_statuses": ["sent", "delivered"],
    "failure_statuses": ["failed", "undelivered"],
    "webhook_path": "/webhooks/sms/twilio/status"
}

LIVE_TEST_COSTS = {
    "twilio_sms_aud": 0.075,
    "test_mode_savings": "Redirects to test number, same cost",
    "warning": "Each live test costs ~$0.075 AUD"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J4.12.1",
        "part_a": "Verify sender ID configured",
        "part_b": "Check Twilio number in Railway vars",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "TWILIO_PHONE_NUMBER configured in settings",
            "expect": {
                "code_contains": ["TWILIO_PHONE_NUMBER"]
            },
            "curl_command": """# Check Railway env vars:
railway variables --service agency-os --kv | grep TWILIO_PHONE_NUMBER"""
        }
    },
    {
        "id": "J4.12.2",
        "part_a": "N/A",
        "part_b": "Send real SMS via TEST_MODE to +61457543392",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/sms/send",
            "auth": True,
            "body": {
                "lead_id": "{{test_lead_id}}",
                "message": "Agency OS E2E Test: Live SMS delivery verification. Timestamp: {{timestamp}}"
            },
            "expect": {
                "status": 200,
                "body_has_fields": ["success", "message_sid"],
                "redirected_to_test_number": True
            },
            "warning": "Sends real SMS - costs ~$0.075 AUD. CEO approval required.",
            "requires_ceo_approval": True,
            "curl_command": """curl -X POST '{api_url}/api/v1/sms/send' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{{test_lead_id}}", "message": "E2E Test SMS"}'"""
        }
    },
    {
        "id": "J4.12.3",
        "part_a": "N/A",
        "part_b": "Confirm SMS received on test phone",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Check test phone (+61457543392) for incoming SMS",
                "2. Verify message received within 30 seconds",
                "3. Note the sender ID displayed",
                "4. Screenshot the received message for records"
            ],
            "expect": {
                "sms_received": True,
                "within_seconds": 30
            }
        }
    },
    {
        "id": "J4.12.4",
        "part_a": "N/A",
        "part_b": "Verify content and personalization correct",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Read the received SMS content",
                "2. Verify it matches the sent message",
                "3. Check for any personalization variables ({{first_name}}, etc.)",
                "4. Confirm all variables are replaced with actual values"
            ],
            "expect": {
                "content_matches": True,
                "no_unresolved_variables": True,
                "character_count_correct": True
            }
        }
    },
    {
        "id": "J4.12.5",
        "part_a": "N/A",
        "part_b": "Verify sender ID displays correctly",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Check the sender ID on received SMS",
                "2. Should display as Twilio phone number (e.g., +61XXXXXXXXX)",
                "3. Verify it matches TWILIO_PHONE_NUMBER env var",
                "4. Note: Some carriers may show different formats"
            ],
            "expect": {
                "sender_id_visible": True,
                "format": "+61XXXXXXXXX"
            }
        }
    },
    {
        "id": "J4.12.6",
        "part_a": "Verify delivery status webhook received",
        "part_b": "Check activity record updated with delivery status",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, action, channel,
                       metadata->>'message_sid' as message_sid,
                       metadata->>'delivery_status' as delivery_status,
                       metadata->>'delivered_at' as delivered_at
                FROM activity
                WHERE channel = 'sms'
                  AND action IN ('sms_sent', 'sms_delivered')
                ORDER BY created_at DESC
                LIMIT 10;
            """,
            "expect": {
                "has_rows": True,
                "delivery_status_present": True,
                "status_values": ["sent", "delivered"]
            },
            "note": "Delivery webhooks may take up to 60 seconds to arrive"
        }
    }
]

PASS_CRITERIA = [
    "SMS received on test phone (+61457543392)",
    "Content displays correctly",
    "Personalization fields replaced",
    "Sender ID correct",
    "Delivery status tracked",
    "Activity record complete"
]

KEY_FILES = [
    "src/config/settings.py",
    "src/engines/sms.py",
    "src/integrations/twilio.py",
    "src/api/routes/webhooks.py"
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
    lines.append("### Test Phone Configuration")
    for key, value in TEST_PHONE_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Twilio Sender Configuration")
    for key, value in TWILIO_SENDER_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### SMS Delivery Statuses")
    lines.append(f"  All: {', '.join(SMS_DELIVERY_STATUS['statuses'])}")
    lines.append(f"  Success: {', '.join(SMS_DELIVERY_STATUS['success_statuses'])}")
    lines.append("")
    lines.append("### Live Test Costs")
    for key, value in LIVE_TEST_COSTS.items():
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
            if lt.get("steps"):
                lines.append("  Steps:")
                for step in lt["steps"][:3]:
                    lines.append(f"    {step}")
            if lt.get("warning"):
                lines.append(f"  Warning: {lt['warning']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
