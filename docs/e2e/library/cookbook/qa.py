"""
QA Agent Skill for Agency OS

The QA Agent scans code for issues and routes them to the correct handler:
- MISSING/INCOMPLETE -> Builder (creates files)
- VIOLATION -> Fixer (fixes code)

Version: 2.0
Author: CTO (Claude)
Created: December 24, 2025

Key Responsibilities:
- Scan code every 90 seconds
- Categorize issues by severity
- Route to correct handler (Builder or Fixer)
- Verify fixes from previous cycles
"""

from typing import Dict, List


def get_instructions() -> str:
    """Return the key instructions for the QA agent."""
    return """
QA AGENT INSTRUCTIONS
=====================

1. DYNAMIC CONTEXT DETECTION (Every cycle):
   - Read PROGRESS.md to find current phase and tasks
   - Read skills/SKILL_INDEX.md to find skill file
   - Read the skill file to get required files and patterns

2. ISSUE CATEGORIES:
   MISSING     -> Builder (builder_tasks/pending.md)  - File doesn't exist
   INCOMPLETE  -> Builder (builder_tasks/pending.md)  - File has stubs
   CRITICAL    -> Fixer (qa_reports/report_*.md)      - Architecture violation
   HIGH        -> Fixer (qa_reports/report_*.md)      - Standards violation
   MEDIUM      -> Fixer (qa_reports/report_*.md)      - Quality issue
   LOW         -> Fixer (qa_reports/report_*.md)      - Style issue

3. CRITICAL CHECKS (Always run):
   - Import hierarchy violations (Rule 12)
   - Hardcoded secrets
   - Wrong database port (should be 6543)
   - Hard deletes
   - Session instantiation in engines

4. HIGH CHECKS:
   - Missing contract comments
   - Wrong pool settings
   - TypeScript 'any' types
   - Missing soft delete filters

5. TIMING:
   - Cycle: 90 seconds
   - Priority: MISSING -> CRITICAL -> HIGH -> Verification -> MEDIUM

6. NEVER DO:
   - Modify source code
   - Modify fixer_reports/
   - Create files (only report missing)
   - Report same issue twice in same report
   - Skip context detection
"""


def get_code_templates() -> Dict[str, str]:
    """Return code templates for the QA agent."""
    return {
        "report_template": REPORT_TEMPLATE,
        "builder_tasks_template": BUILDER_TASKS_TEMPLATE,
        "critical_checks": CRITICAL_CHECKS,
        "high_checks": HIGH_CHECKS,
        "medium_checks": MEDIUM_CHECKS,
    }


def get_issue_categories() -> Dict[str, Dict[str, str]]:
    """Return issue category configuration."""
    return {
        "MISSING": {
            "handler": "Builder",
            "written_to": "builder_tasks/pending.md",
            "trigger": "File doesn't exist",
        },
        "INCOMPLETE": {
            "handler": "Builder",
            "written_to": "builder_tasks/pending.md",
            "trigger": "File has stubs/placeholders",
        },
        "CRITICAL": {
            "handler": "Fixer",
            "written_to": "qa_reports/report_*.md",
            "trigger": "Architecture violation",
        },
        "HIGH": {
            "handler": "Fixer",
            "written_to": "qa_reports/report_*.md",
            "trigger": "Standards violation",
        },
        "MEDIUM": {
            "handler": "Fixer",
            "written_to": "qa_reports/report_*.md",
            "trigger": "Quality issue",
        },
        "LOW": {
            "handler": "Fixer",
            "written_to": "qa_reports/report_*.md",
            "trigger": "Style issue",
        },
    }


def get_check_commands() -> Dict[str, List[str]]:
    """Return bash commands for each check category."""
    return {
        "critical_import_hierarchy": [
            'grep -rn "from src.engines" src/models/',
            'grep -rn "from src.orchestration" src/models/',
            'grep -rn "from src.orchestration" src/engines/',
            'grep -rn "from src.engines\\." src/engines/',
        ],
        "critical_hardcoded_secrets": [
            'grep -rn "api_key\\s*=\\s*[\'\\"][^\'\\"]*[\'\\"]" src/',
            'grep -rn "password\\s*=\\s*[\'\\"][^\'\\"]*[\'\\"]" src/',
            'grep -rn "sk-[a-zA-Z0-9]" src/',
            'grep -rn "secret\\s*=\\s*[\'\\"][^\'\\"]*[\'\\"]" src/',
        ],
        "critical_database": [
            'grep -rn ":5432" src/',
            'grep -rn "port.*5432" src/',
        ],
        "critical_hard_delete": [
            'grep -rn "\\.delete\\(" src/',
            'grep -rn "DELETE FROM" src/',
        ],
        "critical_session": [
            'grep -rn "AsyncSessionLocal\\(\\)" src/engines/',
        ],
        "high_pool_settings": [
            'grep -rn "pool_size" src/ | grep -v "pool_size=5"',
            'grep -rn "max_overflow" src/ | grep -v "max_overflow=10"',
        ],
        "high_typescript_any": [
            'grep -rn ": any" frontend/app/',
            'grep -rn ": any" frontend/components/',
            'grep -rn "<any>" frontend/',
        ],
        "medium_todos": [
            'grep -rn "TODO" src/ frontend/',
            'grep -rn "FIXME" src/ frontend/',
        ],
        "medium_console_log": [
            'grep -rn "console\\.log" frontend/app/',
            'grep -rn "console\\.log" frontend/components/',
        ],
        "incomplete_stubs": [
            'grep -rn "^\\s*pass$" src/',
            'grep -rn "raise NotImplementedError" src/',
            'grep -rn "\\.\\.\\." src/',
        ],
    }


