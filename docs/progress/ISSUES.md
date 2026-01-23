# Issues & Tech Debt — Agency OS

> Log issues here when found. Don't fix unrelated issues mid-task — log and continue.

---

## How to Use This File

When you find an issue during development:
1. Add it to the appropriate severity section
2. Assign an ID (ISS-XXX)
3. Continue with your current task
4. Fix issues in dedicated cleanup sessions

---

## CRITICAL (Blocks launch)

| ID | Issue | Found | Status | Owner |
|----|-------|-------|--------|-------|
| — | None currently | — | — | — |

---

## WARNING (Should fix before launch)

| ID | Issue | Found | Status | Notes |
|----|-------|-------|--------|-------|
| ISS-002 | Phase file naming mismatch | Jan 8 | Open | PHASE_18_E2E_JOURNEY.md describes E2E but should be Phase 21. PHASE_19_EMAIL_INFRA.md should be Phase 18. Consider renaming or renumbering files |

---

## INFO (Nice to fix)

| ID | Issue | Found | Status | Notes |
|----|-------|-------|--------|-------|
| ISS-004 | Lob references in pricing docs | Jan 8 | Open | US-only direct mail. ClickSend is AU solution. Add clarifying note to TIER_PRICING_COST_MODEL_v2.md |
| ISS-005 | Serper integration undocumented | Jan 8 | Open | Code exists at src/integrations/serper.py, no spec file. Create docs/specs/integrations/SERPER.md |
| ISS-006 | Create Salesforge integration spec | Jan 8 | Open | Current email provider but no documentation. Create docs/specs/integrations/SALESFORGE.md |

---

## RESOLVED

| ID | Issue | Fixed | Resolution |
|----|-------|-------|------------|
| ISS-010 | PaginatedResponse.map error | Jan 23 | Fixed `archive/page.tsx:386` to use `campaigns?.items?.map()` |
| ISS-009 | Missing @sentry/nextjs | Jan 23 | Installed package via `npm install @sentry/nextjs` |
| ISS-008 | Missing @radix-ui/react-slider | Jan 23 | Installed package via `npm install @radix-ui/react-slider` |
| ISS-007 | AISpendBreakdown type mismatch | Jan 23 | Updated `lib/api/types.ts` with full AISpendBreakdown interface matching page expectations |
| ISS-001 | SCHEMA_OVERVIEW.md missing migrations 018-031 | Jan 8 | Added all migrations 021-031 with proper table documentation |
| ISS-003 | Synthflow references in 8 files | Jan 8 | Changed to Vapi in: FULL_SYSTEM_ARCHITECTURE.md, user-journey-diagram.html, COMPLETED_PHASES.md, EXPERT_PANEL_LANDING_PAGE.md, user-manual.html. Also fixed Lob → ClickSend |
| ISS-000 | FILE_STRUCTURE.md migration list outdated | Jan 8 | Updated to show migrations 001-031 with gap note |
| ISS-000 | Smartlead/Deepgram stale specs | Jan 8 | Archived to docs/specs/integrations/archive/ |
| ISS-000 | INTEGRATION_INDEX.md stale entries | Jan 8 | Removed Smartlead, Deepgram. Added archive note. Added Serper |
| ISS-000 | FILE_STRUCTURE.md non-existent files | Jan 8 | Removed infraforge.py, smartlead.py, email_infrastructure.py references |
| ISS-000 | ENGINE_INDEX.md Smartlead reference | Jan 8 | Changed to Resend/Salesforge |
| ISS-000 | PHASE_INDEX.md wrong phase numbers | Jan 8 | Rewrote to match PROGRESS.md |
| ISS-000 | CLAUDE.md Smartlead reference | Jan 8 | Changed to Resend + Salesforge |
