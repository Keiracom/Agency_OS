# Task Backlog

Prioritized work queue for Agency OS. Updated by Elliot, approved by Dave.

---

## 🔴 P0 — Blocking Everything

| ID | Task | Role | Status | Notes |
|----|------|------|--------|-------|
| P0-001 | Fix CI pipeline (ruff + TypeScript errors) | Linter | 🔴 TODO | Blocks all merges |
| P0-002 | Set up GitHub push access | — | 🔴 BLOCKED | Need token from Dave |

---

## 🟠 P1 — Before First Customer

| ID | Task | Role | Status | Notes |
|----|------|------|--------|-------|
| P1-001 | E2E Testing - Journey J0 (Signup) | Tester | 🔴 TODO | Phase 21 |
| P1-002 | E2E Testing - Journey J1 (Lead Import) | Tester | 🔴 TODO | Phase 21 |
| P1-003 | E2E Testing - Journey J2 (Campaign Create) | Tester | 🔴 TODO | Phase 21 |
| P1-004 | E2E Testing - Journey J3 (Outreach) | Tester | 🔴 TODO | Phase 21 |
| P1-005 | E2E Testing - Journey J4 (Response Handling) | Tester | 🔴 TODO | Phase 21 |
| P1-006 | E2E Testing - Journey J5 (Analytics) | Tester | 🔴 TODO | Phase 21 |
| P1-007 | E2E Testing - Journey J6 (Billing) | Tester | 🔴 TODO | Phase 21 |
| P1-008 | Fix Funnel Detector (never called) | Builder | 🔴 TODO | From Dave's QA audit |
| P1-009 | Add Voice retry logic | Builder | 🔴 TODO | From Dave's QA audit |
| P1-010 | Enforce LinkedIn weekend rules | Builder | 🔴 TODO | From Dave's QA audit |
| P1-011 | Add retry logic to Salesforge | Builder | 🔴 TODO | No retries currently |
| P1-012 | Add retry logic to Vapi | Builder | 🔴 TODO | No retries currently |
| P1-013 | Fix hardcoded frontend URL in crm.py | Builder | 🔴 TODO | Quick fix |

---

## 🟡 P2 — Important But Not Urgent

| ID | Task | Role | Status | Notes |
|----|------|------|--------|-------|
| P2-001 | Pin all Python dependencies | Builder | 🔴 TODO | Currently using >= |
| P2-002 | Investigate database latency (2.2s) | Builder | 🔴 TODO | Railway region issue? |
| P2-003 | Remove dead code (resend.py, heyreach.py) | Builder | 🔴 TODO | Cleanup |
| P2-004 | Remove _test_token.txt from repo | Builder | 🔴 TODO | Security |
| P2-005 | Move images to cloud storage | Builder | 🔴 TODO | 40 PNGs bloating repo |
| P2-006 | Resolve 42 TODOs in codebase | Builder | 🔴 TODO | Technical debt |
| P2-007 | Remove Xero financial data from repo | Builder | 🔴 TODO | Accidentally committed |

---

## 🟢 P3 — Nice to Have

| ID | Task | Role | Status | Notes |
|----|------|------|--------|-------|
| P3-001 | Set up proper dev environment on this server | Builder | 🔴 TODO | Need python3-venv |
| P3-002 | Document all API integrations | Documenter | 🔴 TODO | 15+ integrations |
| P3-003 | Create integration testing suite | Tester | 🔴 TODO | Beyond E2E |

---

## ✅ Completed

| ID | Task | Completed | Notes |
|----|------|-----------|-------|
| — | Initial audit | 2026-01-28 | AUDIT_REPORT.md |
| — | Deep codebase analysis | 2026-01-28 | CODEBASE_DEEP_DIVE.md |
| — | Agent team structure | 2026-01-28 | This system |

---

## How This Works

1. **Dave** approves priorities and moves tasks to TODO
2. **Elliot** assigns tasks to agent roles and spawns sub-agents
3. **Sub-agents** do the work and report back
4. **Elliot** reviews and creates PRs
5. **Dave** tests and merges

Tasks flow: BACKLOG → IN_PROGRESS → PR → DONE
