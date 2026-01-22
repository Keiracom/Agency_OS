# Migration Audit Report

**Generated:** 2026-01-17
**Purpose:** Identify .md and .json files as candidates for Python-based architecture migration
**Scope:** C:\AI\Agency_OS (excluding node_modules, .next, .git)

---

## 1. Skills Inventory

Files in `skills/` directory — Claude Code instruction sets for specific tasks.

| Path | Lines | Code Blocks | Frontmatter | Purpose |
|------|-------|-------------|-------------|---------|
| `skills/agents/BUILDER_SKILL.md` | 502 | Yes (12) | No | Builder Agent for Agency OS — creates production-rea... |
| `skills/agents/COORDINATION_SKILL.md` | 391 | Yes (32) | No | Three-Agent Pipeline for Agency OS — coordination... |
| `skills/agents/FIXER_SKILL.md` | 412 | Yes (34) | No | Fixer Agent — repairs code violations found by QA... |
| `skills/agents/QA_SKILL.md` | 317 | Yes (20) | No | QA Agent — scans code for issues and routes them... |
| `skills/campaign/CAMPAIGN_SKILL.md` | 642 | Yes (32) | No | Campaign Generation Skills — transform ICP data int... |
| `skills/conversion/CONVERSION_SKILL.md` | 392 | Yes (24) | No | Phase 16: Conversion Intelligence System — statisti... |
| `skills/crm/CRM_INTEGRATION_SKILL.md` | 883 | Yes (38) | No | CRM Push + Customer Import + Platform Intelligence... |
| `skills/frontend/ADMIN_DASHBOARD.md` | 569 | Yes (22) | No | Admin Dashboard — comprehensive admin for platform... |
| `skills/frontend/FRONTEND_BACKEND_SKILL.md` | 1658 | Yes (38) | No | Connect Next.js Frontend to FastAPI Backend... |
| `skills/frontend/MISSING_UI_SKILL.md` | 338 | Yes (30) | No | Phase 14 Missing UI Components — 4 features to add... |
| `skills/frontend/PHASE_21_UI_SKILL.md` | 625 | Yes (30) | No | Phase 21 UI Design System — Bloomberg Terminal aest... |
| `skills/frontend/V0_SKILL.md` | 443 | Yes (42) | No | v0.dev Integration — SDK setup, prompt engineering... |
| `skills/linkedin/LINKEDIN_CONNECTION_SKILL.md` | 807 | Yes (20) | No | LinkedIn Credential-Based Connection for HeyReach... |
| `skills/SKILL_INDEX.md` | N/A | Unknown | No | Index of all available skills |
| `skills/testing/E2E_SKILL.md` | 400 | Yes (34) | **Yes** | E2E Testing Session Skill — multi-session state mgmt |
| `skills/testing/LIVE_UX_TEST_SKILL.md` | 848 | Yes (18) | No | Live End-to-End UX Testing — real APIs, real data... |

**Total:** 16 files | **With Code Blocks:** 15/16 | **With Frontmatter:** 1/16

**Migration Notes:**
- All skills contain executable code examples (Python)
- `E2E_SKILL.md` has YAML frontmatter — indicates skill registration format
- High migration priority — skills define Claude behavior patterns

---

## 2. State Files Inventory

JSON files used for configuration or runtime state.

### 2.1 E2E Testing State (Machine-Read: YES)

| Path | Lines | Purpose | Machine-Read |
|------|-------|---------|--------------|
| `docs/e2e/e2e_state.json` | 17 | E2E test progress tracking | Yes |
| `docs/e2e/e2e_config.json` | 271 | E2E test configuration | Yes |

### 2.2 Project Configuration (Machine-Read: Partial)

| Path | Lines | Purpose | Machine-Read |
|------|-------|---------|--------------|
| `.claude/settings.local.json` | 19 | Claude Code local settings | Yes |
| `frontend/package.json` | 61 | Frontend dependencies | Yes |
| `frontend/tsconfig.json` | 30 | TypeScript config | Yes |
| `frontend/vercel.json` | 28 | Vercel deployment config | Yes |
| `package.json` | 35 | Root dependencies | Yes |
| `vercel.json` | 57 | Root Vercel config | Yes |
| `test-results/.last-run.json` | 3 | Test runner state | Yes |

### 2.3 Xero Financial Data (Machine-Read: YES)

