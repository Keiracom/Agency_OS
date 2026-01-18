"""
Skill: J6.13 — Live LinkedIn Test
Journey: J6 - LinkedIn Outreach
Checks: 4

Purpose: Verify real LinkedIn actions work end-to-end via Unipile.

WARNING: This test sends REAL LinkedIn actions. Use TEST_MODE=true in production!
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
# LIVE TEST CONSTANTS
# =============================================================================

LIVE_TEST_CONFIG = {
    "requires_test_mode": True,
    "test_mode_env": "TEST_MODE=true",
    "test_recipient_env": "TEST_LINKEDIN_RECIPIENT",
    "verify_via": "Unipile dashboard or activity table",
}

UNIPILE_DASHBOARD = {
    "url": "https://app.unipile.com",
    "check_section": "Messages / Connections",
}

PREFLIGHT_CHECKS = [
    "TEST_MODE=true on Railway",
    "TEST_LINKEDIN_RECIPIENT configured",
    "At least one LinkedIn account connected",
    "Daily limit not exhausted",
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J6.13.1",
        "part_a": "Verify at least one LinkedIn account connected",
        "part_b": "Check via API or Unipile dashboard",
        "key_files": [],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/linkedin/accounts",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "min_items": 1
            },
            "curl_command": """curl '{api_url}/api/v1/linkedin/accounts' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J6.13.2",
        "part_a": "N/A",
        "part_b": "Send test connection request (TEST_MODE must be true)",
        "key_files": [],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/linkedin/connection",
            "auth": True,
            "body": {
                "lead_id": "{test_lead_id}",
                "note": "E2E Test - LinkedIn connection request via Unipile"
            },
            "expect": {
                "status": 200,
                "body_has_field": "success"
            },
            "warning": "This sends a REAL connection request to TEST_LINKEDIN_RECIPIENT",
            "curl_command": """curl -X POST '{api_url}/api/v1/linkedin/connection' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{test_lead_id}", "note": "E2E Test"}'"""
        }
    },
    {
        "id": "J6.13.3",
        "part_a": "N/A",
        "part_b": "Verify action appears in Unipile dashboard",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open Unipile dashboard: https://app.unipile.com",
                "2. Navigate to the connected LinkedIn account",
                "3. Check Messages or Connections section",
                "4. Verify test connection request appears",
                "5. Note: If TEST_MODE=true, went to test recipient"
            ],
            "expect": {
                "action_visible": True
            }
        }
    },
    {
        "id": "J6.13.4",
        "part_a": "N/A",
        "part_b": "Check activity logged in database",
        "key_files": [],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, lead_id, action, channel, metadata, created_at
                FROM activity
                WHERE channel = 'linkedin'
                  AND action = 'connection_sent'
                ORDER BY created_at DESC
                LIMIT 1;
            """,
            "expect": {
                "has_record": True,
                "action": "connection_sent",
                "channel": "linkedin"
            }
        }
    }
]

PASS_CRITERIA = [
    "At least one LinkedIn account connected via Unipile",
    "LinkedIn action sent successfully (via TEST_MODE recipient)",
    "Action appears in Unipile dashboard",
    "Activity logged correctly in database"
]

KEY_FILES = [
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
    lines.append("### WARNING")
    lines.append("  This test sends REAL LinkedIn actions!")
    lines.append("  Ensure TEST_MODE=true before running!")
    lines.append("")
    lines.append("### Live Test Configuration")
    for key, value in LIVE_TEST_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Preflight Checks")
    for check in PREFLIGHT_CHECKS:
        lines.append(f"  - [ ] {check}")
    lines.append("")
    lines.append("### Unipile Dashboard")
    for key, value in UNIPILE_DASHBOARD.items():
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
                lines.append(f"  WARNING: {lt['warning']}")
            if lt.get("curl_command"):
                lines.append(f"  curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
