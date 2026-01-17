"""
Skill: J1.12 — ICP Confirmation Flow
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify ICP can be confirmed and applied to client.
"""

CHECKS = [
    {
        "id": "J1.12.1",
        "part_a": "Verify POST /onboarding/confirm endpoint",
        "part_b": "Call with job_id",
        "key_files": ["src/api/routes/onboarding.py"]
    },
    {
        "id": "J1.12.2",
        "part_a": "Verify ICP fields saved to clients table",
        "part_b": "Query clients table",
        "key_files": ["src/api/routes/onboarding.py"]
    },
    {
        "id": "J1.12.3",
        "part_a": "Verify `icp_confirmed_at` timestamp set",
        "part_b": "Check column populated",
        "key_files": ["src/api/routes/onboarding.py"]
    },
    {
        "id": "J1.12.4",
        "part_a": "Verify pool population Prefect flow triggered",
        "part_b": "Check Prefect UI",
        "key_files": ["src/api/routes/onboarding.py"]
    },
    {
        "id": "J1.12.5",
        "part_a": "Verify adjustments can be applied before confirm",
        "part_b": "Pass adjustments, verify saved",
        "key_files": ["src/api/routes/onboarding.py"]
    }
]

PASS_CRITERIA = [
    "Confirm saves ICP to client",
    "All fields populated",
    "Pool population triggered",
    "Adjustments applied if provided"
]

KEY_FILES = [
    "src/api/routes/onboarding.py"
]

# Fields Updated on Confirm
CONFIRM_FIELDS = [
    {"column": "website_url", "source": "ICP data"},
    {"column": "company_description", "source": "ICP data"},
    {"column": "services_offered", "source": "ICP data (TEXT[])"},
    {"column": "icp_industries", "source": "ICP data (TEXT[])"},
    {"column": "icp_company_sizes", "source": "ICP data (TEXT[])"},
    {"column": "icp_locations", "source": "ICP data (TEXT[])"},
    {"column": "icp_titles", "source": "ICP data (TEXT[])"},
    {"column": "icp_pain_points", "source": "ICP data (TEXT[])"},
    {"column": "als_weights", "source": "ICP data (JSONB)"},
    {"column": "icp_confirmed_at", "source": "NOW()"},
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
