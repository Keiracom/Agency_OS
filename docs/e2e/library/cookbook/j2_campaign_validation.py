"""
Skill: J2.2 — Create Campaign Form
Journey: J2 - Campaign Creation & Management
Checks: 6

Purpose: Verify campaign creation flow with simplified fields.
"""

CHECKS = [
    {
        "id": "J2.2.1",
        "part_a": "Read `frontend/app/dashboard/campaigns/new/page.tsx` — verify `useCreateCampaign` hook",
        "part_b": "Navigate to `/dashboard/campaigns/new`",
        "key_files": ["frontend/app/dashboard/campaigns/new/page.tsx"]
    },
    {
        "id": "J2.2.2",
        "part_a": "Verify ICP is fetched via `GET /api/v1/clients/{id}/icp`",
        "part_b": "Check ICP industries/titles display",
        "key_files": ["src/api/routes/clients.py"]
    },
    {
        "id": "J2.2.3",
        "part_a": "Verify form fields: name (required), description (optional), permission_mode",
        "part_b": "Fill form, check validation",
        "key_files": ["frontend/app/dashboard/campaigns/new/page.tsx"]
    },
    {
        "id": "J2.2.4",
        "part_a": "Check channel allocation is NOT in form (system determines)",
        "part_b": "Verify no channel inputs",
        "key_files": ["frontend/app/dashboard/campaigns/new/page.tsx"]
    },
    {
        "id": "J2.2.5",
        "part_a": "Verify POST `/api/v1/campaigns` in `campaigns.py` creates campaign",
        "part_b": "Submit form, verify 201 response",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.2.6",
        "part_a": "Verify campaign created with status='draft'",
        "part_b": "Check DB for new campaign",
        "key_files": ["src/api/routes/campaigns.py"]
    }
]

PASS_CRITERIA = [
    "Form only has name, description, permission_mode",
    "ICP is displayed but not editable (link to settings)",
    "Campaign created successfully",
    "Redirects to campaign list after creation"
]

KEY_FILES = [
    "frontend/app/dashboard/campaigns/new/page.tsx",
    "src/api/routes/campaigns.py",
    "src/api/routes/clients.py"
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
