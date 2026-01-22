# Architecture Doc Skill

**Purpose:** Standard process for creating and verifying architecture documentation.
**Location:** `docs/architecture/`
**Last Updated:** 2026-01-21

---

## When to Use This Skill

- Creating a new architecture doc
- Expanding an existing architecture doc
- Verifying an architecture doc against codebase

---

## Doc Template

Every architecture doc MUST follow this structure:

```markdown
# [Topic] — Agency OS

**Purpose:** [One sentence describing what this doc covers]
**Status:** SPECIFICATION | IMPLEMENTED | PARTIAL
**Last Updated:** [Date]

---

## Overview

[1-2 paragraphs explaining the system/flow]

---

## Code Locations

| Component | File | Purpose |
|-----------|------|---------|
| [Name] | `src/path/to/file.py` | [What it does] |

---

## Data Flow

[Diagram or sequence showing how data moves]

```
Step 1 → Step 2 → Step 3
              ↓
         Step 4
```

---

## Key Rules

1. **Rule Name** — Description
2. **Rule Name** — Description

---

## Configuration

| Setting | Default | Notes |
|---------|---------|-------|
| [Name] | [Value] | [Why] |

---

## Cross-References

- `[related/DOC.md](relative/path)` — How it relates
- `[another/DOC.md](relative/path)` — How it relates

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
```

---

## Checklist: Creating New Doc

Before submitting a new architecture doc:

- [ ] **Header complete** — Purpose, Status, Last Updated
- [ ] **Overview written** — Explains system in plain English
- [ ] **Code locations verified** — Every file path exists and is correct
- [ ] **Data flow included** — Shows how data moves through system
- [ ] **Key rules documented** — Constraints, limits, requirements
- [ ] **Cross-references added** — Links to related architecture docs
- [ ] **Footer added** — Links to TODO.md for gaps
- [ ] **ARCHITECTURE_INDEX.md updated** — Added to index with bullet summary
- [ ] **TODO.md updated** — Add any gaps found to Identified Gaps table

---

## Checklist: Verifying Existing Doc

When auditing an existing doc against codebase:

- [ ] **Code locations still accurate** — Files exist, haven't moved
- [ ] **Functionality matches spec** — Code does what doc says
- [ ] **New code discovered** — Add any files not listed
- [ ] **Cross-references valid** — Linked docs exist
- [ ] **TODO.md updated** — Add any gaps found to Identified Gaps table

---

## Rules

### 1. Architecture First
- Update architecture doc BEFORE changing code
- Code must match the spec, not the other way around

### 2. Single Source of Truth
- Each topic has ONE architecture doc
- No duplicate information across docs
- Cross-reference, don't copy

### 3. Code Locations Required
- Every architecture doc MUST list implementing files
- Use exact paths: `src/engines/scorer.py` not "the scorer engine"
- Verify paths exist before submitting

### 4. Keep Docs Focused
- One doc per system/flow
- If doc exceeds 500 lines, consider splitting
- Prefer depth over breadth

### 5. Status Accuracy
- SPECIFICATION = Doc exists, code doesn't
- PARTIAL = Some code exists, gaps remain
- IMPLEMENTED = Code matches spec fully

### 6. Cross-Reference Format
- Use relative paths: `../business/SCORING.md`
- Include brief note on relationship
- Verify linked doc exists

### 7. Gap Tracking (ENFORCED)
- **NO "Known Gaps" sections in architecture docs**
- Docs describe what IS implemented, not what's missing
- All gaps go in `TODO.md` Identified Gaps table only
- See `TODO.md` "Gap Tracking Rule" section for full policy

---

## Examples

### Good Code Locations Table

| Component | File | Purpose |
|-----------|------|---------|
| WHO Detector | `src/detectors/who_detector.py` | Analyzes lead attributes that convert |
| WHAT Detector | `src/detectors/what_detector.py` | Analyzes content patterns that convert |
| Weight Optimizer | `src/detectors/weight_optimizer.py` | Optimizes ALS component weights |
| Pattern Model | `src/models/conversion_patterns.py` | Stores detected patterns |
| Pattern Flow | `src/orchestration/flows/pattern_learning_flow.py` | Weekly pattern learning |

### Bad Code Locations Table

| Component | File | Purpose |
|-----------|------|---------|
| Detectors | src/detectors/ | The detector stuff |
| Models | various | Data models |

### Good Data Flow

```
Lead Created
    ↓
[Enrichment Flow]
    ↓
Apollo Enrichment → Cache Hit? → Return Cached
    ↓ No
Apify LinkedIn Scrape
    ↓
Clay Fallback (if needed, max 15%)
    ↓
Score Lead (ALS)
    ↓
Allocate Channels
    ↓
Ready for Outreach
```

### Bad Data Flow

```
Leads get enriched and then scored and sent out.
```

---

## Folder Mapping

| Folder | Doc Location |
|--------|--------------|
| `src/models/` | `foundation/DATABASE.md` |
| `src/integrations/` | `distribution/*.md` or `foundation/API_LAYER.md` |
| `src/engines/` | Various based on function |
| `src/detectors/` | `business/CIS.md` |
| `src/services/` | Various based on function |
| `src/orchestration/flows/` | `flows/*.md` |
| `src/api/routes/` | `foundation/API_LAYER.md` |
| `frontend/` | `process/FRONTEND.md` or `process/ADMIN.md` |

---

## Integration with Dev Review Process

This skill is used during:

| Step | Who | How Skill Is Used |
|------|-----|-------------------|
| Step 0 | CTO | Audit existing docs using verification checklist |
| Step 1 | Dev Team | Create/update docs using template and creation checklist |
| Step 2 | CTO | Review docs against checklists |
| Step 3 | Dev Team | Revise based on CTO feedback |
| Step 4 | CTO | Final verification before approval |

---

## Quick Reference

**Creating new doc:**
1. Copy template
2. Fill all sections
3. Verify code paths exist
4. Run creation checklist
5. Update INDEX and TODO

**Verifying existing doc:**
1. Read doc
2. Check each code location
3. Compare spec vs implementation
4. Run verification checklist
5. Update doc and TODO with findings
