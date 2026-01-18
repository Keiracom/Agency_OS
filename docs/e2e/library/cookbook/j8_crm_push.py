"""
Skill: J8.11 — CRM Push Service
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify meetings pushed to client CRM.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
}

# =============================================================================
# CRM PUSH CONSTANTS
# =============================================================================

CRM_PUSH_CONSTANTS = {
    "supported_crms": ["hubspot", "pipedrive", "close", "salesforce"],
    "auth_methods": {
        "hubspot": "oauth",
        "pipedrive": "api_key",
        "close": "api_key",
        "salesforce": "oauth",
    },
    "push_events": ["meeting_created", "meeting_completed", "deal_created", "deal_closed"],
    "push_fields": [
        "crm_contact_id",
        "crm_deal_id",
        "crm_push_status",
        "crm_push_error",
        "crm_pushed_at",
    ],
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.11.1",
        "part_a": "Read `src/services/crm_push_service.py`",
        "part_b": "N/A",
        "key_files": ["src/services/crm_push_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify CRMPushService class exists with push methods for each CRM",
            "expect": {
                "code_contains": ["class CRMPushService", "hubspot", "pipedrive", "close"]
            }
        }
    },
    {
        "id": "J8.11.2",
        "part_a": "Verify HubSpot push (OAuth)",
        "part_b": "Test push",
        "key_files": ["src/services/crm_push_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify HubSpot push uses OAuth token refresh",
            "expect": {
                "code_contains": ["hubspot", "oauth", "access_token", "refresh_token"]
            }
        }
    },
    {
        "id": "J8.11.3",
        "part_a": "Verify Pipedrive push (API key)",
        "part_b": "Test push",
        "key_files": ["src/services/crm_push_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify Pipedrive push uses API key authentication",
            "expect": {
                "code_contains": ["pipedrive", "api_key", "api_token"]
            }
        }
    },
    {
        "id": "J8.11.4",
        "part_a": "Verify Close push (API key)",
        "part_b": "Test push",
        "key_files": ["src/services/crm_push_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify Close push uses API key authentication",
            "expect": {
                "code_contains": ["close", "api_key"]
            }
        }
    },
    {
        "id": "J8.11.5",
        "part_a": "Verify non-blocking (failure doesn't stop meeting)",
        "part_b": "Test error handling",
        "key_files": ["src/services/crm_push_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify CRM push errors are caught and logged without blocking meeting creation",
            "expect": {
                "code_contains": ["try", "except", "log", "error"]
            }
        }
    }
]

PASS_CRITERIA = [
    "CRM push triggered on meeting creation",
    "Contact created/found in CRM",
    "Deal created in CRM",
    "Push failure doesn't break meeting creation"
]

KEY_FILES = [
    "src/services/crm_push_service.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_live_url(path: str) -> str:
    """Get full URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_frontend_url(path: str) -> str:
    """Get full frontend URL for live testing."""
    base = LIVE_CONFIG["frontend_url"]
    return f"{base}{path}"

def get_supabase_url(path: str) -> str:
    """Get full Supabase URL for database queries."""
    base = LIVE_CONFIG["supabase_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API URL: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend URL: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase URL: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect URL: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### CRM Push Constants")
    lines.append(f"- Supported CRMs: {', '.join(CRM_PUSH_CONSTANTS['supported_crms'])}")
    lines.append(f"- Push Events: {', '.join(CRM_PUSH_CONSTANTS['push_events'])}")
    lines.append("")
    lines.append("### Auth Methods")
    for crm, method in CRM_PUSH_CONSTANTS['auth_methods'].items():
        lines.append(f"  - {crm}: {method}")
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
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
