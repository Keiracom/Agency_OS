"""
Skill: J8.12 — External CRM Sync
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify deals can sync from external CRM.
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
# CRM SYNC CONSTANTS
# =============================================================================

CRM_SYNC_CONSTANTS = {
    "supported_crms": ["hubspot", "salesforce", "pipedrive"],
    "stage_mappings": {
        "hubspot": {
            "qualifiedtobuy": "qualified",
            "presentationscheduled": "proposal",
            "decisionmakerboughtin": "negotiation",
            "contractsent": "negotiation",
            "closedwon": "closed_won",
            "closedlost": "closed_lost",
        },
        "salesforce": {
            "qualification": "qualified",
            "needs_analysis": "qualified",
            "proposal": "proposal",
            "negotiation": "negotiation",
            "closed_won": "closed_won",
            "closed_lost": "closed_lost",
        },
        "pipedrive": {
            "qualified": "qualified",
            "contact_made": "qualified",
            "proposal_made": "proposal",
            "negotiations_started": "negotiation",
            "won": "closed_won",
            "lost": "closed_lost",
        },
    },
    "sync_fields": [
        "external_crm_id",
        "external_crm_type",
        "external_stage",
        "last_synced_at",
    ],
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.12.1",
        "part_a": "Read `sync_from_external` method (lines 727-847)",
        "part_b": "N/A",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify sync_from_external method exists with CRM type parameter",
            "expect": {
                "code_contains": ["sync_from_external", "crm_type", "external_id"]
            }
        }
    },
    {
        "id": "J8.12.2",
        "part_a": "Verify stage mapping from HubSpot",
        "part_b": "Check mapping",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify HubSpot stage mapping to internal stages",
            "expect": {
                "code_contains": ["hubspot", "qualifiedtobuy", "closedwon"]
            }
        }
    },
    {
        "id": "J8.12.3",
        "part_a": "Verify stage mapping from Salesforce",
        "part_b": "Check mapping",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify Salesforce stage mapping to internal stages",
            "expect": {
                "code_contains": ["salesforce", "qualification", "closed_won"]
            }
        }
    },
    {
        "id": "J8.12.4",
        "part_a": "Verify stage mapping from Pipedrive",
        "part_b": "Check mapping",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify Pipedrive stage mapping to internal stages",
            "expect": {
                "code_contains": ["pipedrive", "won", "lost"]
            }
        }
    },
    {
        "id": "J8.12.5",
        "part_a": "Verify upsert logic (create or update)",
        "part_b": "Test both",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, external_crm_id, external_crm_type, last_synced_at FROM deals WHERE external_crm_id IS NOT NULL LIMIT 5",
            "expect": {
                "columns": ["id", "external_crm_id", "external_crm_type", "last_synced_at"]
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/deals?select=id,external_crm_id,external_crm_type,last_synced_at&external_crm_id=not.is.null&limit=5' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    }
]

PASS_CRITERIA = [
    "External stages map correctly",
    "Existing deals updated",
    "New deals created",
    "Lead matched by email"
]

KEY_FILES = [
    "src/services/deal_service.py"
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
    lines.append("### CRM Sync Constants")
    lines.append(f"- Supported CRMs: {', '.join(CRM_SYNC_CONSTANTS['supported_crms'])}")
    lines.append(f"- Sync Fields: {', '.join(CRM_SYNC_CONSTANTS['sync_fields'])}")
    lines.append("")
    lines.append("### Stage Mappings")
    for crm, mappings in CRM_SYNC_CONSTANTS['stage_mappings'].items():
        lines.append(f"  {crm}:")
        for ext, internal in list(mappings.items())[:3]:
            lines.append(f"    - {ext} -> {internal}")
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
            if lt.get("query"):
                lines.append(f"  Query: {lt['query']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
