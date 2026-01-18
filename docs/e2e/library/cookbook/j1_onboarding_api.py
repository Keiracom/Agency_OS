"""
Skill: J1.7 — Onboarding API Endpoints
Journey: J1 - Signup & Onboarding
Checks: 6

Purpose: Verify backend onboarding API is complete and triggers Prefect.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "test_agency": {
        "website": "https://sparro.com.au"
    }
}

# =============================================================================
# API ENDPOINTS
# =============================================================================

API_ENDPOINTS = [
    {"method": "POST", "path": "/api/v1/onboarding/analyze", "purpose": "Start extraction", "auth": True},
    {"method": "GET", "path": "/api/v1/onboarding/status/{job_id}", "purpose": "Check progress", "auth": True},
    {"method": "GET", "path": "/api/v1/onboarding/result/{job_id}", "purpose": "Get extracted ICP", "auth": True},
    {"method": "POST", "path": "/api/v1/onboarding/confirm", "purpose": "Confirm and apply ICP", "auth": True},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.7.1",
        "part_a": "Read `src/api/routes/onboarding.py` — verify POST /onboarding/analyze",
        "part_b": "Call API, verify 202 response",
        "key_files": ["src/api/routes/onboarding.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/onboarding/analyze",
            "auth": True,
            "body": {"website_url": "https://sparro.com.au"},
            "expect": {
                "status": 202,
                "body_has_field": "job_id"
            },
            "curl_command": """curl -X POST 'https://agency-os-production.up.railway.app/api/v1/onboarding/analyze' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"website_url": "https://sparro.com.au"}'"""
        }
    },
    {
        "id": "J1.7.2",
        "part_a": "Verify endpoint looks up client from memberships",
        "part_b": "Check query logic",
        "key_files": ["src/api/routes/onboarding.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Endpoint queries memberships table to get client_id for current user",
            "expect": {
                "code_contains": ["memberships", "client_id", "user_id"]
            }
        }
    },
    {
        "id": "J1.7.3",
        "part_a": "Verify `run_deployment('icp_onboarding_flow/onboarding-flow')` called",
        "part_b": "Check Prefect UI for flow run",
        "key_files": ["src/api/routes/onboarding.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Call POST /onboarding/analyze with test website",
                "2. Open Prefect UI: {prefect_url}",
                "3. Go to Flow Runs",
                "4. Verify 'icp_onboarding_flow' run created",
                "5. Check flow state (should be Running or Completed)"
            ],
            "expect": {
                "prefect_flow_created": True,
                "flow_name": "icp_onboarding_flow"
            }
        }
    },
    {
        "id": "J1.7.4",
        "part_a": "Verify GET /onboarding/status/{job_id} returns progress",
        "part_b": "Poll status endpoint",
        "key_files": ["src/api/routes/onboarding.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/onboarding/status/{job_id}",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["status", "completed_steps", "total_steps"]
            },
            "curl_command": """curl 'https://agency-os-production.up.railway.app/api/v1/onboarding/status/{job_id}' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J1.7.5",
        "part_a": "Verify GET /onboarding/result/{job_id} returns extracted ICP",
        "part_b": "After completion, get result",
        "key_files": ["src/api/routes/onboarding.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/onboarding/result/{job_id}",
            "auth": True,
            "precondition": "Job must be completed (status=completed)",
            "expect": {
                "status": 200,
                "body_has_fields": ["icp_titles", "icp_industries", "icp_locations", "pain_points"]
            },
            "curl_command": """curl 'https://agency-os-production.up.railway.app/api/v1/onboarding/result/{job_id}' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J1.7.6",
        "part_a": "Verify POST /onboarding/confirm saves to clients table",
        "part_b": "Confirm ICP, query database",
        "key_files": ["src/api/routes/onboarding.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/onboarding/confirm",
            "auth": True,
            "body": {"job_id": "{job_id}"},
            "expect": {
                "status": 200
            },
            "verify_db": {
                "query": "SELECT icp_confirmed_at FROM clients WHERE id = '{client_id}'",
                "expect_not_null": ["icp_confirmed_at"]
            }
        }
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

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### API Endpoints")
    for ep in API_ENDPOINTS:
        lines.append(f"  {ep['method']} {ep['path']} — {ep['purpose']}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("curl_command"):
            lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
