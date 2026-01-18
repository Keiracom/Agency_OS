"""
Skill: J8.7 — DealService Implementation
Journey: J8 - Meeting & Deals
Checks: 6

Purpose: Verify DealService is complete.
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
# DEAL SERVICE CONSTANTS
# =============================================================================

DEAL_CONSTANTS = {
    "deal_stages": [
        "qualified",
        "proposal",
        "negotiation",
        "closed_won",
        "closed_lost",
    ],
    "stage_probabilities": {
        "qualified": 20,
        "proposal": 40,
        "negotiation": 60,
        "closed_won": 100,
        "closed_lost": 0,
    },
    "lost_reasons": [
        "price",
        "timing",
        "competitor",
        "no_budget",
        "no_decision",
        "lost_contact",
        "other",
    ],
    "api_endpoints": {
        "create": "/api/v1/deals",
        "get": "/api/v1/deals/{id}",
        "update": "/api/v1/deals/{id}",
        "list": "/api/v1/deals",
        "close_won": "/api/v1/deals/{id}/close-won",
        "close_lost": "/api/v1/deals/{id}/close-lost",
    },
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.7.1",
        "part_a": "Read `src/services/deal_service.py` (867 lines)",
        "part_b": "N/A",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify DealService class exists with all required methods",
            "expect": {
                "code_contains": ["class DealService", "def create", "def update_stage", "def close_won", "def close_lost"]
            }
        }
    },
    {
        "id": "J8.7.2",
        "part_a": "Verify `create` method",
        "part_b": "Test deal creation",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/deals",
            "auth": True,
            "body": {
                "lead_id": "{{test_lead_id}}",
                "name": "Test Deal",
                "value": 10000,
                "stage": "qualified"
            },
            "expect": {
                "status": [200, 201, 401, 422],
                "response_contains": ["id", "deal"]
            },
            "curl_command": "curl -X POST '{api_url}/api/v1/deals' -H 'Content-Type: application/json' -H 'Authorization: Bearer {TOKEN}' -d '{\"lead_id\": \"...\", \"name\": \"Test Deal\", \"value\": 10000, \"stage\": \"qualified\"}'"
        }
    },
    {
        "id": "J8.7.3",
        "part_a": "Verify `update_stage` method",
        "part_b": "Test stage changes",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify update_stage method validates stage transitions and updates probability",
            "expect": {
                "code_contains": ["def update_stage", "stage", "probability"]
            }
        }
    },
    {
        "id": "J8.7.4",
        "part_a": "Verify `close_won` method",
        "part_b": "Test winning deal",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify close_won method sets stage to closed_won and probability to 100",
            "expect": {
                "code_contains": ["def close_won", "closed_won", "100"]
            }
        }
    },
    {
        "id": "J8.7.5",
        "part_a": "Verify `close_lost` method",
        "part_b": "Test losing deal",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify close_lost method sets stage to closed_lost with lost_reason",
            "expect": {
                "code_contains": ["def close_lost", "closed_lost", "lost_reason"]
            }
        }
    },
    {
        "id": "J8.7.6",
        "part_a": "Verify `update_value` method",
        "part_b": "Test value updates",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Verify update_value method updates deal value and recalculates weighted_value",
            "expect": {
                "code_contains": ["value", "weighted_value", "probability"]
            }
        }
    }
]

PASS_CRITERIA = [
    "All CRUD methods implemented",
    "Stage validation works",
    "Probability auto-assigned per stage",
    "Lost reason validation works"
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
    lines.append("### Deal Constants")
    lines.append(f"- Deal Stages: {', '.join(DEAL_CONSTANTS['deal_stages'])}")
    lines.append(f"- Lost Reasons: {', '.join(DEAL_CONSTANTS['lost_reasons'])}")
    lines.append("")
    lines.append("### Stage Probabilities")
    for stage, prob in DEAL_CONSTANTS['stage_probabilities'].items():
        lines.append(f"  - {stage}: {prob}%")
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
                lines.append(f"  Curl: {lt['curl_command']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
