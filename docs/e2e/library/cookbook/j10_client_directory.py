"""
Skill: J10.7 — Client Directory
Journey: J10 - Admin Dashboard
Checks: 7

Purpose: Verify client listing and management functionality.
"""

CHECKS = [
    {
        "id": "J10.7.1",
        "part_a": "Read `frontend/app/admin/clients/page.tsx` — verify client list",
        "part_b": "Load clients page, verify list renders",
        "key_files": ["frontend/app/admin/clients/page.tsx"]
    },
    {
        "id": "J10.7.2",
        "part_a": "Verify client search functionality",
        "part_b": "Search for client by name, verify results filter",
        "key_files": ["frontend/app/admin/clients/page.tsx"]
    },
    {
        "id": "J10.7.3",
        "part_a": "Verify client status indicators",
        "part_b": "Check active/paused/cancelled status displays",
        "key_files": ["frontend/app/admin/clients/page.tsx"]
    },
    {
        "id": "J10.7.4",
        "part_a": "Verify client lead count displays",
        "part_b": "Check lead count matches actual leads for client",
        "key_files": ["frontend/app/admin/clients/page.tsx"]
    },
    {
        "id": "J10.7.5",
        "part_a": "Verify client campaign count displays",
        "part_b": "Check campaign count matches actual campaigns",
        "key_files": ["frontend/app/admin/clients/page.tsx"]
    },
    {
        "id": "J10.7.6",
        "part_a": "Verify click navigates to client detail",
        "part_b": "Click client row, verify navigation to detail page",
        "key_files": ["frontend/app/admin/clients/page.tsx", "frontend/app/admin/clients/[id]/page.tsx"]
    },
    {
        "id": "J10.7.7",
        "part_a": "Verify pagination or infinite scroll",
        "part_b": "Navigate pages, verify data loads correctly",
        "key_files": ["frontend/app/admin/clients/page.tsx"]
    }
]

PASS_CRITERIA = [
    "Client list renders with data",
    "Search filters clients correctly",
    "Status indicators are accurate",
    "Lead counts are accurate",
    "Campaign counts are accurate",
    "Navigation to detail works",
    "Pagination functions correctly"
]

KEY_FILES = [
    "frontend/app/admin/clients/page.tsx",
    "frontend/app/admin/clients/[id]/page.tsx",
    "src/api/routes/admin.py"
]

# Client Status Reference
CLIENT_STATUSES = [
    {"status": "active", "color": "green", "description": "Client is active and campaigns running"},
    {"status": "paused", "color": "yellow", "description": "Client paused all campaigns"},
    {"status": "cancelled", "color": "red", "description": "Client cancelled subscription"},
    {"status": "onboarding", "color": "blue", "description": "Client in onboarding process"}
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
