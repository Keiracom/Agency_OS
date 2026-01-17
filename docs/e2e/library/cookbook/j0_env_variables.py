"""
Skill: J0.2 — Environment Variables Audit
Journey: J0 - Infrastructure & Wiring Audit
Checks: 7

Purpose: Every required env var exists in Railway AND has valid format.
"""

CHECKS = [
    {
        "id": "J0.2.1",
        "part_a": "Read config/.env.example — list ALL required vars",
        "part_b": "Use `railway variables --service agency-os --kv` to verify",
        "key_files": ["config/.env.example"]
    },
    {
        "id": "J0.2.2",
        "part_a": "Read src/config/settings.py — check which vars have defaults",
        "part_b": "Identify vars that will crash if missing",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J0.2.3",
        "part_a": "Verify DATABASE_URL uses port 6543 (Transaction Pooler)",
        "part_b": "Query database, check no 'prepared statement' errors",
        "key_files": []
    },
    {
        "id": "J0.2.4",
        "part_a": "Verify DATABASE_URL_MIGRATIONS uses port 5432",
        "part_b": "N/A (migrations run separately)",
        "key_files": []
    },
    {
        "id": "J0.2.5",
        "part_a": "Verify PREFECT_API_URL points to Railway service, not Prefect Cloud",
        "part_b": "Check worker logs for connection URL",
        "key_files": []
    },
    {
        "id": "J0.2.6",
        "part_a": "Verify SENTRY_DSN is set",
        "part_b": "Trigger test error, verify appears in Sentry",
        "key_files": []
    },
    {
        "id": "J0.2.7",
        "part_a": "Verify TEST_MODE=false in production",
        "part_b": "Confirm via settings endpoint or logs",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "All required vars present in Railway",
    "DATABASE_URL uses port 6543",
    "PREFECT_API_URL is self-hosted URL",
    "No Prefect Cloud references"
]

KEY_FILES = [
    "config/.env.example",
    "src/config/settings.py"
]

# Critical Variables Reference
CRITICAL_VARIABLES = {
    "DATABASE_URL": {"required": True, "format": "Must contain `:6543/`"},
    "DATABASE_URL_MIGRATIONS": {"required": True, "format": "Must contain `:5432/`"},
    "SUPABASE_URL": {"required": True, "format": "Must be `https://*.supabase.co`"},
    "SUPABASE_KEY": {"required": True, "format": "Must start with `eyJ` (JWT)"},
    "SUPABASE_SERVICE_KEY": {"required": True, "format": "Must start with `eyJ` (JWT)"},
    "REDIS_URL": {"required": True, "format": "Must be `redis://` or `rediss://`"},
    "PREFECT_API_URL": {"required": True, "format": "Must NOT contain `api.prefect.cloud`"},
    "ANTHROPIC_API_KEY": {"required": True, "format": "Must start with `sk-ant-`"},
    "SENTRY_DSN": {"required": True, "format": "Must be `https://*.ingest.sentry.io`"},
}

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
