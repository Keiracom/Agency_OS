"""
Skill: J9.9 — Campaign Detail Page
Journey: J9 - Client Dashboard
Checks: 5

Purpose: Verify campaign detail page displays campaign configuration, sequence
steps, performance analytics, and associated leads.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
}

# =============================================================================
# CAMPAIGN DETAIL CONSTANTS
# =============================================================================

CAMPAIGN_CONFIG_FIELDS = [
    "name",
    "description",
    "status",
    "target_criteria",
    "created_at",
    "updated_at",
    "starts_at",
    "ends_at",
]

SEQUENCE_STEP_FIELDS = [
    "step_number",
    "type",  # email, linkedin, sms, call
    "delay_days",
    "template_id",
    "subject",
    "status",
]

PERFORMANCE_METRICS = [
    {"name": "open_rate", "label": "Open Rate", "format": "percentage"},
    {"name": "click_rate", "label": "Click Rate", "format": "percentage"},
    {"name": "reply_rate", "label": "Reply Rate", "format": "percentage"},
    {"name": "bounce_rate", "label": "Bounce Rate", "format": "percentage"},
    {"name": "unsubscribe_rate", "label": "Unsubscribe Rate", "format": "percentage"},
    {"name": "conversion_rate", "label": "Conversion Rate", "format": "percentage"},
]

LEAD_ENROLLMENT_STATUSES = [
    "enrolled",
    "active",
    "completed",
    "paused",
    "unsubscribed",
    "bounced",
]

# =============================================================================
# API ENDPOINTS
# =============================================================================

API_ENDPOINTS = [
    {"method": "GET", "path": "/api/v1/campaigns/{id}", "purpose": "Get campaign details", "auth": True},
    {"method": "GET", "path": "/api/v1/campaigns/{id}/sequence", "purpose": "Get sequence steps", "auth": True},
    {"method": "GET", "path": "/api/v1/campaigns/{id}/analytics", "purpose": "Get performance analytics", "auth": True},
    {"method": "GET", "path": "/api/v1/campaigns/{id}/leads", "purpose": "Get enrolled leads", "auth": True},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.9.1",
        "part_a": "Verify campaign detail page renders",
        "part_b": "Navigate to /dashboard/campaigns/[id], check page renders with campaign data",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/campaigns/{campaign_id}",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["id", "name", "status", "created_at"]
            },
            "curl_command": """curl '{api_url}/api/v1/campaigns/{campaign_id}' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J9.9.2",
        "part_a": "Verify campaign configuration displays",
        "part_b": "Page shows campaign name, status, created date, target criteria",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard/campaigns/{campaign_id} (authenticated)",
                "2. Verify campaign name is displayed as page title",
                "3. Check status badge shows current status",
                "4. Verify created date is shown",
                "5. Check target criteria/ICP settings are visible"
            ],
            "expect": {
                "name_displayed": True,
                "status_badge_visible": True,
                "created_date_shown": True,
                "target_criteria_visible": True
            }
        }
    },
    {
        "id": "J9.9.3",
        "part_a": "Verify sequence steps display",
        "part_b": "Page shows email sequence with step timing and status",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/campaigns/{campaign_id}/sequence",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "steps_have_fields": ["step_number", "type", "delay_days"]
            },
            "curl_command": """curl '{api_url}/api/v1/campaigns/{campaign_id}/sequence' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J9.9.4",
        "part_a": "Verify performance analytics display",
        "part_b": "Page shows open rate, click rate, reply rate, bounce rate charts",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/campaigns/{campaign_id}/analytics",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["open_rate", "click_rate", "reply_rate", "bounce_rate"]
            },
            "curl_command": """curl '{api_url}/api/v1/campaigns/{campaign_id}/analytics' \\
  -H 'Authorization: Bearer {token}' | jq '{open_rate, click_rate, reply_rate}'"""
        }
    },
    {
        "id": "J9.9.5",
        "part_a": "Verify associated leads list displays",
        "part_b": "Page shows leads enrolled in campaign with their status",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/campaigns/{campaign_id}/leads",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_field": "data",
                "leads_have_fields": ["lead_id", "status", "current_step", "enrolled_at"]
            },
            "curl_command": """curl '{api_url}/api/v1/campaigns/{campaign_id}/leads' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
]

PASS_CRITERIA = [
    "Campaign detail page renders without errors",
    "Campaign configuration displays completely",
    "Sequence steps show timing and status",
    "Performance analytics charts render",
    "Associated leads list displays with status",
]

KEY_FILES = [
    "frontend/app/dashboard/campaigns/[id]/page.tsx",
    "src/api/routes/campaigns.py",
    "src/models/campaign.py",
    "src/models/sequence_step.py",
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_live_url(path: str) -> str:
    """Get full URL for live testing."""
    base = LIVE_CONFIG["frontend_url"]
    return f"{base}{path}"


def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"


def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Campaign Config Fields")
    for field in CAMPAIGN_CONFIG_FIELDS:
        lines.append(f"  - {field}")
    lines.append("")
    lines.append("### Performance Metrics")
    for metric in PERFORMANCE_METRICS:
        lines.append(f"  - {metric['name']}: {metric['label']} ({metric['format']})")
    lines.append("")
    lines.append("### API Endpoints")
    for ep in API_ENDPOINTS:
        lines.append(f"  {ep['method']} {ep['path']} - {ep['purpose']}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
            if lt.get("url"):
                lines.append(f"  URL: {lt['url']}")
            if lt.get("steps"):
                lines.append("  Steps:")
                for step in lt["steps"]:
                    lines.append(f"    {step}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    lines.append("")
    lines.append("### Key Files")
    for f in KEY_FILES:
        lines.append(f"- {f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_instructions())
