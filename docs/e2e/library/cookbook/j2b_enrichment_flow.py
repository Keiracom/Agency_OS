"""
Skill: J2B.7 — Enrichment Flow
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify Prefect enrichment flow orchestrates the full waterfall with error handling.
"""

CHECKS = [
    {
        "id": "J2B.7.1",
        "part_a": "Read `src/orchestration/flows/lead_enrichment_flow.py` — verify flow definition",
        "part_b": "Check Prefect deployment exists",
        "key_files": ["src/orchestration/flows/lead_enrichment_flow.py"]
    },
    {
        "id": "J2B.7.2",
        "part_a": "Verify flow accepts `assignment_id` parameter and loads assignment data",
        "part_b": "Trace `get_assignment_for_enrichment_task` data loading",
        "key_files": ["src/orchestration/flows/lead_enrichment_flow.py"]
    },
    {
        "id": "J2B.7.3",
        "part_a": "Verify enrichment_status transitions: pending -> in_progress -> completed/failed",
        "part_b": "Trigger flow and monitor status changes in DB",
        "key_files": ["src/orchestration/flows/lead_enrichment_flow.py"]
    },
    {
        "id": "J2B.7.4",
        "part_a": "Verify batch flow `batch_lead_enrichment_flow` exists for multiple leads",
        "part_b": "Test batch enrichment with 3 assignments",
        "key_files": ["src/orchestration/flows/lead_enrichment_flow.py"]
    },
    {
        "id": "J2B.7.5",
        "part_a": "Verify error handling: LinkedIn failures don't crash flow, partial enrichment continues",
        "part_b": "Test with invalid LinkedIn URL to verify graceful failure",
        "key_files": ["src/orchestration/flows/lead_enrichment_flow.py"]
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
