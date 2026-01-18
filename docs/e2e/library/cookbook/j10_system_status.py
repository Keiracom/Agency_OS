"""
Skill: J10.4 — System Status Section
Journey: J10 - Admin Dashboard
Checks: 4

Purpose: Verify system health indicators display correctly.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "test_admin": {
        "email": "david.stephens@keiracom.com",
        "role": "admin"
    }
}

# =============================================================================
# SYSTEM COMPONENTS CONSTANTS
# =============================================================================

SYSTEM_COMPONENTS = [
    {"component": "Supabase DB", "health_endpoint": "/api/v1/health/db", "critical": True},
    {"component": "Prefect Worker", "health_endpoint": "/api/v1/health/prefect", "critical": True},
    {"component": "Redis Cache", "health_endpoint": "/api/v1/health/redis", "critical": False},
    {"component": "Apollo API", "health_endpoint": None, "critical": False},
    {"component": "Salesforge API", "health_endpoint": None, "critical": False},
    {"component": "Unipile API", "health_endpoint": None, "critical": False}
]

HEALTH_STATUS = {
    "healthy": {"color": "green", "icon": "check-circle", "label": "Operational"},
    "degraded": {"color": "yellow", "icon": "alert-triangle", "label": "Degraded"},
    "down": {"color": "red", "icon": "x-circle", "label": "Down"},
    "unknown": {"color": "gray", "icon": "help-circle", "label": "Unknown"}
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.4.1",
        "part_a": "Read `frontend/app/admin/system/page.tsx` — verify health indicators",
        "part_b": "Load system page, verify all services show status",
        "key_files": ["frontend/app/admin/system/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/admin/system",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["System", "Status", "Health"]
            },
            "manual_steps": [
                "1. Login as admin user",
                "2. Navigate to {frontend_url}/admin/system",
                "3. Verify system status page loads",
                "4. Check all service status indicators are visible"
            ]
        }
    },
    {
        "id": "J10.4.2",
        "part_a": "Verify database connection status indicator",
        "part_b": "Check Supabase connection shows green/red correctly",
        "key_files": ["frontend/app/admin/system/page.tsx", "src/api/routes/health.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/health/db",
            "auth": False,
            "expect": {
                "status": 200,
                "body_has_field": "status",
                "status_value": "healthy"
            },
            "curl_command": """curl '{api_url}/api/v1/health/db'
# Expected: {"status": "healthy", "latency_ms": <number>}"""
        }
    },
    {
        "id": "J10.4.3",
        "part_a": "Verify Prefect worker status indicator",
        "part_b": "Check Prefect worker shows online/offline correctly",
        "key_files": ["frontend/app/admin/system/page.tsx", "src/api/routes/health.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/health/prefect",
            "auth": False,
            "expect": {
                "status": 200,
                "body_has_field": "status"
            },
            "curl_command": """curl '{api_url}/api/v1/health/prefect'
# Expected: {"status": "healthy", "workers_online": <number>}""",
            "verify_prefect_ui": {
                "url": "{prefect_url}",
                "check": "UI loads and shows worker status"
            }
        }
    },
    {
        "id": "J10.4.4",
        "part_a": "Verify integration status indicators",
        "part_b": "Check Apollo, Salesforge, etc. show connection status",
        "key_files": ["frontend/app/admin/system/page.tsx", "src/api/routes/admin.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/integrations/status",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["apollo", "salesforge", "unipile"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/integrations/status' \\
  -H 'Authorization: Bearer {token}'
# Returns status of each integration: healthy, error, or not_configured""",
            "manual_steps": [
                "1. On /admin/system page, locate Integration Status section",
                "2. Verify Apollo shows status (green = connected, gray = not configured)",
                "3. Verify Salesforge shows status",
                "4. Verify Unipile shows status",
                "5. Click any integration for more details"
            ]
        }
    }
]

PASS_CRITERIA = [
    "All system status indicators render",
    "Database status reflects actual connection",
    "Prefect worker status is accurate",
    "Integration statuses are accurate"
]

KEY_FILES = [
    "frontend/app/admin/system/page.tsx",
    "src/api/routes/health.py",
    "src/api/routes/admin.py"
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
    lines.append(f"- System Page: {LIVE_CONFIG['frontend_url']}/admin/system")
    lines.append("")
    lines.append("### System Components")
    for comp in SYSTEM_COMPONENTS:
        critical = "CRITICAL" if comp["critical"] else "optional"
        endpoint = comp["health_endpoint"] or "manual check"
        lines.append(f"  - {comp['component']}: {endpoint} ({critical})")
    lines.append("")
    lines.append("### Health Status Codes")
    for status, info in HEALTH_STATUS.items():
        lines.append(f"  - {status}: {info['color']} {info['icon']} - {info['label']}")
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
