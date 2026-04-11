"""
CI guard: reject hardcoded ETV ranges outside category_etv_windows.py.
Directive #328.1 — all ETV windows must come from the canonical config.
"""
import re
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
EXEMPT_FILES = {
    "src/config/category_etv_windows.py",  # canonical source
    "src/integrations/dataforseo.py",       # display buckets, not discovery
    "src/pipeline/stage_4_scoring.py",      # scoring thresholds, not discovery
    "src/clients/dfs_labs_client.py",       # paid_etv_min=0.0 is API param, not window
    "scripts/",                              # diagnostic scripts exempt
    "tests/",                                # tests exempt
    "research/",                             # research docs exempt
}

# Only flag the patterns that are specifically discovery ETV windows.
# paid_etv_min is a DFS API parameter, not a discovery window.
SUSPECT_PATTERNS = [
    r"\betv_min\b",
    r"\betv_max\b",
]

# None defaults are safe (they raise ValueError at runtime).
# Only numeric defaults are violations.
NONE_DEFAULT = re.compile(r"=\s*None\s*,?\s*$")


def _is_exempt(filepath: str) -> bool:
    for exempt in EXEMPT_FILES:
        if filepath.startswith(exempt):
            return True
    return False


def test_no_hardcoded_etv_windows():
    """Ensure no Python file outside exemptions has hardcoded narrow ETV range defaults."""
    violations = []
    src_dir = REPO_ROOT / "src"

    for py_file in src_dir.rglob("*.py"):
        rel_path = str(py_file.relative_to(REPO_ROOT))
        if _is_exempt(rel_path):
            continue

        content = py_file.read_text()
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            # Skip pure comments and docstrings
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            # Skip paid_etv_min / paid_etv_max (DFS API params, not discovery windows)
            if "paid_etv_min" in stripped or "paid_etv_max" in stripped:
                continue
            for pattern in SUSPECT_PATTERNS:
                if not re.search(pattern, stripped):
                    continue
                if "=" not in stripped:
                    continue
                # Must be a default parameter assignment with a numeric literal
                if not re.search(rf'{pattern}\s*(?::\s*float\s*)?=\s*\d', stripped):
                    continue
                # Skip None defaults (they raise ValueError at runtime — safe)
                if NONE_DEFAULT.search(stripped):
                    continue
                violations.append(f"{rel_path}:{i}: {stripped.strip()}")

    assert not violations, (
        "Hardcoded ETV ranges found outside category_etv_windows.py.\n"
        "Use get_etv_window() from src.config.category_etv_windows instead.\n"
        "Violations:\n" + "\n".join(f"  {v}" for v in violations)
    )
