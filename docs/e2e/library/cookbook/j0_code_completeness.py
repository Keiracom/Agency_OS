"""
Skill: J0.6 — Code Completeness Scan
Journey: J0 - Infrastructure & Wiring Audit
Checks: 8

Purpose: Find incomplete implementations that would cause runtime failures.
"""

CHECKS = [
    {
        "id": "J0.6.1",
        "part_a": "Search for `TODO` in src/",
        "part_b": "List and categorize by severity",
        "key_files": ["src/"]
    },
    {
        "id": "J0.6.2",
        "part_a": "Search for `FIXME` in src/",
        "part_b": "List and categorize by severity",
        "key_files": ["src/"]
    },
    {
        "id": "J0.6.3",
        "part_a": "Search for `pass` statements (empty functions)",
        "part_b": "Verify none in critical paths",
        "key_files": ["src/"]
    },
    {
        "id": "J0.6.4",
        "part_a": "Search for `NotImplementedError`",
        "part_b": "Verify none in production code",
        "key_files": ["src/"]
    },
    {
        "id": "J0.6.5",
        "part_a": "Search for `raise Exception` (generic)",
        "part_b": "Should use custom exceptions",
        "key_files": ["src/"]
    },
    {
        "id": "J0.6.6",
        "part_a": "Search for `# type: ignore`",
        "part_b": "Review each for valid reason",
        "key_files": ["src/"]
    },
    {
        "id": "J0.6.7",
        "part_a": "Search for hardcoded URLs/IPs",
        "part_b": "Should use env vars",
        "key_files": ["src/"]
    },
    {
        "id": "J0.6.8",
        "part_a": "Search for `print()` statements",
        "part_b": "Should use logging",
        "key_files": ["src/"]
    }
]

PASS_CRITERIA = [
    "No critical TODOs blocking user flows",
    "No empty `pass` in API routes or engines",
    "No `NotImplementedError` in production code",
    "No hardcoded localhost URLs"
]

KEY_FILES = [
    "src/"
]

# Severity Classification
SEVERITY_RULES = {
    "TODO in engine": "Critical - Must fix before E2E",
    "TODO in test": "Low - Note for later",
    "pass in API route": "Critical - Will cause 500 error",
    "pass in utility": "Medium - May cause silent failure",
    "NotImplementedError": "Critical - Will crash at runtime",
    "Hardcoded localhost": "Critical - Won't work in production",
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