| Path | Lines | Purpose | Machine-Read |
|------|-------|---------|--------------|
| `xero/cache/sync_state.json` | 3 | Sync state tracking | Yes |
| `xero/cache/token.json` | 5 | OAuth token cache | Yes |
| `xero/data/accounts.json` | 1204 | Chart of accounts | Yes |
| `xero/data/account_transactions_analysis.json` | 11936 | Transaction analysis | Yes |
| `xero/data/bank_summary.json` | 37 | Bank account summary | Yes |
| `xero/data/bank_transactions.json` | 24941 | Bank transactions | Yes |
| `xero/data/bank_transactions_p1.json` - `p5.json` | 17860 | Paginated transactions | Yes |
| `xero/data/bills_accpay.json` | 95 | Bills payable | Yes |
| `xero/data/chart_of_accounts.json` | 1204 | Chart of accounts | Yes |
| `xero/data/contacts.json` | 5482 | Contact records | Yes |
| `xero/data/employees.json` | 18 | Employee records | Yes |
| `xero/data/payments.json` | 124 | Payment records | Yes |
| `xero/data/payruns.json` | 33 | Pay run data | Yes |
| `xero/data/trial_balance_summary.json` | 50 | Trial balance | Yes |
| `xero/xero_config.json` | 297 | Xero API configuration | Yes |

### 2.4 Financial Advisor Knowledge Base (Machine-Read: YES)

| Path | Lines | Purpose | Machine-Read |
|------|-------|---------|--------------|
| `xero/data/pay/profile.json` | 555 | User profile context | Yes |
| `xero/data/pay/config/chart_of_accounts.json` | 327 | Account mapping | Yes |
| `xero/data/pay/config/compliance_calendar.json` | 157 | Due date tracking | Yes |
| `xero/data/pay/config/deduction_rules.json` | 268 | Tax deduction rules | Yes |
| `xero/data/pay/config/tax_rates.json` | 133 | Tax rate tables | Yes |
| `xero/data/pay/config/tax_types.json` | 159 | Tax type definitions | Yes |
| `xero/data/pay/knowledge/asset_protection.json` | 492 | Knowledge module | Yes |
| `xero/data/pay/knowledge/business_exit.json` | 566 | Knowledge module | Yes |
| `xero/data/pay/knowledge/business_structures.json` | 909 | Knowledge module | Yes |
| `xero/data/pay/knowledge/cash_flow.json` | 491 | Knowledge module | Yes |
| `xero/data/pay/knowledge/compliance.json` | 488 | Knowledge module | Yes |
| `xero/data/pay/knowledge/decision_trees.json` | 396 | Decision frameworks | Yes |
| `xero/data/pay/knowledge/deductions.json` | 501 | Knowledge module | Yes |
| `xero/data/pay/knowledge/estate_planning.json` | 212 | Knowledge module | Yes |
| `xero/data/pay/knowledge/gst_bas.json` | 372 | Knowledge module | Yes |
| `xero/data/pay/knowledge/index.json` | 193 | Topic index | Yes |
| `xero/data/pay/knowledge/investments.json` | 741 | Knowledge module | Yes |
| `xero/data/pay/knowledge/payroll_super.json` | 240 | Knowledge module | Yes |
| `xero/data/pay/knowledge/penalties.json` | 245 | Knowledge module | Yes |
| `xero/data/pay/knowledge/property.json` | 636 | Knowledge module | Yes |
| `xero/data/pay/knowledge/psi_rules.json` | 176 | Knowledge module | Yes |
| `xero/data/pay/knowledge/salary_packaging.json` | 532 | Knowledge module | Yes |
| `xero/data/pay/knowledge/small_business.json` | 310 | Knowledge module | Yes |
| `xero/data/pay/knowledge/superannuation.json` | 731 | Knowledge module | Yes |
| `xero/data/pay/knowledge/tax_planning.json` | 751 | Knowledge module | Yes |
| `xero/data/pay/knowledge/thresholds.json` | 311 | Knowledge module | Yes |
| `xero/data/pay/knowledge/wealth_fire.json` | 570 | Knowledge module | Yes |
| `xero/data/pay/knowledge/xero.json` | 2034 | Xero operations | Yes |

### 2.5 Temporary/Disposable Files (Machine-Read: NO)

| Path | Lines | Purpose | Machine-Read |
|------|-------|---------|--------------|
| `temp_deployments.json` | 0 | Temp deployment data | No |
| `temp_logs.json` | 0 | Temp log data | No |
| `C:AIAgency_OSxerodatabills_accpay.json` | 279 | Orphaned file | No |

