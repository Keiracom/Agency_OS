"""
Skill: J0.3 — Prefect Configuration Verification
Journey: J0 - Infrastructure & Wiring Audit
Checks: 6

Purpose: Confirm Prefect is self-hosted and flows are deployed.
"""

CHECKS = [
    {
        "id": "J0.3.1",
        "part_a": "Read prefect.yaml — verify work pool `agency-os-pool`",
        "part_b": "Check Prefect UI → Work Pools",
        "key_files": ["prefect.yaml"]
    },
    {
        "id": "J0.3.2",
        "part_a": "Read prefect.yaml — list all 15 flows",
        "part_b": "Check Prefect UI → Deployments",
        "key_files": ["prefect.yaml"]
    },
    {
        "id": "J0.3.3",
        "part_a": "Verify webhook-triggered flows are ACTIVE",
        "part_b": "Check deployment schedules in UI",
        "key_files": []
    },
    {
        "id": "J0.3.4",
        "part_a": "Verify scheduled flows are PAUSED by default",
        "part_b": "Confirm schedules show 'Paused'",
        "key_files": []
    },
    {
        "id": "J0.3.5",
        "part_a": "Read scripts/start-prefect-worker.sh — verify pool creation",
        "part_b": "Check worker creates pool on startup",
        "key_files": ["scripts/start-prefect-worker.sh"]
    },
    {
        "id": "J0.3.6",
        "part_a": "Verify PREFECT_API_DATABASE_CONNECTION_URL is PostgreSQL",
        "part_b": "Check Prefect server logs for 'Using PostgreSQL'",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "Work pool `agency-os-pool` exists",
    "All 15 flows deployed",
    "Webhook flows are Active",
    "Scheduled flows are Paused",
    "Prefect using PostgreSQL (not SQLite)"
]

KEY_FILES = [
    "prefect.yaml",
    "scripts/start-prefect-worker.sh"
]

# Expected Flows Reference
EXPECTED_FLOWS = [
    {"name": "campaign-flow", "trigger": "Webhook", "expected_state": "Active"},
    {"name": "enrichment-flow", "trigger": "Schedule (2 AM)", "expected_state": "PAUSED"},
    {"name": "outreach-flow", "trigger": "Schedule (8-6 PM)", "expected_state": "PAUSED"},
    {"name": "reply-recovery-flow", "trigger": "Schedule (6-hourly)", "expected_state": "PAUSED"},
    {"name": "onboarding-flow", "trigger": "Webhook", "expected_state": "Active"},
    {"name": "icp-reextract-flow", "trigger": "Webhook", "expected_state": "Active"},
    {"name": "pool-population-flow", "trigger": "Webhook", "expected_state": "Active"},
    {"name": "pool-assignment-flow", "trigger": "Webhook", "expected_state": "Active"},
    {"name": "pool-daily-allocation-flow", "trigger": "Schedule (6 AM)", "expected_state": "PAUSED"},
    {"name": "intelligence-flow", "trigger": "Webhook", "expected_state": "Active"},
    {"name": "trigger-lead-research", "trigger": "Webhook", "expected_state": "Active"},
    {"name": "pattern-learning-flow", "trigger": "Schedule (Sunday 3 AM)", "expected_state": "PAUSED"},
    {"name": "client-pattern-learning-flow", "trigger": "Webhook", "expected_state": "Active"},
    {"name": "pattern-backfill-flow", "trigger": "Manual", "expected_state": "Active"},
    {"name": "client-backfill-flow", "trigger": "Webhook", "expected_state": "Active"},
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
