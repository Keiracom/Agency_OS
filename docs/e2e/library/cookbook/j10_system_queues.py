"""
Skill: J10.12 — System Queues Page
Journey: J10 - Admin Dashboard
Checks: 4

Purpose: Verify Prefect queue monitoring and management.
"""

CHECKS = [
    {
        "id": "J10.12.1",
        "part_a": "Read `frontend/app/admin/system/queues/page.tsx` — verify queue display",
        "part_b": "Load queues page, verify queue list renders",
        "key_files": ["frontend/app/admin/system/queues/page.tsx"]
    },
    {
        "id": "J10.12.2",
        "part_a": "Verify queue depth displays",
        "part_b": "Check pending job counts are accurate",
        "key_files": ["frontend/app/admin/system/queues/page.tsx", "src/api/routes/admin.py"]
    },
    {
        "id": "J10.12.3",
        "part_a": "Verify failed jobs display",
        "part_b": "Check failed job count and retry options",
        "key_files": ["frontend/app/admin/system/queues/page.tsx"]
    },
    {
        "id": "J10.12.4",
        "part_a": "Verify link to Prefect UI",
        "part_b": "Click 'Open Prefect UI' link, verify redirect",
        "key_files": ["frontend/app/admin/system/queues/page.tsx"]
    }
]

PASS_CRITERIA = [
    "Queue page loads correctly",
    "Queue depths are accurate",
    "Failed jobs display with retry option",
    "Prefect UI link works"
]

KEY_FILES = [
    "frontend/app/admin/system/queues/page.tsx",
    "src/api/routes/admin.py"
]

# Queue Types Reference
QUEUE_TYPES = [
    {"queue": "enrichment", "purpose": "Lead enrichment jobs", "worker": "prefect-worker"},
    {"queue": "outreach", "purpose": "Email/SMS sending jobs", "worker": "prefect-worker"},
    {"queue": "scoring", "purpose": "Lead scoring jobs", "worker": "prefect-worker"},
    {"queue": "scraping", "purpose": "LinkedIn/web scraping jobs", "worker": "prefect-worker"}
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
