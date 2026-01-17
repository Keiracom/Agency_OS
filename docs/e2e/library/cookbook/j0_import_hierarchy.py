"""
Skill: J0.7 — Import Hierarchy Verification
Journey: J0 - Infrastructure & Wiring Audit
Checks: 6

Purpose: Ensure no circular imports or layer violations.
"""

CHECKS = [
    {
        "id": "J0.7.1",
        "part_a": "Verify models/ only imports from exceptions",
        "part_b": "Grep imports in src/models/",
        "key_files": ["src/models/"]
    },
    {
        "id": "J0.7.2",
        "part_a": "Verify integrations/ only imports from models",
        "part_b": "Grep imports in src/integrations/",
        "key_files": ["src/integrations/"]
    },
    {
        "id": "J0.7.3",
        "part_a": "Verify engines/ only imports from models, integrations",
        "part_b": "Grep imports in src/engines/",
        "key_files": ["src/engines/"]
    },
    {
        "id": "J0.7.4",
        "part_a": "Verify orchestration/ can import all layers",
        "part_b": "Grep imports in src/orchestration/",
        "key_files": ["src/orchestration/"]
    },
    {
        "id": "J0.7.5",
        "part_a": "Check for engine-to-engine imports (forbidden)",
        "part_b": "Should pass data via orchestration",
        "key_files": ["src/engines/"]
    },
    {
        "id": "J0.7.6",
        "part_a": "Run `python -c \"import src.api.main\"`",
        "part_b": "No ImportError",
        "key_files": ["src/api/main.py"]
    }
]

PASS_CRITERIA = [
    "No engine-to-engine imports",
    "No integration-to-engine imports",
    "API starts without ImportError",
    "All flows import without error"
]

KEY_FILES = [
    "src/models/",
    "src/integrations/",
    "src/engines/",
    "src/orchestration/",
    "src/api/main.py"
]

# Import Hierarchy Reference (Enforced)
IMPORT_HIERARCHY = """
Layer 4: src/orchestration/  → Can import ALL below
Layer 3: src/engines/        → models, integrations ONLY
Layer 2: src/integrations/   → models ONLY
Layer 1: src/models/         → exceptions ONLY
"""

# Common Violations
COMMON_VIOLATIONS = [
    "Engine importing another engine",
    "Integration importing engine",
    "Model importing integration",
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
    lines.append("")
    lines.append("### Import Hierarchy")
    lines.append(IMPORT_HIERARCHY)
    return "\n".join(lines)
