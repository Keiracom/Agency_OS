"""
Skill: J6.8 — LinkedIn Account Management
Journey: J6 - LinkedIn Outreach
Checks: 4

Purpose: Verify LinkedIn account connection via Unipile hosted auth.

Note: Unipile uses hosted auth flow - no credential storage needed.
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
# ACCOUNT MANAGEMENT CONSTANTS
# =============================================================================

UNIPILE_AUTH_CONFIG = {
    "flow_type": "hosted",  # OAuth handled by Unipile
    "callback_url": "/api/v1/linkedin/callback",
    "account_statuses": ["connected", "disconnected", "reconnecting", "error"],
}

UNIPILE_ACCOUNT_ENDPOINTS = {
    "list_accounts": {"path": "/accounts", "method": "GET"},
    "get_account": {"path": "/accounts/{account_id}", "method": "GET"},
    "create_auth_link": {"path": "/hosted-auth/linkedin", "method": "POST"},
    "disconnect": {"path": "/accounts/{account_id}", "method": "DELETE"},
}

ACCOUNT_SYNC_CONFIG = {
    "sync_to_db": True,
    "table": "linkedin_accounts",
    "fields": ["account_id", "name", "status", "daily_remaining", "connected_at"],
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J6.8.1",
        "part_a": "Read `get_accounts` method in UnipileClient",
        "part_b": "N/A",
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
        "id": "J6.8.2",
        "part_a": "Read `create_hosted_auth_link` method for LinkedIn OAuth",
        "part_b": "N/A",
        "key_files": ["src/integrations/unipile.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Unipile hosted auth link generation exists",
            "expect": {
                "code_contains": ["hosted-auth", "linkedin", "create"]
            }
        }
    },
    {
        "id": "J6.8.3",
        "part_a": "Verify account status sync to database",
        "part_b": "N/A",
        "key_files": ["src/services/linkedin_connection_service.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT account_id, status, daily_remaining, updated_at
                FROM linkedin_accounts
                WHERE status = 'connected'
                ORDER BY updated_at DESC
                LIMIT 5;
            """,
            "expect": {
                "has_records": True,
                "fields": ["account_id", "status", "daily_remaining"]
            }
        }
    },
    {
        "id": "J6.8.4",
        "part_a": "Verify disconnect/removal handled gracefully",
        "part_b": "N/A",
        "key_files": ["src/integrations/unipile.py", "src/api/routes/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Account disconnection updates status and cleans up",
            "expect": {
                "code_contains": ["disconnect", "delete", "status"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Account listing works via Unipile API",
    "Hosted auth flow for new account connection",
    "Account status synced to database",
    "Disconnection handled gracefully"
]

KEY_FILES = [
    "src/integrations/unipile.py",
    "src/services/linkedin_connection_service.py",
    "src/api/routes/linkedin.py"
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
    lines.append("### Unipile Auth Configuration")
    for key, value in UNIPILE_AUTH_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Account Endpoints")
    for name, config in UNIPILE_ACCOUNT_ENDPOINTS.items():
        lines.append(f"  {name}: {config['method']} {config['path']}")
    lines.append("")
    lines.append("### Database Sync")
    for key, value in ACCOUNT_SYNC_CONFIG.items():
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
