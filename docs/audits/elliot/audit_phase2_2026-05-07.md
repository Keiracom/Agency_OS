# audit_phase2_elliot.md

**Author:** Elliottbot (callsign ELLIOT)
**Compiled:** 2026-05-07
**Worktree:** `/home/elliotbot/clawd/Agency_OS` @ `33911164`
**Format:** Phase 2 follow-up. Facts and locations only. No opinions.

---

## TASK E1 — Full Test Suite Run

**Command:** `pytest tests/ -m "not live" --tb=short`
**Run started:** 2026-05-07 22:50 UTC
**Run duration:** 217.60s (3 min 37 s)
**Logfile:** `/tmp/elliot_phase2_pytest.log`

### Final summary line (verbatim)

```
= 25 failed, 3385 passed, 28 skipped, 4 deselected, 26 xfailed, 185 warnings, 16 errors in 217.60s (0:03:37) =
```

| Outcome | Count |
|---|---|
| passed | **3385** |
| failed | **25** |
| errors (collection / fixture) | **16** |
| skipped | **28** |
| deselected | 4 |
| xfailed (expected fail) | 26 |
| warnings | 185 |
| **Total executed** | **3480** (3385 + 25 + 28 + 26 + 16 errors counted separately) |

### Failures by file (25 failed)

- `tests/integrations/test_dncr_client.py` — **13 failures** (entire file): TestHappyPathRegistered, TestHappyPathNotRegistered, TestMissingApiKey, TestNetworkTimeout, TestHTTP500, TestHTTP429, TestInvalidJSON, TestCacheHit, TestCacheExpiry, TestDegradedNotCached, TestPhoneNormalisation, TestNeverRaises (×2)
- `tests/orchestration/flows/test_free_enrichment_flow.py::test_flow_skips_promote_when_disabled` — 1
- `tests/test_campaign_executor.py::test_sequence_step_not_found_raises` — 1
- `tests/test_engines/test_closer.py::test_handle_meeting_request_intent` — 1
- `tests/test_flows/test_directive_196_resilience.py::test_enrich_tier_failure_continues` — 1
- `tests/test_services/test_cis_negative_signals.py` — 2 (TestSDKBrainNegativeSignals + TestNegativeSignalsDecreaseWeights)
- `tests/test_siege_enhancements.py` — 3 (TestAustralianLeadNoApolloFallback ×2 + TestMockDataEnrichment)
- `tests/unit/test_rescore_engine.py` — 3 (test_promotes_qualifying_reject, test_dry_run_makes_no_db_writes, test_rescore_result_counts_correct)

### Errors (16 — all collection/import errors)

- `tests/test_engines/test_scout.py` — **15 errors** (entire file fails to collect): TestScoutEngineProperties, TestEnrichmentValidation ×5, TestCacheBehavior ×2, TestWaterfallTiers ×2, TestBatchEnrichment, TestEnrichmentMerge ×2, TestHelperFunctions ×2
- `tests/test_siege_enhancements.py::TestAustralianLeadNoApolloFallback::test_au_lead_uses_siege` — 1

**Notable patterns:**
1. `tests/integrations/test_dncr_client.py` fully red — DNCR (Do Not Call Register) client likely missing or signature changed
2. `tests/test_engines/test_scout.py` fully red — collection error suggests `src/engines/scout.py` import broke (Phase 1 audit noted my session removed `siege_waterfall` constructor param + property; tests still expect old signature)
3. `tests/test_siege_enhancements.py` red — same root cause (deleted `siege_waterfall.py` integration)
4. `tests/unit/test_rescore_engine.py` 3 failures — rescore engine assertions drifted

---

## TASK E2 — Revenue Path Trace

Three chains: **Email**, **LinkedIn**, **Voice**. Every file + function in order. Each step marked `EXISTS` / `BROKEN` / `MISSING`.

### Chain 1 — Email Outreach

