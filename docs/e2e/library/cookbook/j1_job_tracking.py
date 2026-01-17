"""
Skill: J1.11 — ICP Extraction Job Tracking
Journey: J1 - Signup & Onboarding
Checks: 6

Purpose: Verify extraction job progress is tracked and reported.
"""

CHECKS = [
    {
        "id": "J1.11.1",
        "part_a": "Verify `icp_extraction_jobs` table exists",
        "part_b": "Query table schema",
        "key_files": []
    },
    {
        "id": "J1.11.2",
        "part_a": "Verify job created with status='pending' on analyze",
        "part_b": "Check database after submit",
        "key_files": ["src/api/routes/onboarding.py"]
    },
    {
        "id": "J1.11.3",
        "part_a": "Verify status updates to 'running' when Prefect starts",
        "part_b": "Check during extraction",
        "key_files": ["src/orchestration/flows/onboarding_flow.py"]
    },
    {
        "id": "J1.11.4",
        "part_a": "Verify `completed_steps` and `total_steps` updated",
        "part_b": "Poll status endpoint",
        "key_files": ["src/api/routes/onboarding.py"]
    },
    {
        "id": "J1.11.5",
        "part_a": "Verify `extracted_icp` JSONB populated on completion",
        "part_b": "Query database after complete",
        "key_files": ["src/orchestration/flows/onboarding_flow.py"]
    },
    {
        "id": "J1.11.6",
        "part_a": "Verify `error_message` populated on failure",
        "part_b": "Trigger failure, check database",
        "key_files": ["src/orchestration/flows/onboarding_flow.py"]
    }
]

PASS_CRITERIA = [
    "Job record created",
    "Progress tracked",
    "ICP data saved on success",
    "Error captured on failure"
]

KEY_FILES = [
    "src/api/routes/onboarding.py",
    "src/orchestration/flows/onboarding_flow.py"
]

# Job Status Flow
JOB_STATUS_FLOW = "pending → running → completed (or failed)"

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
