"""
Skill: J10.5 — Alerts Section
Journey: J10 - Admin Dashboard
Checks: 4

Purpose: Verify critical alerts display and notification system.
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
# ALERT TYPES CONSTANTS
# =============================================================================

ALERT_TYPES = [
    {"type": "critical", "color": "red", "priority": 1, "examples": ["System down", "API key expired"]},
    {"type": "warning", "color": "yellow", "priority": 2, "examples": ["Rate limit approaching", "Budget threshold"]},
    {"type": "info", "color": "blue", "priority": 3, "examples": ["New client signup", "Campaign completed"]}
]

ALERT_ACTIONS = {
    "view_details": "Navigate to related page for more information",
    "dismiss": "Mark alert as acknowledged and hide from list",
    "snooze": "Temporarily hide alert for specified duration",
    "take_action": "Execute recommended fix or workaround"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.5.1",
        "part_a": "Read admin page alerts component — verify alert types",
        "part_b": "Load dashboard, verify alerts section renders",
        "key_files": ["frontend/app/admin/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/alerts?status=active",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True
            },
            "curl_command": """curl '{api_url}/api/v1/admin/alerts?status=active' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J10.5.2",
        "part_a": "Verify critical alerts display with priority",
        "part_b": "Create test alert, verify it appears in list",
        "key_files": ["frontend/app/admin/page.tsx", "src/api/routes/admin.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/admin/alerts/test",
            "auth": True,
            "body": {
                "type": "warning",
                "message": "Test alert for E2E verification",
                "source": "e2e_test"
            },
            "expect": {
                "status": [200, 201],
                "body_has_field": "id"
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/admin/alerts/test' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"type": "warning", "message": "Test alert", "source": "e2e_test"}'""",
            "cleanup": "DELETE alert after test",
            "manual_steps": [
                "1. After creating test alert, refresh /admin page",
                "2. Verify alert appears in Alerts section",
                "3. Check alert shows correct type (warning = yellow)",
                "4. Verify alert message matches what was sent"
            ]
        }
    },
    {
        "id": "J10.5.3",
        "part_a": "Verify alert dismissal functionality",
        "part_b": "Dismiss an alert, verify it is removed",
        "key_files": ["frontend/app/admin/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "PATCH",
            "url": "{api_url}/api/v1/admin/alerts/{alert_id}/dismiss",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_field": "dismissed"
            },
            "curl_command": """curl -X PATCH '{api_url}/api/v1/admin/alerts/{alert_id}/dismiss' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin page, locate an active alert",
                "2. Click the dismiss (X) button on the alert",
                "3. Verify alert is removed from the list",
                "4. Refresh page, verify alert remains dismissed"
            ]
        }
    },
    {
        "id": "J10.5.4",
        "part_a": "Verify alert actions (view details, take action)",
        "part_b": "Click alert action, verify navigation or modal",
        "key_files": ["frontend/app/admin/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. On /admin page, find an alert with 'View Details' action",
                "2. Click 'View Details' button",
                "3. Verify navigation to relevant page (e.g., /admin/system for system alerts)",
                "4. Return to /admin page",
                "5. Find alert with 'Take Action' button if available",
                "6. Click 'Take Action', verify modal or action executes"
            ],
            "expect": {
                "view_details_navigates": True,
                "take_action_works": True,
                "modals_dismiss_properly": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Alerts section renders correctly",
    "Critical alerts show with proper priority",
    "Alert dismissal works",
    "Alert actions navigate correctly"
]

KEY_FILES = [
    "frontend/app/admin/page.tsx",
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
    lines.append("")
    lines.append("### Alert Types")
    for alert in ALERT_TYPES:
        lines.append(f"  - {alert['type']}: priority {alert['priority']}, color {alert['color']}")
        lines.append(f"    Examples: {', '.join(alert['examples'])}")
    lines.append("")
    lines.append("### Alert Actions")
    for action, description in ALERT_ACTIONS.items():
        lines.append(f"  - {action}: {description}")
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