| # | File | Function / Symbol | Status | Notes |
|---|---|---|---|---|
| 1 | `src/api/routes/approvals.py` | `approve_approval` (POST `/approvals/{id}/approve`) | EXISTS | Approves draft message; flips `approval_queue` row |
| 2 | `src/orchestration/flows/hourly_cadence_flow.py` | `hourly_cadence_flow` → instantiates `OutreachDispatcher` (line 131) | EXISTS | Reads `campaign_lead_messages` where `status='approved'` |
| 3 | `src/outreach/dispatcher.py` | `OutreachDispatcher.dispatch()` (line 106) | EXISTS | Pipeline: timing → compliance → rate → send → record |
| 4 | `src/outreach/safety/timing_engine.py` | `TimingEngine.check()` | EXISTS | Window/quiet-hours gate |
| 5 | `src/outreach/safety/compliance_guard.py` | `ComplianceGuard.check()` | EXISTS | Suppression + DNCR-style check |
| 6 | `src/orchestration/tasks/outreach_tasks.py` | `outreach_tasks` (line 275: `email_engine.send(...)`) | EXISTS | JIT-validates client/campaign/lead before calling engine |
| 7 | `src/engines/email.py` | `EmailEngine.send` (line 120) | **BROKEN** | Calls `self.salesforge.send_email(...)` at line 335 |
| 8 | `src/engines/email.py` | `EmailEngine.salesforge` property (line 115) | **BROKEN** | `if self._salesforge is None: raise NotImplementedError("dead path: removed in PR-A #593")` |
| 9 | `src/integrations/salesforge.py` | `SalesforgeClient`, `get_salesforge_client` | **MISSING** | File deleted in PR-A #593. Import at email.py L63 is commented out: `# from src.integrations.salesforge import SalesforgeClient, get_salesforge_client` |
| 10 | `mcp__salesforge__*` (MCP server) | `add_leads`, `create_campaign`, `send_email` (implicit via campaign), `list_campaigns`, `pause_campaign`, `resume_campaign`, `list_domains`, `get_warmup_status`, `get_campaign_stats` | EXISTS (MCP) | MCP bridge exists; no Python integration calls it |
| 11 | API key — `SALESFORGE_API_KEY` | env var | **BROKEN** | Status `dead_401` per `elliot_internal.api_keys_ledger`. `last_verified=NULL`. Note: "Add to Railway if outreach runs on Railway. Currently Vultr-only." |
| 12 | Reply ingestion — `src/api/routes/outreach_webhooks.py` | webhook handler | EXISTS | Inbound email replies parsed & classified — never received any (`replies` table = 0 rows) |
| 13 | Persistence: `public.campaign_lead_messages.sent_at` | column | EXISTS | All 113 rows currently `sent_at=NULL`, `status='draft'` (see E3) |

**Summary:** Email chain is **BROKEN at step 7–9** (the `EmailEngine.send` → `salesforge.send_email` path). Even with a key, the Python integration file does not exist; only the MCP shim does. No fallback to Resend (Resend file `src/integrations/resend.py` also MISSING).

