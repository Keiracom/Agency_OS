"""
Skill: J2.4 — Campaign Activation Flow
Journey: J2 - Campaign Creation & Management
Checks: 5

Purpose: Verify campaign activation triggers Prefect flow.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co"
}

# =============================================================================
# ACTIVATION FLOW
# =============================================================================

ACTIVATION_FLOW = [
    {"step": 1, "action": "API call POST /campaigns/{id}/activate"},
    {"step": 2, "action": "Validate campaign has leads"},
    {"step": 3, "action": "Trigger campaign_flow in Prefect"},
    {"step": 4, "action": "Update status to 'active'"},
    {"step": 5, "action": "Log activity"},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2.4.1",
        "part_a": "Read `src/api/routes/campaigns.py` — find activate endpoint",
        "part_b": "Locate POST `/campaigns/{id}/activate`",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Endpoint POST /campaigns/{id}/activate exists",
            "expect": {
                "code_contains": ["@router.post", "/activate", "campaign_id"]
            }
        }
    },
    {
        "id": "J2.4.2",
        "part_a": "Verify activation triggers `campaign_flow` in Prefect",
        "part_b": "Check Prefect deployment exists",
        "key_files": ["src/orchestration/flows/campaign_flow.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open Prefect UI: {prefect_url}",
                "2. Navigate to Deployments",
                "3. Search for 'campaign_flow' or 'campaign-flow'",
                "4. Verify deployment exists and is active"
            ],
            "expect": {
                "deployment_exists": True,
                "deployment_active": True
            },
            "prefect_url": "{prefect_url}/deployments"
        }
    },
    {
        "id": "J2.4.3",
        "part_a": "Read `src/orchestration/flows/campaign_flow.py` — verify JIT validation",
        "part_b": "Check validation steps",
        "key_files": ["src/orchestration/flows/campaign_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Flow performs JIT validation before processing",
            "expect": {
                "code_contains": ["validate", "leads", "campaign"]
            },
            "manual_verify": [
                "1. Read campaign_flow.py",
                "2. Look for validation logic at start of flow",
                "3. Verify it checks: has leads, has valid ICP, not already active"
            ]
        }
    },
    {
        "id": "J2.4.4",
        "part_a": "Verify campaign status updates to 'active'",
        "part_b": "Check DB after activation",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "api_then_db",
            "steps": [
                "1. Create a campaign with leads (or use existing)",
                "2. Call POST /api/v1/campaigns/{id}/activate",
                "3. Query database for campaign status"
            ],
            "api_call": {
                "method": "POST",
                "url": "{api_url}/api/v1/campaigns/{campaign_id}/activate",
                "auth": True
            },
            "db_query": "SELECT status FROM campaigns WHERE id = '{campaign_id}'",
            "expect": {
                "api_status": 200,
                "db_status": "active"
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/campaigns/{campaign_id}/activate' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J2.4.5",
        "part_a": "Verify webhook triggers flow OR API triggers flow",
        "part_b": "Test both trigger methods",
        "key_files": ["src/api/routes/campaigns.py", "src/orchestration/flows/campaign_flow.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Activate a campaign via API",
                "2. Open Prefect UI → Flow Runs",
                "3. Find the campaign_flow run triggered by activation",
                "4. Verify flow parameters include campaign_id",
                "5. Check flow completes successfully"
            ],
            "expect": {
                "flow_triggered": True,
                "flow_has_campaign_id": True,
                "flow_completes": True
            },
            "prefect_url": "{prefect_url}/flow-runs"
        }
    }
]

PASS_CRITERIA = [
    "Activation triggers Prefect flow",
    "JIT validation runs (fails if missing requirements)",
    "Campaign status changes to 'active'",
    "Activity logged in activities table"
]

KEY_FILES = [
    "src/api/routes/campaigns.py",
    "src/orchestration/flows/campaign_flow.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Activation Flow")
    for step in ACTIVATION_FLOW:
        lines.append(f"  Step {step['step']}: {step['action']}")
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
