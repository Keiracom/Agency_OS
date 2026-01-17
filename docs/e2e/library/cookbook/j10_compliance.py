"""
Skill: J10.14 — Compliance Pages
Journey: J10 - Admin Dashboard
Checks: 6

Purpose: Verify compliance management including suppression lists and bounces.
"""

CHECKS = [
    {
        "id": "J10.14.1",
        "part_a": "Read `frontend/app/admin/compliance/page.tsx` — verify layout",
        "part_b": "Load compliance page, verify sections render",
        "key_files": ["frontend/app/admin/compliance/page.tsx"]
    },
    {
        "id": "J10.14.2",
        "part_a": "Read `frontend/app/admin/compliance/suppression/page.tsx` — verify list",
        "part_b": "Load suppression page, verify suppressed emails display",
        "key_files": ["frontend/app/admin/compliance/suppression/page.tsx"]
    },
    {
        "id": "J10.14.3",
        "part_a": "Verify suppression list add functionality",
        "part_b": "Add email to suppression, verify it appears in list",
        "key_files": ["frontend/app/admin/compliance/suppression/page.tsx", "src/api/routes/admin.py"]
    },
    {
        "id": "J10.14.4",
        "part_a": "Read `frontend/app/admin/compliance/bounces/page.tsx` — verify display",
        "part_b": "Load bounces page, verify bounce list renders",
        "key_files": ["frontend/app/admin/compliance/bounces/page.tsx"]
    },
    {
        "id": "J10.14.5",
        "part_a": "Verify bounce categorization",
        "part_b": "Check hard/soft bounce categories display correctly",
        "key_files": ["frontend/app/admin/compliance/bounces/page.tsx"]
    },
    {
        "id": "J10.14.6",
        "part_a": "Verify DNCR (Do Not Call Registry) integration",
        "part_b": "Check DNCR status for phone numbers displays",
        "key_files": ["frontend/app/admin/compliance/page.tsx", "src/integrations/dncr.py"]
    }
]

PASS_CRITERIA = [
    "Compliance page loads correctly",
    "Suppression list displays and is manageable",
    "Adding to suppression works",
    "Bounce list displays correctly",
    "Bounce categories are accurate",
    "DNCR status is visible"
]

KEY_FILES = [
    "frontend/app/admin/compliance/page.tsx",
    "frontend/app/admin/compliance/suppression/page.tsx",
    "frontend/app/admin/compliance/bounces/page.tsx",
    "src/api/routes/admin.py",
    "src/integrations/dncr.py"
]

# Compliance Types Reference
COMPLIANCE_TYPES = [
    {"type": "suppression", "reason": "Unsubscribe request", "action": "Never email again"},
    {"type": "hard_bounce", "reason": "Invalid email", "action": "Add to suppression"},
    {"type": "soft_bounce", "reason": "Temporary failure", "action": "Retry later"},
    {"type": "spam_complaint", "reason": "Marked as spam", "action": "Add to suppression"},
    {"type": "dncr", "reason": "Do Not Call Registry", "action": "Never call/SMS"}
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