**Resend status:** `src/integrations/resend_client.py` EXISTS (file present; original audit row claiming `resend.py` MISSING was a filename-convention error — credit Aiden's catch). `RESEND_API_KEY` is `live` in ledger. `agencyxos.ai` domain verification failed per session memory. Resend is not currently wired into the email outreach chain — the email engine (`engines/email.py`) calls `salesforge.send_email()`, not Resend; Resend is used by transactional/reply paths (api/routes/email.py, webhooks.py, reply_tasks.py).

### Chain 2 — LinkedIn Outreach

| # | File | Function / Symbol | Status | Notes |
|---|---|---|---|---|
| 1 | `src/api/routes/approvals.py` | `approve_approval` | EXISTS | Same approval entry as email |
| 2 | `src/orchestration/flows/hourly_cadence_flow.py` | dispatcher invocation | EXISTS | |
| 3 | `src/outreach/dispatcher.py` | `OutreachDispatcher.dispatch(touch={'channel':'linkedin'})` | EXISTS | Routes channel to unipile branch |
| 4 | `src/outreach/safety/linkedin_account_state.py` | `LinkedInAccountState` FSM | EXISTS (soft-imported) | May not be merged — try/except at dispatcher L43-47 |
| 5 | `src/engines/linkedin.py` | `LinkedInEngine.connect`, `send_message` | EXISTS | Imports `UnipileClient, get_unipile_client` from `src/integrations/unipile.py` (line 62) |
| 6 | `src/integrations/unipile.py` | `UnipileClient`, `get_unipile_client` | EXISTS | 25,789 bytes, last modified Mar 11 |
| 7 | `mcp__unipile__*` (MCP server) | `send_connection`, `send_message`, `withdraw_invitation`, `list_connections`, `get_account_status`, etc. | EXISTS (MCP) | |
| 8 | API key — `UNIPILE_API_KEY` | env var | **BROKEN** | Status `dead_401` per `api_keys_ledger`. `last_verified=NULL`. Note: "Add to Railway if LinkedIn outreach runs on Railway." |
| 9 | LinkedIn DSN credentials per client — `public.client_linkedin_credentials` | table | EXISTS | Table present in DB (per Phase 1 audit) |
| 10 | Outbound queue — `public.linkedin_action_queue` | table | EXISTS but EMPTY | 0 rows |
| 11 | Persistence — `public.linkedin_connections` | table | EXISTS but EMPTY | 0 rows |

**Summary:** LinkedIn chain is **EXISTS-but-BROKEN at step 8**. Code is present and importable; integration file exists. **The blocker is the API key (`dead_401`)**. No code-level deletions on this chain — purely a credentials/ops fix to unblock.

### Chain 3 — Voice Outreach

| # | File | Function / Symbol | Status | Notes |
|---|---|---|---|---|
| 1 | `src/api/routes/approvals.py` | approval | EXISTS | |
| 2 | `src/orchestration/flows/voice_flow.py` | `voice_flow` Prefect flow | EXISTS | Active flow; line 417 imports `get_elevenagents_client` |
| 3 | `src/integrations/elevenagents_client.py` | `ElevenAgentsClient`, `get_elevenagents_client` | EXISTS | 22,413 bytes, last modified May 7 |
| 4 | `ElevenAgentsClient.__init__` (line 139) | constructor | **BROKEN-by-naming** | `self.api_key = api_key or settings.elevenlabs_api_key` → reads `ELEVENLABS_API_KEY` (status: `unknown` in ledger), NOT `ELEVENAGENTS_API_KEY` |
| 5 | `src/engines/voice.py` | `VoiceEngine` | **MISSING** | Referenced in `outreach_tasks.py:43` import is commented out: `# from src.engines.voice import VoiceEngine` ("DEPRECATED: Vapi voice engine removed 2026-02-25") |
| 6 | `src/integrations/vapi.py` | `VapiClient` | EXISTS-DEPRECATED | 21,798 bytes, last modified May 3. Status `deprecated` in ledger. Voice flow does not call it. |
| 7 | `mcp__vapi__*` (MCP server) | call/transcript tools | EXISTS (MCP) but DEPRECATED | |
| 8 | API key — `ELEVENLABS_API_KEY` | env var | **UNKNOWN** | Status `unknown` in ledger, `last_verified=NULL` |
| 9 | API key — `ELEVENAGENTS_API_KEY` | env var | not in ledger | ARCHITECTURE.md §4 lists ElevenAgents as LIVE; key not tracked in `api_keys_ledger` |
| 10 | Telnyx for AU PSTN — `src/integrations/telnyx_client.py` | `TelnyxClient`, `get_telnyx_client` | EXISTS | 17,716 bytes, Bearer-auth via `settings.telnyx_api_key` / `os.getenv("TELNYX_API_KEY")`. Active Python caller: `src/engines/sms.py` only. **NOT consumed by `voice_flow.py`** — voice flow imports only `elevenagents_client`, so no PSTN dial-out is wired into the voice chain. `TELNYX_API_KEY` status `unknown` in ledger. (Original audit row claiming `telnyx.py` MISSING was a filename-convention error — credit Aiden's catch.) |
| 11 | `src/integrations/twilio*.py` | any Twilio client | **MISSING** | No twilio-named file exists in `src/integrations/`. `TWILIO_AUTH_TOKEN` status `live` in ledger but no Python caller. Per session memory: Twilio replaced by Telnyx. |
| 12 | Persistence — `public.voice_calls` | table | EXISTS but EMPTY | 0 rows |
| 13 | Persistence — `public.voice_call_context` | table | EXISTS but EMPTY | 0 rows |

**Summary:** Voice chain is **MISSING the engine layer** (`src/engines/voice.py` deleted) and the **PSTN carrier integration** (`src/integrations/telnyx.py` and `src/integrations/twilio.py` both MISSING). The Conversational AI vendor client (`elevenagents_client.py`) exists but reads the wrong env var (`elevenlabs_api_key` not `elevenagents_api_key`). Voice flow imports the client at line 417 but the chain has no PSTN dial-out, no engine wrapper, and an unverified key.

### Cross-cutting status — files MISSING that the revenue path imports or references

| Missing file | Referenced by |
|---|---|
| `src/integrations/salesforge.py` | `src/engines/email.py` (commented) |
| `src/integrations/twilio*.py` | no Python caller (replaced by Telnyx) |
| `src/engines/voice.py` | `src/orchestration/tasks/outreach_tasks.py` (commented L43) |

**Files that exist but were originally mis-reported as missing in earlier draft (corrected here):**

| File | Status | Notes |
|---|---|---|
| `src/integrations/resend_client.py` | EXISTS | Used by transactional / reply / webhook paths, not by outreach email engine |
| `src/integrations/telnyx_client.py` | EXISTS | Used by `src/engines/sms.py`, NOT wired into voice flow |

---

## TASK E3 — Pipeline End-to-End Status

**Question:** Has a single prospect ever gone through the full pipeline from discovery to outreach in a real (non-test, non-mock) run?

**Answer: NO.** Evidence below.

### Database evidence (single run, queried 2026-05-07)

| Stage | Table | Row count | Notes |
|---|---|---|---|
| Discovery (Stage 1) | `public.business_universe` | **8,643** | Real domains discovered via Google Maps / DataForSEO |
| Pipeline pool | `public.lead_pool` | **429** | Real domains promoted to pool |
| Lead conversion | `public.leads` | **468** | Real leads (mix of campaigns) |
| Campaign linkage | `public.campaign_leads` | **77** | Real lead-to-campaign assignments |
| Message drafts | `public.campaign_lead_messages` | **113** | All `status='draft'`, all `sent_at=NULL`. Single batch on 2026-03-25 09:00 UTC. Channels: linkedin=54, voice=53, email=6. |
| Campaigns | `public.campaigns` | **9** | Includes "Demo Campaign", "[TEST] Live Test", "E2E Test Campaign Jan 7", "Sydney Alpha", "Ignition", "Australian B2B Outreach" — mix of test seeds and real campaigns |
| **Sends** | `public.campaign_sends` | **0** | **Zero rows. No outbound has been recorded.** |
| **Outreach telemetry** | `public.outreach_telemetry` | **0** | Zero |
| **Replies** | `public.replies` | **0** | Zero |
| **LinkedIn actions queued** | `public.linkedin_action_queue` | **0** | Zero |
| **LinkedIn connections made** | `public.linkedin_connections` | **0** | Zero |
| **Voice calls placed** | `public.voice_calls` | **0** | Zero |
| **Lead outreach history** | `public.lead_outreach_history` | **0** | Zero |
| **Meetings booked** | `public.meetings` | **0** | Zero |
| **Demos booked** | `public.demo_bookings` | **0** | Zero |
| **Deals created** | `public.deals` | **0** | Zero |
| **Sales pipeline** | `public.sales_pipeline` | **0** | Zero |
| **Revenue attribution** | `public.revenue_attribution` | **0** | Zero |
| CIS run log | `public.cis_run_log` | **5** | Scoring has run 5 times |
| Enrichment raw responses | `public.enrichment_raw_responses` | **0** | Zero captured (note: GOV-8 violation flagged in prior audits) |

### Furthest a real prospect has reached

A real prospect (non-test) has gone:

```
business_universe (discovered) → lead_pool (promoted) → leads (qualified) →
campaign_leads (assigned to campaign) → campaign_lead_messages (DRAFT generated)
                                                                    ↑
                                                          STOPS HERE — no row
                                                          has ever transitioned
                                                          status='draft' → 'sent'
```

The earliest and latest `campaign_lead_messages.created_at` are both within a 5-minute window on **2026-03-25 08:57–09:02 UTC**. That single batch produced 113 drafts and nothing has been generated since (~6 weeks ago). All drafts remain in `status='draft'` with `sent_at=NULL`, `approved_at=NULL`.

### Conclusion (factual, not opinion)

- **No email has ever been sent through the production code path.**
- **No LinkedIn message, connection, or invitation has ever been sent.**
- **No voice call has ever been placed.**
- **No reply, meeting, demo, deal, or revenue row exists.**
- The pipeline has demonstrably executed Stages 1–~10 (discovery → message generation), but Stage 11 (outbound dispatch) has **zero recorded executions** in production.

---

## End of audit_phase2_elliot.md

Facts and locations only per Dave's spec. Pytest summary captured in §E1 above.
