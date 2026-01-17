"""
Skill: J10.8 — Client Detail Page
Journey: J10 - Admin Dashboard
Checks: 5

Purpose: Verify individual client detail page functionality.
"""

CHECKS = [
    {
        "id": "J10.8.1",
        "part_a": "Read `frontend/app/admin/clients/[id]/page.tsx` — verify layout",
        "part_b": "Load client detail page, verify sections render",
        "key_files": ["frontend/app/admin/clients/[id]/page.tsx"]
    },
    {
        "id": "J10.8.2",
        "part_a": "Verify client profile section displays",
        "part_b": "Check company name, ICP, settings display",
        "key_files": ["frontend/app/admin/clients/[id]/page.tsx"]
    },
    {
        "id": "J10.8.3",
        "part_a": "Verify client campaigns list",
        "part_b": "Check all campaigns for this client display",
        "key_files": ["frontend/app/admin/clients/[id]/page.tsx"]
    },
    {
        "id": "J10.8.4",
        "part_a": "Verify client leads section",
        "part_b": "Check leads associated with client display",
        "key_files": ["frontend/app/admin/clients/[id]/page.tsx"]
    },
    {
        "id": "J10.8.5",
        "part_a": "Verify client actions (pause, edit, delete)",
        "part_b": "Test pause client action, verify status change",
        "key_files": ["frontend/app/admin/clients/[id]/page.tsx", "src/api/routes/admin.py"]
    }
]

PASS_CRITERIA = [
    "Client detail page loads correctly",
    "Profile information displays accurately",
    "Campaigns list is complete",
    "Leads section shows associated leads",
    "Client actions work correctly"
]

KEY_FILES = [
    "frontend/app/admin/clients/[id]/page.tsx",
    "src/api/routes/admin.py"
]

# Client Detail Sections Reference
CLIENT_SECTIONS = [
    {"section": "Profile", "fields": ["company_name", "industry", "website", "icp_summary"]},
    {"section": "Campaigns", "fields": ["name", "status", "leads_count", "created_at"]},
    {"section": "Leads", "fields": ["name", "company", "score", "status"]},
    {"section": "Settings", "fields": ["outreach_frequency", "channels", "timezone"]},
    {"section": "Billing", "fields": ["plan", "mrr", "next_billing_date"]}
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
