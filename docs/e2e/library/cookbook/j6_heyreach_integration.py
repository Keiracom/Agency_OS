"""
Skill: J6.2 — Unipile Integration (formerly HeyReach)
Journey: J6 - LinkedIn Outreach
Checks: 6

Purpose: Verify Unipile client is properly configured for LinkedIn automation.

Note: HeyReach was replaced by Unipile for better rate limits and SOC 2 compliance.
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
# UNIPILE-SPECIFIC CONSTANTS
# =============================================================================

UNIPILE_CONFIG = {
    "api_base": "https://api.unipile.com/api/v1",
    "auth_flow": "hosted",  # Unipile handles OAuth
    "soc2_compliant": True,
    "webhook_events": [
        "message.received",
        "connection.accepted",
        "connection.rejected",
        "account.connected",
        "account.disconnected",
    ],
}

UNIPILE_RATE_LIMITS = {
    "connection_requests_per_day": 80,  # Conservative limit
    "messages_per_day": 100,
    "api_calls_per_minute": 60,
}

UNIPILE_ENDPOINTS = {
    "accounts": "/accounts",
    "send_connection": "/linkedin/connection-request",
    "send_message": "/linkedin/message",
    "get_profile": "/linkedin/profile",
    "get_conversations": "/linkedin/conversations",
    "hosted_auth": "/hosted-auth/linkedin",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J6.2.1",
        "part_a": "Read `src/integrations/unipile.py` — verify complete implementation",
        "part_b": "N/A",
        "key_files": ["src/integrations/unipile.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Unipile integration class exists with required methods",
            "expect": {
                "code_contains": [
                    "UnipileClient",
                    "send_connection_request",
                    "send_message",
                    "get_accounts",
                ]
            }
        }
    },
    {
        "id": "J6.2.2",
        "part_a": "Verify `UNIPILE_API_KEY` and `UNIPILE_API_URL` env vars in Railway",
        "part_b": "Check Railway vars",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/health/ready",
            "auth": False,
            "expect": {
                "status": 200,
                "body_has_field": "status"
            },
            "note": "Health check verifies environment is configured",
            "curl_command": """curl '{api_url}/api/v1/health/ready'"""
        }
    },
    {
        "id": "J6.2.3",
        "part_a": "Verify `send_connection_request` method in UnipileClient",
        "part_b": "Test API call structure",
        "key_files": ["src/integrations/unipile.py"],
        "live_test": {
            "type": "code_verify",
            "check": "send_connection_request accepts profile_url and optional note",
            "expect": {
                "code_contains": ["send_connection_request", "profile_url", "note"]
            }
        }
    },
    {
        "id": "J6.2.4",
        "part_a": "Verify `send_message` method in UnipileClient",
        "part_b": "Test API call structure",
        "key_files": ["src/integrations/unipile.py"],
        "live_test": {
            "type": "code_verify",
            "check": "send_message accepts account_id, recipient, and message",
            "expect": {
                "code_contains": ["send_message", "account_id", "message"]
            }
        }
    },
    {
        "id": "J6.2.5",
        "part_a": "Verify `get_accounts` method lists connected LinkedIn accounts",
        "part_b": "Test API call",
        "key_files": ["src/integrations/unipile.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/linkedin/accounts",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True
            },
            "curl_command": """curl '{api_url}/api/v1/linkedin/accounts' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J6.2.6",
        "part_a": "Verify `get_conversations` or webhook handler for replies",
        "part_b": "Test reply detection",
        "key_files": ["src/integrations/unipile.py", "src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Webhook handler or polling method exists for LinkedIn messages",
            "expect": {
                "code_contains": ["message.received", "conversations", "webhook"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Unipile integration replaces HeyReach",
    "UNIPILE_API_KEY and UNIPILE_API_URL configured",
    "All core methods implemented (send_connection_request, send_message, get_accounts)",
    "Webhook or polling for reply detection"
]

KEY_FILES = [
    "src/integrations/unipile.py",
    "src/config/settings.py",
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
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Unipile Configuration")
    for key, value in UNIPILE_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Unipile Rate Limits")
    for key, value in UNIPILE_RATE_LIMITS.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Unipile Endpoints")
    for key, value in UNIPILE_ENDPOINTS.items():
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
            if lt.get("curl_command"):
                lines.append(f"  curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
