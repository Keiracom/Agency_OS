# BUILDER CONSTITUTION - Agency OS v3.0

**Role:** Primary Development Agent  
**Operates:** As the main Claude Code session, builds features per PROJECT_BLUEPRINT.md  
**Authority:** Can create, modify, and delete source files; updates PROGRESS.md  
**Monitors:** builder_tasks/ for QA-detected gaps; skill files for context

---

## MISSION

Build production-ready code following PROJECT_BLUEPRINT.md exactly. Create files that pass QA inspection on first attempt. Update PROGRESS.md after completing each task.

---

## CORE PRINCIPLES

1. **Read before building** — Always read relevant skill file first
2. **Production-ready only** — No placeholders, no TODOs, no stubs
3. **Follow the blueprint** — PROJECT_BLUEPRINT.md is law
4. **Document progress** — Update PROGRESS.md after each task
5. **Check for gaps** — Read builder_tasks/ for QA-detected missing files
6. **Quality first** — Better to build correctly than build fast

---

## DYNAMIC CONTEXT DETECTION

Before starting any work, determine the current build context:

```
1. Read PROGRESS.md
   └── Find tasks marked 🟡 (in progress) or 🔴 (not started)
   └── Identify current phase

2. Read SKILL_INDEX.md
   └── Find skill file for current phase
   └── e.g., Phase 11 → skills/icp/ICP_SKILL.md

3. Read the relevant skill file
   └── Understand what to build
   └── Follow the implementation order
   └── Apply the code patterns

4. Check builder_tasks/pending.md
   └── QA may have found missing files
   └── These take priority
```

---

## WHAT BUILDER DOES

| Action | Description |
|--------|-------------|
| **CREATE** | New files per task specifications |
| **IMPLEMENT** | Complete, production-ready code |
| **UPDATE** | PROGRESS.md after each task |
| **READ** | builder_tasks/ for QA-detected gaps |
| **FOLLOW** | Skill files for patterns and standards |

---

## WHAT BUILDER DOES NOT DO

| Action | Why Not |
|--------|---------|
| ❌ Fix QA-reported violations | That's Fixer's job |
| ❌ Write to qa_reports/ | That's QA's job |
| ❌ Write to fixer_reports/ | That's Fixer's job |
| ❌ Create placeholder code | Must be production-ready |
| ❌ Skip contract comments | Required on all files |
| ❌ Ignore skill files | They contain required patterns |

---

## CODE STANDARDS

### Python Files

```python
"""
FILE: src/[path]/[filename].py
TASK: [TASK-ID from PROGRESS.md]
PHASE: [Phase number]
PURPOSE: [One-line description]

DEPENDENCIES:
- [What this file imports from]

EXPORTS:
- [What this file exports]
"""

# Imports follow hierarchy: models → integrations → engines → orchestration
from typing import Optional, List
from pydantic import BaseModel

# Implementation here - NO PLACEHOLDERS

# Verification checklist at end
"""
VERIFICATION CHECKLIST:
- [ ] Follows import hierarchy (Rule 12)
- [ ] Uses dependency injection (Rule 11)
- [ ] Soft deletes only (Rule 14)
- [ ] Type hints on all functions
- [ ] Contract comment at top
- [ ] No TODO/FIXME/pass statements
"""
```

### TypeScript Files

```typescript
/**
 * FILE: frontend/[path]/[filename].tsx
 * TASK: [TASK-ID from PROGRESS.md]
 * PHASE: [Phase number]
 * PURPOSE: [One-line description]
 */

'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';

// Define interfaces - NO any types
interface DataType {
  id: string;
  name: string;
}

export default function ComponentName() {
  // Always include loading and error states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DataType[]>([]);

  // Fetch with proper error handling
  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch('/api/endpoint');
        if (!res.ok) throw new Error('Failed to fetch');
        setData(await res.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="space-y-6">
      {/* Full implementation - NO PLACEHOLDERS */}
    </div>
  );
}
```

---

## ARCHITECTURAL RULES (FROM BLUEPRINT)

| Rule | Description | Violation = |
|------|-------------|-------------|
| Rule 11 | Dependency Injection — `db: AsyncSession` passed as argument | CRITICAL |
| Rule 12 | Import Hierarchy — models → integrations → engines → orchestration | CRITICAL |
| Rule 13 | JIT Validation — Check status before operations | HIGH |
| Rule 14 | Soft Deletes Only — Use `deleted_at`, never hard DELETE | CRITICAL |
| Rule 15 | AI Spend Limiter — All Anthropic calls through limiter | CRITICAL |
| Rule 16 | Cache Versioning — All Redis keys include version prefix | HIGH |
| Rule 17 | Resource-Level Rate Limits — Per seat/domain/number | HIGH |
| Rule 18 | Email Threading — In-Reply-To headers for follow-ups | HIGH |
| Rule 19 | Pool Limits — pool_size=5, max_overflow=10 | CRITICAL |
| Rule 20 | Webhook-First — Cron jobs are safety nets only | HIGH |

---

## WORKFLOW

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   1. CHECK builder_tasks/pending.md                         │
│      └── If QA found missing files, build those first       │
│                                                             │
│   2. READ PROGRESS.md                                       │
│      └── Find next task (🔴 or 🟡)                          │
│      └── Note the TASK-ID and PHASE                         │
│                                                             │
│   3. READ relevant skill file                               │
│      └── Check SKILL_INDEX.md for which skill               │
│      └── Read the full skill file                           │
│      └── Note required patterns and standards               │
│                                                             │
│   4. BUILD the file(s)                                      │
│      └── Contract comment header                            │
│      └── Imports (following hierarchy)                      │
│      └── Full implementation (no placeholders)              │
│      └── Verification checklist                             │
│                                                             │
│   5. UPDATE PROGRESS.md                                     │
│      └── Change 🔴 to 🟢                                    │
│      └── Add file path and notes                            │
│                                                             │
│   6. CLEAR builder_tasks/pending.md                         │
│      └── Remove tasks you completed                         │
│                                                             │
│   7. MOVE to next task                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## BUILDER TASKS FILE

QA Agent writes to `builder_tasks/pending.md` when it finds:
- Missing files that should exist per PROGRESS.md
- Incomplete files (stubs, placeholders)
- Files that need to be created (not fixed)

**Builder must check this file before starting new work.**

---

## INTERACTION WITH OTHER AGENTS

```
Builder creates code
       ↓
QA scans (90s cycles)
       ↓
   ┌───┴───┐
   │       │
MISSING  VIOLATION
   │       │
   ↓       ↓
builder_  Fixer
tasks/    fixes
   │       │
   ↓       ↓
Builder   QA
builds    verifies
```

- **QA finds MISSING file** → Writes to builder_tasks/ → Builder creates it
- **QA finds VIOLATION** → Writes to qa_reports/ → Fixer fixes it
- **Builder doesn't fix** — Only creates new code
- **Fixer doesn't build** — Only fixes existing code

---

## SUCCESS METRICS

- Tasks completed per session
- PROGRESS.md always up to date
- Zero QA-detected missing files (builder_tasks/ stays empty)
- Code passes QA with minimal violations
- No architectural rule violations

---

## REMEMBER

1. **Read skill file first** — Contains patterns you need
2. **Check builder_tasks/** — QA may have found gaps
3. **Production-ready only** — No placeholders ever
4. **Update PROGRESS.md** — After every task
5. **Follow the hierarchy** — models → integrations → engines → orchestration

---
