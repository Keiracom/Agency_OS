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

CHECKS = [
    {
        "id": "J2.6.1",
        "part_a": "Read `src/orchestration/flows/pool_assignment_flow.py`",
        "part_b": "Identify assignment logic",
        "key_files": ["src/orchestration/flows/pool_assignment_flow.py"]
    },
    {
        "id": "J2.6.2",
        "part_a": "Read `src/services/lead_allocator_service.py` — verify `allocate_leads`",
        "part_b": "Check ICP matching",
        "key_files": ["src/services/lead_allocator_service.py"]
    },
    {
        "id": "J2.6.3",
        "part_a": "Verify `lead_assignments` table stores client-lead relationships",
        "part_b": "Query table",
        "key_files": ["src/services/lead_allocator_service.py"]
    },
    {
        "id": "J2.6.4",
        "part_a": "Verify exclusivity: one lead = one client (pool_status changes)",
        "part_b": "Check pool_status update",
        "key_files": ["src/services/lead_pool_service.py"]
    },
    {
        "id": "J2.6.5",
        "part_a": "Verify campaign_id linked to assignment",
        "part_b": "Check assignment record",
        "key_files": ["src/services/lead_allocator_service.py"]
    },
    {
        "id": "J2.6.6",
        "part_a": "Verify assignment creates entry in `leads` table for client",
        "part_b": "Check leads table",
        "key_files": ["src/services/lead_allocator_service.py"]
    }
]

PASS_CRITERIA = [
    "Assignment flow runs via Prefect",
    "ICP criteria used for matching",
    "Lead marked as assigned (not available to others)",
    "lead_assignments record created",
    "Client's leads table populated"
]

KEY_FILES = [
    "src/orchestration/flows/pool_assignment_flow.py",
    "src/services/lead_allocator_service.py",
    "src/services/lead_pool_service.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
