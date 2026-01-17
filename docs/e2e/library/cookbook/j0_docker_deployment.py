"""
Skill: J0.8 — Docker & Deployment Verification
Journey: J0 - Infrastructure & Wiring Audit
Checks: 7

Purpose: Verify Docker builds and deployment config is correct.
"""

CHECKS = [
    {
        "id": "J0.8.1",
        "part_a": "Read Dockerfile — verify multi-stage build",
        "part_b": "Build locally: `docker build -t test .`",
        "key_files": ["Dockerfile"]
    },
    {
        "id": "J0.8.2",
        "part_a": "Verify non-root user (appuser)",
        "part_b": "Check container user in logs",
        "key_files": ["Dockerfile"]
    },
    {
        "id": "J0.8.3",
        "part_a": "Verify HEALTHCHECK command",
        "part_b": "Container health status",
        "key_files": ["Dockerfile"]
    },
    {
        "id": "J0.8.4",
        "part_a": "Read .github/workflows/ci.yml — verify jobs",
        "part_b": "Check GitHub Actions runs",
        "key_files": [".github/workflows/ci.yml"]
    },
    {
        "id": "J0.8.5",
        "part_a": "Verify Railway deploy step",
        "part_b": "Check Railway deployment logs",
        "key_files": [".github/workflows/ci.yml"]
    },
    {
        "id": "J0.8.6",
        "part_a": "Verify all requirements in requirements.txt",
        "part_b": "No ModuleNotFoundError at runtime",
        "key_files": ["requirements.txt"]
    },
    {
        "id": "J0.8.7",
        "part_a": "Check Camoufox stage (optional)",
        "part_b": "Only if Tier 3 scraping needed",
        "key_files": ["Dockerfile"]
    }
]

PASS_CRITERIA = [
    "Docker builds without errors",
    "CI pipeline passes",
    "Railway deployment succeeds",
    "No missing dependencies at runtime"
]

KEY_FILES = [
    "Dockerfile",
    "Dockerfile.prefect",
    "Dockerfile.worker",
    ".github/workflows/ci.yml",
    "requirements.txt"
]

# CI/CD Pipeline Jobs Reference
CI_JOBS = [
    {"name": "backend-lint", "tool": "Ruff", "purpose": "Code style", "blocking": True},
    {"name": "backend-typecheck", "tool": "MyPy", "purpose": "Type safety", "blocking": False},
    {"name": "backend-test", "tool": "Pytest", "purpose": "Tests", "blocking": False},
    {"name": "frontend-check", "tool": "ESLint + TSC", "purpose": "Lint + Types", "blocking": False},
    {"name": "deploy", "tool": "Railway CLI", "purpose": "Auto-deploy main", "blocking": True},
]

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
