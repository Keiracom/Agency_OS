"""
Skill: J4.11 — Provider Selection
Journey: J4 - SMS Outreach
Checks: 4

Purpose: Verify SMS provider selection logic (Twilio vs ClickSend).
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

PROVIDER_CONFIG = {
    "available_providers": ["twilio", "clicksend"],
    "default_provider": "twilio",
    "env_var": "SMS_PROVIDER",
    "selection_methods": ["config", "api_param", "campaign_setting"]
}

TWILIO_CONFIG = {
    "name": "twilio",
    "cost_per_sms_aud": 0.075,
    "features": ["delivery_tracking", "inbound_webhooks", "two_way_sms"],
    "regions": ["AU", "US", "UK", "global"]
}

CLICKSEND_CONFIG = {
    "name": "clicksend",
    "cost_per_sms_aud": 0.065,
    "features": ["delivery_tracking", "bulk_sms", "alphanumeric_sender"],
    "regions": ["AU", "NZ", "global"]
}

PROVIDER_SELECTION_PRIORITY = [
    "1. Campaign-level setting (if specified)",
    "2. API parameter (if specified)",
    "3. Environment variable SMS_PROVIDER",
    "4. Default (twilio)"
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J4.11.1",
        "part_a": "Verify SMS_PROVIDER setting in settings.py",
        "part_b": "Check Railway env var",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "SMS_PROVIDER environment variable defined",
            "expect": {
                "code_contains": ["SMS_PROVIDER"]
            },
            "curl_command": """# Check Railway env var:
railway variables --service agency-os --kv | grep SMS_PROVIDER"""
        }
    },
    {
        "id": "J4.11.2",
        "part_a": "Verify provider factory/selection logic in sms.py",
        "part_b": "Check get_sms_client method",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Provider selection logic exists in SMS engine",
            "expect": {
                "code_contains": [
                    "get_sms_client",
                    "twilio",
                    "clicksend",
                    "provider"
                ],
                "pattern": "def.*get_sms_client|_get_provider|provider.*selection"
            }
        }
    },
    {
        "id": "J4.11.3",
        "part_a": "Verify Twilio selected by default",
        "part_b": "Check default value",
        "key_files": ["src/config/settings.py", "src/engines/sms.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Default provider is Twilio",
            "expect": {
                "code_contains": ["default", "twilio"],
                "default_value": "twilio"
            }
        }
    },
    {
        "id": "J4.11.4",
        "part_a": "Verify ClickSend can be selected via config",
        "part_b": "Test provider switch",
        "key_files": ["src/engines/sms.py", "src/integrations/clicksend.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/sms/send",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "message": "ClickSend provider test",
                "provider": "clicksend"
            },
            "expect": {
                "status": 200,
                "provider_used": "clicksend",
                "body_has_field": "message_id"
            },
            "warning": "Sends real SMS via ClickSend - costs ~$0.065 AUD",
            "curl_command": """curl -X POST '{api_url}/api/v1/sms/send' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{test_lead_id}", "message": "Test", "provider": "clicksend"}'"""
        }
    }
]

PASS_CRITERIA = [
    "SMS_PROVIDER setting exists",
    "Provider selection logic implemented",
    "Twilio is default provider",
    "ClickSend selectable as alternative"
]

KEY_FILES = [
    "src/config/settings.py",
    "src/engines/sms.py",
    "src/integrations/twilio.py",
    "src/integrations/clicksend.py"
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
    lines.append("### Provider Configuration")
    for key, value in PROVIDER_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Twilio Configuration")
    for key, value in TWILIO_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### ClickSend Configuration")
    for key, value in CLICKSEND_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Provider Selection Priority")
    for item in PROVIDER_SELECTION_PRIORITY:
        lines.append(f"  {item}")
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
            if lt.get("warning"):
                lines.append(f"  Warning: {lt['warning']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
