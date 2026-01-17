"""
Fixer Agent Skill for Agency OS

The Fixer Agent repairs code violations found by QA. It does NOT create new files
(Builder's job) and does NOT fix MISSING/INCOMPLETE issues.

Version: 2.0
Author: CTO (Claude)
Created: December 24, 2025

Key Responsibilities:
- Fix CRITICAL and HIGH violations only
- Skip MISSING/INCOMPLETE (route to Builder)
- Document all fixes with marker comments
- Escalate when architectural changes needed
"""

from typing import Dict, List


def get_instructions() -> str:
    """Return the key instructions for the Fixer agent."""
    return """
FIXER AGENT INSTRUCTIONS
========================

1. ISSUE ROUTING:
   MISSING     -> Skip (BUILDER_REQ) - Builder creates files
   INCOMPLETE  -> Skip (BUILDER_REQ) - Builder completes stubs
   CRITICAL    -> Fix immediately    - Architecture violations
   HIGH        -> Fix immediately    - Standards violations
   MEDIUM      -> Skip               - Low priority
   LOW         -> Skip               - Style only
   STILL_BROKEN -> Re-fix            - Previous attempt failed

2. FIX PATTERNS (Always add marker comment):
   - Import hierarchy violation -> Remove cross-engine import
   - Missing contract comment -> Add FILE/TASK/PHASE/PURPOSE header
   - Hardcoded secret -> Move to environment config
   - Hard delete -> Convert to soft delete (deleted_at)
   - Session instantiation -> Convert to dependency injection
   - Wrong database port -> Change 5432 to 6543
   - Wrong pool settings -> pool_size=5, max_overflow=10
   - TypeScript 'any' type -> Define proper interface
   - Missing error handling -> Add try/catch with proper handling

3. MARKER COMMENT STANDARD:
   Python:  # FIXED by fixer-agent: [description] (Rule [N])
   TypeScript: // FIXED by fixer-agent: [description]

4. ESCALATION CRITERIA (Don't fix, escalate instead):
   - Architectural change needed (multiple files must change)
   - Unclear intent (don't know correct behavior)
   - Circular dependency (multiple valid solutions)
   - External change needed (API key, config, database)
   - Repeated failure (same issue failed 3+ times)

5. NEVER DO:
   - Create new files
   - Fix MISSING/INCOMPLETE
   - Fix MEDIUM/LOW
   - Refactor working code
   - Skip documentation
   - Guess at fixes
"""


def get_code_templates() -> Dict[str, str]:
    """Return code templates for the Fixer agent."""
    return {
        "fix_log_template": FIX_LOG_TEMPLATE,
        "import_hierarchy_fix": IMPORT_HIERARCHY_FIX,
        "contract_comment_fix": CONTRACT_COMMENT_FIX,
        "hardcoded_secret_fix": HARDCODED_SECRET_FIX,
        "hard_delete_fix": HARD_DELETE_FIX,
        "session_instantiation_fix": SESSION_INSTANTIATION_FIX,
        "typescript_any_fix": TYPESCRIPT_ANY_FIX,
        "error_handling_fix": ERROR_HANDLING_FIX,
    }


def get_fix_patterns() -> List[Dict[str, str]]:
    """Return all fix patterns with before/after examples."""
    return [
        {
            "name": "Import Hierarchy Violation",
            "severity": "CRITICAL",
            "detection": "Engine importing from another engine",
            "before": "from src.engines.scorer import calculate_als_score",
            "after": "# FIXED by fixer-agent: removed cross-engine import (Rule 12)\n# Data now passed from orchestration layer via method argument",
        },
        {
            "name": "Missing Contract Comment",
            "severity": "HIGH",
            "detection": "Python file without FILE: header in first 10 lines",
            "before": "from sqlalchemy import Column, String",
            "after": '# FIXED by fixer-agent: added contract comment\n"""\nFILE: src/models/lead.py\nTASK: MOD-006\nPHASE: 2\nPURPOSE: Lead model with ALS scoring fields\n"""\nfrom sqlalchemy import Column, String',
        },
        {
            "name": "Hardcoded Secret",
            "severity": "CRITICAL",
            "detection": "API key, password, or secret in code",
            "before": 'api_key = "sk-abc123xyz789"',
            "after": "# FIXED by fixer-agent: moved secrets to environment config\nfrom src.config.settings import settings\n\napi_key = settings.ANTHROPIC_API_KEY",
        },
        {
            "name": "Hard Delete",
            "severity": "CRITICAL",
            "detection": "Using .delete() or DELETE FROM",
            "before": "await db.delete(lead)\nawait db.commit()",
            "after": "# FIXED by fixer-agent: converted to soft delete (Rule 14)\nfrom datetime import datetime\n\nlead.deleted_at = datetime.utcnow()\nawait db.commit()",
        },
        {
            "name": "Session Instantiation in Engine",
            "severity": "CRITICAL",
            "detection": "Engine creating its own database session",
            "before": "async with AsyncSessionLocal() as db:",
            "after": "# FIXED by fixer-agent: dependency injection (Rule 11)\nasync def enrich(self, db: AsyncSession, lead_id: str):",
        },
        {
            "name": "Wrong Database Port",
            "severity": "CRITICAL",
            "detection": "Using port 5432 instead of 6543",
            "before": 'DATABASE_URL = "postgresql://user:pass@db.supabase.co:5432/postgres"',
            "after": '# FIXED by fixer-agent: use transaction pooler port 6543\nDATABASE_URL = "postgresql://user:pass@db.supabase.co:6543/postgres"',
        },
        {
            "name": "TypeScript Any Type",
            "severity": "HIGH",
            "detection": ": any or <any> in TypeScript",
            "before": "const [data, setData] = useState<any[]>([]);",
            "after": "// FIXED by fixer-agent: added proper types\ninterface DataItem {\n  id: string;\n  name: string;\n}\nconst [data, setData] = useState<DataItem[]>([]);",
        },
    ]


