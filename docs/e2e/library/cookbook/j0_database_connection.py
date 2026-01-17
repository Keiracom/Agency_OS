"""
Skill: J0.4 — Database Connection Verification
Journey: J0 - Infrastructure & Wiring Audit
Checks: 6

Purpose: Verify correct pooler port and connection settings.
"""

CHECKS = [
    {
        "id": "J0.4.1",
        "part_a": "Read src/integrations/supabase.py — verify pool settings",
        "part_b": "N/A",
        "key_files": ["src/integrations/supabase.py"]
    },
    {
        "id": "J0.4.2",
        "part_a": "Verify pool_size=5, max_overflow=10",
        "part_b": "Check active connections in Supabase dashboard",
        "key_files": ["src/integrations/supabase.py"]
    },
    {
        "id": "J0.4.3",
        "part_a": "Verify statement_cache_size=0 (Supavisor compatibility)",
        "part_b": "Execute query, no 'prepared statement' errors",
        "key_files": ["src/integrations/supabase.py"]
    },
    {
        "id": "J0.4.4",
        "part_a": "Verify expire_on_commit=False",
        "part_b": "N/A",
        "key_files": ["src/integrations/supabase.py"]
    },
    {
        "id": "J0.4.5",
        "part_a": "Read get_db_session() — verify commit/rollback/close",
        "part_b": "N/A",
        "key_files": ["src/integrations/supabase.py"]
    },
    {
        "id": "J0.4.6",
        "part_a": "Test database query via health endpoint",
        "part_b": "Call /api/v1/health/ready, check database latency",
        "key_files": ["src/api/routes/health.py"]
    }
]

PASS_CRITERIA = [
    "Connection uses port 6543",
    "Statement caching disabled",
    "Health check returns database healthy",
    "No connection pool exhaustion errors"
]

KEY_FILES = [
    "src/integrations/supabase.py",
    "src/api/routes/health.py"
]

# Expected Configuration
EXPECTED_CONFIG = {
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 1800,
    "pool_pre_ping": True,
    "statement_cache_size": 0,  # CRITICAL for Supavisor
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
