# FM-BUILD-V1 Post-Mortem

**Date:** 2026-04-20
**Directive:** FM-BUILD-V1 (Facilities Manager sourcing — 100 records for test-and-tag client)
**Outcome:** 81 email-only records delivered (target was 100 with email + phone)
**Cost:** ~$2.03 AUD (81 Leadmagic credits) + ~$0 ContactOut (prepaid, now exhausted)
**Duration:** ~18 hours elapsed across 2 sessions

---

## What Went Right

1. **Stage 1 company expansion worked well.** 80 CEO anchors → 549 companies across 9 sectors including the fm_providers sector Dave identified as missing. Rebalancing via peer review caught WA underweight and duplicates.

2. **ContactOut search was the right discovery tool.** 771 FM profiles from 74 companies in one API pass. Title-variant search (FM, FC, Property, Operations, Maintenance, Site Manager) cast a wide net.

3. **Peer review caught real issues every time.** Aiden caught: off-target titles (19%), WA geographic gap, Transfield zombie entry, duplicates, yield math errors, Leadmagic AU mobile 0%, and the ContactOut stats vs usability distinction. Every flag was material.

4. **Pilot-before-production discipline (once enforced) prevented waste.** The 5-profile Leadmagic pilot confirmed 80% email hit rate and 0% mobile hit rate before committing $2+ AUD of spend. Should have been standard from the start.

5. **Parallel execution (sem=10) was 10x faster than sequential.** 171 profiles enriched in ~30 seconds vs the sequential run that was projected at 85 minutes.

---

## What Went Wrong

### CRITICAL: Silent try/except burned 608 ContactOut phone credits

**What happened:** The enrichment script used `{"profile": url}` instead of `{"linkedin_url": url}`. ContactOut returned 400 (bad request). The script caught the error silently and continued. 82 calls consumed phone credits on malformed requests. After the run, the account was locked (403 on all endpoints).

**Root cause:** No pre-production pilot. No response validation. Silent exception handling that swallowed errors instead of surfacing them.

**Impact:** $0 AUD direct cost (prepaid credits) but 214 phone credits now stranded behind the email credit gate. Phone enrichment became impossible for this job.

**Prevention:**
- RULE: Every API script must run a 3-5 profile pilot with verbatim response logging before production execution. No exceptions.
- RULE: Non-2xx responses must log and raise, never silently continue. `try/except: pass` on API calls is a governance violation.
- RULE: Verify the exact parameter names against API docs or a working code path in `src/integrations/` before writing ad-hoc scripts.

### CRITICAL: Prospeo included in waterfall despite being deprecated 5 weeks ago

**What happened:** Elliot included Prospeo as a tertiary email fallback in the FM pipeline recommendation. Prospeo was deprecated in Directive #192 (2026-03-13). No active API calls exist in the codebase.

**Root cause:** CLAUDE.md listed Prospeo in the MCP bridge server list (infrastructure capability) which Elliot conflated with "ratified for use." The Dead References table didn't include Prospeo because the deprecation was never propagated to governance docs.

**Impact:** No direct cost (never actually called Prospeo). But the recommendation was wrong and would have failed at execution if followed.

**Prevention:**
- RULE: MCP bridge server list ≠ ratified providers. Check the waterfall ratification (ceo:waterfall_layer_order_v2) for approved providers.
- RULE: When a provider is deprecated, update ALL governance artefacts in the same PR: Dead References tables, MANUAL.md, ARCHITECTURE.md, settings.py, env vars, MCP registry, agent_memories.

### HIGH: Reported numbers from memory, not from file

**What happened:** Elliot reported 1,089 profiles / 128 companies from Stage 2. Actual file contained 771 profiles / 74 companies. The discrepancy was caught by Aiden's peer review.

**Root cause:** Elliot read metadata before the script finished writing, then reported those stale numbers as final. No verification against the actual output file.

**Impact:** Misleading yield estimates propagated through Stage 3 planning.

**Prevention:**
- RULE: At every stage completion, read the ACTUAL output file and report verified numbers. Never report from memory or partial reads.
- RULE: Proactive data inspection is part of stage completion, not a separate review step.

### HIGH: Used build sub-agent instead of scout for research/API tasks

**What happened:** Elliot spawned a build-2 sub-agent for the ContactOut search (549 companies × API calls). Dave flagged this twice — scout exists specifically for this type of work.

**Root cause:** Habit. Elliot defaulted to in-terminal sub-agents because they're faster to spawn. Didn't consider that scout provides persistence, context isolation, and independent TG presence.

**Prevention:**
- RULE: If a task is primarily API calls, web research, data collection, or sourcing → route to scout. If it's code writing → route to build agents.
- RULE: If you're about to use `run_in_background: true` on a bash command, that's a signal it should be a scout job.

### MEDIUM: Sequential execution when parallel was available

**What happened:** First enrichment run was sequential (1.2s delay × 171 profiles). With 30s Leadmagic response times, this would have taken 85 minutes. Killed and restarted with sem=10, finished in 30 seconds.

