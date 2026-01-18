"""
Skill: J10.12 — System Queues Page
Journey: J10 - Admin Dashboard
Checks: 4

Purpose: Verify Prefect queue monitoring and management.
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
# QUEUE MONITORING CONSTANTS
# =============================================================================

QUEUE_TYPES = [
    {"queue": "enrichment", "purpose": "Lead enrichment jobs", "worker": "prefect-worker"},
    {"queue": "outreach", "purpose": "Email/SMS sending jobs", "worker": "prefect-worker"},
    {"queue": "scoring", "purpose": "Lead scoring jobs", "worker": "prefect-worker"},
    {"queue": "scraping", "purpose": "LinkedIn/web scraping jobs", "worker": "prefect-worker"}
]

FLOW_STATES = {
    "pending": {"color": "gray", "description": "Waiting to run"},
    "running": {"color": "blue", "description": "Currently executing"},
    "completed": {"color": "green", "description": "Finished successfully"},
    "failed": {"color": "red", "description": "Execution failed"},
    "cancelled": {"color": "orange", "description": "Manually cancelled"},
    "crashed": {"color": "red", "description": "Unexpected termination"}
}

PREFECT_ENDPOINTS = {
    "flows": "/api/flows",
    "flow_runs": "/api/flow_runs",
    "deployments": "/api/deployments",
    "work_pools": "/api/work_pools"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.12.1",
        "part_a": "Read `frontend/app/admin/system/queues/page.tsx` — verify queue display",
        "part_b": "Load queues page, verify queue list renders",
        "key_files": ["frontend/app/admin/system/queues/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/admin/system/queues",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["Queues", "Status", "Pending"]
            },
            "manual_steps": [
                "1. Login as admin user",
                "2. Navigate to {frontend_url}/admin/system/queues",
                "3. Verify queues page loads",
                "4. Check queue list displays with status indicators"
            ]
        }
    },
    {
        "id": "J10.12.2",
        "part_a": "Verify queue depth displays",
        "part_b": "Check pending job counts are accurate",
        "key_files": ["frontend/app/admin/system/queues/page.tsx", "src/api/routes/admin.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/queues/status",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["queues", "total_pending", "total_running"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/queues/status' \\
  -H 'Authorization: Bearer {token}'""",
            "prefect_verify": {
                "url": "{prefect_url}/api/flow_runs/filter",
                "method": "POST",
                "body": {"flow_runs": {"state": {"type": {"any_": ["PENDING", "RUNNING"]}}}},
                "note": "Compare with Prefect API directly for queue depth verification"
            }
        }
    },
    {
        "id": "J10.12.3",
        "part_a": "Verify failed jobs display",
        "part_b": "Check failed job count and retry options",
        "key_files": ["frontend/app/admin/system/queues/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/queues/failed",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True
            },
            "curl_command": """curl '{api_url}/api/v1/admin/queues/failed' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/system/queues page, locate 'Failed Jobs' section",
                "2. Verify failed jobs list displays with error summaries",
                "3. Check 'Retry' button exists for each failed job",
                "4. Click 'Retry' on a failed job, verify it re-queues"
            ]
        }
    },
    {
        "id": "J10.12.4",
        "part_a": "Verify link to Prefect UI",
        "part_b": "Click 'Open Prefect UI' link, verify redirect",
        "key_files": ["frontend/app/admin/system/queues/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. On /admin/system/queues page, locate 'Open Prefect UI' button",
                "2. Click the button",
                "3. Verify Prefect UI opens in new tab at {prefect_url}",
                "4. Check Prefect UI loads and shows flow runs",
                "5. Verify worker status shows in Prefect UI"
            ],
            "expect": {
                "prefect_link_visible": True,
                "prefect_ui_loads": True
            },
            "prefect_direct_check": {
                "url": "{prefect_url}/api/health",
                "curl_command": """curl '{prefect_url}/api/health'
# Expected: healthy response from Prefect server"""
            }
        }
    }
]

PASS_CRITERIA = [
    "Queue page loads correctly",
    "Queue depths are accurate",
    "Failed jobs display with retry option",
    "Prefect UI link works"
]

KEY_FILES = [
    "frontend/app/admin/system/queues/page.tsx",
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

def get_prefect_url(path: str) -> str:
    """Get full Prefect URL for live testing."""
    base = LIVE_CONFIG["prefect_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append(f"- Queues Page: {LIVE_CONFIG['frontend_url']}/admin/system/queues")
    lines.append("")
    lines.append("### Queue Types")
    for queue in QUEUE_TYPES:
        lines.append(f"  - {queue['queue']}: {queue['purpose']}")
    lines.append("")
    lines.append("### Flow States")
    for state, info in FLOW_STATES.items():
        lines.append(f"  - {state}: {info['color']} - {info['description']}")
    lines.append("")
    lines.append("### Prefect API Endpoints")
    for name, endpoint in PREFECT_ENDPOINTS.items():
        lines.append(f"  - {name}: {LIVE_CONFIG['prefect_url']}{endpoint}")
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
