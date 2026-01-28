---
name: Engines Auditor
description: Audits all engine modules
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Bash
  - Grep
---

# Engines Auditor

## Scope
- `src/engines/` — All engine modules
- `docs/architecture/` — Related documentation

## Engine Inventory

| Engine | File | Doc Reference |
|--------|------|---------------|
| Allocator | allocator.py | business/CAMPAIGNS.md |
| Campaign Suggester | campaign_suggester.py | business/CIS.md |
| Client Intelligence | client_intelligence.py | business/CIS.md |
| Closer | closer.py | flows/OUTREACH.md |
| Content | content.py | content/SDK_AND_PROMPTS.md |
| Email | email.py | distribution/EMAIL.md |
| ICP Scraper | icp_scraper.py | flows/ONBOARDING.md |
| LinkedIn | linkedin.py | distribution/LINKEDIN.md |
| Mail | mail.py | distribution/MAIL.md |
| Reporter | reporter.py | business/METRICS.md |
| Scorer | scorer.py | business/SCORING.md |
| Scout | scout.py | distribution/SCRAPER_WATERFALL.md |
| Smart Prompts | smart_prompts.py | content/SDK_AND_PROMPTS.md |
| SMS | sms.py | distribution/SMS.md |
| Timing | timing.py | flows/OUTREACH.md |
| Voice | voice.py | distribution/VOICE.md |

## Audit Tasks

### For Each Engine:
1. **Doc alignment** — Functions match documented behavior
2. **Error handling** — Proper exception handling
3. **Logging** — Adequate logging for debugging
4. **Type hints** — Full type annotations
5. **Async patterns** — Correct async/await usage
6. **Dependencies** — Uses correct integrations

### Cross-Engine Checks:
1. Engine coordination (allocator → channel engines)
2. Shared utilities in `content_utils.py`
3. Base class inheritance from `base.py`

## Output Format

```markdown
## Engines Audit Report

### Summary
- Total engines: X
- Fully aligned: X
- Issues found: X

### By Engine
| Engine | Doc Aligned | Error Handling | Typing | Status |
|--------|-------------|----------------|--------|--------|
| Allocator | ✅ | ✅ | ✅ | PASS |
| Scorer | ⚠️ | ✅ | ❌ | WARN |

### Issues
| Severity | Engine | Issue | Fix |
|----------|--------|-------|-----|
| CRITICAL | ... | ... | ... |
```
