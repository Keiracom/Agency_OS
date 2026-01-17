"""
Skill: J2.3 — Campaign Detail Page
Journey: J2 - Campaign Creation & Management
Checks: 5

Purpose: Verify campaign detail displays real data.

KNOWN ISSUE: Campaign detail page uses HARDCODED MOCK DATA (lines 14-42).
This MUST be fixed before E2E testing.
"""

CHECKS = [
    {
        "id": "J2.3.1",
        "part_a": "Read `frontend/app/dashboard/campaigns/[id]/page.tsx` — **VERIFY DATA SOURCE**",
        "part_b": "Navigate to `/dashboard/campaigns/{id}`",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"]
    },
    {
        "id": "J2.3.2",
        "part_a": "CRITICAL: Check if using mock data (lines 14-42) or real API",
        "part_b": "Check network tab for API call",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"]
    },
    {
        "id": "J2.3.3",
        "part_a": "Verify GET `/api/v1/campaigns/{id}` returns campaign with metrics",
        "part_b": "Test endpoint directly",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.3.4",
        "part_a": "Verify activate/pause buttons call correct endpoints",
        "part_b": "Click activate/pause",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"]
    },
    {
        "id": "J2.3.5",
        "part_a": "Verify lead list shows real leads",
        "part_b": "Check leads section",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"]
    }
]

PASS_CRITERIA = [
    "Page fetches real campaign data (FIX REQUIRED)",
    "Stats (total leads, contacted, replied) accurate",
    "Activate/Pause buttons work",
    "Lead list loads from API"
]

KEY_FILES = [
    "frontend/app/dashboard/campaigns/[id]/page.tsx",
    "src/api/routes/campaigns.py"
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