def get_escalation_criteria() -> List[str]:
    """Return criteria for when to escalate instead of fix."""
    return [
        "Architectural change needed - Multiple files must change",
        "Unclear intent - Don't know what correct behavior is",
        "Circular dependency - Multiple valid solutions",
        "External change needed - API key, config, database",
        "Repeated failure - Same issue failed 3+ times",
    ]


def generate_fix_marker(description: str, rule_number: int = None) -> str:
    """
    Generate a standard fix marker comment.

    Args:
        description: What was fixed
        rule_number: Optional rule number reference

    Returns:
        Formatted marker comment
    """
    if rule_number:
        return f"# FIXED by fixer-agent: {description} (Rule {rule_number})"
    return f"# FIXED by fixer-agent: {description}"


def generate_ts_fix_marker(description: str) -> str:
    """Generate a TypeScript fix marker comment."""
    return f"// FIXED by fixer-agent: {description}"


# =============================================================================
# CODE TEMPLATES
# =============================================================================

FIX_LOG_TEMPLATE = """
# FIXER AGENT LOG

**Log ID:** FIX-YYYYMMDD-HHMM
**Timestamp:** [ISO 8601]
**QA Report:** qa_reports/report_YYYYMMDD_HHMM.md

---

## CONTEXT

**Phase:** [X]
**Skill:** [path]

---

## FIXES APPLIED

### Fix #1: CRIT-001

- **File:** [path]
- **Line:** [N]
- **Issue:** [description]
- **Rule:** Rule [N]

**Before:**
```python
[code]
```

**After:**
```python
[code]
```

**Verification:** Line [N] should [check]

---

## BUILDER_REQUIRED

| Issue | Type | File |
|-------|------|------|
| MISS-001 | MISSING | [path] |

---

## SKIPPED

| Issue | Severity | Reason |
|-------|----------|--------|
| MED-001 | MEDIUM | Policy |

---

## ESCALATED

| Issue | File | Reason |
|-------|------|--------|
| CRIT-003 | [path] | [why needs human] |

---

## SUMMARY

| Action | Count |
|--------|-------|
| Fixed | X |
| Builder Req | X |
| Skipped | X |
| Escalated | X |
"""

IMPORT_HIERARCHY_FIX = """
# BEFORE
from src.engines.scorer import calculate_als_score

# AFTER
# FIXED by fixer-agent: removed cross-engine import (Rule 12)
# Data now passed from orchestration layer via method argument
"""

CONTRACT_COMMENT_FIX = '''
# BEFORE
from sqlalchemy import Column, String
from pydantic import BaseModel

class Lead(Base):
    ...

# AFTER
# FIXED by fixer-agent: added contract comment
"""
FILE: src/models/lead.py
TASK: MOD-006
PHASE: 2
PURPOSE: Lead model with ALS scoring fields

DEPENDENCIES:
- src/models/base

EXPORTS:
- Lead, LeadCreate, LeadResponse
"""
from sqlalchemy import Column, String
from pydantic import BaseModel

class Lead(Base):
    ...
'''

HARDCODED_SECRET_FIX = """
# BEFORE
api_key = "sk-abc123xyz789"
password = "super_secret"

# AFTER
# FIXED by fixer-agent: moved secrets to environment config
from src.config.settings import settings

api_key = settings.ANTHROPIC_API_KEY
password = settings.DATABASE_PASSWORD
"""

HARD_DELETE_FIX = """
# BEFORE
await db.delete(lead)
await db.commit()

# AFTER
# FIXED by fixer-agent: converted to soft delete (Rule 14)
from datetime import datetime

lead.deleted_at = datetime.utcnow()
await db.commit()
"""

SESSION_INSTANTIATION_FIX = """
# BEFORE
class ScoutEngine:
    async def enrich(self, lead_id: str):
        async with AsyncSessionLocal() as db:
            lead = await db.get(Lead, lead_id)
            ...

# AFTER
# FIXED by fixer-agent: dependency injection (Rule 11)
class ScoutEngine:
    async def enrich(self, db: AsyncSession, lead_id: str):
        lead = await db.get(Lead, lead_id)
        ...
"""

TYPESCRIPT_ANY_FIX = """
// BEFORE
const [data, setData] = useState<any[]>([]);
const handleClick = (item: any) => { ... };

// AFTER
// FIXED by fixer-agent: added proper types
interface DataItem {
  id: string;
  name: string;
  status: string;
}

const [data, setData] = useState<DataItem[]>([]);
const handleClick = (item: DataItem) => { ... };
"""

ERROR_HANDLING_FIX = """
// BEFORE
useEffect(() => {
  fetch('/api/data')
    .then(res => res.json())
    .then(data => setData(data));
}, []);

// AFTER
// FIXED by fixer-agent: added error handling
useEffect(() => {
  async function fetchData() {
    try {
      const res = await fetch('/api/data');
      if (!res.ok) throw new Error('Failed to fetch');
      const data = await res.json();
      setData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }
  fetchData();
}, []);
"""


if __name__ == "__main__":
    print(get_instructions())
