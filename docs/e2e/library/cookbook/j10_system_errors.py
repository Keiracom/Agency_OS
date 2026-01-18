"""
Skill: J10.11 — System Errors Page
Journey: J10 - Admin Dashboard
Checks: 4

Purpose: Verify system error logging and display functionality.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "sentry_url": "https://david-stephens-1q.sentry.io/issues/",
    "test_admin": {
        "email": "david.stephens@keiracom.com",
        "role": "admin"
    }
}

# =============================================================================
# ERROR TRACKING CONSTANTS
# =============================================================================

ERROR_SEVERITIES = [
    {"level": "critical", "color": "red", "examples": ["Database connection lost", "API key invalid"]},
    {"level": "error", "color": "orange", "examples": ["Email send failed", "Enrichment failed"]},
    {"level": "warning", "color": "yellow", "examples": ["Rate limit approaching", "Slow response"]},
    {"level": "info", "color": "blue", "examples": ["Scheduled job completed", "Config changed"]}
]

ERROR_SOURCES = ["api", "prefect", "integrations", "database", "frontend"]

SENTRY_PROJECT = "agency-os-backend"

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.11.1",
        "part_a": "Read `frontend/app/admin/system/errors/page.tsx` — verify error list",
        "part_b": "Load errors page, verify error log renders",
        "key_files": ["frontend/app/admin/system/errors/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/admin/system/errors",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["Errors", "Severity", "Source"]
            },
            "manual_steps": [
                "1. Login as admin user",
                "2. Navigate to {frontend_url}/admin/system/errors",
                "3. Verify error log page loads",
                "4. Check error list displays with severity indicators"
            ]
        }
    },
    {
        "id": "J10.11.2",
        "part_a": "Verify error details display",
        "part_b": "Click error row, verify stack trace and context display",
        "key_files": ["frontend/app/admin/system/errors/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/errors?limit=10",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["id", "message", "severity", "timestamp", "source"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/errors?limit=10' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/system/errors page, click an error row",
                "2. Verify error detail modal/panel opens",
                "3. Check stack trace is displayed (if available)",
                "4. Verify context info shows: user, request, timestamp"
            ]
        }
    },
    {
        "id": "J10.11.3",
        "part_a": "Verify error filtering by severity",
        "part_b": "Filter by critical/warning/info, verify list updates",
        "key_files": ["frontend/app/admin/system/errors/page.tsx"],
        "live_test": {
            "type": "api_batch",
            "tests": [
                {
                    "name": "Filter by critical",
                    "method": "GET",
                    "url": "{api_url}/api/v1/admin/errors?severity=critical&limit=5",
                    "expect": {"all_items_have": {"severity": "critical"}}
                },
                {
                    "name": "Filter by error",
                    "method": "GET",
                    "url": "{api_url}/api/v1/admin/errors?severity=error&limit=5",
                    "expect": {"all_items_have": {"severity": "error"}}
                },
                {
                    "name": "Filter by warning",
                    "method": "GET",
                    "url": "{api_url}/api/v1/admin/errors?severity=warning&limit=5",
                    "expect": {"all_items_have": {"severity": "warning"}}
                }
            ],
            "auth": True,
            "curl_command": """curl '{api_url}/api/v1/admin/errors?severity=critical&limit=5' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/system/errors page, locate severity filter",
                "2. Select 'Critical' filter",
                "3. Verify only critical errors display (red indicators)",
                "4. Select 'Warning' filter",
                "5. Verify only warnings display (yellow indicators)"
            ]
        }
    },
    {
        "id": "J10.11.4",
        "part_a": "Verify Sentry integration link",
        "part_b": "Check 'View in Sentry' link works for each error",
        "key_files": ["frontend/app/admin/system/errors/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. On /admin/system/errors page, find error with Sentry ID",
                "2. Click 'View in Sentry' link/button",
                "3. Verify opens Sentry dashboard in new tab",
                "4. Confirm Sentry shows same error with full details",
                "5. Alternative: Check Sentry URL format: {sentry_url}"
            ],
            "expect": {
                "sentry_link_visible": True,
                "sentry_opens_correctly": True
            },
            "sentry_api_check": {
                "url": "https://sentry.io/api/0/projects/david-stephens-1q/agency-os-backend/issues/",
                "note": "Requires SENTRY_AUTH_TOKEN from config/RAILWAY_ENV_VARS.txt"
            }
        }
    }
]

PASS_CRITERIA = [
    "Error log page loads correctly",
    "Error details display properly",
    "Severity filtering works",
    "Sentry integration is functional"
]

KEY_FILES = [
    "frontend/app/admin/system/errors/page.tsx",
    "src/api/routes/admin.py",
    "src/integrations/sentry_utils.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_frontend_url(path: str) -> str:
    """Get full frontend URL for live testing."""
    base = LIVE_CONFIG["frontend_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append(f"- Sentry: {LIVE_CONFIG['sentry_url']}")
    lines.append(f"- Errors Page: {LIVE_CONFIG['frontend_url']}/admin/system/errors")
    lines.append("")
    lines.append("### Error Severities")
    for sev in ERROR_SEVERITIES:
        lines.append(f"  - {sev['level']}: {sev['color']}")
        lines.append(f"    Examples: {', '.join(sev['examples'])}")
    lines.append("")
    lines.append("### Error Sources")
    lines.append(f"  {', '.join(ERROR_SOURCES)}")
    lines.append("")
    lines.append("### Sentry Integration")
    lines.append(f"  Project: {SENTRY_PROJECT}")
    lines.append(f"  Dashboard: {LIVE_CONFIG['sentry_url']}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("type"):
            lines.append(f"  Live Test Type: {lt['type']}")
        if lt.get("curl_command"):
            lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
