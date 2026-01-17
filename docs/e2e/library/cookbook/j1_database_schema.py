"""
Skill: J1.14 — Database Schema Verification
Journey: J1 - Signup & Onboarding
Checks: 6

Purpose: Verify all required tables and columns exist.
"""

CHECKS = [
    {
        "id": "J1.14.1",
        "part_a": "Verify `users` table has: id, email, full_name",
        "part_b": "Query schema",
        "key_files": []
    },
    {
        "id": "J1.14.2",
        "part_a": "Verify `clients` table has all ICP columns",
        "part_b": "Query schema",
        "key_files": []
    },
    {
        "id": "J1.14.3",
        "part_a": "Verify `memberships` table has: user_id, client_id, role, accepted_at",
        "part_b": "Query schema",
        "key_files": []
    },
    {
        "id": "J1.14.4",
        "part_a": "Verify `icp_extraction_jobs` table exists",
        "part_b": "Query schema",
        "key_files": []
    },
    {
        "id": "J1.14.5",
        "part_a": "Verify `handle_new_user` trigger exists",
        "part_b": "Query pg_triggers",
        "key_files": []
    },
    {
        "id": "J1.14.6",
        "part_a": "Verify `get_onboarding_status` function exists",
        "part_b": "Call RPC",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "All tables exist",
    "All columns exist",
    "Trigger exists and active",
    "RPC callable"
]

KEY_FILES = []

# Schema Verification Queries
SCHEMA_QUERIES = """
-- Check users table
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'users';

-- Check trigger exists
SELECT tgname FROM pg_trigger WHERE tgname = 'on_auth_user_created';

-- Check RPC exists
SELECT proname FROM pg_proc WHERE proname = 'get_onboarding_status';
"""

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