**Total JSON Files:** 85+ | **Machine-Read:** ~90%

**Migration Notes:**
- E2E state files are source of truth — migrate to database or Python state manager
- Financial advisor knowledge base is structured for retrieval — consider embedding in vector DB
- Xero data files are API cache — already machine-read by Python client

---

## 3. Process/Roadmap Files

Files that track tasks, phases, or progress.

| Path | Lines | Task Lists | Checkboxes | Format |
|------|-------|------------|------------|--------|
| `PROGRESS.md` | 301 | Yes | 14 | Tables + checkboxes |
| `progress_backup.md` | 1179 | Yes | 37 | Tables + checkboxes |
| `progress_18b_append.md` | 53 | Yes | 4 | Checkboxes |
| `docs/progress/COMPLETED_PHASES.md` | 360 | Yes | Unknown | Tables |
| `docs/progress/ISSUES.md` | 55 | Yes | Unknown | Issue log format |
| `docs/progress/SESSION_LOG.md` | 151 | Yes | Unknown | Session entries |
| `docs/progress/PHASE_18B_ICP_FIX.md` | 153 | Yes | Unknown | Task list |
| `PROJECT_BLUEPRINT.md` | 240 | Yes | 0 | Reference tables |
| `PROJECT_BLUEPRINT_FULL_ARCHIVE.md` | 2057 | Yes | 62 | Reference + checkboxes |
| `DEPLOYMENT.md` | 473 | Yes | 32 | Step-by-step + checkboxes |
| `PHASE_21_E2E_TESTING.md` | 529 | Yes | 23 | Journey spec + checkboxes |
| `unipile.md` | 1527 | Yes | 36 | Migration plan |

**Migration Notes:**
- `PROGRESS.md` is central roadmap — high priority for structured data migration
- Progress files use markdown checkboxes — could migrate to database task tracking
- Multiple backup/append files suggest need for single source of truth

---

## 4. E2E Documentation

Files in `docs/e2e/` — end-to-end testing system.

| Path | Lines | Type | Code Blocks |
|------|-------|------|-------------|
| `docs/e2e/e2e_state.json` | 17 | State | N/A |
| `docs/e2e/e2e_config.json` | 271 | Config | N/A |
| `docs/e2e/E2E_MASTER.md` | 98 | Spec | 4 |
| `docs/e2e/E2E_INSTRUCTIONS.md` | 278 | Spec | 6 |
| `docs/e2e/E2E_SESSION_SYSTEM.md` | 392 | Spec | 18 |
| `docs/e2e/E2E_TASK_BREAKDOWN.md` | 350 | Spec | 2 |
| `docs/e2e/E2E_TEST_PLAN.md` | 355 | Spec | 4 |
| `docs/e2e/COMMON_ISSUES.md` | 214 | Log | 45 |
| `docs/e2e/FILE_REFERENCE.md` | 200 | Spec | 2 |
| `docs/e2e/FILES_CREATED.md` | 89 | Log | 2 |
| `docs/e2e/FIXES_APPLIED.md` | 373 | Log | 10 |
| `docs/e2e/ISSUES_FOUND.md` | 227 | Log | 4 |
| `docs/e2e/J0_INFRASTRUCTURE.md` | 401 | Spec | 4 |
| `docs/e2e/J1_ONBOARDING.md` | 533 | Spec | 8 |
| `docs/e2e/J2_CAMPAIGN.md` | 411 | Spec | 10 |
| `docs/e2e/J2B_ENRICHMENT.md` | 409 | Spec | 16 |
| `docs/e2e/J3_EMAIL.md` | 429 | Spec | 10 |
| `docs/e2e/J4_SMS.md` | 423 | Spec | 12 |
| `docs/e2e/J5_VOICE.md` | 456 | Spec | 10 |
| `docs/e2e/J6_LINKEDIN.md` | 392 | Spec | 8 |
| `docs/e2e/J7_REPLY.md` | 517 | Spec | 14 |
| `docs/e2e/J8_MEETING.md` | 506 | Spec | 10 |
| `docs/e2e/J9_DASHBOARD.md` | 459 | Spec | 8 |
| `docs/e2e/J10_ADMIN.md` | 533 | Spec | 14 |

**Total:** 24 files (2 JSON + 22 MD)

