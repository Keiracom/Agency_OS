"""
Skill: J2B.7 — Enrichment Flow
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify Prefect enrichment flow orchestrates the full waterfall with error handling.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co"
}

# =============================================================================
# FLOW CONFIGURATION
# =============================================================================

FLOW_CONFIG = {
    "deployment_name": "lead-enrichment-flow",
    "status_transitions": ["pending", "in_progress", "completed", "failed"],
    "retry_policy": {"attempts": 2, "delay_seconds": 10},
    "batch_size": 10
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2B.7.1",
        "part_a": "Read `src/orchestration/flows/lead_enrichment_flow.py` — verify flow definition",
        "part_b": "Check Prefect deployment exists",
        "key_files": ["src/orchestration/flows/lead_enrichment_flow.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{prefect_url}/api/deployments/name/lead-enrichment/lead-enrichment-flow",
            "auth": False,
            "expect": {
                "status": 200,
                "body_has_field": "id"
            },
            "curl_command": """curl -X GET '{prefect_url}/api/deployments/name/lead-enrichment/lead-enrichment-flow'"""
        }
    },
    {
        "id": "J2B.7.2",
        "part_a": "Verify flow accepts `assignment_id` parameter and loads assignment data",
        "part_b": "Trace `get_assignment_for_enrichment_task` data loading",
        "key_files": ["src/orchestration/flows/lead_enrichment_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Flow accepts assignment_id parameter",
            "expect": {
                "code_contains": ["assignment_id", "get_assignment", "load"]
            }
        }
    },
    {
        "id": "J2B.7.3",
        "part_a": "Verify enrichment_status transitions: pending -> in_progress -> completed/failed",
        "part_b": "Trigger flow and monitor status changes in DB",
        "key_files": ["src/orchestration/flows/lead_enrichment_flow.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT la.id, la.enrichment_status,
                       la.enrichment_started_at,
                       la.enrichment_completed_at,
                       la.enrichment_error
                FROM lead_assignments la
                WHERE la.enrichment_status IS NOT NULL
                ORDER BY la.updated_at DESC
                LIMIT 10;
            """,
            "expect": {
                "status_values": ["pending", "in_progress", "completed", "failed"]
            }
        }
    },
    {
        "id": "J2B.7.4",
        "part_a": "Verify batch flow `batch_lead_enrichment_flow` exists for multiple leads",
        "part_b": "Test batch enrichment with 3 assignments",
        "key_files": ["src/orchestration/flows/lead_enrichment_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Batch enrichment flow exists",
            "expect": {
                "code_contains": ["batch_lead_enrichment", "assignment_ids", "for", "enrich"]
            }
        }
    },
    {
        "id": "J2B.7.5",
        "part_a": "Verify error handling: LinkedIn failures don't crash flow, partial enrichment continues",
        "part_b": "Test with invalid LinkedIn URL to verify graceful failure",
        "key_files": ["src/orchestration/flows/lead_enrichment_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Error handling with retries implemented",
            "expect": {
                "code_contains": ["try", "except", "retry", "failed", "error"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Flow runs via Prefect with proper task orchestration",
    "Assignment data loaded correctly at flow start",
    "Status transitions tracked in database",
    "Batch enrichment processes multiple leads",
    "Errors handled gracefully with retries (2x, 10s delay)"
]

KEY_FILES = [
    "src/orchestration/flows/lead_enrichment_flow.py",
    "src/engines/scout.py",
    "src/models/lead.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Flow Configuration")
    for key, value in FLOW_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
