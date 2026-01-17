"""
Skill: J8.12 — External CRM Sync
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify deals can sync from external CRM.
"""

CHECKS = [
    {
        "id": "J8.12.1",
        "part_a": "Read `sync_from_external` method (lines 727-847)",
        "part_b": "N/A",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.12.2",
        "part_a": "Verify stage mapping from HubSpot",
        "part_b": "Check mapping",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.12.3",
        "part_a": "Verify stage mapping from Salesforce",
        "part_b": "Check mapping",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.12.4",
        "part_a": "Verify stage mapping from Pipedrive",
        "part_b": "Check mapping",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.12.5",
        "part_a": "Verify upsert logic (create or update)",
        "part_b": "Test both",
        "key_files": ["src/services/deal_service.py"]
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
