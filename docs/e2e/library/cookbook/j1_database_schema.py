"""
Skill: J1.14 — Database Schema Verification
Journey: J1 - Signup & Onboarding
Checks: 6

Purpose: Verify all required tables and columns exist.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "note": "Schema queries require service_role_key for information_schema access"
}

# =============================================================================
# EXPECTED SCHEMA
# =============================================================================

EXPECTED_SCHEMA = {
    "users": ["id", "email", "full_name", "created_at"],
    "clients": [
        "id", "name", "tier", "website_url", "company_description",
        "services_offered", "icp_industries", "icp_company_sizes",
        "icp_locations", "icp_titles", "icp_pain_points", "als_weights",
        "icp_confirmed_at", "created_at"
    ],
    "memberships": ["id", "user_id", "client_id", "role", "accepted_at", "created_at"],
    "icp_extraction_jobs": [
        "id", "client_id", "website_url", "status",
        "completed_steps", "total_steps", "extracted_icp",
        "error_message", "created_at"
    ]
}

# =============================================================================
# SCHEMA QUERIES
# =============================================================================

SCHEMA_QUERIES = {
    "table_columns": """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = '{table_name}'
        ORDER BY ordinal_position;
    """,
    "check_trigger": """
        SELECT tgname, tgenabled
        FROM pg_trigger
        WHERE tgname = 'on_auth_user_created';
    """,
    "check_function": """
        SELECT proname, pronargs
        FROM pg_proc
        WHERE proname = 'get_onboarding_status';
    """
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.14.1",
        "part_a": "Verify `users` table has: id, email, full_name",
        "part_b": "Query schema",
        "key_files": [],
        "live_test": {
            "type": "db_query",
            "query": SCHEMA_QUERIES["table_columns"].format(table_name="users"),
            "expect": {
                "columns_exist": ["id", "email", "full_name"],
                "id_type": "uuid",
                "email_type": "text"
            },
            "curl_command": """curl -X POST '{supabase_url}/rest/v1/rpc/sql' \\
  -H 'apikey: {service_role_key}' \\
  -H 'Authorization: Bearer {service_role_key}' \\
  -H 'Content-Type: application/json' \\
  -d '{"query": "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = \\'users\\'"}'"""
        }
    },
    {
        "id": "J1.14.2",
        "part_a": "Verify `clients` table has all ICP columns",
        "part_b": "Query schema",
        "key_files": [],
        "live_test": {
            "type": "db_query",
            "query": SCHEMA_QUERIES["table_columns"].format(table_name="clients"),
            "expect": {
                "columns_exist": [
                    "id", "name", "tier", "website_url",
                    "icp_industries", "icp_titles", "icp_locations",
                    "icp_pain_points", "icp_confirmed_at"
                ],
                "icp_industries_type": "ARRAY",
                "icp_titles_type": "ARRAY"
            }
        }
    },
    {
        "id": "J1.14.3",
        "part_a": "Verify `memberships` table has: user_id, client_id, role, accepted_at",
        "part_b": "Query schema",
        "key_files": [],
        "live_test": {
            "type": "db_query",
            "query": SCHEMA_QUERIES["table_columns"].format(table_name="memberships"),
            "expect": {
                "columns_exist": ["user_id", "client_id", "role", "accepted_at"],
                "user_id_type": "uuid",
                "client_id_type": "uuid"
            }
        }
    },
    {
        "id": "J1.14.4",
        "part_a": "Verify `icp_extraction_jobs` table exists",
        "part_b": "Query schema",
        "key_files": [],
        "live_test": {
            "type": "db_query",
            "query": SCHEMA_QUERIES["table_columns"].format(table_name="icp_extraction_jobs"),
            "expect": {
                "columns_exist": [
                    "id", "client_id", "status",
                    "completed_steps", "total_steps",
                    "extracted_icp", "error_message"
                ],
                "extracted_icp_type": "jsonb"
            }
        }
    },
    {
        "id": "J1.14.5",
        "part_a": "Verify `handle_new_user` trigger exists",
        "part_b": "Query pg_triggers",
        "key_files": [],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT tgname, tgenabled, pg_get_triggerdef(oid) as definition
                FROM pg_trigger
                WHERE tgname = 'on_auth_user_created';
            """,
            "expect": {
                "trigger_exists": True,
                "tgenabled": "O"
            },
            "note": "tgenabled='O' means trigger is enabled for all modes"
        }
    },
    {
        "id": "J1.14.6",
        "part_a": "Verify `get_onboarding_status` function exists",
        "part_b": "Call RPC",
        "key_files": [],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{supabase_url}/rest/v1/rpc/get_onboarding_status",
            "headers": {
                "apikey": "{anon_key}",
                "Authorization": "Bearer {user_jwt}"
            },
            "body": {},
            "expect": {
                "status": 200,
                "body_has_field": "needs_onboarding"
            },
            "curl_command": """curl -X POST '{supabase_url}/rest/v1/rpc/get_onboarding_status' \\
  -H 'apikey: {anon_key}' \\
  -H 'Authorization: Bearer {user_jwt}' \\
  -H 'Content-Type: application/json' \\
  -d '{}'"""
        }
    }
]

PASS_CRITERIA = [
    "All tables exist with required columns",
    "Column types correct (uuid, text[], jsonb)",
    "Trigger exists and enabled",
    "RPC function callable"
]

KEY_FILES = []

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Note: {LIVE_CONFIG['note']}")
    lines.append("")
    lines.append("### Expected Schema")
    for table, columns in EXPECTED_SCHEMA.items():
        lines.append(f"  {table}: {', '.join(columns[:5])}...")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("expect", {}).get("columns_exist"):
            cols = lt["expect"]["columns_exist"]
            lines.append(f"  Expected columns: {', '.join(cols[:4])}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
