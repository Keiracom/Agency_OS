"""
Skill: J9.6 — Leads List Page
Journey: J9 - Client Dashboard
Checks: 7

Purpose: Verify leads list page displays all leads for the client with filtering,
sorting, pagination, and correct ALS scores.
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
# LEADS LIST CONSTANTS
# =============================================================================

LEAD_TABLE_COLUMNS = [
    "name",
    "company",
    "title",
    "email",
    "als_score",
    "status",
    "last_activity",
    "created_at",
]

LEAD_STATUSES = [
    "new",
    "contacted",
    "qualified",
    "meeting_scheduled",
    "proposal_sent",
    "won",
    "lost",
]

FILTER_OPTIONS = {
    "tier": ["hot", "warm", "cool", "cold", "dead"],
    "status": LEAD_STATUSES,
    "campaign_id": "UUID of campaign",
}

SORT_COLUMNS = ["als_score", "name", "company", "created_at", "last_activity"]

PAGINATION_DEFAULTS = {
    "page": 1,
    "per_page": 25,
    "max_per_page": 100,
}

# =============================================================================
# API ENDPOINTS
# =============================================================================

API_ENDPOINTS = [
    {"method": "GET", "path": "/api/v1/leads", "purpose": "List leads with pagination", "auth": True},
    {"method": "GET", "path": "/api/v1/leads?tier=hot", "purpose": "Filter by ALS tier", "auth": True},
    {"method": "GET", "path": "/api/v1/leads?search=query", "purpose": "Search leads", "auth": True},
    {"method": "GET", "path": "/api/v1/leads?sort=als_score&order=desc", "purpose": "Sort leads", "auth": True},
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J9.6.1",
        "part_a": "Verify leads list page renders",
        "part_b": "Navigate to /dashboard/leads, check table renders with lead data",
        "key_files": ["frontend/app/dashboard/leads/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/dashboard/leads",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["leads", "Name", "Company", "Score"]
            },
            "curl_command": """curl '{frontend_url}/dashboard/leads' \\
  -H 'Cookie: sb-access-token={token}'"""
        }
    },
    {
        "id": "J9.6.2",
        "part_a": "Verify leads API returns paginated results",
        "part_b": "GET /api/v1/leads returns leads with pagination metadata",
        "key_files": ["src/api/routes/leads.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/leads",
            "auth": True,
            "expect": {
                "status": 200,
                "body_has_fields": ["data", "total", "page", "per_page"]
            },
            "curl_command": """curl '{api_url}/api/v1/leads' \\
  -H 'Authorization: Bearer {token}' | jq '{total: .total, page: .page, count: (.data | length)}'"""
        }
    },
    {
        "id": "J9.6.3",
        "part_a": "Verify lead columns display correctly",
        "part_b": "Table shows name, company, ALS score, status, last activity",
        "key_files": ["frontend/app/dashboard/leads/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard/leads (authenticated)",
                "2. Verify table has columns: Name, Company, Score, Status, Last Activity",
                "3. Check that lead rows display data for each column",
                "4. Verify ALS score shows with tier color indicator"
            ],
            "expect": {
                "all_columns_visible": True,
                "data_populated": True,
                "score_has_color": True
            }
        }
    },
    {
        "id": "J9.6.4",
        "part_a": "Verify ALS tier filter works",
        "part_b": "Filter by Hot/Warm/Cool/Cold/Dead, verify filtered results",
        "key_files": ["frontend/app/dashboard/leads/page.tsx", "src/api/routes/leads.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/leads?tier=hot",
            "auth": True,
            "expect": {
                "status": 200,
                "all_leads_in_tier": "hot",
                "all_scores_gte": 85
            },
            "curl_command": """curl '{api_url}/api/v1/leads?tier=hot' \\
  -H 'Authorization: Bearer {token}' | jq '.data[] | select(.als_score < 85)'"""
        }
    },
    {
        "id": "J9.6.5",
        "part_a": "Verify search functionality works",
        "part_b": "Search by lead name or company, verify matching results",
        "key_files": ["frontend/app/dashboard/leads/page.tsx", "src/api/routes/leads.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/leads?search=test",
            "auth": True,
            "expect": {
                "status": 200,
                "results_contain_search_term": True
            },
            "curl_command": """curl '{api_url}/api/v1/leads?search=test' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J9.6.6",
        "part_a": "Verify sorting works on columns",
        "part_b": "Click column header, verify sort order changes (asc/desc)",
        "key_files": ["frontend/app/dashboard/leads/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/leads?sort=als_score&order=desc",
            "auth": True,
            "expect": {
                "status": 200,
                "results_sorted_desc_by": "als_score"
            },
            "curl_command": """curl '{api_url}/api/v1/leads?sort=als_score&order=desc' \\
  -H 'Authorization: Bearer {token}' | jq '.data[:5] | .[].als_score'"""
        }
    },
    {
        "id": "J9.6.7",
        "part_a": "Verify clicking lead navigates to detail",
        "part_b": "Click lead row, navigate to /dashboard/leads/[id]",
        "key_files": ["frontend/app/dashboard/leads/page.tsx", "frontend/app/dashboard/leads/[id]/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open {frontend_url}/dashboard/leads (authenticated)",
                "2. Click on a lead row in the table",
                "3. Verify navigation to /dashboard/leads/{lead_id}",
                "4. Verify lead detail page loads"
            ],
            "expect": {
                "click_navigates": True,
                "url_contains_lead_id": True,
                "detail_page_loads": True
            }
        }
    },
]

PASS_CRITERIA = [
    "Leads list page renders with table",
    "API returns paginated lead data",
    "All required columns display correctly",
    "ALS tier filter filters leads correctly",
    "Search filters leads by name/company",
    "Column sorting works (asc/desc)",
    "Click navigates to lead detail page",
]

KEY_FILES = [
    "frontend/app/dashboard/leads/page.tsx",
    "frontend/app/dashboard/leads/[id]/page.tsx",
    "src/api/routes/leads.py",
    "src/models/lead.py",
    "frontend/components/ui/table.tsx",
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
    lines.append("### Lead Table Columns")
    for col in LEAD_TABLE_COLUMNS:
        lines.append(f"  - {col}")
    lines.append("")
    lines.append("### Filter Options")
    lines.append(f"  Tiers: {', '.join(FILTER_OPTIONS['tier'])}")
    lines.append(f"  Statuses: {', '.join(FILTER_OPTIONS['status'])}")
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
