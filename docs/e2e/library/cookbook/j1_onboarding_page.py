"""
Skill: J1.6 — Onboarding Page (Website URL)
Journey: J1 - Signup & Onboarding
Checks: 6

Purpose: Verify main onboarding page accepts website URL and triggers extraction.
"""

CHECKS = [
    {
        "id": "J1.6.1",
        "part_a": "Read `frontend/app/onboarding/page.tsx` — verify form exists",
        "part_b": "Load /onboarding, verify input field",
        "key_files": ["frontend/app/onboarding/page.tsx"]
    },
    {
        "id": "J1.6.2",
        "part_a": "Verify API call to `/api/v1/onboarding/analyze`",
        "part_b": "Submit URL, check network request",
        "key_files": ["frontend/app/onboarding/page.tsx"]
    },
    {
        "id": "J1.6.3",
        "part_a": "Verify Authorization header includes session token",
        "part_b": "Check request headers",
        "key_files": ["frontend/app/onboarding/page.tsx"]
    },
    {
        "id": "J1.6.4",
        "part_a": "Verify `job_id` stored in localStorage",
        "part_b": "After submit, check localStorage",
        "key_files": ["frontend/app/onboarding/page.tsx"]
    },
    {
        "id": "J1.6.5",
        "part_a": "Verify redirect to `/dashboard?icp_job={job_id}`",
        "part_b": "After submit, verify URL",
        "key_files": ["frontend/app/onboarding/page.tsx"]
    },
    {
        "id": "J1.6.6",
        "part_a": "Verify 'Skip for now' link goes to /onboarding/skip",
        "part_b": "Click skip, verify navigation",
        "key_files": ["frontend/app/onboarding/page.tsx"]
    }
]

PASS_CRITERIA = [
    "Page renders with URL input",
    "Submit triggers API call",
    "Job ID received and stored",
    "Redirect to dashboard with job param"
]

KEY_FILES = [
    "frontend/app/onboarding/page.tsx",
    "src/api/routes/onboarding.py"
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
