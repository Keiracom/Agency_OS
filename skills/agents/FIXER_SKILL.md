# SKILL.md — Fixer Agent

**Skill:** Fixer Agent for Agency OS  
**Author:** CTO (Claude)  
**Version:** 2.0  
**Created:** December 24, 2025

---

## Purpose

The Fixer Agent repairs code violations found by QA. It does NOT create new files (Builder's job) and does NOT fix MISSING/INCOMPLETE issues.

---

## Issue Routing

| QA Category | Your Action | Reason |
|-------------|-------------|--------|
| MISSING | Skip (BUILDER_REQ) | Builder creates files |
| INCOMPLETE | Skip (BUILDER_REQ) | Builder completes stubs |
| CRITICAL | Fix immediately | Architecture violations |
| HIGH | Fix immediately | Standards violations |
| MEDIUM | Skip | Low priority |
| LOW | Skip | Style only |
| STILL_BROKEN | Re-fix | Previous attempt failed |

---

## Fix Patterns

### Pattern 1: Import Hierarchy Violation (CRITICAL)

**Detection:** Engine importing from another engine

```python
# BEFORE
from src.engines.scorer import calculate_als_score

# AFTER
# FIXED by fixer-agent: removed cross-engine import (Rule 12)
# Data now passed from orchestration layer via method argument
```

**Note:** You cannot fully fix this — you remove the import, but Builder/orchestration must update the calling code.

---

### Pattern 2: Missing Contract Comment (HIGH)

**Detection:** Python file without FILE: header in first 10 lines

```python
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
```

---

### Pattern 3: Hardcoded Secret (CRITICAL)

**Detection:** API key, password, or secret in code

```python
# BEFORE
api_key = "sk-abc123xyz789"
password = "super_secret"

# AFTER
# FIXED by fixer-agent: moved secrets to environment config
from src.config.settings import settings

api_key = settings.ANTHROPIC_API_KEY
password = settings.DATABASE_PASSWORD
```

---

### Pattern 4: Hard Delete (CRITICAL)

**Detection:** Using .delete() or DELETE FROM

```python
# BEFORE
await db.delete(lead)
await db.commit()

# AFTER
# FIXED by fixer-agent: converted to soft delete (Rule 14)
from datetime import datetime

lead.deleted_at = datetime.utcnow()
await db.commit()
```

---

### Pattern 5: Session Instantiation in Engine (CRITICAL)

**Detection:** Engine creating its own database session

```python
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
```

---

### Pattern 6: Wrong Database Port (CRITICAL)

**Detection:** Using port 5432 instead of 6543

```python
# BEFORE
DATABASE_URL = "postgresql://user:pass@db.supabase.co:5432/postgres"

# AFTER
# FIXED by fixer-agent: use transaction pooler port 6543
DATABASE_URL = "postgresql://user:pass@db.supabase.co:6543/postgres"
```

---

### Pattern 7: Wrong Pool Settings (CRITICAL)

**Detection:** pool_size != 5 or max_overflow != 10

```python
# BEFORE
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30
)

# AFTER
# FIXED by fixer-agent: corrected pool settings (Rule 19)
engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10
)
```

---

### Pattern 8: TypeScript Any Type (HIGH)

**Detection:** `: any` or `<any>` in TypeScript

```typescript
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
```

---

### Pattern 9: Missing Error Handling (HIGH)

**Detection:** Fetch without try/catch

```typescript
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
```

---

### Pattern 10: Missing Export (HIGH)

**Detection:** Class/function defined but not exported in `__init__.py`

```python
# BEFORE - src/engines/__init__.py
from .scout import ScoutEngine
from .scorer import ScorerEngine

# AFTER - src/engines/__init__.py
# FIXED by fixer-agent: added missing export
from .scout import ScoutEngine
from .scorer import ScorerEngine
from .allocator import AllocatorEngine  # Added
```

---

### Pattern 11: Missing Soft Delete in Query (HIGH)

**Detection:** SELECT without deleted_at check

```python
# BEFORE
query = select(Lead).where(Lead.client_id == client_id)

# AFTER
# FIXED by fixer-agent: added soft delete filter (Rule 14)
query = select(Lead).where(
    Lead.client_id == client_id,
    Lead.deleted_at.is_(None)
)
```

---

### Pattern 12: Missing Admin Auth (CRITICAL - Admin routes only)

**Detection:** Admin route without require_platform_admin

```python
# BEFORE
@router.get("/admin/clients")
async def get_clients(
    db: AsyncSession = Depends(get_db)
):
    ...

# AFTER
# FIXED by fixer-agent: added admin auth protection
@router.get("/admin/clients")
async def get_clients(
    admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db)
):
    ...
```

---

## Fix Log Template

```markdown
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
```

---

## Escalation Criteria

Escalate when:

1. **Architectural change needed** — Multiple files must change
2. **Unclear intent** — Don't know what correct behavior is
3. **Circular dependency** — Multiple valid solutions
4. **External change needed** — API key, config, database
5. **Repeated failure** — Same issue failed 3+ times

---

## Never Do

- ❌ Create new files
- ❌ Fix MISSING/INCOMPLETE
- ❌ Fix MEDIUM/LOW
- ❌ Refactor working code
- ❌ Skip documentation
- ❌ Guess at fixes

---

## Marker Comment Standard

Always add this exact format:

```python
# FIXED by fixer-agent: [description] (Rule [N])
```

```typescript
// FIXED by fixer-agent: [description]
```

QA looks for these markers to verify.

---
