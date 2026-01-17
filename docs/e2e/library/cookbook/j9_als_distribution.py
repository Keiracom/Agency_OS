"""
Skill: J9.4 — ALS Distribution Widget
Journey: J9 - Client Dashboard
Checks: 6

Purpose: Verify ALS (Agency Lead Score) distribution widget displays correct
tier breakdown (Hot, Warm, Cool, Cold, Dead) with accurate counts and visual chart.
"""

CHECKS = [
    {
        "id": "J9.4.1",
        "part_a": "Verify ALS distribution widget renders",
        "part_b": "Check widget displays on dashboard with chart visualization",
        "key_files": ["frontend/app/dashboard/page.tsx"]
    },
    {
        "id": "J9.4.2",
        "part_a": "Verify correct tier thresholds are used",
        "part_b": "Hot: 85-100, Warm: 60-84, Cool: 35-59, Cold: 20-34, Dead: <20",
        "key_files": ["frontend/app/dashboard/page.tsx", "src/engines/scorer.py"]
    },
    {
        "id": "J9.4.3",
        "part_a": "Verify Hot tier count matches database",
        "part_b": "Count leads with score >= 85 for tenant, compare to widget",
        "key_files": ["src/api/routes/leads.py"]
    },
    {
        "id": "J9.4.4",
        "part_a": "Verify all tier counts sum to total leads",
        "part_b": "Hot + Warm + Cool + Cold + Dead = Total Leads",
        "key_files": ["frontend/app/dashboard/page.tsx"]
    },
    {
        "id": "J9.4.5",
        "part_a": "Verify tier colors are visually distinct",
        "part_b": "Check each tier has appropriate color coding (green, yellow, orange, blue, gray)",
        "key_files": ["frontend/app/dashboard/page.tsx"]
    },
    {
        "id": "J9.4.6",
        "part_a": "Verify clicking tier filters leads list",
        "part_b": "Click on a tier segment, navigate to leads filtered by that tier",
        "key_files": ["frontend/app/dashboard/page.tsx", "frontend/app/dashboard/leads/page.tsx"]
    },
]

PASS_CRITERIA = [
    "ALS distribution widget renders with chart",
    "Tier thresholds match spec (Hot: 85-100, etc.)",
    "Tier counts match database records",
    "All tier counts sum to total leads",
    "Each tier has distinct color coding",
    "Clicking tier filters leads list correctly",
]

KEY_FILES = [
    "frontend/app/dashboard/page.tsx",
    "frontend/components/leads/ALSScorecard.tsx",
    "src/engines/scorer.py",
    "src/api/routes/leads.py",
]


def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    lines.append("")
    lines.append("### Key Files")
    for f in KEY_FILES:
        lines.append(f"- {f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_instructions())
