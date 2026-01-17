"""
Skill: J0.1 — Railway Services Health
Journey: J0 - Infrastructure & Wiring Audit
Checks: 6

Purpose: Verify all 3 Railway services are deployed and responding.
"""

CHECKS = [
    {
        "id": "J0.1.1",
        "part_a": "Read Dockerfile — verify entry point is `uvicorn src.api.main:app`",
        "part_b": "Call https://agency-os-production.up.railway.app/api/v1/health",
        "key_files": ["Dockerfile"]
    },
    {
        "id": "J0.1.2",
        "part_a": "Read Dockerfile.prefect — verify start script exists",
        "part_b": "Call https://prefect-server-production-f9b1.up.railway.app/api/health",
        "key_files": ["Dockerfile.prefect"]
    },
    {
        "id": "J0.1.3",
        "part_a": "Read Dockerfile.worker — verify PYTHONPATH=/app",
        "part_b": "Check Prefect UI for active worker",
        "key_files": ["Dockerfile.worker"]
    },
    {
        "id": "J0.1.4",
        "part_a": "Read docker-compose.yml — verify 3-service architecture",
        "part_b": "N/A (Railway deployment)",
        "key_files": ["docker-compose.yml"]
    },
    {
        "id": "J0.1.5",
        "part_a": "Check scripts/start-prefect-server.sh uses Railway PORT",
        "part_b": "Verify Prefect UI accessible",
        "key_files": ["scripts/start-prefect-server.sh"]
    },
    {
        "id": "J0.1.6",
        "part_a": "Check scripts/start-prefect-worker.sh waits for server health",
        "part_b": "Check worker logs for 'Started worker'",
        "key_files": ["scripts/start-prefect-worker.sh"]
    }
]

PASS_CRITERIA = [
    "API returns `{\"status\": \"healthy\"}` with HTTP 200",
    "Prefect returns healthy status",
    "Worker shows as online in Prefect UI"
]

KEY_FILES = [
    "Dockerfile",
    "Dockerfile.prefect",
    "Dockerfile.worker",
    "docker-compose.yml",
    "scripts/start-prefect-server.sh",
    "scripts/start-prefect-worker.sh"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
