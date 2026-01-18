"""
Skill: J8.9 — Deal Auto-Creation from Meeting
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify deals auto-created from positive meeting outcomes.
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
# AUTO-CREATE CONSTANTS
# =============================================================================

AUTOCREATE_CONSTANTS = {
    "trigger_outcomes": ["good"],
    "auto_create_stages": {
        "good": "qualified",
        "neutral": None,
        "bad": None,
    },
    "attribution_fields": [
        "meeting_id",
        "lead_id",
        "converting_channel",
        "converting_activity_id",
    ],
    "api_endpoints": {
        "record_outcome": "/api/v1/meetings/{id}/outcome",
    },
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.9.1",
        "part_a": "Read `record_outcome` method (lines 364-460)",
        "part_b": "N/A",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify record_outcome method with create_deal parameter",
            "expect": {
                "code_contains": ["def record_outcome", "create_deal", "outcome"]
            }
        }
    },
    {
        "id": "J8.9.2",
        "part_a": "Verify `create_deal=True` parameter",
        "part_b": "Test auto-creation",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/meetings/{meeting_id}/outcome",
            "auth": True,
            "body": {
                "outcome": "good",
                "notes": "Interested in proposal",
                "create_deal": True
            },
            "expect": {
                "status": [200, 201, 401, 404],
                "response_contains": ["meeting", "deal"]
            },
            "curl_command": "curl -X POST '{api_url}/api/v1/meetings/{meeting_id}/outcome' -H 'Content-Type: application/json' -H 'Authorization: Bearer {TOKEN}' -d '{\"outcome\": \"good\", \"create_deal\": true}'"
        }
    },
    {
        "id": "J8.9.3",
        "part_a": "Verify deal linked to meeting",
        "part_b": "Check deal.meeting_id",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT d.id, d.meeting_id, m.id as meeting_check FROM deals d JOIN meetings m ON d.meeting_id = m.id LIMIT 5",
            "expect": {
                "columns": ["id", "meeting_id", "meeting_check"],
                "meeting_id_not_null": True
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/deals?select=id,meeting_id,meetings(id)&meeting_id=not.is.null&limit=5' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.9.4",
        "part_a": "Verify meeting.deal_id updated",
        "part_b": "Check meeting record",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, deal_id, outcome FROM meetings WHERE deal_id IS NOT NULL LIMIT 5",
            "expect": {
                "columns": ["id", "deal_id", "outcome"],
                "deal_id_not_null": True
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/meetings?select=id,deal_id,outcome&deal_id=not.is.null&limit=5' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.9.5",
        "part_a": "Verify attribution carried forward",
        "part_b": "Check deal fields",
        "key_files": ["src/services/deal_service.py", "src/services/meeting_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify converting_channel and converting_activity_id passed from meeting to deal",
            "expect": {
                "code_contains": ["converting_channel", "converting_activity_id"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Deal created on good outcome",
    "Meeting and deal linked",
    "Attribution preserved"
]

KEY_FILES = [
    "src/services/meeting_service.py",
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
    lines.append("### Auto-Create Constants")
    lines.append(f"- Trigger Outcomes: {', '.join(AUTOCREATE_CONSTANTS['trigger_outcomes'])}")
    lines.append(f"- Attribution Fields: {', '.join(AUTOCREATE_CONSTANTS['attribution_fields'])}")
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
            if lt.get("query"):
                lines.append(f"  Query: {lt['query']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
