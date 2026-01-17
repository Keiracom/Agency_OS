"""
Skill: J1.9 — Manual Entry Fallback
Journey: J1 - Signup & Onboarding
Checks: 7

Purpose: Verify manual entry page handles scraper failures.
"""

CHECKS = [
    {
        "id": "J1.9.1",
        "part_a": "Read `frontend/app/onboarding/manual-entry/page.tsx` — verify 3 tabs",
        "part_b": "Load page, verify tabs",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"]
    },
    {
        "id": "J1.9.2",
        "part_a": "Verify 'Paste Content' tab calls `/api/v1/onboarding/analyze-content`",
        "part_b": "Paste content, submit",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"]
    },
    {
        "id": "J1.9.3",
        "part_a": "Verify min 100 character validation",
        "part_b": "Submit short content, verify error",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"]
    },
    {
        "id": "J1.9.4",
        "part_a": "Verify 'Use LinkedIn' tab calls `/api/v1/onboarding/analyze-linkedin`",
        "part_b": "Enter LinkedIn URL, submit",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"]
    },
    {
        "id": "J1.9.5",
        "part_a": "Verify LinkedIn URL validation (must contain linkedin.com/company)",
        "part_b": "Enter invalid URL, verify error",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"]
    },
    {
        "id": "J1.9.6",
        "part_a": "Verify 'Skip' tab calls `/api/v1/onboarding/skip-icp`",
        "part_b": "Enter company name, skip",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"]
    },
    {
        "id": "J1.9.7",
        "part_a": "Verify failedUrl preserved from query param",
        "part_b": "Access with ?url=xxx, verify shown",
        "key_files": ["frontend/app/onboarding/manual-entry/page.tsx"]
    }
]

PASS_CRITERIA = [
    "All 3 tabs render",
    "Paste content validated (min 100 chars)",
    "LinkedIn URL validated",
    "Skip creates basic profile",
    "Failed URL shown to user"
]

KEY_FILES = [
    "frontend/app/onboarding/manual-entry/page.tsx"
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
