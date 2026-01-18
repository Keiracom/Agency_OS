"""
Skill: J1.11 — ICP Extraction Job Tracking
Journey: J1 - Signup & Onboarding
Checks: 6

Purpose: Verify extraction job progress is tracked and reported.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "test_website": "https://sparro.com.au"
}

# =============================================================================
# JOB STATUS FLOW
# =============================================================================

JOB_STATUS_FLOW = [
    {"status": "pending", "trigger": "API call to /onboarding/analyze"},
    {"status": "running", "trigger": "Prefect flow starts"},
    {"status": "completed", "trigger": "Extraction succeeds"},
    {"status": "failed", "trigger": "Extraction errors out"},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.11.1",
        "part_a": "Verify `icp_extraction_jobs` table exists",
        "part_b": "Query table schema",
        "key_files": [],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'icp_extraction_jobs'
                ORDER BY ordinal_position;
            """,
            "expect": {
                "columns_exist": ["id", "client_id", "status", "completed_steps", "total_steps", "extracted_icp", "error_message", "created_at"]
            },
            "curl_command": """curl -X POST '{supabase_url}/rest/v1/rpc/sql' \\
  -H 'apikey: {anon_key}' \\
  -H 'Authorization: Bearer {service_role_key}' \\
  -H 'Content-Type: application/json' \\
  -d '{"query": "SELECT column_name FROM information_schema.columns WHERE table_name = \\'icp_extraction_jobs\\'"}'"""
        }
    },
    {
        "id": "J1.11.2",
        "part_a": "Verify job created with status='pending' on analyze",
        "part_b": "Check database after submit",
        "key_files": ["src/api/routes/onboarding.py"],
        "live_test": {
            "type": "api_then_db",
            "steps": [
                "1. Call POST /api/v1/onboarding/analyze with test website",
                "2. Capture returned job_id",
                "3. Query icp_extraction_jobs WHERE id = {job_id}",
                "4. Verify status = 'pending' or 'running' (fast transition)"
            ],
            "api_call": {
                "method": "POST",
                "url": "{api_url}/api/v1/onboarding/analyze",
                "auth": True,
                "body": {"website_url": "https://sparro.com.au"}
            },
            "db_query": "SELECT status FROM icp_extraction_jobs WHERE id = '{job_id}'",
            "expect": {
                "api_status": 202,
                "db_status": ["pending", "running"]
            }
        }
    },
    {
        "id": "J1.11.3",
        "part_a": "Verify status updates to 'running' when Prefect starts",
        "part_b": "Check during extraction",
        "key_files": ["src/orchestration/flows/onboarding_flow.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Submit extraction via POST /api/v1/onboarding/analyze",
                "2. Immediately poll GET /api/v1/onboarding/status/{job_id}",
                "3. Observe status transition: pending → running",
                "4. Check Prefect UI for flow run with matching parameters"
            ],
            "expect": {
                "status_transitions": ["pending", "running"],
                "prefect_flow_visible": True
            },
            "prefect_check": "Open {prefect_url} → Flow Runs → Find 'icp_onboarding_flow'"
        }
    },
    {
        "id": "J1.11.4",
        "part_a": "Verify `completed_steps` and `total_steps` updated",
        "part_b": "Poll status endpoint",
        "key_files": ["src/api/routes/onboarding.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/onboarding/status/{job_id}",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["status", "completed_steps", "total_steps"],
                "completed_steps_range": [0, 5],
                "total_steps_value": 5
            },
            "curl_command": """curl '{api_url}/api/v1/onboarding/status/{job_id}' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J1.11.5",
        "part_a": "Verify `extracted_icp` JSONB populated on completion",
        "part_b": "Query database after complete",
        "key_files": ["src/orchestration/flows/onboarding_flow.py"],
        "live_test": {
            "type": "db_query",
            "precondition": "Wait for job status = 'completed'",
            "query": """
                SELECT extracted_icp
                FROM icp_extraction_jobs
                WHERE id = '{job_id}' AND status = 'completed';
            """,
            "expect": {
                "extracted_icp_not_null": True,
                "extracted_icp_has_fields": ["icp_titles", "icp_industries", "pain_points"]
            },
            "note": "Extraction typically takes 30-60 seconds"
        }
    },
    {
        "id": "J1.11.6",
        "part_a": "Verify `error_message` populated on failure",
        "part_b": "Trigger failure, check database",
        "key_files": ["src/orchestration/flows/onboarding_flow.py"],
        "live_test": {
            "type": "api_then_db",
            "steps": [
                "1. Call POST /api/v1/onboarding/analyze with invalid/unreachable URL",
                "2. Wait for job to fail (poll status)",
                "3. Query icp_extraction_jobs for error_message"
            ],
            "api_call": {
                "method": "POST",
                "url": "{api_url}/api/v1/onboarding/analyze",
                "auth": True,
                "body": {"website_url": "https://this-domain-does-not-exist-12345.com"}
            },
            "db_query": "SELECT status, error_message FROM icp_extraction_jobs WHERE id = '{job_id}'",
            "expect": {
                "status": "failed",
                "error_message_not_null": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Job record created on analyze call",
    "Progress tracked with completed_steps/total_steps",
    "ICP data saved to extracted_icp on success",
    "Error message captured on failure"
]

KEY_FILES = [
    "src/api/routes/onboarding.py",
    "src/orchestration/flows/onboarding_flow.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Job Status Flow")
    for state in JOB_STATUS_FLOW:
        lines.append(f"  {state['status']}: {state['trigger']}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("steps"):
            lines.append("  Steps:")
            for step in lt["steps"]:
                lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
