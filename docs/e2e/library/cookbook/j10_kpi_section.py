"""
Skill: J10.3 — KPI Section
Journey: J10 - Admin Dashboard
Checks: 8

Purpose: Verify Key Performance Indicator cards display correct metrics.
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
# KPI METRICS CONSTANTS
# =============================================================================

KPI_METRICS = [
    {"name": "Active Leads", "source": "leads table count", "trend": "7-day change", "endpoint": "/api/v1/admin/stats/leads"},
    {"name": "Active Campaigns", "source": "campaigns where status='active'", "trend": "vs last month", "endpoint": "/api/v1/admin/stats/campaigns"},
    {"name": "Revenue", "source": "revenue table sum", "trend": "MTD vs last month", "endpoint": "/api/v1/admin/stats/revenue"},
    {"name": "AI Costs", "source": "llm_usage table sum", "trend": "MTD vs budget", "endpoint": "/api/v1/admin/stats/ai-costs"},
    {"name": "Clients", "source": "clients table count", "trend": "30-day change", "endpoint": "/api/v1/admin/stats/clients"},
    {"name": "Messages Sent", "source": "outreach_log count", "trend": "24h count", "endpoint": "/api/v1/admin/stats/messages"}
]

TREND_INDICATORS = {
    "up": {"color": "green", "icon": "arrow-up", "meaning": "Metric increased"},
    "down": {"color": "red", "icon": "arrow-down", "meaning": "Metric decreased"},
    "neutral": {"color": "gray", "icon": "minus", "meaning": "No significant change"}
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.3.1",
        "part_a": "Read admin page KPI component — verify metrics list",
        "part_b": "Load dashboard, verify KPI cards render",
        "key_files": ["frontend/app/admin/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/admin",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["Leads", "Campaigns", "Revenue", "Clients"]
            }
        }
    },
    {
        "id": "J10.3.2",
        "part_a": "Verify Active Leads KPI displays correctly",
        "part_b": "Check lead count matches database count",
        "key_files": ["frontend/app/admin/page.tsx", "src/api/routes/admin.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT COUNT(*) as total_leads
                FROM leads
                WHERE deleted_at IS NULL;
            """,
            "expect": {
                "returns_count": True
            },
            "api_verify": {
                "method": "GET",
                "url": "{api_url}/api/v1/admin/stats/leads",
                "expect": {"body_has_field": "count"}
            },
            "curl_command": """curl '{api_url}/api/v1/admin/stats/leads' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J10.3.3",
        "part_a": "Verify Active Campaigns KPI displays correctly",
        "part_b": "Check campaign count matches active campaigns",
        "key_files": ["frontend/app/admin/page.tsx", "src/api/routes/admin.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT COUNT(*) as active_campaigns
                FROM campaigns
                WHERE status = 'active'
                AND deleted_at IS NULL;
            """,
            "expect": {
                "returns_count": True
            },
            "curl_command": """curl '{api_url}/api/v1/admin/stats/campaigns' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J10.3.4",
        "part_a": "Verify Revenue KPI displays correctly",
        "part_b": "Check revenue figure is calculated correctly",
        "key_files": ["frontend/app/admin/page.tsx", "frontend/app/admin/revenue/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/stats/revenue",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["total", "mrr", "period"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/stats/revenue' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J10.3.5",
        "part_a": "Verify AI Cost KPI displays correctly",
        "part_b": "Check AI spend matches cost tracking",
        "key_files": ["frontend/app/admin/page.tsx", "frontend/app/admin/costs/ai/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/stats/ai-costs",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["total_cost", "period", "budget"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/stats/ai-costs' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J10.3.6",
        "part_a": "Verify Client Count KPI displays correctly",
        "part_b": "Check client count matches database",
        "key_files": ["frontend/app/admin/page.tsx", "frontend/app/admin/clients/page.tsx"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT COUNT(*) as total_clients
                FROM clients
                WHERE status = 'active'
                AND deleted_at IS NULL;
            """,
            "expect": {
                "returns_count": True
            },
            "curl_command": """curl '{api_url}/api/v1/admin/stats/clients' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J10.3.7",
        "part_a": "Verify KPI trend indicators work",
        "part_b": "Check up/down arrows reflect actual changes",
        "key_files": ["frontend/app/admin/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Navigate to /admin dashboard",
                "2. Observe KPI cards with trend indicators",
                "3. Verify green up-arrow = metric increased",
                "4. Verify red down-arrow = metric decreased",
                "5. Verify percentage shows period comparison (e.g., +12% vs last week)"
            ],
            "expect": {
                "trend_arrows_visible": True,
                "percentage_shown": True,
                "colors_match_direction": True
            }
        }
    },
    {
        "id": "J10.3.8",
        "part_a": "Verify KPI cards link to detail pages",
        "part_b": "Click each KPI card, verify navigation",
        "key_files": ["frontend/app/admin/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. On /admin page, click 'Active Leads' KPI card",
                "2. Verify navigation to leads list or detail page",
                "3. Click 'Revenue' KPI card",
                "4. Verify navigation to /admin/revenue",
                "5. Click 'AI Costs' KPI card",
                "6. Verify navigation to /admin/costs/ai"
            ],
            "expect": {
                "cards_clickable": True,
                "navigates_to_detail": True
            }
        }
    }
]

PASS_CRITERIA = [
    "All KPI cards render with data",
    "Lead count is accurate",
    "Campaign count is accurate",
    "Revenue calculation is correct",
    "AI cost tracking is accurate",
    "Client count matches reality",
    "Trend indicators reflect actual changes",
    "KPI cards are clickable and navigate correctly"
]

KEY_FILES = [
    "frontend/app/admin/page.tsx",
    "src/api/routes/admin.py",
    "frontend/app/admin/revenue/page.tsx",
    "frontend/app/admin/costs/ai/page.tsx",
    "frontend/app/admin/clients/page.tsx"
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
    lines.append("### KPI Metrics")
    for metric in KPI_METRICS:
        lines.append(f"  - {metric['name']}: {metric['source']} (trend: {metric['trend']})")
    lines.append("")
    lines.append("### Trend Indicators")
    for direction, info in TREND_INDICATORS.items():
        lines.append(f"  - {direction}: {info['color']} {info['icon']} - {info['meaning']}")
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
