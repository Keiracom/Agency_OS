"""
Skill: J5.2 — Vapi Integration
Journey: J5 - Voice Outreach
Checks: 7

Purpose: Verify Vapi client is properly configured.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "vapi_dashboard": "https://dashboard.vapi.ai",
    "client_id": "81dbaee6-4e71-48ad-be40-fa915fae66e0",
    "user_id": "a60bcdbd-4a31-43e7-bcc8-3ab998c44ac2",
    "test_email": "david.stephens@keiracom.com",
    "test_phone": "+61457543392",
    "warning": "Vapi calls cost money - ensure TEST_MODE=true before testing"
}

# =============================================================================
# VAPI CONFIGURATION
# =============================================================================

VAPI_CONFIG = {
    "env_vars": {
        "api_key": "VAPI_API_KEY",
        "phone_number_id": "VAPI_PHONE_NUMBER_ID",
        "assistant_id": "VAPI_ASSISTANT_ID"
    },
    "api_base_url": "https://api.vapi.ai",
    "required_methods": [
        "create_assistant",
        "start_outbound_call",
        "get_call",
        "parse_webhook"
    ],
    "webhook_events": [
        "call-started",
        "call-ended",
        "transcript-update",
        "function-call"
    ]
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.2.1",
        "part_a": "Read `src/integrations/vapi.py` — verify complete implementation",
        "part_b": "N/A",
        "key_files": ["src/integrations/vapi.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Vapi integration has all required methods",
            "expect": {
                "code_contains": ["VapiClient", "create_assistant", "start_outbound_call", "get_call", "parse_webhook"]
            }
        }
    },
    {
        "id": "J5.2.2",
        "part_a": "Verify `VAPI_API_KEY` env var exists",
        "part_b": "Check Railway vars for VAPI_API_KEY",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Settings includes VAPI_API_KEY",
            "expect": {
                "code_contains": ["VAPI_API_KEY"]
            }
        }
    },
    {
        "id": "J5.2.3",
        "part_a": "Verify `VAPI_PHONE_NUMBER_ID` env var exists",
        "part_b": "Check Railway vars for VAPI_PHONE_NUMBER_ID",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Settings includes VAPI_PHONE_NUMBER_ID",
            "expect": {
                "code_contains": ["VAPI_PHONE_NUMBER_ID"]
            }
        }
    },
    {
        "id": "J5.2.4",
        "part_a": "Verify `create_assistant` method implemented",
        "part_b": "Test assistant creation via API",
        "key_files": ["src/integrations/vapi.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/voice/assistants",
            "auth": True,
            "body": {
                "name": "E2E Test Assistant",
                "campaign_id": "{test_campaign_id}",
                "voice_settings": {
                    "voice_id": "pNInz6obpgDQGcFmaJgB",
                    "provider": "11labs"
                }
            },
            "expect": {
                "status": [200, 201],
                "body_has_field": "assistant_id"
            },
            "warning": "Creates Vapi assistant - may incur costs",
            "curl_command": """curl -X POST '{api_url}/api/v1/voice/assistants' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"name": "E2E Test", "campaign_id": "{campaign_id}"}'"""
        }
    },
    {
        "id": "J5.2.5",
        "part_a": "Verify `start_outbound_call` method implemented",
        "part_b": "Test call initiation via API",
        "key_files": ["src/integrations/vapi.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/voice/calls",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "assistant_id": "{test_assistant_id}"
            },
            "expect": {
                "status": [200, 201, 202],
                "body_has_field": "call_id"
            },
            "warning": "Initiates live call - CEO approval required",
            "curl_command": """curl -X POST '{api_url}/api/v1/voice/calls' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{lead_id}", "assistant_id": "{assistant_id}"}'"""
        }
    },
    {
        "id": "J5.2.6",
        "part_a": "Verify `get_call` method implemented",
        "part_b": "Test call status retrieval via API",
        "key_files": ["src/integrations/vapi.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/voice/calls/{call_id}",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["id", "status", "duration", "ended_reason"]
            },
            "curl_command": """curl '{api_url}/api/v1/voice/calls/{call_id}' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J5.2.7",
        "part_a": "Verify `parse_webhook` method implemented",
        "part_b": "Test webhook parsing with sample payload",
        "key_files": ["src/integrations/vapi.py"],
        "live_test": {
            "type": "code_verify",
            "check": "parse_webhook handles all event types",
            "expect": {
                "code_contains": ["call-started", "call-ended", "transcript", "webhook"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Vapi integration is complete (290 lines verified)",
    "API key and phone number configured",
    "Assistant operations work",
    "Call operations work",
    "Webhook parsing works"
]

KEY_FILES = [
    "src/integrations/vapi.py",
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
    lines.append(f"- Vapi Dashboard: {LIVE_CONFIG['vapi_dashboard']}")
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### Vapi Configuration")
    lines.append(f"  API Base: {VAPI_CONFIG['api_base_url']}")
    lines.append(f"  Env Vars: {', '.join(VAPI_CONFIG['env_vars'].values())}")
    lines.append(f"  Required Methods: {', '.join(VAPI_CONFIG['required_methods'])}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
            if lt.get("warning"):
                lines.append(f"  Warning: {lt['warning']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
