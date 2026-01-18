"""
Skill: J10.8 — Client Detail Page
Journey: J10 - Admin Dashboard
Checks: 5

Purpose: Verify individual client detail page functionality.
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
    "test_admin": {
        "email": "david.stephens@keiracom.com",
        "role": "admin"
    }
}

# =============================================================================
# CLIENT DETAIL CONSTANTS
# =============================================================================

CLIENT_SECTIONS = [
    {"section": "Profile", "fields": ["company_name", "industry", "website", "icp_summary"]},
    {"section": "Campaigns", "fields": ["name", "status", "leads_count", "created_at"]},
    {"section": "Leads", "fields": ["name", "company", "score", "status"]},
    {"section": "Settings", "fields": ["outreach_frequency", "channels", "timezone"]},
    {"section": "Billing", "fields": ["plan", "mrr", "next_billing_date"]}
]

CLIENT_ACTIONS = [
    {"action": "pause", "description": "Pause all client campaigns", "confirm_required": True},
    {"action": "resume", "description": "Resume paused campaigns", "confirm_required": False},
    {"action": "edit", "description": "Edit client settings", "confirm_required": False},
    {"action": "delete", "description": "Soft delete client (archive)", "confirm_required": True}
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.8.1",
        "part_a": "Read `frontend/app/admin/clients/[id]/page.tsx` — verify layout",
        "part_b": "Load client detail page, verify sections render",
        "key_files": ["frontend/app/admin/clients/[id]/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/clients/{client_id}",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["id", "name", "status", "created_at"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/clients/{client_id}' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. Navigate to /admin/clients and click a client",
                "2. Verify client detail page loads at /admin/clients/{id}",
                "3. Check all sections render: Profile, Campaigns, Leads, Settings, Billing"
            ]
        }
    },
    {
        "id": "J10.8.2",
        "part_a": "Verify client profile section displays",
        "part_b": "Check company name, ICP, settings display",
        "key_files": ["frontend/app/admin/clients/[id]/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. On client detail page, locate Profile section",
                "2. Verify company name displays prominently",
                "3. Check industry field is populated",
                "4. Verify website link is clickable",
                "5. Check ICP summary shows target persona details"
            ],
            "expect": {
                "profile_section_exists": True,
                "company_name_visible": True,
                "icp_summary_visible": True
            }
        }
    },
    {
        "id": "J10.8.3",
        "part_a": "Verify client campaigns list",
        "part_b": "Check all campaigns for this client display",
        "key_files": ["frontend/app/admin/clients/[id]/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/clients/{client_id}/campaigns",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["id", "name", "status"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/clients/{client_id}/campaigns' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On client detail page, locate Campaigns section",
                "2. Verify campaigns list shows all client campaigns",
                "3. Check each campaign shows: name, status, lead count",
                "4. Click a campaign to verify navigation to campaign detail"
            ]
        }
    },
    {
        "id": "J10.8.4",
        "part_a": "Verify client leads section",
        "part_b": "Check leads associated with client display",
        "key_files": ["frontend/app/admin/clients/[id]/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/clients/{client_id}/leads?limit=10",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True
            },
            "curl_command": """curl '{api_url}/api/v1/admin/clients/{client_id}/leads?limit=10' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On client detail page, locate Leads section",
                "2. Verify recent leads display with key info",
                "3. Check leads show: name, company, score, status",
                "4. Verify 'View All' link to full lead list"
            ]
        }
    },
    {
        "id": "J10.8.5",
        "part_a": "Verify client actions (pause, edit, delete)",
        "part_b": "Test pause client action, verify status change",
        "key_files": ["frontend/app/admin/clients/[id]/page.tsx", "src/api/routes/admin.py"],
        "live_test": {
            "type": "api",
            "method": "PATCH",
            "url": "{api_url}/api/v1/admin/clients/{client_id}/status",
            "auth": True,
            "body": {
                "status": "paused"
            },
            "expect": {
                "status": 200,
                "body_has_field": "status"
            },
            "curl_command": """curl -X PATCH '{api_url}/api/v1/admin/clients/{client_id}/status' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"status": "paused"}'""",
            "manual_steps": [
                "1. On client detail page, locate action buttons",
                "2. Click 'Pause Client' button",
                "3. Verify confirmation modal appears",
                "4. Confirm action and verify status changes to 'paused'",
                "5. Verify all campaigns for client are also paused",
                "6. Test 'Resume' action to restore active status"
            ],
            "warning": "This modifies client status - use with caution in production"
        }
    }
]

PASS_CRITERIA = [
    "Client detail page loads correctly",
    "Profile information displays accurately",
    "Campaigns list is complete",
    "Leads section shows associated leads",
    "Client actions work correctly"
]

KEY_FILES = [
    "frontend/app/admin/clients/[id]/page.tsx",
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
    lines.append(f"- Client Detail: {LIVE_CONFIG['frontend_url']}/admin/clients/{{client_id}}")
    lines.append("")
    lines.append("### Client Detail Sections")
    for section in CLIENT_SECTIONS:
        lines.append(f"  - {section['section']}: {', '.join(section['fields'][:3])}...")
    lines.append("")
    lines.append("### Client Actions")
    for action in CLIENT_ACTIONS:
        confirm = " (requires confirm)" if action["confirm_required"] else ""
        lines.append(f"  - {action['action']}: {action['description']}{confirm}")
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
        if lt.get("warning"):
            lines.append(f"  Warning: {lt['warning']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
