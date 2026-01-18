"""
Skill: J10.9 — Revenue Page
Journey: J10 - Admin Dashboard
Checks: 4

Purpose: Verify revenue tracking and reporting functionality.
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
# REVENUE METRICS CONSTANTS
# =============================================================================

REVENUE_METRICS = [
    {"metric": "MRR", "calculation": "Sum of all active client monthly fees", "format": "currency"},
    {"metric": "ARR", "calculation": "MRR * 12", "format": "currency"},
    {"metric": "Churn", "calculation": "Cancelled MRR / Total MRR", "format": "percentage"},
    {"metric": "Net Revenue", "calculation": "New MRR - Churned MRR", "format": "currency"},
    {"metric": "LTV", "calculation": "Average MRR * Average customer lifetime", "format": "currency"}
]

REVENUE_PERIODS = ["day", "week", "month", "quarter", "year", "all_time"]

CHART_TYPES = {
    "mrr_trend": "Line chart showing MRR over time",
    "revenue_by_client": "Bar chart showing revenue per client",
    "churn_analysis": "Area chart showing churn trends"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.9.1",
        "part_a": "Read `frontend/app/admin/revenue/page.tsx` — verify revenue display",
        "part_b": "Load revenue page, verify metrics render",
        "key_files": ["frontend/app/admin/revenue/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/admin/revenue",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["Revenue", "MRR", "ARR"]
            },
            "manual_steps": [
                "1. Login as admin user",
                "2. Navigate to {frontend_url}/admin/revenue",
                "3. Verify revenue page loads",
                "4. Check key metrics display: MRR, ARR, Churn"
            ]
        }
    },
    {
        "id": "J10.9.2",
        "part_a": "Verify MRR (Monthly Recurring Revenue) calculation",
        "part_b": "Check MRR matches sum of client subscriptions",
        "key_files": ["frontend/app/admin/revenue/page.tsx", "src/api/routes/admin.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/revenue/mrr",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["mrr", "mrr_change", "period"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/revenue/mrr' \\
  -H 'Authorization: Bearer {token}'""",
            "db_verify": {
                "query": """
                    SELECT SUM(mrr) as total_mrr
                    FROM clients
                    WHERE status = 'active'
                    AND deleted_at IS NULL;
                """,
                "expect": "MRR from API matches database sum"
            }
        }
    },
    {
        "id": "J10.9.3",
        "part_a": "Verify revenue trend chart displays",
        "part_b": "Check chart renders with historical data",
        "key_files": ["frontend/app/admin/revenue/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/revenue/trend?period=month&range=12",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["date", "revenue"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/revenue/trend?period=month&range=12' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/revenue page, locate trend chart",
                "2. Verify chart displays 12 months of data",
                "3. Hover over data points to see values",
                "4. Change period selector and verify chart updates"
            ]
        }
    },
    {
        "id": "J10.9.4",
        "part_a": "Verify revenue breakdown by client",
        "part_b": "Check per-client revenue displays correctly",
        "key_files": ["frontend/app/admin/revenue/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/revenue/by-client",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True,
                "array_items_have_fields": ["client_id", "client_name", "mrr"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/revenue/by-client' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/revenue page, locate 'Revenue by Client' section",
                "2. Verify each client shows with their MRR contribution",
                "3. Check totals sum to overall MRR",
                "4. Click client name to navigate to client detail"
            ]
        }
    }
]

PASS_CRITERIA = [
    "Revenue page loads correctly",
    "MRR calculation is accurate",
    "Revenue trend chart displays",
    "Per-client breakdown is accurate"
]

KEY_FILES = [
    "frontend/app/admin/revenue/page.tsx",
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
    lines.append(f"- Revenue Page: {LIVE_CONFIG['frontend_url']}/admin/revenue")
    lines.append("")
    lines.append("### Revenue Metrics")
    for metric in REVENUE_METRICS:
        lines.append(f"  - {metric['metric']}: {metric['calculation']} ({metric['format']})")
    lines.append("")
    lines.append("### Revenue Periods")
    lines.append(f"  Available: {', '.join(REVENUE_PERIODS)}")
    lines.append("")
    lines.append("### Chart Types")
    for chart, desc in CHART_TYPES.items():
        lines.append(f"  - {chart}: {desc}")
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
