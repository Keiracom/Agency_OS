"""
Skill: J2.6 — Lead Pool Assignment
Journey: J2 - Campaign Creation & Management
Checks: 6

Purpose: Verify leads are assigned from pool to clients exclusively.

Exclusivity Model:
- lead_pool.pool_status changes from 'available' to 'assigned'
- lead_assignments links pool lead to client
- Client's leads table gets copy of lead data
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
# POOL STATUS TRANSITIONS
# =============================================================================

POOL_STATUS_TRANSITIONS = [
    {"from": "available", "to": "assigned", "trigger": "Client assignment"},
    {"from": "assigned", "to": "available", "trigger": "Client releases lead"},
    {"from": "available", "to": "excluded", "trigger": "Marked as bad data"},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2.6.1",
        "part_a": "Read `src/orchestration/flows/pool_assignment_flow.py`",
        "part_b": "Identify assignment logic",
        "key_files": ["src/orchestration/flows/pool_assignment_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Assignment flow exists with proper structure",
            "expect": {
                "code_contains": ["@flow", "assign", "pool", "client"]
            }
        }
    },
    {
        "id": "J2.6.2",
        "part_a": "Read `src/services/lead_allocator_service.py` — verify `allocate_leads`",
        "part_b": "Check ICP matching",
        "key_files": ["src/services/lead_allocator_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Allocator uses ICP criteria for matching",
            "expect": {
                "code_contains": ["icp", "industry", "title", "location", "allocate"]
            }
        }
    },
    {
        "id": "J2.6.3",
        "part_a": "Verify `lead_assignments` table stores client-lead relationships",
        "part_b": "Query table",
        "key_files": ["src/services/lead_allocator_service.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT la.id, la.client_id, la.pool_lead_id, la.campaign_id,
                       la.assigned_at, la.channel
                FROM lead_assignments la
                ORDER BY la.assigned_at DESC
                LIMIT 10;
            """,
            "expect": {
                "table_exists": True,
                "rows_have_fields": ["client_id", "pool_lead_id", "assigned_at"]
            }
        }
    },
    {
        "id": "J2.6.4",
        "part_a": "Verify exclusivity: one lead = one client (pool_status changes)",
        "part_b": "Check pool_status update",
        "key_files": ["src/services/lead_pool_service.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT lp.id, lp.email, lp.pool_status,
                       (SELECT COUNT(*) FROM lead_assignments la WHERE la.pool_lead_id = lp.id) as assignment_count
                FROM lead_pool lp
                WHERE lp.pool_status = 'assigned'
                LIMIT 10;
            """,
            "expect": {
                "assigned_leads_have_assignments": True,
                "pool_status": "assigned"
            },
            "note": "Assigned leads should have pool_status='assigned' and 1+ assignments"
        }
    },
    {
        "id": "J2.6.5",
        "part_a": "Verify campaign_id linked to assignment",
        "part_b": "Check assignment record",
        "key_files": ["src/services/lead_allocator_service.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT la.id, la.campaign_id, c.name as campaign_name
                FROM lead_assignments la
                JOIN campaigns c ON c.id = la.campaign_id
                LIMIT 5;
            """,
            "expect": {
                "campaign_id_not_null": True,
                "join_succeeds": True
            }
        }
    },
    {
        "id": "J2.6.6",
        "part_a": "Verify assignment creates entry in `leads` table for client",
        "part_b": "Check leads table",
        "key_files": ["src/services/lead_allocator_service.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.client_id, l.email, l.pool_lead_id, l.campaign_id
                FROM leads l
                WHERE l.pool_lead_id IS NOT NULL
                ORDER BY l.created_at DESC
                LIMIT 10;
            """,
            "expect": {
                "pool_lead_id_linked": True,
                "client_id_set": True
            },
            "note": "leads.pool_lead_id should reference lead_pool.id"
        }
    }
]

PASS_CRITERIA = [
    "Assignment flow runs via Prefect",
    "ICP criteria used for matching",
    "Lead marked as assigned (not available to others)",
    "lead_assignments record created with campaign_id",
    "Client's leads table populated with pool reference"
]

KEY_FILES = [
    "src/orchestration/flows/pool_assignment_flow.py",
    "src/services/lead_allocator_service.py",
    "src/services/lead_pool_service.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Pool Status Transitions")
    for t in POOL_STATUS_TRANSITIONS:
        lines.append(f"  {t['from']} → {t['to']}: {t['trigger']}")
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
