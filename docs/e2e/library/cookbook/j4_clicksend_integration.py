"""
Skill: J4.3 — ClickSend Integration
Journey: J4 - SMS Outreach
Checks: 6

Purpose: Verify ClickSend client is properly configured as alternative SMS provider.
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

CLICKSEND_CONFIG = {
    "env_vars": {
        "username": "CLICKSEND_USERNAME",
        "api_key": "CLICKSEND_API_KEY",
        "sender_id": "CLICKSEND_SENDER_ID"
    },
    "api_base_url": "https://rest.clicksend.com/v3",
    "webhook_paths": {
        "delivery_report": "/webhooks/sms/clicksend/delivery"
    },
    "sender_id_max_length": 11,
    "australian_sender_rules": "Alphanumeric sender ID allowed for AU"
}

SMS_PROVIDER_CONFIG = {
    "default_provider": "twilio",
    "fallback_provider": "clicksend",
    "cost_per_sms_aud": 0.065
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J4.3.1",
        "part_a": "Read `src/integrations/clicksend.py` — verify complete implementation",
        "part_b": "N/A",
        "key_files": ["src/integrations/clicksend.py"],
        "live_test": {
            "type": "code_verify",
            "check": "ClickSend integration has all required methods",
            "expect": {
                "code_contains": [
                    "ClickSendClient",
                    "send_sms",
                    "CLICKSEND_USERNAME",
                    "CLICKSEND_API_KEY"
                ],
                "file_length_min": 100
            }
        }
    },
    {
        "id": "J4.3.2",
        "part_a": "Verify `CLICKSEND_USERNAME` env var configured",
        "part_b": "Check Railway vars for CLICKSEND_USERNAME",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "CLICKSEND_USERNAME defined in settings",
            "expect": {
                "code_contains": ["CLICKSEND_USERNAME"]
            },
            "curl_command": """# Check Railway env vars:
railway variables --service agency-os --kv | grep CLICKSEND_USERNAME"""
        }
    },
    {
        "id": "J4.3.3",
        "part_a": "Verify `CLICKSEND_API_KEY` env var configured",
        "part_b": "Check Railway vars for CLICKSEND_API_KEY",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "CLICKSEND_API_KEY defined in settings",
            "expect": {
                "code_contains": ["CLICKSEND_API_KEY"]
            },
            "curl_command": """# Check Railway env vars:
railway variables --service agency-os --kv | grep CLICKSEND_API_KEY"""
        }
    },
    {
        "id": "J4.3.4",
        "part_a": "Verify `CLICKSEND_SENDER_ID` env var configured",
        "part_b": "Check Railway vars for CLICKSEND_SENDER_ID",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "CLICKSEND_SENDER_ID defined in settings",
            "expect": {
                "code_contains": ["CLICKSEND_SENDER_ID"]
            },
            "curl_command": """# Check Railway env vars:
railway variables --service agency-os --kv | grep CLICKSEND_SENDER_ID"""
        }
    },
    {
        "id": "J4.3.5",
        "part_a": "Verify `send_sms` method complete",
        "part_b": "Call API with test data",
        "key_files": ["src/integrations/clicksend.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/sms/send",
            "auth": True,
            "body": {
                "lead_id": "{{test_lead_id}}",
                "message": "ClickSend integration test",
                "provider": "clicksend"
            },
            "expect": {
                "status": 200,
                "body_has_field": "message_id"
            },
            "warning": "Sends real SMS via ClickSend - costs ~$0.065 AUD",
            "curl_command": """curl -X POST '{api_url}/api/v1/sms/send' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{{test_lead_id}}", "message": "Test", "provider": "clicksend"}'"""
        }
    },
    {
        "id": "J4.3.6",
        "part_a": "Verify webhook parsing for delivery status",
        "part_b": "Test webhook parsing",
        "key_files": ["src/integrations/clicksend.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/webhooks/sms/clicksend/delivery",
            "auth": False,
            "body": {
                "message_id": "CS_TEST_123",
                "status": "delivered",
                "to": "+61400000000",
                "timestamp": "2024-01-01T00:00:00Z"
            },
            "expect": {
                "status": 200
            },
            "curl_command": """curl -X POST '{api_url}/webhooks/sms/clicksend/delivery' \\
  -H 'Content-Type: application/json' \\
  -d '{"message_id": "CS_TEST", "status": "delivered"}'"""
        }
    }
]

PASS_CRITERIA = [
    "ClickSend integration is complete",
    "All 3 ClickSend credentials configured (Username, API Key, Sender ID)",
    "SMS sends successfully via ClickSend",
    "Webhooks parse correctly"
]

KEY_FILES = [
    "src/integrations/clicksend.py",
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
    lines.append("### ClickSend Configuration")
    lines.append("  Required Environment Variables:")
    for key, value in CLICKSEND_CONFIG["env_vars"].items():
        lines.append(f"    - {value}")
    lines.append(f"  API Base: {CLICKSEND_CONFIG['api_base_url']}")
    lines.append(f"  Sender ID Max Length: {CLICKSEND_CONFIG['sender_id_max_length']}")
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