**Migration Notes:**
- `e2e_state.json` is already machine-read — single source of truth pattern
- Journey specs (J0-J10) contain executable test steps — could migrate to pytest fixtures
- Log files track issues/fixes — could migrate to database issue tracker

---

## 5. Phase Documentation

Files in `docs/phases/` — development phase specifications.

| Path | Lines | Status |
|------|-------|--------|
| `docs/phases/PHASE_01_FOUNDATION.md` | 69 | Completed |
| `docs/phases/PHASE_02_MODELS.md` | 78 | Completed |
| `docs/phases/PHASE_03_INTEGRATIONS.md` | 103 | Completed |
| `docs/phases/PHASE_04_ENGINES.md` | 95 | Completed |
| `docs/phases/PHASE_05_ORCHESTRATION.md` | 108 | Completed |
| `docs/phases/PHASE_06_AGENTS.md` | 98 | Completed |
| `docs/phases/PHASE_07_API.md` | 100 | Completed |
| `docs/phases/PHASE_08_FRONTEND.md` | 111 | Completed |
| `docs/phases/PHASE_09_TESTING.md` | 89 | Completed |
| `docs/phases/PHASE_10_DEPLOYMENT.md` | 94 | Completed |
| `docs/phases/PHASE_11_ICP.md` | 130 | Completed |
| `docs/phases/PHASE_12_CAMPAIGN_EXEC.md` | 48 | Completed |
| `docs/phases/PHASE_13_FRONTEND_BACKEND.md` | 82 | Completed |
| `docs/phases/PHASE_14_MISSING_UI.md` | 72 | Completed |
| `docs/phases/PHASE_15_UX_TEST.md` | 78 | Completed |
| `docs/phases/PHASE_16_CONVERSION.md` | 124 | Completed |
| `docs/phases/PHASE_17_LAUNCH_PREREQ.md` | 125 | In Progress |
| `docs/phases/PHASE_18_EMAIL_INFRA.md` | 155 | In Progress |
| `docs/phases/PHASE_19_EMAIL_INFRA.md` | 82 | In Progress |
| `docs/phases/PHASE_21_UI_OVERHAUL.md` | 181 | Not Started |
| `docs/phases/PHASE_22_MARKETING_AUTO.md` | 119 | Planned |
| `docs/phases/PHASE_23_PLATFORM_INTEL.md` | 92 | Planned |
| `docs/phases/PHASE_24_LEAD_POOL.md` | 185 | Planned |
| `docs/phases/PHASE_24H_LINKEDIN_CONNECTION.md` | 573 | Planned |
| `docs/phases/PHASE_INDEX.md` | 124 | Index |
| `docs/phases/archive/PHASE_24E_CRM_PUSH_ORIGINAL_SPEC.md` | N/A | Archived |
| `docs/phases/archive/PHASE_24F_CUSTOMER_IMPORT_ORIGINAL_SPEC.md` | N/A | Archived |

**Total:** 27 files | **Completed:** 16 | **In Progress:** 3 | **Planned:** 4 | **Archived:** 2

**Migration Notes:**
- Phase files are read-only reference — low migration priority
- Status tracking duplicated between phase files and PROGRESS.md
- Consider consolidating status to single source (database or PROGRESS.md)

---

## 6. Other Candidates

Additional files containing executable instructions, code blocks, or task tracking.

### 6.1 Root-Level Executable Docs

| Path | Lines | Code Blocks | Checkboxes | Purpose |
|------|-------|-------------|------------|---------|
| `CLAUDE.md` | 511 | 34 | 0 | Main Claude Code instructions |
| `CLAUDE_DESKTOP.md` | 323 | 8 | 9 | Claude Desktop protocol |
| `CLAUDE_CODE_AUDIT_PHASE_24.md` | 391 | 2 | 0 | Audit prompt template |
| `CLAUDE_CODE_PROMPT_CIS_DATA_GAPS.md` | 137 | 2 | 0 | Implementation prompt |
| `DEPLOYMENT.md` | 473 | 56 | 32 | Deployment guide |
| `DEPLOYMENT_ISSUES.md` | 46 | 4 | 0 | Issue tracker |
| `HANDOFF.md` | 126 | 4 | 0 | Team handoff protocol |
| `PLAN_PROSPEO_WATERFALL.md` | 191 | 18 | 0 | Feature planning doc |
| `README.md` | 18 | 0 | 0 | Project readme |

