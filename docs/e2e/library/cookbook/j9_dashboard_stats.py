"""
Skill: J9.2 — Dashboard Stats API
Journey: J9 - Client Dashboard
Checks: 8

Purpose: Verify dashboard statistics API returns correct data for leads,
campaigns, emails sent, and response rates for the authenticated client.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "client_id": "81dbaee6-4e71-48ad-be40-fa915fae66e0",
    "user_id": "a60bcdbd-4a31-43e7-bcc8-3ab998c44ac2",
    "test_email": "david.stephens@keiracom.com",
    "test_phone": "+61457543392",
}

# =============================================================================
# DASHBOARD KPI METRICS
# =============================================================================

DASHBOARD_METRICS = {
    "total_leads": {
        "description": "Total number of leads for tenant",
        "field": "total_leads",
        "type": "integer",
    },
    "active_campaigns": {
        "description": "Number of active campaigns",
        "field": "active_campaigns",
        "type": "integer",
    },
    "emails_sent": {
        "description": "Total emails sent",
        "field": "emails_sent",
        "type": "integer",
    },
    "response_rate": {
        "description": "Reply rate as percentage",
        "field": "response_rate",
        "type": "float",
        "formula": "(replies / emails_sent) * 100",
    },
    "meetings_booked": {
        "description": "Total meetings scheduled",
        "field": "meetings_booked",
        "type": "integer",
    },
}

DATE_RANGE_OPTIONS = ["7d", "30d", "90d", "all"]

# =============================================================================
# API ENDPOINTS
# =============================================================================

API_ENDPOINTS = [
    {"method": "GET", "path": "/api/v1/customers/stats", "purpose": "Get dashboard stats", "auth": True},
    {"method": "GET", "path": "/api/v1/customers/stats?range=30d", "purpose": "Get stats with date range", "auth": True},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.2.1",
        "part_a": "Verify /api/v1/customers/stats endpoint exists",
        "part_b": "Make GET request to stats endpoint with valid auth token",
        "key_files": ["src/api/routes/customers.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/customers/stats",
            "auth": True,
            "expect": {
                "status": 200,
                "content_type": "application/json"
            },
            "curl_command": """curl '{api_url}/api/v1/customers/stats' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J9.2.2",
        "part_a": "Verify total leads count is returned",
        "part_b": "Check response contains total_leads field with integer value",
        "key_files": ["src/api/routes/customers.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/customers/stats",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_field": "total_leads",
                "field_type": {"total_leads": "integer"}
            },
            "curl_command": """curl '{api_url}/api/v1/customers/stats' \\
  -H 'Authorization: Bearer {token}' | jq '.total_leads'"""
        }
    },
    {
        "id": "J9.2.3",
        "part_a": "Verify active campaigns count is returned",
        "part_b": "Check response contains active_campaigns field with integer value",
        "key_files": ["src/api/routes/customers.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/customers/stats",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_field": "active_campaigns",
                "field_type": {"active_campaigns": "integer"}
            },
            "curl_command": """curl '{api_url}/api/v1/customers/stats' \\
  -H 'Authorization: Bearer {token}' | jq '.active_campaigns'"""
        }
    },
    {
        "id": "J9.2.4",
        "part_a": "Verify emails sent count is returned",
        "part_b": "Check response contains emails_sent field with integer value",
        "key_files": ["src/api/routes/customers.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/customers/stats",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_field": "emails_sent",
                "field_type": {"emails_sent": "integer"}
            },
            "curl_command": """curl '{api_url}/api/v1/customers/stats' \\
  -H 'Authorization: Bearer {token}' | jq '.emails_sent'"""
        }
    },
    {
        "id": "J9.2.5",
        "part_a": "Verify response rate is calculated correctly",
        "part_b": "Check response_rate = (replies / emails_sent) * 100",
        "key_files": ["src/api/routes/customers.py"],
        "live_test": {
            "type": "db_query",
            "description": "Verify response_rate calculation matches database",
            "queries": [
                {
                    "sql": "SELECT COUNT(*) FROM emails WHERE client_id = '{client_id}' AND status = 'sent'",
                    "alias": "emails_sent"
                },
                {
                    "sql": "SELECT COUNT(*) FROM replies WHERE client_id = '{client_id}'",
                    "alias": "replies"
                }
            ],
            "expect": {
                "formula": "(replies / emails_sent) * 100 == api_response.response_rate"
            }
        }
    },
    {
        "id": "J9.2.6",
        "part_a": "Verify stats are scoped to authenticated client",
        "part_b": "Stats should only include data for the logged-in client's tenant",
        "key_files": ["src/api/routes/customers.py", "src/api/auth.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Stats query filters by client_id from authenticated user's membership",
            "expect": {
                "code_contains": ["client_id", "current_user", "membership"]
            }
        }
    },
    {
        "id": "J9.2.7",
        "part_a": "Verify stats endpoint returns 401 for unauthenticated requests",
        "part_b": "Make request without auth token, expect 401 Unauthorized",
        "key_files": ["src/api/routes/customers.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/customers/stats",
            "auth": False,
            "expect": {
                "status": 401,
                "body_contains": ["Unauthorized", "unauthenticated", "token"]
            },
            "curl_command": """curl '{api_url}/api/v1/customers/stats'"""
        }
    },
    {
        "id": "J9.2.8",
        "part_a": "Verify stats display correctly in dashboard UI",
        "part_b": "Check KPI cards show values from API response",
        "key_files": ["frontend/app/dashboard/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Call API: GET {api_url}/api/v1/customers/stats",
                "2. Note the returned values (total_leads, active_campaigns, etc.)",
                "3. Open {frontend_url}/dashboard in browser",
                "4. Compare KPI card values with API response",
                "5. Verify values match exactly"
            ],
            "expect": {
                "kpi_cards_match_api": True,
                "all_metrics_displayed": True
            }
        }
    },
]

PASS_CRITERIA = [
    "Stats endpoint returns 200 with valid auth",
    "total_leads count matches database records for tenant",
    "active_campaigns count matches active campaign records",
    "emails_sent count matches sent email records",
    "response_rate calculated correctly",
    "Stats scoped to authenticated client only",
    "Returns 401 for unauthenticated requests",
    "Frontend displays stats from API correctly",
]

KEY_FILES = [
    "src/api/routes/customers.py",
    "src/api/auth.py",
    "frontend/app/dashboard/page.tsx",
    "frontend/components/admin/KPICard.tsx",
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_live_url(path: str) -> str:
    """Get full URL for live testing."""
    base = LIVE_CONFIG["frontend_url"]
    return f"{base}{path}"


def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"


def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Dashboard Metrics")
    for name, metric in DASHBOARD_METRICS.items():
        lines.append(f"  {name}: {metric['description']} ({metric['type']})")
    lines.append("")
    lines.append("### API Endpoints")
    for ep in API_ENDPOINTS:
        lines.append(f"  {ep['method']} {ep['path']} - {ep['purpose']}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
            if lt.get("url"):
                lines.append(f"  URL: {lt['url']}")
            if lt.get("steps"):
                lines.append("  Steps:")
                for step in lt["steps"]:
                    lines.append(f"    {step}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:60]}...")
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
