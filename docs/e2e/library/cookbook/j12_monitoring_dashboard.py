"""
Skill: J12.7 — Monitoring Dashboard
Journey: J12 - SDK Rollout & Monitoring
Checks: 6

Purpose: Verify admin dashboard shows SDK metrics.
"""

CHECKS = [
    {
        "id": "J12.7.1",
        "part_a": "Verify SDK metrics page exists",
        "part_b": "Navigate to /admin/sdk/metrics — page loads",
        "key_files": ["frontend/app/admin/sdk/metrics/page.tsx"]
    },
    {
        "id": "J12.7.2",
        "part_a": "Verify daily cost chart displayed",
        "part_b": "Check chart shows SDK cost per day for last 30 days",
        "key_files": ["frontend/app/admin/sdk/metrics/page.tsx"]
    },
    {
        "id": "J12.7.3",
        "part_a": "Verify cost by agent type breakdown",
        "part_b": "Check: enrichment, email, voice_kb, objection costs shown",
        "key_files": ["frontend/app/admin/sdk/metrics/page.tsx"]
    },
    {
        "id": "J12.7.4",
        "part_a": "Verify cache hit rate metric displayed",
        "part_b": "Check percentage shown with warning if < 50%",
        "key_files": ["frontend/app/admin/sdk/metrics/page.tsx"]
    },
    {
        "id": "J12.7.5",
        "part_a": "Verify average turns per call metric",
        "part_b": "Check metric helps identify runaway agents",
        "key_files": ["frontend/app/admin/sdk/metrics/page.tsx"]
    },
    {
        "id": "J12.7.6",
        "part_a": "Verify API endpoint returns metrics data",
        "part_b": "Check GET /api/v1/admin/sdk/metrics returns JSON",
        "key_files": ["src/api/routes/admin.py"]
    }
]

PASS_CRITERIA = [
    "SDK metrics page accessible",
    "Daily cost chart works",
    "Cost breakdown by agent type",
    "Cache hit rate visible",
    "Turns per call tracked",
    "API returns correct data"
]

KEY_FILES = [
    "frontend/app/admin/sdk/metrics/page.tsx",
    "src/api/routes/admin.py"
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
