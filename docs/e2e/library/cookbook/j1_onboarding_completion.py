"""
Skill: J1.13 — Onboarding Completion
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify onboarding completes and user lands on dashboard.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "test_user": {
        "email": "david.stephens@keiracom.com"
    }
}

# =============================================================================
# ONBOARDING COMPLETION CRITERIA
# =============================================================================

COMPLETION_CRITERIA = [
    {"field": "icp_confirmed_at", "condition": "NOT NULL", "meaning": "ICP confirmed"},
    {"field": "needs_onboarding", "condition": "FALSE", "meaning": "RPC returns false"},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.13.1",
        "part_a": "Verify `icp_confirmed_at` being set marks onboarding complete",
        "part_b": "Query database",
        "key_files": [],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT
                    c.id as client_id,
                    c.icp_confirmed_at,
                    CASE WHEN c.icp_confirmed_at IS NOT NULL
                         THEN 'COMPLETE'
                         ELSE 'INCOMPLETE'
                    END as onboarding_status
                FROM clients c
                JOIN memberships m ON m.client_id = c.id
                JOIN users u ON u.id = m.user_id
                WHERE u.email = '{test_email}';
            """,
            "expect": {
                "icp_confirmed_at_not_null": True,
                "onboarding_status": "COMPLETE"
            }
        }
    },
    {
        "id": "J1.13.2",
        "part_a": "Verify `get_onboarding_status()` returns `needs_onboarding=false` after confirm",
        "part_b": "Call RPC",
        "key_files": [],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{supabase_url}/rest/v1/rpc/get_onboarding_status",
            "headers": {
                "apikey": "{anon_key}",
                "Authorization": "Bearer {user_jwt}"
            },
            "body": {},
            "expect": {
                "status": 200,
                "body": {
                    "needs_onboarding": False
                }
            },
            "curl_command": """curl -X POST '{supabase_url}/rest/v1/rpc/get_onboarding_status' \\
  -H 'apikey: {anon_key}' \\
  -H 'Authorization: Bearer {user_jwt}' \\
  -H 'Content-Type: application/json' \\
  -d '{}'"""
        }
    },
    {
        "id": "J1.13.3",
        "part_a": "Verify dashboard loads without redirect loop",
        "part_b": "Access /dashboard after confirm",
        "key_files": [],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/dashboard",
            "auth": True,
            "expect": {
                "status": 200,
                "no_redirect_to": "/onboarding",
                "body_contains": ["Dashboard", "Campaigns", "Leads"]
            },
            "manual_steps": [
                "1. Login as test user (must have completed onboarding)",
                "2. Navigate directly to /dashboard",
                "3. Verify page loads without redirecting to /onboarding",
                "4. Verify no console errors about redirect loops"
            ]
        }
    },
    {
        "id": "J1.13.4",
        "part_a": "Verify ICP data displayed on dashboard",
        "part_b": "Check dashboard shows ICP",
        "key_files": ["frontend/app/dashboard/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Login and navigate to /dashboard",
                "2. Look for ICP summary section or widget",
                "3. Verify industries, titles, locations displayed",
                "4. Verify data matches what was confirmed in J1.12"
            ],
            "expect": {
                "icp_visible": True,
                "shows_industries": True,
                "shows_titles": True
            },
            "note": "Dashboard may show ICP in sidebar, header, or dedicated card"
        }
    },
    {
        "id": "J1.13.5",
        "part_a": "Verify activity logged for onboarding completion",
        "part_b": "Query activities table",
        "key_files": [],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT
                    a.event_type,
                    a.event_data,
                    a.created_at
                FROM activities a
                WHERE a.client_id = '{client_id}'
                  AND a.event_type IN ('onboarding_complete', 'icp_confirmed')
                ORDER BY a.created_at DESC
                LIMIT 1;
            """,
            "expect": {
                "row_exists": True,
                "event_type_in": ["onboarding_complete", "icp_confirmed"]
            },
            "note": "Activity may be named differently - check for any onboarding-related event"
        }
    }
]

PASS_CRITERIA = [
    "Onboarding status reflects complete",
    "Dashboard accessible without redirect",
    "No redirect loops",
    "ICP visible on dashboard",
    "Activity logged"
]

KEY_FILES = [
    "frontend/app/dashboard/page.tsx"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append("")
    lines.append("### Completion Criteria")
    for c in COMPLETION_CRITERIA:
        lines.append(f"  {c['field']} {c['condition']} → {c['meaning']}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("manual_steps"):
            lines.append("  Manual Steps:")
            for step in lt["manual_steps"]:
                lines.append(f"    {step}")
        if lt.get("steps"):
            lines.append("  Steps:")
            for step in lt["steps"]:
                lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
