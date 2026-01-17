"""
Skill: J8.11 — CRM Push Service
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify meetings pushed to client CRM.
"""

CHECKS = [
    {
        "id": "J8.11.1",
        "part_a": "Read `src/services/crm_push_service.py`",
        "part_b": "N/A",
        "key_files": ["src/services/crm_push_service.py"]
    },
    {
        "id": "J8.11.2",
        "part_a": "Verify HubSpot push (OAuth)",
        "part_b": "Test push",
        "key_files": ["src/services/crm_push_service.py"]
    },
    {
        "id": "J8.11.3",
        "part_a": "Verify Pipedrive push (API key)",
        "part_b": "Test push",
        "key_files": ["src/services/crm_push_service.py"]
    },
    {
        "id": "J8.11.4",
        "part_a": "Verify Close push (API key)",
        "part_b": "Test push",
        "key_files": ["src/services/crm_push_service.py"]
    },
    {
        "id": "J8.11.5",
        "part_a": "Verify non-blocking (failure doesn't stop meeting)",
        "part_b": "Test error handling",
        "key_files": ["src/services/crm_push_service.py"]
    }
]

PASS_CRITERIA = [
    "CRM push triggered on meeting creation",
    "Contact created/found in CRM",
    "Deal created in CRM",
    "Push failure doesn't break meeting creation"
]

KEY_FILES = [
    "src/services/crm_push_service.py"
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
