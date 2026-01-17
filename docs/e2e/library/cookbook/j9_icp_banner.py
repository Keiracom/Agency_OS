"""
Skill: J9.13 — ICP Banner and Modal
Journey: J9 - Client Dashboard
Checks: 4

Purpose: Verify ICP (Ideal Customer Profile) progress banner displays completion
status and modal allows review and editing of ICP criteria.
"""

CHECKS = [
    {
        "id": "J9.13.1",
        "part_a": "Verify ICP progress banner renders",
        "part_b": "Check ICPProgressBanner component displays on dashboard",
        "key_files": ["frontend/components/icp-progress-banner.tsx", "frontend/app/dashboard/page.tsx"]
    },
    {
        "id": "J9.13.2",
        "part_a": "Verify banner shows completion percentage",
        "part_b": "Banner displays ICP completion progress (e.g., '75% complete')",
        "key_files": ["frontend/components/icp-progress-banner.tsx"]
    },
    {
        "id": "J9.13.3",
        "part_a": "Verify clicking banner opens ICP modal",
        "part_b": "Click banner, ICPReviewModal opens with ICP criteria",
        "key_files": ["frontend/components/icp-progress-banner.tsx", "frontend/components/icp-review-modal.tsx"]
    },
    {
        "id": "J9.13.4",
        "part_a": "Verify ICP modal displays criteria",
        "part_b": "Modal shows industries, company sizes, job titles, locations",
        "key_files": ["frontend/components/icp-review-modal.tsx"]
    },
]

PASS_CRITERIA = [
    "ICP progress banner renders on dashboard",
    "Banner shows accurate completion percentage",
    "Clicking banner opens ICP review modal",
    "Modal displays all ICP criteria fields",
]

KEY_FILES = [
    "frontend/components/icp-progress-banner.tsx",
    "frontend/components/icp-review-modal.tsx",
    "frontend/app/dashboard/page.tsx",
    "src/api/routes/onboarding.py",
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
