"""
Skill: J1.12 — ICP Confirmation Flow
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify ICP can be confirmed and applied to client.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "test_adjustments": {
        "icp_titles": ["CEO", "Founder", "Managing Director"],
        "icp_industries": ["Technology", "SaaS", "E-commerce"]
    }
}

# =============================================================================
# FIELDS UPDATED ON CONFIRM
# =============================================================================

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

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.12.1",
        "part_a": "Verify POST /onboarding/confirm endpoint",
        "part_b": "Call with job_id",
        "key_files": ["src/api/routes/onboarding.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/onboarding/confirm",
            "auth": True,
            "body": {"job_id": "{job_id}"},
            "precondition": "Requires completed extraction job_id from J1.11",
            "expect": {
                "status": 200,
                "body_contains": ["success", "confirmed"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/onboarding/confirm' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"job_id": "{job_id}"}'"""
        }
    },
    {
        "id": "J1.12.2",
        "part_a": "Verify ICP fields saved to clients table",
        "part_b": "Query clients table",
        "key_files": ["src/api/routes/onboarding.py"],
        "live_test": {
            "type": "db_query",
            "precondition": "After calling /onboarding/confirm",
            "query": """
                SELECT
                    website_url,
                    company_description,
                    services_offered,
                    icp_industries,
                    icp_titles,
                    icp_locations,
                    icp_pain_points
                FROM clients
                WHERE id = '{client_id}';
            """,
            "expect": {
                "fields_not_null": ["website_url", "icp_industries", "icp_titles"]
            }
        }
    },
    {
        "id": "J1.12.3",
        "part_a": "Verify `icp_confirmed_at` timestamp set",
        "part_b": "Check column populated",
        "key_files": ["src/api/routes/onboarding.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT icp_confirmed_at
                FROM clients
                WHERE id = '{client_id}';
            """,
            "expect": {
                "icp_confirmed_at_not_null": True,
                "icp_confirmed_at_recent": "Within last 5 minutes"
            }
        }
    },
    {
        "id": "J1.12.4",
        "part_a": "Verify pool population Prefect flow triggered",
        "part_b": "Check Prefect UI",
        "key_files": ["src/api/routes/onboarding.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. After calling /onboarding/confirm, open Prefect UI",
                "2. Navigate to Flow Runs",
                "3. Look for 'pool_population_flow' or 'initial_pool_population'",
                "4. Verify flow was triggered with correct client_id"
            ],
            "expect": {
                "prefect_flow_triggered": True,
                "flow_name": "pool_population_flow"
            },
            "prefect_url": "{prefect_url}/flow-runs"
        }
    },
    {
        "id": "J1.12.5",
        "part_a": "Verify adjustments can be applied before confirm",
        "part_b": "Pass adjustments, verify saved",
        "key_files": ["src/api/routes/onboarding.py"],
        "live_test": {
            "type": "api_then_db",
            "steps": [
                "1. Call POST /onboarding/confirm with job_id AND adjustments",
                "2. Query clients table",
                "3. Verify adjusted values saved (not original extraction values)"
            ],
            "api_call": {
                "method": "POST",
                "url": "{api_url}/api/v1/onboarding/confirm",
                "auth": True,
                "body": {
                    "job_id": "{job_id}",
                    "adjustments": {
                        "icp_titles": ["CEO", "Founder", "Managing Director"],
                        "icp_industries": ["Technology", "SaaS"]
                    }
                }
            },
            "db_query": "SELECT icp_titles, icp_industries FROM clients WHERE id = '{client_id}'",
            "expect": {
                "icp_titles_contains": ["CEO", "Founder"],
                "icp_industries_contains": ["Technology", "SaaS"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/onboarding/confirm' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"job_id": "{job_id}", "adjustments": {"icp_titles": ["CEO", "Founder"]}}'"""
        }
    }
]

PASS_CRITERIA = [
    "Confirm saves ICP to client",
    "All fields populated correctly",
    "Pool population flow triggered",
    "Adjustments applied when provided"
]

KEY_FILES = [
    "src/api/routes/onboarding.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Fields Updated on Confirm")
    for field in CONFIRM_FIELDS:
        lines.append(f"  {field['column']}: {field['source']}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("precondition"):
            lines.append(f"  Precondition: {lt['precondition']}")
        if lt.get("steps"):
            lines.append("  Steps:")
            for step in lt["steps"]:
                lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
