"""
Skill: J1.7 — Onboarding API Endpoints
Journey: J1 - Signup & Onboarding
Checks: 6

Purpose: Verify backend onboarding API is complete and triggers Prefect.
"""

CHECKS = [
    {
        "id": "J1.7.1",
        "part_a": "Read `src/api/routes/onboarding.py` — verify POST /onboarding/analyze",
        "part_b": "Call API, verify 202 response",
        "key_files": ["src/api/routes/onboarding.py"]
    },
    {
        "id": "J1.7.2",
        "part_a": "Verify endpoint looks up client from memberships",
        "part_b": "Check query logic",
        "key_files": ["src/api/routes/onboarding.py"]
    },
    {
        "id": "J1.7.3",
        "part_a": "Verify `run_deployment('icp_onboarding_flow/onboarding-flow')` called",
        "part_b": "Check Prefect UI for flow run",
        "key_files": ["src/api/routes/onboarding.py"]
    },
    {
        "id": "J1.7.4",
        "part_a": "Verify GET /onboarding/status/{job_id} returns progress",
        "part_b": "Poll status endpoint",
        "key_files": ["src/api/routes/onboarding.py"]
    },
    {
        "id": "J1.7.5",
        "part_a": "Verify GET /onboarding/result/{job_id} returns extracted ICP",
        "part_b": "After completion, get result",
        "key_files": ["src/api/routes/onboarding.py"]
    },
    {
        "id": "J1.7.6",
        "part_a": "Verify POST /onboarding/confirm saves to clients table",
        "part_b": "Confirm ICP, query database",
        "key_files": ["src/api/routes/onboarding.py"]
    }
]

PASS_CRITERIA = [
    "Analyze endpoint returns job_id",
    "Prefect flow triggered",
    "Status endpoint returns progress",
    "Result endpoint returns ICP data",
    "Confirm endpoint saves to database"
]

KEY_FILES = [
    "src/api/routes/onboarding.py",
    "src/orchestration/flows/onboarding_flow.py"
]

# API Endpoints Reference
API_ENDPOINTS = [
    {"method": "POST", "endpoint": "/onboarding/analyze", "purpose": "Start extraction"},
    {"method": "GET", "endpoint": "/onboarding/status/{job_id}", "purpose": "Check progress"},
    {"method": "GET", "endpoint": "/onboarding/result/{job_id}", "purpose": "Get extracted ICP"},
    {"method": "POST", "endpoint": "/onboarding/confirm", "purpose": "Confirm and apply ICP"},
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
