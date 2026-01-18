"""
Skill: J9.10 — Reports Page
Journey: J9 - Client Dashboard
Checks: 5

Purpose: Verify reports page displays performance reports, allows date range
selection, and provides export functionality.
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
# REPORTS CONSTANTS
# =============================================================================

REPORT_TYPES = [
    {"name": "lead_generation", "label": "Lead Generation Report"},
    {"name": "email_performance", "label": "Email Performance Report"},
    {"name": "campaign_analytics", "label": "Campaign Analytics Report"},
    {"name": "conversion_funnel", "label": "Conversion Funnel Report"},
    {"name": "activity_summary", "label": "Activity Summary Report"},
]

DATE_RANGE_PRESETS = [
    {"value": "7d", "label": "Last 7 days"},
    {"value": "30d", "label": "Last 30 days"},
    {"value": "90d", "label": "Last 90 days"},
    {"value": "ytd", "label": "Year to date"},
    {"value": "custom", "label": "Custom range"},
]

EXPORT_FORMATS = ["csv", "pdf", "xlsx"]

REPORT_METRICS = {
    "lead_generation": ["new_leads", "leads_by_source", "leads_by_tier", "conversion_rate"],
    "email_performance": ["emails_sent", "open_rate", "click_rate", "reply_rate", "bounce_rate"],
    "campaign_analytics": ["campaign_performance", "sequence_completion", "best_performing_templates"],
    "conversion_funnel": ["stage_counts", "conversion_rates", "time_in_stage", "drop_off_points"],
}

# =============================================================================
# API ENDPOINTS
# =============================================================================

API_ENDPOINTS = [
    {"method": "GET", "path": "/api/v1/reports", "purpose": "Get available reports", "auth": True},
    {"method": "GET", "path": "/api/v1/reports/{type}?start={date}&end={date}", "purpose": "Get specific report data", "auth": True},
    {"method": "GET", "path": "/api/v1/reports/{type}/export?format=csv", "purpose": "Export report", "auth": True},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.10.1",
        "part_a": "Verify reports page renders",
        "part_b": "Navigate to /dashboard/reports, check page renders with report options",
        "key_files": ["frontend/app/dashboard/reports/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/dashboard/reports",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["reports", "Lead Generation", "Email Performance"]
            },
            "curl_command": """curl '{frontend_url}/dashboard/reports' \\
  -H 'Cookie: sb-access-token={token}'"""
        }
    },
    {
        "id": "J9.10.2",
        "part_a": "Verify reports API returns data",
        "part_b": "GET /api/v1/reports returns report data for tenant",
        "key_files": ["src/api/routes/reports.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/reports/lead_generation",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["data", "date_range", "metrics"]
            },
            "curl_command": """curl '{api_url}/api/v1/reports/lead_generation' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J9.10.3",
        "part_a": "Verify date range selector works",
        "part_b": "Select date range, verify report data updates accordingly",
        "key_files": ["frontend/app/dashboard/reports/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/reports/email_performance?start=2026-01-01&end=2026-01-18",
            "auth": True,
            "expect": {
                "status": 200,
                "date_range_applied": True,
                "body_has_field": "date_range"
            },
            "curl_command": """curl '{api_url}/api/v1/reports/email_performance?start=2026-01-01&end=2026-01-18' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J9.10.4",
        "part_a": "Verify report metrics display",
        "part_b": "Page shows lead generation, email performance, conversion metrics",
        "key_files": ["frontend/app/dashboard/reports/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard/reports (authenticated)",
                "2. Select 'Lead Generation Report'",
                "3. Verify metrics displayed: new leads, leads by source, leads by tier",
                "4. Select 'Email Performance Report'",
                "5. Verify metrics: emails sent, open rate, click rate, reply rate",
                "6. Check charts and visualizations render correctly"
            ],
            "expect": {
                "lead_metrics_visible": True,
                "email_metrics_visible": True,
                "charts_render": True
            }
        }
    },
    {
        "id": "J9.10.5",
        "part_a": "Verify export functionality works",
        "part_b": "Click export button, download CSV/PDF of report data",
        "key_files": ["frontend/app/dashboard/reports/page.tsx", "src/api/routes/reports.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/reports/lead_generation/export?format=csv",
            "auth": True,
            "expect": {
                "status": 200,
                "content_type": "text/csv",
                "content_disposition_contains": "attachment"
            },
            "curl_command": """curl -I '{api_url}/api/v1/reports/lead_generation/export?format=csv' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
]

PASS_CRITERIA = [
    "Reports page renders without errors",
    "Reports API returns data for tenant",
    "Date range selector filters data correctly",
    "Report metrics display accurately",
    "Export generates downloadable file",
]

KEY_FILES = [
    "frontend/app/dashboard/reports/page.tsx",
    "src/api/routes/reports.py",
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
    lines.append("### Report Types")
    for report in REPORT_TYPES:
        lines.append(f"  - {report['name']}: {report['label']}")
    lines.append("")
    lines.append("### Date Range Presets")
    for preset in DATE_RANGE_PRESETS:
        lines.append(f"  - {preset['value']}: {preset['label']}")
    lines.append("")
    lines.append("### Export Formats")
    lines.append(f"  {', '.join(EXPORT_FORMATS)}")
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
