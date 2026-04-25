# Outreach Layer Audit — 2026-04-25

**Author:** AIDEN
**Peer-reviewed by:** ELLIOT
**Scope:** read-only audit of `src/engines/email.py`, `linkedin.py`, `sms.py`, `closer.py`, `src/services/voice_post_call_processor.py`, `src/orchestration/flows/outreach_flow.py`, plus `prefect.yaml`. ~6,800 lines.
**Lens:** the same lens that produced the BU+CIS audit (`docs/MANUAL.md` directive `CD-PLAYER-V1`, dual-scorer load-bearing finding). Separate "literal write happens" from "it does the right thing."
**Predecessor:** companion to BU+CIS audit (14 gaps + dual-scorer code-debt). Outreach is the data-source for CIS — its readiness gates Stage 8 going live.

---

## 1. Verdict

The Manual's wording **"Stage 8 WIRED, not yet live-tested"** is **mostly accurate for engines** and **softer than reality for orchestration**.

- **Engines (email, LinkedIn, SMS, voice closer, voice post-call):** real third-party SDK calls, not stubs, not mocks. Compliance gates present. CIS hooks fire on real send/reply events.
- **Orchestration:** `outreach_flow.py` is wired for email/LinkedIn/SMS only. Voice runs as a **separate** Prefect flow (`voice_outreach_flow`). Both are paused in `prefect.yaml` — schedules and entrypoints exist but `paused: true` until two unpause conditions land.
- **Cross-cutting:** lighter than BU+CIS findings — no 0%-population disasters. The instrumentation actually fires. Gaps are orchestration-shape: voice not in the unified flow, no global cost ceiling, thin live-test coverage.

This audit downgrades one gap from the first read (OUT-2, scheduling) and confirms the others.

---

## 2. Per-Channel Findings

### 2.1 Email (`src/engines/email.py`, 879 lines)

| Question | Finding | Evidence |
|---|---|---|
| Real API call? | Yes — Salesforge SDK | `email.py:332` `result = await self.salesforge.send_email()` |
| Stubbed/mocked? | No. Singleton `get_email_engine()` fetches real client | `email.py:830`, integration at `email.py:114` |
| Error handling | try/except with metadata; no per-engine retry (delegated to orchestration) | `email.py:399-408` |
| Compliance gating | Hard block — Directive 057 physical address validation | `email.py:173-189` (no `client.branding.address` → no send) |
| Kill-switch | Indirect: Salesforge client singleton can be disabled at integration layer; no per-engine flag | n/a |
| CIS hook | Post-success, non-blocking | `email.py:644-665` (status `sent` written at line 636, FK `business_universe_id` set) |
| DB writes | Activity row with full HTML body, template tracking, A/B test IDs, `client_id` + `campaign_id` + `lead_id` | `email.py:613-642` |

**Verdict:** production-ready. No load-bearing gaps.

### 2.2 LinkedIn (`src/engines/linkedin.py`, 1,278 lines)

Migration from HeyReach → Unipile is complete (verified by import paths; no dead HeyReach references found).

| Question | Finding | Evidence |
|---|---|---|
| Real API call? | Yes — Unipile API | `linkedin.py:496-508` (`send_invitation`, `send_message`) |
| Stubbed/mocked? | No. Singleton `get_linkedin_engine()` returns real Unipile client | `linkedin.py:1219`, init at `linkedin.py:222` |
| Error handling | try/except + Redis-only quota fallback on Unipile API failure | `linkedin.py:559-568`, `linkedin.py:285-292` |
| Compliance gating | Combined manual + auto activity quota check; weekend reduction (Sat 50% / Sun 0%) | `linkedin.py:451-474`, `linkedin.py:175-200` |
| Optimal-window gate | Weekday 9-11 AM and 1-2 PM only; outside-window returns `scheduled`, not `sent` | `linkedin.py:394-427`, Sunday pause at `linkedin.py:441-449` |
| CIS hook | Post-success, non-blocking | `linkedin.py:1191-1212` |
| DB writes | Activity row with full message body, links extracted, template + A/B IDs | `linkedin.py:1162-1186` |

