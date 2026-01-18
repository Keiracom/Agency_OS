"""
Skill: J10.7 — Client Directory
Journey: J10 - Admin Dashboard
Checks: 7

Purpose: Verify client listing and management functionality.
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
# CLIENT ISOLATION CONSTANTS
# =============================================================================

CLIENT_STATUSES = [
    {"status": "active", "color": "green", "description": "Client is active and campaigns running"},
    {"status": "paused", "color": "yellow", "description": "Client paused all campaigns"},
    {"status": "cancelled", "color": "red", "description": "Client cancelled subscription"},
    {"status": "onboarding", "color": "blue", "description": "Client in onboarding process"}
]

CLIENT_ISOLATION_FIELDS = {
    "leads": "client_id",
    "campaigns": "client_id",
    "outreach_log": "client_id",
    "icp_profiles": "client_id"
}

CLIENT_METRICS = [
    {"metric": "total_leads", "description": "Total leads in pool for this client"},
    {"metric": "active_campaigns", "description": "Number of running campaigns"},
    {"metric": "messages_sent", "description": "Total outreach messages sent"},
    {"metric": "replies_received", "description": "Total replies received"},
    {"metric": "mrr", "description": "Monthly recurring revenue from client"}
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J10.7.1",
        "part_a": "Read `frontend/app/admin/clients/page.tsx` — verify client list",
        "part_b": "Load clients page, verify list renders",
        "key_files": ["frontend/app/admin/clients/page.tsx"],
        "live_test": {
            "type": "http",
            "method": "GET",
            "url": "{frontend_url}/admin/clients",
            "auth": True,
            "expect": {
                "status": 200,
                "body_contains": ["Clients", "Status", "Name"]
            },
            "manual_steps": [
                "1. Login as admin user",
                "2. Navigate to {frontend_url}/admin/clients",
                "3. Verify client list page loads",
                "4. Check table/grid of clients displays"
            ]
        }
    },
    {
        "id": "J10.7.2",
        "part_a": "Verify client search functionality",
        "part_b": "Search for client by name, verify results filter",
        "key_files": ["frontend/app/admin/clients/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/clients?search={search_term}",
            "auth": True,
            "test_values": {
                "search_term": "test"
            },
            "expect": {
                "status": 200,
                "body_is_array": True
            },
            "curl_command": """curl '{api_url}/api/v1/admin/clients?search=test' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/clients page, locate search input",
                "2. Type a client name or part of name",
                "3. Verify list filters to show matching clients",
                "4. Clear search, verify full list returns"
            ]
        }
    },
    {
        "id": "J10.7.3",
        "part_a": "Verify client status indicators",
        "part_b": "Check active/paused/cancelled status displays",
        "key_files": ["frontend/app/admin/clients/page.tsx"],
        "live_test": {
            "type": "api_batch",
            "tests": [
                {
                    "name": "Filter by active",
                    "method": "GET",
                    "url": "{api_url}/api/v1/admin/clients?status=active",
                    "expect": {"all_items_have": {"status": "active"}}
                },
                {
                    "name": "Filter by paused",
                    "method": "GET",
                    "url": "{api_url}/api/v1/admin/clients?status=paused",
                    "expect": {"all_items_have": {"status": "paused"}}
                }
            ],
            "auth": True,
            "curl_command": """curl '{api_url}/api/v1/admin/clients?status=active' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/clients page, locate status filter",
                "2. Verify active clients show green indicator",
                "3. Verify paused clients show yellow indicator",
                "4. Verify cancelled clients show red indicator"
            ]
        }
    },
    {
        "id": "J10.7.4",
        "part_a": "Verify client lead count displays",
        "part_b": "Check lead count matches actual leads for client",
        "key_files": ["frontend/app/admin/clients/page.tsx"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT c.id, c.name,
                       (SELECT COUNT(*) FROM leads WHERE client_id = c.id AND deleted_at IS NULL) as lead_count
                FROM clients c
                WHERE c.deleted_at IS NULL
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "name", "lead_count"]
            },
            "curl_command": """curl '{api_url}/api/v1/admin/clients/{client_id}/stats' \\
  -H 'Authorization: Bearer {token}'"""
        }
    },
    {
        "id": "J10.7.5",
        "part_a": "Verify client campaign count displays",
        "part_b": "Check campaign count matches actual campaigns",
        "key_files": ["frontend/app/admin/clients/page.tsx"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT c.id, c.name,
                       (SELECT COUNT(*) FROM campaigns WHERE client_id = c.id AND deleted_at IS NULL) as campaign_count
                FROM clients c
                WHERE c.deleted_at IS NULL
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "name", "campaign_count"]
            }
        }
    },
    {
        "id": "J10.7.6",
        "part_a": "Verify click navigates to client detail",
        "part_b": "Click client row, verify navigation to detail page",
        "key_files": ["frontend/app/admin/clients/page.tsx", "frontend/app/admin/clients/[id]/page.tsx"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. On /admin/clients page, click on any client row",
                "2. Verify navigation to /admin/clients/{client_id}",
                "3. Check client detail page loads",
                "4. Verify URL contains the client ID"
            ],
            "expect": {
                "navigates_to_detail": True,
                "url_contains_client_id": True
            }
        }
    },
    {
        "id": "J10.7.7",
        "part_a": "Verify pagination or infinite scroll",
        "part_b": "Navigate pages, verify data loads correctly",
        "key_files": ["frontend/app/admin/clients/page.tsx"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{api_url}/api/v1/admin/clients?limit=10&offset=10",
            "auth": True,
            "expect": {
                "status": 200,
                "body_is_array": True
            },
            "curl_command": """curl '{api_url}/api/v1/admin/clients?limit=10&offset=10' \\
  -H 'Authorization: Bearer {token}'""",
            "manual_steps": [
                "1. On /admin/clients page with many clients",
                "2. Click 'Next' page or scroll to load more",
                "3. Verify additional clients load",
                "4. Check no duplicate clients appear"
            ]
        }
    }
]

PASS_CRITERIA = [
    "Client list renders with data",
    "Search filters clients correctly",
    "Status indicators are accurate",
    "Lead counts are accurate",
    "Campaign counts are accurate",
    "Navigation to detail works",
    "Pagination functions correctly"
]

KEY_FILES = [
    "frontend/app/admin/clients/page.tsx",
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
    lines.append(f"- Clients Page: {LIVE_CONFIG['frontend_url']}/admin/clients")
    lines.append("")
    lines.append("### Client Statuses")
    for status in CLIENT_STATUSES:
        lines.append(f"  - {status['status']}: {status['color']} - {status['description']}")
    lines.append("")
    lines.append("### Client Isolation (Multi-Tenant)")
    for table, field in CLIENT_ISOLATION_FIELDS.items():
        lines.append(f"  - {table}: isolated by {field}")
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