### 6.2 Architecture Documentation

| Path | Lines | Code Blocks | Purpose |
|------|-------|-------------|---------|
| `docs/architecture/DECISIONS.md` | 128 | Unknown | Tech stack decisions |
| `docs/architecture/FILE_STRUCTURE.md` | 279 | Unknown | File organization |
| `docs/architecture/IMPORT_HIERARCHY.md` | 135 | Unknown | Import rules |
| `docs/architecture/RULES.md` | 166 | Unknown | Claude Code rules |

### 6.3 Finance Documentation

| Path | Lines | Purpose |
|------|-------|---------|
| `docs/finance/12_MONTH_PL_PROJECTION.md` | 615 | P&L projection |
| `docs/finance/12_MONTH_PL_PROJECTION_v2.md` | 527 | P&L v2 |
| `docs/finance/agency_os_buyer_guide_v2.md` | 484 | Sales doc |
| `docs/finance/agency_os_buyer_guide_v3.md` | 503 | Sales doc v3 |
| `docs/finance/MEETING_GUARANTEE_ANALYSIS.md` | 289 | Analysis |
| `docs/finance/STAFFING_PLAN.md` | 487 | Org planning |
| `docs/finance/Y1_PL_FINAL.md` | 137 | Year 1 P&L |
| `docs/finance/Y2_PL_FINAL.md` | 194 | Year 2 P&L |
| `docs/finance/YEAR_2_PL_PROJECTION.md` | 641 | Y2 projection |

### 6.4 Marketing Documentation

| Path | Lines | Purpose |
|------|-------|---------|
| `docs/marketing/EXPERT_PANEL_LANDING_PAGE.md` | 488 | Landing page copy |
| `docs/marketing/LANDING_PAGE_COMPETITIVE_ANALYSIS.md` | 397 | Competitor analysis |
| `docs/marketing/MARKETING_LAUNCH_PLAN.md` | 1355 | Launch strategy |

### 6.5 Audit Reports

| Path | Lines | Purpose |
|------|-------|---------|
| `docs/audits/E2E_FIXES_2026-01-07.md` | 217 | E2E test results |
| `docs/audits/E2E_PHASE21_RESULTS.md` | 192 | Phase 21 results |
| `docs/audits/QA_AUDIT_2026-01-07.md` | 314 | QA report |
| `docs/audits/UX_AUDIT_2026-01-04.md` | 342 | UX review |
| `docs/DOCUMENTATION_AUDIT_REPORT.md` | 375 | Doc audit |

### 6.6 Xero Documentation

| Path | Lines | Purpose |
|------|-------|---------|
| `xero/CLAUDE.md` | N/A | Xero integration instructions |
| `xero/data/pay/CLAUDE.md` | N/A | Financial advisor instructions |
| `xero/data/pay/dave/mortgages.md` | N/A | Personal financial data |

### 6.7 Large/Exceptional Files

| Path | Lines | Notes |
|------|-------|-------|
| `FILE_TREE.md` | 40,416 | Auto-generated directory listing |
| `unipile.md` | 1,527 | Research notes with task tracking |

---

## Summary Statistics

| Category | File Count | Total Lines |
|----------|------------|-------------|
| Skills | 16 | ~8,227 |
| E2E Documentation | 24 | ~8,700 |
| Phase Documentation | 27 | ~3,100 |
| JSON State Files | 85+ | ~95,000 |
| Root MD Files | 17 | ~50,000 |
| Other Docs | ~30 | ~10,000 |

**Grand Total:** ~179 files | ~175,000 lines

---

## Migration Priority Recommendations

### High Priority (Machine-Read, Active State)

1. **`docs/e2e/e2e_state.json`** — E2E progress tracking
2. **`docs/e2e/e2e_config.json`** — E2E configuration
3. **`PROGRESS.md`** — Central roadmap (convert to database)
4. **Skills directory** — All 16 skill files (consider Python-based skill loader)

### Medium Priority (Reference, Machine-Readable)

5. **Financial advisor knowledge base** — 21 JSON modules in `xero/data/pay/knowledge/`
6. **Phase documentation** — Status tracking could consolidate
7. **Xero data cache** — Already Python-managed

### Low Priority (Human Reference)

8. **Finance documentation** — Static analysis
9. **Marketing documentation** — Static content
10. **Architecture documentation** — Design reference

---

*End of Migration Audit Report*
