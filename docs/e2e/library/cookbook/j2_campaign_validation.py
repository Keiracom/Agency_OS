"""
Skill: J2.2 — Create Campaign Form
Journey: J2 - Campaign Creation & Management
Checks: 6

Purpose: Verify campaign creation flow with simplified fields.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "test_campaign": {
        "name": "E2E Test Campaign",
        "description": "Created by E2E testing",
        "permission_mode": "auto"
    }
}

# =============================================================================
# FORM FIELDS
# =============================================================================

FORM_FIELDS = [
    {"name": "name", "required": True, "type": "text"},
    {"name": "description", "required": False, "type": "textarea"},
    {"name": "permission_mode", "required": True, "type": "select", "options": ["auto", "manual"]},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2.2.1",
        "part_a": "Read `frontend/app/dashboard/campaigns/new/page.tsx` — verify `useCreateCampaign` hook",
        "part_b": "Navigate to `/dashboard/campaigns/new`",
        "key_files": ["frontend/app/dashboard/campaigns/new/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/dashboard/campaigns/new",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["Create Campaign", "Name", "Description"]
            }
        }
    },
    {
        "id": "J2.2.2",
        "part_a": "Verify ICP is fetched via `GET /api/v1/clients/{id}/icp`",
        "part_b": "Check ICP industries/titles display",
        "key_files": ["src/api/routes/clients.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/clients/me/icp",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["icp_industries", "icp_titles", "icp_locations"]
            },
            "curl_command": """curl '{api_url}/api/v1/clients/me/icp' \\
  -H 'Authorization: Bearer {token}'""",
            "note": "Use /clients/me/icp or /clients/{client_id}/icp depending on implementation"
        }
    },
    {
        "id": "J2.2.3",
        "part_a": "Verify form fields: name (required), description (optional), permission_mode",
        "part_b": "Fill form, check validation",
        "key_files": ["frontend/app/dashboard/campaigns/new/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Navigate to /dashboard/campaigns/new",
                "2. Try to submit with empty name - verify validation error",
                "3. Fill in name only, submit - should succeed",
                "4. Verify description is optional",
                "5. Check permission_mode dropdown has options"
            ],
            "expect": {
                "name_required": True,
                "description_optional": True,
                "permission_mode_has_options": True
            }
        }
    },
    {
        "id": "J2.2.4",
        "part_a": "Check channel allocation is NOT in form (system determines)",
        "part_b": "Verify no channel inputs",
        "key_files": ["frontend/app/dashboard/campaigns/new/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Navigate to /dashboard/campaigns/new",
                "2. Inspect all form fields",
                "3. Verify NO fields for email/SMS/voice/LinkedIn allocation",
                "4. Channel allocation is determined by system based on ICP"
            ],
            "expect": {
                "no_channel_inputs": True,
                "no_allocation_sliders": True
            }
        }
    },
    {
        "id": "J2.2.5",
        "part_a": "Verify POST `/api/v1/campaigns` in `campaigns.py` creates campaign",
        "part_b": "Submit form, verify 201 response",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/campaigns",
            "auth": True,
            "body": {
                "name": "E2E Test Campaign",
                "description": "Created by E2E testing",
                "permission_mode": "auto"
            },
            "expect": {
                "status": 201,
                "body_has_fields": ["id", "name", "status"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/campaigns' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"name": "E2E Test Campaign", "description": "Created by E2E testing", "permission_mode": "auto"}'"""
        }
    },
    {
        "id": "J2.2.6",
        "part_a": "Verify campaign created with status='draft'",
        "part_b": "Check DB for new campaign",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "db_query",
            "precondition": "After creating campaign via API",
            "query": """
                SELECT id, name, status, created_at
                FROM campaigns
                WHERE name = 'E2E Test Campaign'
                ORDER BY created_at DESC
                LIMIT 1;
            """,
            "expect": {
                "status": "draft",
                "name": "E2E Test Campaign"
            }
        }
    }
]

PASS_CRITERIA = [
    "Form only has name, description, permission_mode",
    "ICP is displayed but not editable (link to settings)",
    "Campaign created successfully with 201",
    "Campaign status is 'draft' on creation",
    "Redirects to campaign list after creation"
]

KEY_FILES = [
    "frontend/app/dashboard/campaigns/new/page.tsx",
    "src/api/routes/campaigns.py",
    "src/api/routes/clients.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Create Page: {LIVE_CONFIG['frontend_url']}/dashboard/campaigns/new")
    lines.append("")
    lines.append("### Form Fields")
    for field in FORM_FIELDS:
        req = "required" if field["required"] else "optional"
        lines.append(f"  {field['name']}: {field['type']} ({req})")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("steps"):
            lines.append("  Steps:")
            for step in lt["steps"][:3]:
                lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
