# C1 Comprehensive System Audit — Phase 1.5
**Date:** 2026-04-22
**Auditor:** Audit Master sub-agent (Elliot session)
**Scope:** End-to-end codebase audit reflecting Stage 9/10, Prefect rebuild, agent_comms, enforcer, batch mode, writer/critic

## Executive Summary

- **Critical Issues:** 0 (no exit gate blockers)
- **High Priority:** 8 (should fix before P1.5 close)
- **Medium Priority:** 5 (tech debt, non-blocking)
- **Low Priority:** 3 (nice-to-have)
- **Total Issues:** 16

**Exit Gate Verdict:** PASS — no critical blockers.

---

## HIGH Findings

### H1: Dropped domains write partial data only (GOV-8)
**File:** `src/orchestration/flows/pipeline_f_master_flow.py:177-200`
**Issue:** GOV-8 fix for dropped domains writes domain + display_name + dropped_at only. Full Stage 2/3/4 data discarded.
**Impact:** Intelligence loss — no forensic trail for why a domain was dropped.
**Fix:** Extend dropped domain BU write to include all Stage 2-5 extracts.

### H2: Stage 9 social posts not persisted (GOV-8)
**File:** `src/intelligence/stage9_social.py`
**Issue:** Stage 9 scrapes DM LinkedIn + company posts but returns in-memory only. No database write.
**Impact:** Re-fetch on every run (GOV-8 "never re-fetched" violated).
**Fix:** Add dm_social_posts and company_social_posts JSONB columns to BU, write Stage 9 output.

### H3: DataForSEO bundle not written to BU on drop (GOV-8)
**File:** `src/intelligence/dfs_signal_bundle.py`
**Issue:** Stage 4 DFS 5-endpoint bundle (~$0.046 USD/domain) lost if domain drops at Stage 5.
**Impact:** Paid intelligence not captured.
**Fix:** Write DFS bundle to BU immediately after Stage 4, before Stage 5 scoring gate.

### H4: Gemini pool exhaustion halts entire Stage 3
**File:** `src/intelligence/gemini_client.py`
**Issue:** Stage 3 website comprehension runs Gemini with concurrency semaphore. 429 rate limit = entire batch waits, no fallback.
**Impact:** Pipeline stall on high-volume runs.
**Fix:** Add timeout + skip logic (mark domain comprehension_timeout, proceed with partial data).

### H5: Critic timeout = ship unreviewed
**File:** `src/pipeline/stage_10_critic.py:186-200`
**Issue:** On timeout, returns score=0 + needs_review=True but no blocking gate in message generator.
**Impact:** Low-quality messages written if critic times out.
**Fix:** Hard gate in message generator — if critic timeout AND email channel, skip write + log for manual review.

### H6: Stage 9/10 test failures (fixture drift)
**Files:** `tests/test_stage_10_message_generator.py`, `tests/test_stage_9_10_flow.py`
**Issue:** 6 failures — agency_profile signature changes (PR #371-373) broke test fixtures.
**Impact:** Blocks deployment confidence.
**Fix:** Update test fixtures to match current critique_and_revise signature (agency_profile now required).

### H7: BU write ON CONFLICT DO NOTHING = silent data loss
**File:** `src/orchestration/flows/pipeline_f_master_flow.py:~230`
**Issue:** BU INSERT uses ON CONFLICT DO NOTHING — concurrent write silently dropped.
**Impact:** GOV-8 violation (data not persisted).
**Fix:** Change to ON CONFLICT (domain) DO UPDATE SET ... to merge new fields.

### H8: Email waterfall Hunter reference conflict
**File:** `ARCHITECTURE.md` (Section 3 deprecated vs Section 5 exception)
**Issue:** Hunter marked DEPRECATED but also listed as LIVE exception for L2 email fallback.
**Impact:** Documentation conflict.
**Fix:** Confirm Hunter status in Pipeline F v2.1, update docs accordingly.

---

## MEDIUM Findings

### M1: Agent comms references but no implementation
**Evidence:** 0 results for agent_comms in src/. Commit messages reference it but no files found.
**Fix:** Confirm if replaced by Telegram cross-post. Update docs.

### M2: Outreach channels default to all 4 when NULL
**File:** `src/pipeline/stage_10_message_generator.py:168`
**Issue:** NULL outreach_channels defaults to email+LinkedIn+SMS+voice. May send costly channels for low-Propensity leads.
**Fix:** Apply Propensity gate to SMS/voice (e.g., only if >= 75).

### M3: Enforcer Rule 1 evaluates concurrence unconditionally
**File:** `src/telegram_bot/enforcer_bot.py:46`
**Issue:** Rule 1 checks concurrence even when /stage0 not issued.
**Fix:** Add /stage0-active check to Rule 1 trigger logic.

### M4: Pydantic v2 deprecation warnings (4 instances)
**Files:** `src/api/routes/webhooks_outbound.py`, `src/agents/base_agent.py`
**Fix:** Migrate to ConfigDict pattern.

### M5: Prefect flow paused flags inconsistent
**File:** `prefect.yaml`
**Fix:** Document unpause criteria in ops runbook.

---

## LOW Findings

### L1: 59 TODO/FIXME markers in codebase
### L2: Template token regex too narrow (`src/pipeline/email_scoring_gate.py:~15`)
### L3: No circuit breaker on BrightData rate limits

---

## Files Audited
Core enrichment: siege_waterfall.py, waterfall_v2.py, scout.py, campaign_trigger.py
Pipeline stages: stage_9_social.py, stage_10_message_generator.py, stage_10_critic.py, pipeline_f_master_flow.py
Orchestration: enrichment_flow.py, health_check_flow.py, cohort_runner.py
Infrastructure: enforcer_bot.py, chat_bot.py, memory_listener.py, prefect.yaml
Governance: ARCHITECTURE.md, MANUAL.md, CLAUDE.md
