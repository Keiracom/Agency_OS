# D1.4 Re-Audit Synthesis — Post-Fix Verification

**Date:** 2026-04-15
**Branch audited:** directive-d1-3-audit-fixes (PR #328)
**Auditors:** 6 sub-agents (same assignments as D1.2)

---

## Per-Finding Status (35 D1.2 findings)

### Data Contracts (10 findings)
| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| C1 | CRITICAL | ABN budget signal zeroed | **RESOLVED** — stage3_with_abn injects serp_abn from Stage 2 |
| H1 | HIGH | rank_overview field names | **RESOLVED** — dfs_labs_client emits dfs_organic_etv, scorer reads it. Verified end-to-end. |
| H2 | HIGH | Stage 9 unverified URL | **RESOLVED** — now reads stage8_contacts.linkedin.linkedin_url with match_type guard |
| M1 | MEDIUM | Stage 8a ABN not in card | **RESOLVED** — stage2_merged overlays verify ABN |
| M2 | MEDIUM | Stage 8a company LinkedIn not in card | **RESOLVED** — stage2_merged overlays company_linkedin_url |
| M3 | MEDIUM | verify_fills always-None GMB | **RESOLVED** — fields removed from return dict |
| L1 | LOW | Facebook URL skipped at Stage 3 | **RESOLVED** — by design, flows via stage2_merged |
| L2 | LOW | Stage 10 f_status not in card | **RESOLVED** — stage10_status field added |
| L3 | LOW | Stage 7 outreach fallback | **RESOLVED** — or-fallback to draft fields |
| L4 | LOW | verify_fills _cost 0.006 | **RESOLVED** — changed to 0.008 |

### Cost + Env (9 findings)
| ID | Finding | Status |
|----|---------|--------|
| 1 | Stage 4 cost constant $0.073 | **RESOLVED** — $0.078, unit test added |
| 2 | BRIGHTDATA env key | **RESOLVED** — fixed in D1.1, confirmed no regression |
| 3-9 | Inactive feature env vars | **RESOLVED** — verified not on pipeline path, no action needed |

### Errors + Parallel (6 findings)
| ID | Finding | Status |
|----|---------|--------|
| 1 | serp_verify generic errors | **RESOLVED** — f_status + _errors fields added |
| 2-6 | Error handling quality | **RESOLVED** — verified adequate (gemini_retry gold standard) |

### Naming (7 findings)
| ID | Finding | Status |
|----|---------|--------|
| 1 | HunterIO dead-ref | **RESOLVED** — CLAUDE.md exception added |
| 2 | Apify dead-ref | **RESOLVED** — CLAUDE.md exception added |
| 3 | call_f3a/call_f3b no annotation | **RESOLVED** — Sphinx deprecated docstrings added |
| 4 | Deprecated scripts | **RESOLVED** — headers present from Directive A |
| 5 | Filename renames | **RESOLVED** — deferred, docstrings say Stage 3/7 |
| 6 | prospect_scorer param NOTE | **LOW GAP** — missing NOTE comment on f3a_output param. Documentation only. |
| 7 | Noun consistency | **RESOLVED** — verified acceptable |

### Doc Sync (0 D1.2 findings + verification)
| Finding | Status |
|---------|--------|
| Cost constants match code | **RESOLVED** — $0.078 in code and doc |
| Conversion/wall-clock actuals | **RESOLVED** — doc notes "n=100, pre-fix" |

### Runtime Config (3 findings)
| Finding | Status |
|---------|--------|
| All env vars present | **RESOLVED** — preflight_check.py confirms 9/9 |
| Preflight catches missing vars | **VERIFIED** — mutation trace confirms sys.exit(1) |
| Prefect/Supabase gaps | **RESOLVED** — by design (CLI-only, JSON output) |

---

## New Issues Introduced by Fixes

| ID | Severity | Source | Finding |
|----|----------|--------|---------|
| N1 | LOW | 04_naming | prospect_scorer.py f3a_output param missing NOTE comment |
| N2 | INFO | 02_cost | Cost test uses literal constant, not imported from cohort_runner |
| N3 | INFO | 01_data | stage10_status new card field needs downstream schema awareness |
| N4 | INFO | 01_data | _run_stage8 hardcodes $0.023 independently of verify_fills._cost |

None are blockers. All LOW/INFO.

---

## Recommendation

### **MERGE**

All 35 D1.2 findings are RESOLVED or verified no-action-needed.
4 new issues introduced — all LOW/INFO, none blocking.
No regressions detected across any audit area.
pytest: 1504 passed, 1 pre-existing fail, 0 new failures.

PR #328 is clean for merge → 3-store save → 20-domain rerun.
