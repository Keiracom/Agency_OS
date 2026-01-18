"""
Skill: J1.3 — Auto-Provisioning Trigger
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify database trigger creates client + membership on user signup.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "frontend_url": "https://agency-os-liart.vercel.app",
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "db_connection": "postgresql://postgres.jatzvazlbusedwsnqxzr:{{DB_PASSWORD}}@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J1.3.1",
        "part_a": "Read `supabase/migrations/016_auto_provision_client.sql` — verify trigger exists",
        "part_b": "N/A (code verification only)",
        "key_files": ["supabase/migrations/016_auto_provision_client.sql"],
        "live_test": {
            "type": "code_verify",
            "check": "Trigger function handle_new_user() exists in migration file",
            "expect": {
                "file_contains": ["CREATE OR REPLACE FUNCTION", "handle_new_user", "TRIGGER"]
            }
        }
    },
    {
        "id": "J1.3.2",
        "part_a": "Verify `handle_new_user()` creates user in `users` table",
        "part_b": "After signup, query users table",
        "key_files": ["supabase/migrations/016_auto_provision_client.sql"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, email, full_name FROM users WHERE email = '{test_email}'",
            "expect": {
                "row_count": 1,
                "fields": ["id", "email", "full_name"]
            }
        }
    },
    {
        "id": "J1.3.3",
        "part_a": "Verify function creates client with tier='ignition', subscription_status='trialing', credits=1250",
        "part_b": "Query clients table for new record",
        "key_files": ["supabase/migrations/016_auto_provision_client.sql"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT c.id, c.name, c.tier, c.subscription_status, c.credits
                FROM clients c
                JOIN memberships m ON m.client_id = c.id
                JOIN users u ON u.id = m.user_id
                WHERE u.email = '{test_email}'
            """,
            "expect": {
                "row_count": 1,
                "values": {
                    "tier": "ignition",
                    "subscription_status": "trialing",
                    "credits": 1250
                }
            }
        }
    },
    {
        "id": "J1.3.4",
        "part_a": "Verify function creates membership with role='owner', accepted_at=NOW()",
        "part_b": "Query memberships table",
        "key_files": ["supabase/migrations/016_auto_provision_client.sql"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT m.role, m.accepted_at
                FROM memberships m
                JOIN users u ON u.id = m.user_id
                WHERE u.email = '{test_email}'
            """,
            "expect": {
                "row_count": 1,
                "values": {
                    "role": "owner"
                },
                "not_null": ["accepted_at"]
            }
        }
    },
    {
        "id": "J1.3.5",
        "part_a": "Verify trigger is `AFTER INSERT ON auth.users`",
        "part_b": "Check trigger exists in database",
        "key_files": ["supabase/migrations/016_auto_provision_client.sql"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT tgname, tgenabled
                FROM pg_trigger
                WHERE tgname = 'on_auth_user_created'
            """,
            "expect": {
                "row_count": 1,
                "values": {
                    "tgenabled": "O"  # Origin-enabled
                }
            }
        }
    }
]

PASS_CRITERIA = [
    "User record created in users table",
    "Client record created with tier=ignition",
    "Membership created with role=owner",
    "All 3 records linked correctly"
]

KEY_FILES = [
    "supabase/migrations/016_auto_provision_client.sql"
]

# =============================================================================
# VERIFICATION QUERIES
# =============================================================================

VERIFICATION_SQL = """
-- After signup, verify all 3 records exist and are linked
SELECT
    u.id as user_id,
    u.email,
    c.id as client_id,
    c.name as client_name,
    c.tier,
    c.subscription_status,
    c.credits,
    m.role,
    m.accepted_at
FROM users u
JOIN memberships m ON m.user_id = u.id
JOIN clients c ON c.id = m.client_id
WHERE u.email = '{test_email}';
"""

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append("")
    lines.append("### Verification Query")
    lines.append("```sql")
    lines.append(VERIFICATION_SQL.strip())
    lines.append("```")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lt = check.get("live_test", {})
        if lt.get("type") == "db_query":
            lines.append(f"  Query: {lt.get('query', '').strip()[:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
