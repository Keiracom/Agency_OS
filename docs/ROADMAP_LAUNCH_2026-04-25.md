# Agency OS Launch Roadmap

Generated: 2026-04-25
Authors: ELLIOT + AIDEN (dual-concur)
Source: BU+CIS audit (14 gaps) + Outreach audit (6 gaps) + session findings
Total items: 30

---

## CRITICAL (blocks launch)

| # | Item | Source | Owner | Blocked on |
|---|------|--------|-------|------------|
| C1 | Per-domain + per-customer spend cap in outreach_flow.py | OUT-3 | ORION | — |
| C2 | Voice channel integration into unified outreach flow | OUT-1 | TBD | — |
| C3 | Deepgram STT implementation in voice_agent_telnyx.py:572 | OUT-6 | TBD | — |
| C4 | BU backlog driver flow (free-mode now, paid-mode post-revenue) | BU audit | ORION S2 | S1 complete |
| C5 | Stage 1 BU-exclusion query — filter by pipeline_status | BU audit | TBD | — |
| C6 | DFS top-up ($15-20 USD) — blocks all pipeline validation | Ops | Dave | Dave action |

## HIGH (launch quality)

| # | Item | Source | Owner | Blocked on |
|---|------|--------|-------|------------|
| H1 | filter_reason writes on every gate exit (99.97% NULL) | BU audit | ORION S1 | — |
| H2 | stage_completed_at writes (0% populated) | BU audit | ORION S1 | — |
| H3 | ABN match sweep (abn_matched 0.05% -> ~40%) | BU audit | ORION S1 | — |
| H4 | Stage 0->1 trigger fix (5,022 phantom queue) | BU audit | ORION S3 | S1 complete |
| H5 | rescore_engine CIS reconciliation (dual-scorer code debt) | CIS audit | ORION S4 | S1 complete |
| H6 | LinkedIn 'scheduled' return status handling in outreach_flow | OUT-5 | TBD | — |
| H7 | Live integration tests for LinkedIn/SMS/voice (1 each) | OUT-4 | TBD | — |
| H8 | Suppression cross-check in paid_enrichment.py | BU audit | ORION S1 | — |
| H9 | Choose canonical scoring engine (pipeline vs engine) — architecture decision | CIS audit | Dave decision | — |
| H10 | ORION/ATLAS inbox-watcher inotify edge case — add -e moved_to | Session finding | TBD | — |

## MEDIUM (system health)

| # | Item | Source | Owner | Blocked on |
|---|------|--------|-------|------------|
| M1 | discovery_batch_id population (0% today) | BU audit | ORION | — |
| M2 | Signal decay — re-scoring stale prospects (14/60/180 day cadence) | BU audit | TBD | H5 |
| M3 | Provider rotation on enrichment failure | BU audit | TBD | — |
| M4 | Dead-domain cleanup (DNS re-check) | BU audit | TBD | — |
| M5 | converted_verticals population (CIS outcome feedback) | BU audit | TBD | Outreach live |
| M6 | last_enriched_at reliability fix | BU audit | ORION | — |
| M7 | Outreach unpause conditions documented in MANUAL.md | OUT-6b | TBD | — |
| M8 | Prefect 3.x Deployment.build_from_flow migration | CD Player | TBD | — |
| M9 | campaign_leads junction table — verify populate state | Aiden A4 | TBD | — |
| M10 | BU readiness threshold instrumentation (Coverage/Verified/Outcomes/Trajectory) | Aiden A5 | TBD | — |
| M11 | write_manual_mirror.py — auto-update on save signals OR block stale mirror | Aiden A1 | TBD | — |

## LOW (post-launch)

| # | Item | Source | Owner | Blocked on |
|---|------|--------|-------|------------|
| L1 | Customer feedback loop (CIS->BU corrections) | BU audit | TBD | Outreach live |
| L2 | Session-level memory dedup for listener | Listener tune v1 | TBD | — |
| L3 | Enforcer clone-aware check (skip Rule 2 for ATLAS/ORION) | Session finding | TBD | — |
| L4 | Re-insert 367 soft-deleted non-AU domains when C5 ships | BU recovery | TBD | C5 |
| L5 | Outreach unpause checklist consolidation (prefect.yaml comments -> operator doc) | Aiden A6 | TBD | — |

## IN-FLIGHT

| # | Item | Status | Owner |
|---|------|--------|-------|
| IF1 | ORION: BU Closed-Loop S1 (H1, H2, H3, H8) | Running | ORION |
| IF2 | ATLAS: Phase 2.1 dashboard wiring | COMPLETE (377721b9) | ATLAS |
| IF3 | Outreach audit doc | MERGED (PR #409) | Aiden |

## BLOCKED ON DAVE (external actions)

| # | Item | Type |
|---|------|------|
| B1 | DFS top-up ($15-20 USD) | Payment |
| B2 | ContactOut API credits | Support ticket |
| B3 | Forager API support ticket | Support ticket |
| B4 | Reacher port 25 (needs dedicated VPS or Oracle Cloud) | Infrastructure |
| B5 | Salesforge API key refresh | Credential |
| B6 | Unipile API key refresh | Credential |
| B7 | Stripe key rotation | Credential |

---

## Sequencing

**Phase 2.1** (ATLAS — in-flight): Dashboard wiring to real BU data. COMPLETE.

**BU Closed-Loop Engine** (ORION — 4 substeps):
- S1: Instrumentation writes (H1, H2, H3, H8) — IN PROGRESS
- S2: Backlog driver flow (C4) — after S1
- S3: Stage 0->1 trigger fix (H4) — after S1
- S4: rescore_engine CIS reconciliation (H5) — after S1

**Outreach Hardening** (post-BU-CLE):
- C1 (spend cap), C2 (voice integration), H6 (LinkedIn scheduled), H7 (live tests)

**Demo Build** (parallel, no DFS needed):
- Curated 20-domain seed, IS_DEMO_MODE flag, demo tenant, DEMO MODE banner

**Investor Prep** (parallel):
- Elliot Voice MVP (post-demo)
- Investor rehearsal Q&A pressure-test

**Soft Launch** (post-all-critical):
- Unpause outreach flows
- First 5 founding customers
- CIS starts learning from real outcomes