**Verdict:** wired. **Watch:** the `scheduled` return status (vs `sent`) needs verified handling on the orchestration side — re-queue vs skip semantics not yet validated end-to-end.

### 2.3 SMS (`src/engines/sms.py`, 572 lines)

| Question | Finding | Evidence |
|---|---|---|
| Real API call? | Yes — Telnyx (post-Twilio migration per Directive #167 P3) | `sms.py:204` `result: dict[str, Any] = await telnyx.send_sms()` |
| Stubbed/mocked? | No. `get_telnyx_client()` returns real singleton | `sms.py:200-202` |
| Error handling | APIError raised on failure; generic exception catch downstream; no per-engine retry | `sms.py:211-216`, `sms.py:279-287` |
| Compliance gating | DNCR cached check for +61 numbers — blocks immediately if `lead.dncr_checked` and `lead.dncr_result` set | `sms.py:166-196`, fresh check at `sms.py:208` if not cached |
| Kill-switch | None at engine level. Soft rate-limit gate only | `sms.py:150-164` |
| CIS hook | Post-success, non-blocking | `sms.py:511-531` |
| DB writes | Activity row with body, links, FKs | `sms.py:481-505` |

**Verdict:** wired. **Watch:** DNCR caching depends on enrichment populating `lead.dncr_checked` + `lead.dncr_result`. If enrichment hasn't run, fresh check on every send (acceptable cost, but assumes upstream behaviour).

### 2.4 Voice Closer (`src/engines/closer.py`, 1,087 lines)

Inbound-reply classifier (intent detection), not the outbound call initiator.

| Question | Finding | Evidence |
|---|---|---|
| Real API call? | Yes — Anthropic Claude for intent classification | `closer.py:179` `classification = await self.anthropic.classify_intent()` |
| Stubbed/mocked? | No. Real client | `closer.py:1049`, init at `closer.py:105` |
| Error handling | try/except non-blocking; low-confidence flagged for review (`< 0.6`) | `closer.py:268-275`, `closer.py:190-197` |
| Compliance gating | Unsubscribe propagates to lead_pool via `LeadPoolService.mark_unsubscribed()` (Directive 055) | `closer.py:559-575` |
| Kill-switch | None — processes all replies | n/a |
| CIS hook | `record_als_conversion()` for meeting requests | `closer.py:503-515` |
| DB writes | Activity row with intent + confidence; thread linked via `conversation_thread_id` | `closer.py:419-432` |

**Verdict:** wired for the receive side.

### 2.5 Voice Post-Call (`src/services/voice_post_call_processor.py`, 1,528 lines)

Processes transcripts from completed calls; classifies outcome and writes back to CIS.

| Question | Finding | Evidence |
|---|---|---|
| Real API call? | Yes — Claude Haiku for outcome classification, with rule-based fallback if AI fails | `voice_post_call_processor.py:385`, fallback at `voice_post_call_processor.py:432-589` |
| Compliance gating | Unsubscribe → updates `lead_pool.is_unsubscribed=true` AND adds to `SuppressionService` | `voice_post_call_processor.py:941-971` |
| CIS hook | Writes `conversion_events` AND updates `cis_outreach_outcomes` via `CISService.update_outreach_outcome()` | `voice_post_call_processor.py:1145-1218` |
| Outcome → CIS status mapping | `BOOKED → meeting_booked`, `UNSUBSCRIBE → unsubscribed`, `ANGRY → complained` | `voice_post_call_processor.py:1178-1182` |
| DB writes | `voice_calls` updated, `lead_pool` status updated per outcome | `voice_post_call_processor.py:649-667`, `710-719`, `879-888` |

**Verdict:** wired for the post-call side. **Receives only — does not initiate calls.** Outbound voice initiation lives in `voice_agent_telnyx.py` (out of audit scope) which carries an explicit TODO at line 572: *"Implement Deepgram STT"*. That is an incomplete dependency for live voice outreach.

---

## 3. Orchestration (`src/orchestration/flows/outreach_flow.py`, 1,435 lines)

| Question | Finding | Evidence |
|---|---|---|
| Lead pull | `leads` table joined to `clients`, `campaigns`. Filters: `status=in_sequence`, active subscription, `credits_remaining > 0`, campaign active | `outreach_flow.py:461-496` |
| Schedule | Prefect `@flow` declared with `ConcurrentTaskRunner(max_workers=10)`. Schedule lives in `prefect.yaml` (see §4) | `outreach_flow.py:1136-1143` |
| Spend cap (global) | **Missing** — only per-channel rate limits (email 50/day, LinkedIn 17/day configurable, SMS 100/day). Per-customer gated only by `client.credits_remaining > 0` | n/a |
| Admission control | Soft gates: halts campaign if Hot+Warm < 5%, verified_email < 80%, DM identified < 60%. No "don't touch this domain again for N days" rule | `outreach_flow.py:78-214`, `outreach_flow.py:203-214` |
| State changes | CIS channel performance updated per (campaign, channel) at flow finish. Lead status flips happen inside engine sends. Campaign itself not updated | `outreach_flow.py:1333-1382` |
| Channel coverage | Email + LinkedIn + SMS dispatched per lead. **Voice absent** — no `send_voice_outreach_task()` in this flow | `outreach_flow.py:1243-1330` |

**Load-bearing finding:** voice is dispatched by a **separate** flow (`voice_outreach_flow`), not the unified outreach pipeline.

---

## 4. Prefect Schedules (`prefect.yaml`)

Verified line-by-line per Elliot's pointer:

```
prefect.yaml:25-37  — pause comments for outreach-flow, voice-outreach-flow,
                       reply-recovery-flow, pattern-learning-flow, etc.
prefect.yaml:104-115 outreach-flow         — paused: true
                       entrypoint hourly_outreach_flow
                       batch_size: 50
                       Unpause when: campaign approval framework live
prefect.yaml:121-132 voice-outreach-flow   — paused: true
                       entrypoint voice_flow.py:voice_outreach_flow
                       cron: "*/30 9-20 * * 1-6"
                       concurrency_limit: 1
                       Unpause when: Vapi/Telnyx integration deployed +
                                    TCP Code compliance verified
```

**Implication:** the schedule is *defined and intentionally paused*, not absent. Original audit's OUT-2 ("scheduling unclear") downgrades to a soft gap. The work to unpause is configuration + dependency-readiness, not flow design.

---

## 5. Cross-Cutting

### 5.1 TODO / FIXME / Stubs
- `src/engines/voice_agent_telnyx.py:572` — `# TODO: Implement Deepgram STT` (outside this audit's read scope, but blocks the voice unpause condition).
- No other concerning TODO/FIXME markers in scope.

### 5.2 Deprecated Imports
None. HeyReach references in `linkedin.py` are comments only, not imports.

### 5.3 Test Coverage
- `tests/test_engines/test_email.py` — `MockSalesforgeClient` (mocked API).
- `tests/test_engines/test_linkedin.py`, `test_sms.py`, `test_closer.py` — exist (assume mocked APIs).
- `tests/live/test_outreach_live.py` — live integration test for email only.

**Gap:** live-integration parity for LinkedIn / SMS / voice is missing.

---

## 6. Cross-Reference to BU+CIS Audit (companion finding)

The two audits together expose a consistent half-loop pattern:

| Layer | Built? | Wired to live API? | Scheduled? | Closed-loop? | Load-bearing gap |
|---|---|---|---|---|---|
| Pipeline → BU | yes | yes | yes | **no** (no backlog driver) | re-entry missing |
| BU instrumentation | yes | n/a | n/a | **partial** (7 dormant columns 0%-populated) | `filter_reason`, `discovery_batch_id`, `abn_matched`, `converted_verticals` |
| CIS outcome capture | yes | yes (idle pending outreach) | yes (Sun 03:00) | **partial** (dual-scorer: `engines/scorer.py` reads weights, `pipeline/stage_4_scoring.py` does not) | dual-scorer reconciliation |
| Outreach engines | yes | yes | yes (paused intentionally) | yes per-channel | none critical |
| Outreach orchestration | yes | yes | yes (paused) | **partial** (voice on separate flow, no global spend cap) | OUT-1, OUT-3 |

The pattern repeats across BU, CIS, and outreach: schemas and call sites exist; the integrative behaviour is incomplete.

---

## 7. Fix List (revised, peer-reviewed)

| ID | Severity | Fix | Rationale |
|---|---|---|---|
| OUT-1 | HIGH | Wire voice into the unified `outreach_flow` OR formalise the split and ensure CIS reconciles cross-flow channel performance | Today voice outcomes write to CIS via the post-call processor, but the unified channel-performance view in `outreach_flow.py:1333-1382` won't see them. Half-loop pattern repeats. |
| OUT-2 | LOW (downgraded) | Document outreach-flow + voice-outreach-flow unpause conditions in `docs/MANUAL.md` (currently only in `prefect.yaml` comments) | Schedules exist; the gap is operator-readable documentation. |
| OUT-3 | CRITICAL | Add per-domain + per-customer spend cap to `outreach_flow` as a *gate-as-code* (GOV-12), not a comment | Same defect class as the $73 AUD CD Player budget incident (PR #407). Per-channel rate limits ≠ per-customer ceiling. A bug could blow credits before per-channel limits hit. |
| OUT-4 | HIGH | Resolve `src/engines/voice_agent_telnyx.py:572` Deepgram STT TODO | Hard blocker on voice-outreach-flow unpause condition (TCP Code compliance presumes working STT). |
| OUT-5 | MEDIUM | Verify `outreach_flow` correctly handles LinkedIn `scheduled` return status (re-queue vs skip) | Caller-side semantics not validated. If `scheduled` is silently treated as `sent`, optimal-window enforcement leaks. |
| OUT-6 | MEDIUM | Build live-integration test parity (LinkedIn / SMS / voice — one each, mockable APIs) | Manual claims "not yet live-tested" — current test coverage agrees only for email. |

Sequencing once unpause-readiness is met:
1. OUT-3 (spend cap) — must land before any unpause.
2. OUT-1 (voice unification) — before voice flow unpauses.
3. OUT-4 (Deepgram STT) — same.
4. OUT-5 — before LinkedIn flow runs at scale.
5. OUT-6 — before any cohort-scale outreach.
6. OUT-2 — anytime; doc-only.

---

## 8. Open Questions (for next session)

- `voice_flow.py:voice_outreach_flow` was not in this audit scope. Trace: does it consume `voice_agent_telnyx.py` directly, or have its own initiator path?
- Where is `client.credits_remaining` decremented? If only at billing layer and not inside `outreach_flow`, the per-customer gate is stale relative to in-flight sends — relevant to OUT-3.
- The `campaign approval framework` referenced in the unpause condition for `outreach-flow` — is this the same pending_approval/approved enum addition (commit `5d2c35a9`)? If yes, unpause is closer than the Manual implies.

---

## 9. Provenance

- Read-only audit. AUD 0 spend.
- Code reads via `Read` tool.
- Schema/data verifications via Supabase MCP bridge against project `jatzvazlbusedwsnqxzr`.
- `prefect.yaml` verifications via `grep` after Elliot's pointer.
- Peer-review concur: Elliot 2026-04-25.
- Companion: `docs/MANUAL.md` directive `CD-PLAYER-V1` (BU+CIS audit, same session).