**Root cause:** Existing pipeline config (GLOBAL_SEM_LEADMAGIC=10) wasn't used. Ad-hoc scripts don't inherit pipeline infrastructure — each one re-invents concurrency from scratch.

**Prevention:**
- RULE: Ad-hoc scripts must use asyncio.gather with semaphore for batch API calls. Sequential loops are only acceptable for < 10 items.

### MEDIUM: Leadmagic endpoint path wrong

**What happened:** First enrichment run used GET `/email-finder` (returned 404). Correct endpoint is POST `/email-finder`. Also tried `/v1/people/email-finder` (also 404). The working call is `POST https://api.leadmagic.io/email-finder` with JSON body.

**Root cause:** Didn't check `src/integrations/leadmagic.py` which has the correct endpoint and method. Wrote ad-hoc code instead of reusing existing integration.

**Prevention:**
- RULE: Before calling any provider API in an ad-hoc script, check `src/integrations/` for existing working code. Use the same endpoint, method, and params.

### LOW: ContactOut search credits exhausted mid-run

**What happened:** 3,043 search credits consumed against a 2,447 balance. Credits ran out at ~company 75 of 549. The remaining 475 companies were never searched.

**Impact:** Reduced the FM profile pool. Only 74 of 549 companies yielded results.

**Root cause:** The original recommendation estimated ~1,000 credits for 549 companies. Actual usage was 3x higher because: (a) 2 primary titles per company = 2 credits minimum, (b) secondary titles added 4 more credits per company with no primary hits, (c) no early-exit when credits were low.

**Prevention:**
- RULE: Check live credit balance via API before starting a credit-consuming run. Set a hard cap in the script that stops execution at 80% of available credits.

---

## Bigger Picture Lessons

### 1. Ad-hoc scripts are the highest-risk code path

Pipeline F modules have proper error handling, rate limiting, circuit breakers, and tests. Ad-hoc scripts in `scripts/` have none of these. Every bug in FM-BUILD-V1 came from ad-hoc code, not from pipeline infrastructure. When we write one-shot scripts, we drop every safety measure we built into the pipeline.

**Action:** One-shot scripts must follow the same discipline as pipeline code: pilot first, explicit error handling, parallel execution via semaphore, and provider param verification against `src/integrations/`.

### 2. "Available" ≠ "Ratified" ≠ "Working"

Three different levels of provider readiness got conflated:
- **Available:** listed in MCP bridge / settings.py (Prospeo — available but deprecated)
- **Ratified:** in the waterfall ratification doc (Hunter — ratified but dead API key)
- **Working:** returns data on a live API call (Leadmagic email — actually works)

Only "working" matters for execution. The other two are governance artifacts that can be stale.

**Action:** Before any enrichment run, health-check every provider in the waterfall with a single live call. Report which are working, not which are ratified.

### 3. Credit accounting must be real-time, not snapshot

We operated on stale credit snapshots throughout:
- Leadmagic: 2,494 (stale from 2026-03-25, actual was 4,324)
- ContactOut search: 2,447 (stale, actual was 0 after Stage 2)
- Hunter: "unknown" (actually dead — 401)

**Action:** Every session that touches external APIs should start with a live credit check on every active provider. Write results to ceo_memory with timestamp.

### 4. The peer review system works — when it's not bypassed

Aiden caught every material issue: off-target titles, yield math errors, Leadmagic AU mobile 0%, ContactOut stats vs usability gap, stale numbers, missing CSV columns. The system works when both bots check each other's work.

What didn't work: Elliot skipping pre-production pilots, reporting unverified numbers, and silently swallowing API errors. These bypassed the peer review system by presenting "done" before work was actually verified.

### 5. ContactOut's credit model is opaque and fragile

Three separate credit pools (search, email, phone) with no phone-only endpoint. Account-level 403 when any pool hits zero. No API endpoint to check balances (only /v1/stats which reports billing-period allocation, not usability). The enrich endpoint bundles email+phone, gated by email credits.

**Action:** Document ContactOut's credit model explicitly in ceo_memory. Before any ContactOut-heavy run, verify all three pools have sufficient credits via /v1/stats AND a test enrich call.

---

## Cost Accounting

| Item | Credits | $AUD |
|------|---------|------|
| DFS category discovery | 8 calls | $0.81 |
| ContactOut search | 3,043 credits (prepaid) | $0 incremental |
| ContactOut phone (wasted on 400s) | ~82 credits (prepaid) | $0 incremental |
| Leadmagic email | 81 credits | $1.22 |
| Leadmagic pilot calls | 10 credits | $0.15 |
| **Total variable spend** | — | **~$2.18 AUD** |

| Asset | Value |
|-------|-------|
| ContactOut search credits remaining | 0 |
| ContactOut email credits remaining | 0 |
| ContactOut phone credits remaining | 214 (stranded) |
| Leadmagic credits remaining | ~4,233 |

---

## Deliverable

81 Facilities Managers across 54 AU companies in 9 sectors. Each record has: name, title, seniority, company, parent company, sector, state, employer type, location, LinkedIn URL, verified email.

No phone numbers (ContactOut locked, Leadmagic mobile 0% AU).

File: `scripts/output/fm_prospects_81.csv`
