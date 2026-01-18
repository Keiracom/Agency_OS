"""
Skill: J2.3 — Campaign Detail Page
Journey: J2 - Campaign Creation & Management
Checks: 5

Purpose: Verify campaign detail displays real data.

KNOWN ISSUE: Campaign detail page uses HARDCODED MOCK DATA (lines 14-42).
This MUST be fixed before E2E testing.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "note": "CRITICAL: Verify page uses real API data, not mock data"
}

# =============================================================================
# KNOWN ISSUES
# =============================================================================

KNOWN_ISSUES = [
    {
        "issue": "Mock data in campaign detail page",
        "file": "frontend/app/dashboard/campaigns/[id]/page.tsx",
        "lines": "14-42",
        "severity": "CRITICAL",
        "fix_required": True
    }
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2.3.1",
        "part_a": "Read `frontend/app/dashboard/campaigns/[id]/page.tsx` — **VERIFY DATA SOURCE**",
        "part_b": "Navigate to `/dashboard/campaigns/{id}`",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"],
        "live_test": {
            "type": "code_verify",
            "check": "Page must use useCampaign hook or fetch, NOT hardcoded mock data",
            "look_for": ["useCampaign", "fetch", "useQuery"],
            "red_flags": ["const campaign = {", "mockCampaign", "hardcoded"],
            "expect": {
                "uses_api": True,
                "no_mock_data": True
            }
        }
    },
    {
        "id": "J2.3.2",
        "part_a": "CRITICAL: Check if using mock data (lines 14-42) or real API",
        "part_b": "Check network tab for API call",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Navigate to /dashboard/campaigns/{campaign_id}",
                "2. Open DevTools > Network tab",
                "3. Look for GET /api/v1/campaigns/{id} request",
                "4. If NO request found → FAIL (using mock data)",
                "5. If request found → verify response matches displayed data"
            ],
            "expect": {
                "api_call_made": True,
                "data_matches_response": True
            },
            "severity": "CRITICAL"
        }
    },
    {
        "id": "J2.3.3",
        "part_a": "Verify GET `/api/v1/campaigns/{id}` returns campaign with metrics",
        "part_b": "Test endpoint directly",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/campaigns/{campaign_id}",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["id", "name", "status", "total_leads", "contacted", "replied"]
            },
            "curl_command": """curl '{api_url}/api/v1/campaigns/{campaign_id}' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J2.3.4",
        "part_a": "Verify activate/pause buttons call correct endpoints",
        "part_b": "Click activate/pause",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"],
        "live_test": {
            "type": "api_batch",
            "tests": [
                {
                    "name": "Activate campaign",
                    "method": "POST",
                    "url": "{api_url}/api/v1/campaigns/{campaign_id}/activate",
                    "expect": {"status": 200}
                },
                {
                    "name": "Pause campaign",
                    "method": "POST",
                    "url": "{api_url}/api/v1/campaigns/{campaign_id}/pause",
                    "expect": {"status": 200}
                }
            ],
            "auth": True,
            "manual_steps": [
                "1. Navigate to campaign detail page",
                "2. Click 'Activate' button, verify status changes",
                "3. Click 'Pause' button, verify status changes",
                "4. Check network tab for API calls"
            ]
        }
    },
    {
        "id": "J2.3.5",
        "part_a": "Verify lead list shows real leads",
        "part_b": "Check leads section",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/campaigns/{campaign_id}/leads",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True
            },
            "manual_steps": [
                "1. Navigate to campaign detail page",
                "2. Scroll to leads section",
                "3. Verify leads list is populated (or shows 'No leads yet')",
                "4. Click on a lead to verify navigation"
            ]
        }
    }
]

PASS_CRITERIA = [
    "Page fetches real campaign data (FIX REQUIRED if using mock)",
    "Stats (total leads, contacted, replied) accurate",
    "Activate/Pause buttons work and call API",
    "Lead list loads from API"
]

KEY_FILES = [
    "frontend/app/dashboard/campaigns/[id]/page.tsx",
    "src/api/routes/campaigns.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append("")
    lines.append("### ⚠️ KNOWN ISSUES")
    for issue in KNOWN_ISSUES:
        lines.append(f"  - {issue['issue']}")
        lines.append(f"    File: {issue['file']} (lines {issue['lines']})")
        lines.append(f"    Severity: {issue['severity']}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("severity"):
            lines.append(f"  ⚠️ Severity: {lt['severity']}")
        if lt.get("manual_steps"):
            lines.append("  Steps:")
            for step in lt["manual_steps"][:3]:
                lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