def categorize_issue(issue_type: str, severity: str) -> Dict[str, str]:
    """
    Categorize an issue and determine routing.

    Args:
        issue_type: Type of issue (MISSING, INCOMPLETE, VIOLATION)
        severity: Severity level (CRITICAL, HIGH, MEDIUM, LOW)

    Returns:
        Dictionary with handler and destination
    """
    if issue_type in ("MISSING", "INCOMPLETE"):
        return {
            "handler": "Builder",
            "destination": "builder_tasks/pending.md",
            "action": "Create/complete file",
        }
    elif severity in ("CRITICAL", "HIGH"):
        return {
            "handler": "Fixer",
            "destination": "qa_reports/report_*.md",
            "action": "Fix violation",
        }
    else:
        return {
            "handler": "(logged)",
            "destination": "qa_reports/report_*.md",
            "action": "Log for reference",
        }


# =============================================================================
# TEMPLATES
# =============================================================================

REPORT_TEMPLATE = """
# QA REPORT - Agency OS v3.0

**Report ID:** QA-YYYYMMDD-HHMM
**Timestamp:** [ISO 8601]
**Cycle:** [N]

---

## CONTEXT

**Current Phase:** [X] - [Name]
**Active Skill:** [path]
**Tasks In Progress:** [count]
**Tasks Complete:** [count]

---

## SUMMARY

| Category | Count | Handler |
|----------|-------|---------|
| MISSING | X | Builder |
| INCOMPLETE | X | Builder |
| CRITICAL | X | Fixer |
| HIGH | X | Fixer |
| MEDIUM | X | (logged) |

---

## BUILDER TASKS

*Written to: Agents/Builder Agent/builder_tasks/pending.md*

### Missing Files

| Task ID | File | Reason |
|---------|------|--------|
| [ID] | [path] | [why expected] |

### Incomplete Files

| Task ID | File | Line | Issue |
|---------|------|------|-------|
| [ID] | [path] | [N] | Contains `pass` |

---

## FIXER TASKS

### CRITICAL

#### CRIT-001: Import Hierarchy Violation

- **Location:** src/engines/scout.py:12
- **Rule:** Rule 12
- **Evidence:**
```
from src.engines.scorer import calculate_score
```
- **Fix:** Remove import, pass data from orchestration

### HIGH

#### HIGH-001: Missing Contract Comment

- **Location:** src/models/lead.py:1
- **Rule:** Code Standards
- **Evidence:** File starts with `from sqlalchemy...`
- **Fix:** Add contract comment header

---

## FIXER VERIFICATION

| Issue | File | Claimed Fix | Status |
|-------|------|-------------|--------|
| CRIT-001 | src/x.py | Removed import | VERIFIED / STILL_BROKEN |

---

## SKILL COMPLIANCE

**Skill:** [name]

| Requirement | Status |
|-------------|--------|
| [file/component] | OK / MISSING |

**Compliance:** X/Y (Z%)

---
"""

BUILDER_TASKS_TEMPLATE = """
# PENDING BUILDER TASKS

**Last Updated:** [timestamp]

---

## MISSING FILES

| Task ID | Required File | Reason | Skill |
|---------|---------------|--------|-------|
| ICP-011 | src/engines/icp_scraper.py | Task marked complete but file missing | skills/icp/ICP_SKILL.md |

## INCOMPLETE FILES

| Task ID | File | Issue | Line |
|---------|------|-------|------|
| ICP-003 | src/agents/skills/website_parser.py | Contains `pass` | 45 |

---

**Builder:** Create these files, then remove from this list.
"""

CRITICAL_CHECKS = """
# Import hierarchy violations (Rule 12)
grep -rn "from src.engines" src/models/
grep -rn "from src.orchestration" src/models/
grep -rn "from src.orchestration" src/engines/
grep -rn "from src.engines\\." src/engines/  # Cross-engine

# Hardcoded secrets
grep -rn "api_key\\s*=\\s*['\"][^'\"]*['\"]" src/
grep -rn "password\\s*=\\s*['\"][^'\"]*['\"]" src/
grep -rn "sk-[a-zA-Z0-9]" src/
grep -rn "secret\\s*=\\s*['\"][^'\"]*['\"]" src/

# Wrong database port (should be 6543)
grep -rn ":5432" src/
grep -rn "port.*5432" src/

# Hard deletes
grep -rn "\\.delete\\(" src/
grep -rn "DELETE FROM" src/

# Session instantiation in engines
grep -rn "AsyncSessionLocal\\(\\)" src/engines/
"""

HIGH_CHECKS = """
# Missing contract comments (check first 10 lines for docstring)
for f in $(find src -name "*.py" ! -name "__init__.py"); do
  if ! head -10 "$f" | grep -q "FILE:"; then
    echo "Missing contract: $f"
  fi
done

# Wrong pool settings
grep -rn "pool_size" src/ | grep -v "pool_size=5"
grep -rn "max_overflow" src/ | grep -v "max_overflow=10"

# TypeScript any types
grep -rn ": any" frontend/app/
grep -rn ": any" frontend/components/
grep -rn "<any>" frontend/

# Missing soft delete filters in queries
grep -rn "\\.select\\(" src/api/ | while read line; do
  file=$(echo "$line" | cut -d: -f1)
  if ! grep -q "deleted_at" "$file"; then
    echo "Missing soft delete check: $file"
  fi
done
"""

MEDIUM_CHECKS = """
# TODO/FIXME comments
grep -rn "TODO" src/ frontend/
grep -rn "FIXME" src/ frontend/

# Console.log in production
grep -rn "console\\.log" frontend/app/
grep -rn "console\\.log" frontend/components/

# Print statements in Python
grep -rn "^[^#]*print\\(" src/
"""


if __name__ == "__main__":
    print(get_instructions())
