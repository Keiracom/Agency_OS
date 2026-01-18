"""
Skill: J6.11 — Seat/Account Management
Journey: J6 - LinkedIn Outreach
Checks: 3

Purpose: Verify LinkedIn account status and quota tracking.

Note: "Seat" terminology from HeyReach maps to "Account" in Unipile.
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
# SEAT/ACCOUNT MANAGEMENT CONSTANTS
# =============================================================================

ACCOUNT_STATUS_VALUES = [
    "connected",
    "disconnected",
    "reconnecting",
    "error",
    "rate_limited",
]

QUOTA_TRACKING = {
    "connections_daily": 80,
    "messages_daily": 100,
    "reset_time": "00:00 UTC",
    "tracked_in": "Redis + DB",
}

ACCOUNT_FIELDS = {
    "account_id": "Unipile account identifier",
    "name": "LinkedIn display name",
    "status": "Connection status",
    "daily_remaining": "Remaining actions for today",
    "last_synced_at": "Last status sync timestamp",
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J6.11.1",
        "part_a": "Verify `get_account_status` method in engine",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/linkedin/accounts/{account_id}/status",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["status", "daily_remaining"]
            },
            "curl_command": """curl '{api_url}/api/v1/linkedin/accounts/{account_id}/status' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J6.11.2",
        "part_a": "Verify quota check via Unipile or internal tracking",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py", "src/integrations/unipile.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Quota tracking before sending actions",
            "expect": {
                "code_contains": ["daily_remaining", "quota", "limit"]
            }
        }
    },
    {
        "id": "J6.11.3",
        "part_a": "Verify remaining quota returned correctly",
        "part_b": "Check response",
        "key_files": [],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/linkedin/status",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["accounts", "total_remaining"]
            },
            "curl_command": """curl '{api_url}/api/v1/linkedin/status' \\
  -H 'Authorization: Bearer {token}'"""
        }
    }
]

PASS_CRITERIA = [
    "Account status retrievable via API",
    "Remaining quota accurate and updated",
    "Multiple accounts supported",
    "Status synced to database for dashboard display"
]

KEY_FILES = [
    "src/engines/linkedin.py",
    "src/integrations/unipile.py",
    "src/services/linkedin_connection_service.py"
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
    lines.append("### Account Status Values")
    for status in ACCOUNT_STATUS_VALUES:
        lines.append(f"  - {status}")
    lines.append("")
    lines.append("### Quota Tracking")
    for key, value in QUOTA_TRACKING.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Account Fields")
    for field, description in ACCOUNT_FIELDS.items():
        lines.append(f"  {field}: {description}")
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
