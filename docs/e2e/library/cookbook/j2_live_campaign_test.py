"""
Skill: J2.12 — Campaign Edge Cases
Journey: J2 - Campaign Creation & Management
Checks: 6

Purpose: Test error handling and edge conditions.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co"
}

# =============================================================================
# EDGE CASE SCENARIOS
# =============================================================================

EDGE_CASES = [
    {"scenario": "no_icp_configured", "expected": "Warning but allow creation"},
    {"scenario": "no_leads", "expected": "Fail activation validation"},
    {"scenario": "no_sequences", "expected": "Fail or warn on activation"},
    {"scenario": "duplicate_name", "expected": "Allow (names not unique) or reject"},
    {"scenario": "zero_allocation", "expected": "Validation error"},
    {"scenario": "pause_mid_sequence", "expected": "Preserve sequence state"},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2.12.1",
        "part_a": "Create campaign without ICP configured",
        "part_b": "Should warn but allow",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/campaigns",
            "auth": True,
            "body": {
                "name": "No ICP Test Campaign",
                "description": "Testing without ICP"
            },
            "precondition": "Ensure client has no ICP configured (icp_confirmed_at = NULL)",
            "expect": {
                "status": [201, 200],
                "body_has_field": "id"
            },
            "note": "May return warning in response but should still create campaign"
        }
    },
    {
        "id": "J2.12.2",
        "part_a": "Activate campaign with no leads",
        "part_b": "Should fail validation",
        "key_files": ["src/api/routes/campaigns.py", "src/orchestration/flows/campaign_flow.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/campaigns/{campaign_id}/activate",
            "auth": True,
            "precondition": "Campaign has 0 leads assigned",
            "expect": {
                "status": [400, 422],
                "body_contains": ["leads", "required", "empty"]
            },
            "curl_command": """# First create campaign, then try to activate without leads
curl -X POST '{api_url}/api/v1/campaigns/{campaign_id}/activate' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J2.12.3",
        "part_a": "Activate campaign with no sequences",
        "part_b": "Should fail or warn",
        "key_files": ["src/api/routes/campaigns.py", "src/orchestration/flows/campaign_flow.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/campaigns/{campaign_id}/activate",
            "auth": True,
            "precondition": "Campaign has leads but no sequences configured",
            "expect": {
                "status": [400, 422],
                "body_contains": ["sequence", "required"]
            }
        }
    },
    {
        "id": "J2.12.4",
        "part_a": "Duplicate campaign name",
        "part_b": "Check uniqueness constraint",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "api_batch",
            "tests": [
                {
                    "name": "Create first campaign",
                    "method": "POST",
                    "url": "{api_url}/api/v1/campaigns",
                    "body": {"name": "Duplicate Test Name"},
                    "expect": {"status": 201}
                },
                {
                    "name": "Create second with same name",
                    "method": "POST",
                    "url": "{api_url}/api/v1/campaigns",
                    "body": {"name": "Duplicate Test Name"},
                    "expect": {"status": [201, 409]}
                }
            ],
            "auth": True,
            "note": "Behavior depends on whether names must be unique"
        }
    },
    {
        "id": "J2.12.5",
        "part_a": "Campaign with 0% allocation (all channels)",
        "part_b": "Check validation",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "code_verify",
            "check": "System determines channel allocation, not user",
            "expect": {
                "no_user_allocation_input": True
            },
            "note": "Channel allocation is system-determined based on ICP and tier - user cannot set to 0%"
        }
    },
    {
        "id": "J2.12.6",
        "part_a": "Pause mid-sequence",
        "part_b": "Verify sequence state preservation",
        "key_files": ["src/api/routes/campaigns.py", "src/orchestration/flows/campaign_flow.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Create and activate a campaign with multi-step sequence",
                "2. Wait for some leads to progress to step 2+",
                "3. Call POST /campaigns/{id}/pause",
                "4. Query leads table for current_sequence_step",
                "5. Verify steps are preserved (not reset to 0)",
                "6. Reactivate campaign",
                "7. Verify leads resume from their saved step"
            ],
            "expect": {
                "sequence_step_preserved": True,
                "no_step_reset_on_pause": True,
                "resume_from_saved_step": True
            },
            "db_verify": """
                SELECT l.id, l.email, l.current_sequence_step, l.last_contacted_at
                FROM leads l
                WHERE l.campaign_id = '{campaign_id}'
                ORDER BY l.current_sequence_step DESC
                LIMIT 10;
            """
        }
    }
]

PASS_CRITERIA = [
    "Appropriate validation errors returned",
    "No silent failures on edge cases",
    "State preserved on pause/resume"
]

KEY_FILES = [
    "src/api/routes/campaigns.py",
    "src/orchestration/flows/campaign_flow.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append("")
    lines.append("### Edge Case Scenarios")
    for ec in EDGE_CASES:
        lines.append(f"  {ec['scenario']}: {ec['expected']}")
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
