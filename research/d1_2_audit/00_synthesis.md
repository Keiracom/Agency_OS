# Pipeline F v2.1 Seam Audit — Synthesis

**Directive:** D1.2
**Date:** 2026-04-15
**Auditors:** 6 sub-agents (build-2, build-3, test-4, review-5, research-1, devops-6)

---

## Finding Count by Severity

| Severity | Count | Source Reports |
|----------|-------|----------------|
| CRITICAL | 1 | 01_data_contracts |
| HIGH | 4 | 01_data_contracts (2), 04_naming (2) |
| MEDIUM | 7 | 01_data_contracts (3), 02_cost_and_env (1), 03_errors_and_parallel (1), 04_naming (2) |
| LOW | 8 | 01_data_contracts (4), 02_cost_and_env (3), 04_naming (2) |
| **Total** | **20** | |

---

## Top 10 Findings Ranked by Risk-to-Rerun

### 1. [CRITICAL] ABN budget signal permanently zeroed (01_data_contracts C1)
Stage 5 reads `f3a_output.get("abn")` but Stage 3 output never contains ABN (schema says "ABN comes from Stage 2 SERP only"). The +3 budget score for ABN registration is always 0. Every domain's budget score is undercounted by 3 points.
**Fix:** Pass `stage2["serp_abn"]` into Stage 5 scorer alongside stage3 output. ~5 min.

### 2. [HIGH] Stage 9 scrapes unverified LinkedIn URL (01_data_contracts H2)
cohort_runner passes Stage 8a candidate URL to Stage 9, not Stage 8b L2-verified URL. If L2 rejected the candidate (wrong person), Stage 9 still scrapes their posts — collecting wrong-person social data for outreach.
**Fix:** Use `stage8_contacts["linkedin"]["linkedin_url"]` (verified) instead of `fills["dm_linkedin_url"]` (candidate). ~5 min.

### 3. [HIGH] rank_overview field names unverified (01_data_contracts H1)
Stage 5 reads `dfs_organic_etv`, `dfs_organic_keywords`, etc. from rank_overview. If DFS client returns different keys, all scoring silently zeros via `.get() or 0`. No runtime error — just wrong scores.
**Fix:** Add key verification or normalize in signal_bundle output. ~10 min.

### 4. [HIGH] HunterIO and Apify in dead-reference table but actively used (04_naming)
CLAUDE.md lists both as dead references with replacements. Pipeline F actively uses Hunter (email L2) and Apify (LinkedIn L2 scraper, posts). These are CEO-ratified decisions from this session that were never reflected in CLAUDE.md.
**Fix:** Update CLAUDE.md dead-reference table with exceptions. ~5 min.

### 5. [HIGH] call_f3a/call_f3b public API names not annotated (04_naming)
GeminiClient methods retain old naming with no NOTE/DEPRECATED marker on the methods themselves. Callers in cohort_runner invoke by old name.
**Fix:** Add deprecation docstring to methods. Deferred to filename rename directive. ~2 min.

### 6. [MEDIUM] Stage 4 cost constant undercount (02_cost_and_env)
Fixed constant $0.073 but actual 10 endpoints sum to $0.0775. Delta = -$0.0045/domain. At 100-cohort = -$0.45 invisible.
**Fix:** Update constant to $0.078. ~1 min.

### 7. [MEDIUM] Stage 8a ABN not propagated to Stage 11 card (01_data_contracts M1)
verify_fills finds ABN via compound SERP (more accurate than Stage 2). Stage 11 card only reads Stage 2 ABN.
**Fix:** Prefer Stage 8a ABN over Stage 2 in card assembly. ~5 min.

### 8. [MEDIUM] Stage 7 outreach not fallback into Stage 11 card (01_data_contracts L3)
If Stage 10 is gated out (no email), card.outreach is None. Stage 7 already generated draft outreach but it's not used as fallback.
**Fix:** Card assembly should fallback to Stage 7 drafts when Stage 10 is None. ~5 min.

### 9. [MEDIUM] serp_verify.py generic error handling (03_errors_and_parallel)
All exceptions return empty dict — can't distinguish network failure from no data.
**Fix:** Add f_status field to serp_verify return. ~10 min.

### 10. [MEDIUM] Stage 10 f_status not propagated to card (01_data_contracts L2)
Partial Stage 10 (VR succeeded, outreach failed) produces eligible card with silently missing outreach.
**Fix:** Check Stage 10 f_status in card assembly. ~5 min.

---

## Recommended Fix Order Before 20-Domain Rerun

### MUST FIX (blocks rerun accuracy):
1. ABN signal zeroed (#1) — 5 min
2. Stage 9 unverified URL (#2) — 5 min
3. Stage 4 cost constant (#6) — 1 min

### SHOULD FIX (improves quality):
4. Stage 7 outreach fallback (#8) — 5 min
5. Stage 8a ABN propagation (#7) — 5 min
6. CLAUDE.md dead-ref exceptions (#4) — 5 min

### DEFERRABLE (post-rerun):
7. rank_overview key verification (#3) — needs live data check
8. call_f3a/call_f3b annotation (#5) — cosmetic
9. serp_verify error handling (#9) — nice-to-have
10. Stage 10 f_status propagation (#10) — edge case

**Total estimated fix time for MUST+SHOULD: ~26 min**

---

## Findings Deferrable to Post-Rerun

- Env var mismatches for inactive features (HeyGen, Deepgram, Telnyx, Calendly) — not on pipeline path
- Prefect deployment gap (0 Pipeline F flows) — CLI-only is correct for now
- Supabase write gap (pipeline outputs to JSON only) — by design for testing phase
- Noun consistency (prospect/lead/domain) — cosmetic
- Filename renames (comprehend_schema_f3a.py → stage3_identify.py) — deferred to dedicated directive
- bulk_domain_metrics pricing TODO — not in pipeline path

---

## Sub-Agent Metrics

| Agent | Report | Findings | Tokens | Duration |
|-------|--------|----------|--------|----------|
| build-2 | 01_data_contracts | 10 | 72,221 | 215s |
| build-3 | 02_cost_and_env | 9 | 66,941 | 175s |
| test-4 | 03_errors_and_parallel | 6 | 97,879 | 164s |
| review-5 | 04_naming | 7 | 39,581 | 121s |
| research-1 | 05_doc_drift | 0 (clean) | 71,542 | 156s |
| devops-6 | 06_runtime_config | 3 | 57,775 | 67s |
| **Total** | **7 reports** | **35** | **405,939** | **~4 min** |

