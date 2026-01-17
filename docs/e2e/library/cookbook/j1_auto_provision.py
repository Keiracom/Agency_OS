"""
Skill: J1.3 — Auto-Provisioning Trigger
Journey: J1 - Signup & Onboarding
Checks: 5

Purpose: Verify database trigger creates client + membership on user signup.
"""

CHECKS = [
    {
        "id": "J1.3.1",
        "part_a": "Read `supabase/migrations/016_auto_provision_client.sql` — verify trigger exists",
        "part_b": "N/A",
        "key_files": ["supabase/migrations/016_auto_provision_client.sql"]
    },
    {
        "id": "J1.3.2",
        "part_a": "Verify `handle_new_user()` creates user in `users` table",
        "part_b": "After signup, query users table",
        "key_files": ["supabase/migrations/016_auto_provision_client.sql"]
    },
    {
        "id": "J1.3.3",
        "part_a": "Verify function creates client with tier='ignition', subscription_status='trialing', credits=1250",
        "part_b": "Query clients table for new record",
        "key_files": ["supabase/migrations/016_auto_provision_client.sql"]
    },
    {
        "id": "J1.3.4",
        "part_a": "Verify function creates membership with role='owner', accepted_at=NOW()",
        "part_b": "Query memberships table",
        "key_files": ["supabase/migrations/016_auto_provision_client.sql"]
    },
    {
        "id": "J1.3.5",
        "part_a": "Verify trigger is `AFTER INSERT ON auth.users`",
        "part_b": "Check trigger exists in database",
        "key_files": ["supabase/migrations/016_auto_provision_client.sql"]
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

# Verification Query
VERIFICATION_SQL = """
-- After signup, verify all 3 records exist
SELECT u.id, u.email, c.name, c.tier, c.subscription_status, m.role
FROM users u
JOIN memberships m ON m.user_id = u.id
JOIN clients c ON c.id = m.client_id
WHERE u.email = 'test@example.com';
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
