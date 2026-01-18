"""
Skill: J4.2 — Twilio Integration
Journey: J4 - SMS Outreach
Checks: 6

Purpose: Verify Twilio client is properly configured.
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
    "test_phone": "+61457543392"
}

# =============================================================================
# SMS DOMAIN CONSTANTS
# =============================================================================

TWILIO_CONFIG = {
    "env_vars": {
        "account_sid": "TWILIO_ACCOUNT_SID",
        "auth_token": "TWILIO_AUTH_TOKEN",
        "phone_number": "TWILIO_PHONE_NUMBER"
    },
    "api_base_url": "https://api.twilio.com/2010-04-01",
    "webhook_paths": {
        "status_callback": "/webhooks/sms/twilio/status",
        "inbound": "/webhooks/sms/twilio/inbound"
    },
    "expected_phone_format": "+61*********"  # Australian format
}

SMS_PROVIDER_CONFIG = {
    "default_provider": "twilio",
    "fallback_provider": "clicksend",
    "cost_per_sms_aud": 0.075
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J4.2.1",
        "part_a": "Read `src/integrations/twilio.py` — verify complete implementation",
        "part_b": "N/A",
        "key_files": ["src/integrations/twilio.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Twilio integration has all required methods",
            "expect": {
                "code_contains": [
                    "TwilioClient",
                    "send_sms",
                    "parse_inbound_webhook",
                    "parse_status_webhook",
                    "Client"
                ],
                "file_length_min": 200
            }
        }
    },
    {
        "id": "J4.2.2",
        "part_a": "Verify `TWILIO_ACCOUNT_SID` env var configured",
        "part_b": "Check Railway vars for TWILIO_ACCOUNT_SID",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "TWILIO_ACCOUNT_SID defined in settings",
            "expect": {
                "code_contains": ["TWILIO_ACCOUNT_SID"]
            },
            "curl_command": """# Check Railway env vars:
railway variables --service agency-os --kv | grep TWILIO_ACCOUNT_SID"""
        }
    },
    {
        "id": "J4.2.3",
        "part_a": "Verify `TWILIO_AUTH_TOKEN` env var configured",
        "part_b": "Check Railway vars for TWILIO_AUTH_TOKEN",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "TWILIO_AUTH_TOKEN defined in settings",
            "expect": {
                "code_contains": ["TWILIO_AUTH_TOKEN"]
            },
            "curl_command": """# Check Railway env vars:
railway variables --service agency-os --kv | grep TWILIO_AUTH_TOKEN"""
        }
    },
    {
        "id": "J4.2.4",
        "part_a": "Verify `TWILIO_PHONE_NUMBER` env var configured",
        "part_b": "Check Railway vars for TWILIO_PHONE_NUMBER",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "TWILIO_PHONE_NUMBER defined in settings",
            "expect": {
                "code_contains": ["TWILIO_PHONE_NUMBER"]
            },
            "curl_command": """# Check Railway env vars:
railway variables --service agency-os --kv | grep TWILIO_PHONE_NUMBER"""
        }
    },
    {
        "id": "J4.2.5",
        "part_a": "Verify `send_sms` method complete",
        "part_b": "Call API with test data",
        "key_files": ["src/integrations/twilio.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/sms/send",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "message": "Twilio integration test"
            },
            "expect": {
                "status": 200,
                "body_has_field": "message_sid"
            },
            "warning": "Sends real SMS via Twilio - costs ~$0.075 AUD",
            "curl_command": """curl -X POST '{api_url}/api/v1/sms/send' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{test_lead_id}", "message": "Test SMS"}'"""
        }
    },
    {
        "id": "J4.2.6",
        "part_a": "Verify `parse_inbound_webhook` for replies",
        "part_b": "Test webhook parsing",
        "key_files": ["src/integrations/twilio.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/webhooks/sms/twilio/inbound",
            "auth": False,
            "body": {
                "From": "+61400000000",
                "To": "+61400000001",
                "Body": "Test reply message",
                "MessageSid": "SM_TEST_123"
            },
            "content_type": "application/x-www-form-urlencoded",
            "expect": {
                "status": 200
            },
            "curl_command": """curl -X POST '{api_url}/webhooks/sms/twilio/inbound' \\
  -H 'Content-Type: application/x-www-form-urlencoded' \\
  -d 'From=+61400000000&To=+61400000001&Body=Test&MessageSid=SM_TEST'"""
        }
    }
]

PASS_CRITERIA = [
    "Twilio integration is complete (250 lines verified)",
    "All 3 Twilio credentials configured (SID, Token, Phone)",
    "SMS sends successfully via Twilio",
    "Webhooks parse correctly"
]

KEY_FILES = [
    "src/integrations/twilio.py",
    "src/config/settings.py"
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
    lines.append("### Twilio Configuration")
    lines.append("  Required Environment Variables:")
    for key, value in TWILIO_CONFIG["env_vars"].items():
        lines.append(f"    - {value}")
    lines.append(f"  Webhook Paths:")
    for key, value in TWILIO_CONFIG["webhook_paths"].items():
        lines.append(f"    - {key}: {value}")
    lines.append("")
    lines.append("### SMS Provider Configuration")
    for key, value in SMS_PROVIDER_CONFIG.items():
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
                lines.append(f"  Curl: {lt['curl_command'][:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
