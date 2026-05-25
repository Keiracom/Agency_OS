# Customer-Lens Gaps — Impl-Feasibility Notes (Atlas)

**Directive:** KEI-CUSTOMER-LENS-GAPS 2026-05-25 ~1779749200. **Lens:** impl-feasibility on the 7 V1 hard gates.

Short note per gap. Each names the substrate that exists, the architecture work required (ratified or not), and the impl-feasibility verdict.

---

## gap.cost_visibility_per_task — live + retrospective per-task cost view

**Substrate exists:** PR #1137 metering pipeline + PR #1139 Item 1 scoping (cost-attribution wrappers over the 6 MAL primitives).

**Architecture work needed:** `task_id` propagation through every LLM call site. Today PR #1137 is per-tenant; per-task adds a correlation dimension. Three touchpoints:
1. MCP `invoke()` signature in `src/keiracom_system/mcp/server.py` (PR #1136) — add `task_id: str` required kwarg
2. Wrapper `ingest`/`recall` signatures (PR #1134 `src/keiracom_system/memory/wrappers/`) — accept + pass-through to metering
3. Metering pipeline SQL view (PR #1137) — add `task_id` column to attribution events

**Verdict:** FEASIBLE without new architecture ratification. ~50-80 LoC change total + tests. Sequenced behind PR #1139 Item 1 build (which lands the per-MAL-primitive substrate).

**Flag:** task_id source-of-truth needs naming (chat message UUID? bd issue id? Temporal workflow id?). Most likely Temporal workflow id once `temp.middleware` (Layer 5, Orion PR #1150) lands — task IS the workflow.

---

## gap.approval_gate_irreversible — mobile push approval flow

**Substrate:** Cat 19 `ux.add.inline_push_approvals` (V3 per inventory). NONE built.

**Architecture work needed:** push notification infrastructure (gap 7 below). Approval-gate UX requires:
- Tenant approval-policy table (which actions require approval — DDL ops, billing changes, destructive deletes)
- Pending-approval state in agent workflow (Temporal middleware suspends, awaits)
- Notification dispatch on approval-needed (push + email fallback)
- Inline approval action (deep-link → approve/reject → workflow resumes)

**Verdict:** ARCHITECTURE NOT YET RATIFIED. Approval-gate is RATIFIED-CEO in Cat 19 as **V3** (`ux.add.inline_push_approvals`); for V1 the gap is the irreversible-action approval policy + Temporal-suspend pattern. Both depend on `temp.middleware` Layer 5. Not V1 blocker per inventory; V3 target.

**Flag:** V1 mitigation is operator-side — agents do NOT execute irreversible actions without explicit chat-message approval (text-based not push). Document as V1 discipline; V3 ships push.

---

## gap.memory_editing_ui — editable Memory Inspector

**Substrate exists:** Cat 19 `ux.surface.memory_inspector` (V1 or V2 — read-only viewing). Hindsight per-memory delete API confirmed via PR #1130 OpenAPI probe: `DELETE /v1/default/banks/{bank_id}/memories/{memory_id}`. PR #1136 already exposes via Delete MCP tool (Scale tier).

**Architecture work needed:** edit semantics. Hindsight's design pattern per PR #1129 (Viktor's domain mapping) treats observations as evidence-grounded — "refined rather than overwritten — history preserved". So **edit-as-supersede** is the cleaner semantic than in-place mutation:
- User edits memory → MCP layer fires AntiPattern wrapper with `supersedes_memory_id=<old>` per PR #1134
- Old memory remains in history (audit trail preserved); new memory is the surfaced version on next recall
- Customer sees the edit as "updated" but the audit log shows full evolution

**Verdict:** FEASIBLE — Hindsight's existing primitives support this directly. No new architecture ratification. Wrapper exists (AntiPattern with `supersedes_memory_id`); MCP `supersede` tool exposed at Pro+ (PR #1136 tier_router). UI work belongs in Cat 19 Memory Inspector surface; ~150-200 LoC frontend + the supersede-on-edit flow.

**Flag:** in-place mutation NOT supported by Hindsight by design. Customer-facing language must NOT call it "edit" if compliance audit needs the full history — call it "update" or "revise" and surface the prior version in audit view.

---

## gap.self_correction_loop — agent reviews own output before delivery

**Substrate exists:** `temp.async.post_validation` RATIFIED in Cat 5 inventory ("Post-call validation (response shape + citation validity) — ASYNC continuation"). NOT yet built.

**Architecture work needed:** Temporal middleware (Phase A6 Layer 5, Orion PR #1150). The "agent reviews own output" pattern needs:
- Pre-delivery validation hook in middleware (sync or async)
- Validation tool surface (citation check + format check + factual self-consistency)
- Retry policy on validation fail (regenerate vs surface error vs partial result)

**Verdict:** ARCHITECTURE PARTIALLY RATIFIED — `temp.async.post_validation` exists as a row but not as a built component. Belongs to Layer 5 (Orion's Temporal middleware deep-dive PR #1150). Once middleware ships, the validation hook is a small additional tool registration. ~100 LoC inside middleware + per-validator implementation.

**Flag:** Hindsight's reflect endpoint already does citation validation natively per PR #1129 ("Validates citations — only IDs that were actually retrieved can be cited"). So one validator class is FREE on the reflect path. Format + factual checks are net-new work.

---

## gap.style_learning — matches customer writing tone/vocab

**Substrate exists:** Hindsight's observation consolidation (per PR #1130 smoke: 49 ops → 31 new + 13 updated observations in 158s) naturally captures stylistic patterns over time when customer writing is the input. TaskContext wrapper (PR #1134) is the ingest path. Per-tenant scoping via TenantExtension (Orion PR #1132 + #1135) ensures the patterns are customer-specific not cross-tenant.

**Architecture work needed:** EXPLICIT style-vector extraction is OPTIONAL — Hindsight's reflect-with-disposition (Cat 6 deep-dive PR #1149) already shapes responses through bank-level disposition traits (Skepticism/Literalism/Empathy 1-5). For V1, the implicit learning via observation accumulation is sufficient; explicit style modelling is V2 work.

**Verdict:** FEASIBLE FOR V1 via existing primitives — wrap TaskContext ingest around customer messages (already done); recall on reply generation surfaces customer-style patterns. No new architecture ratification needed. V2 explicit style modelling (style-vector per tenant) is a follow-up.

**Flag:** depends on Phase A5 memory backfill (mentioned in dispatch). Without backfill, V1 starts from zero customer context and learns over the first ~N interactions. Operator should document this expectation in onboarding ("the system gets better at your style after the first week of use").

---

## gap.output_format_flexibility — same content as email/Slack/PDF/Notion

**Substrate exists:** Cat 19 `ux.artifacts.file_types_v1` covers V1 INLINE rendering (code/markdown/PDF preview/images/CSV/Word/Excel/JSON/YAML). What's missing: multi-channel DELIVERY (send via email/Slack/Notion API).

**Architecture work needed:** multi-channel send. Per `cust.multi_channel_communication` (RATIFIED — locked tonight per `tonight_decisions_locked.multi_channel_slack_whatsapp_via_composio`):
- Send via email → Resend (existing fleet integration; needs per-tenant FROM domain)
- Send via Slack → Composio (per-customer segregation — depends on Composio POC `Agency_OS-aynv` clearing)
- Send via WhatsApp → Composio
- Send via Notion → Composio
- PDF generation → wkhtmltopdf or weasyprint (small lib choice; in-process)

**Verdict:** ARCHITECTURE RATIFIED at top level (`cust.multi_channel_communication` locked); IMPL gated on Composio per-tenant POC `Agency_OS-aynv` for Slack/WhatsApp/Notion. Email via Resend is FEASIBLE today without Composio. PDF is FEASIBLE today (pure library choice).

**Flag:** PDF/email feasible immediately; Slack/WhatsApp/Notion blocked on `Agency_OS-aynv` POC outcome. Stage V1 delivery: Email + PDF first; Composio-mediated channels after POC clears.

---

## gap.push_notifications_async — APNs + FCM

**Substrate exists:** NONE built. Per `ux.mobile_strategy_web_v1` (v2 lock) V1 is web-only Next.js + React Native parallel; mobile + native push is V1.1.

**Architecture work needed:**
- **V1 substitute:** Web-push (browser-native Notifications API + Service Worker). Per-tenant push-subscription storage in Postgres. ~150-200 LoC + service worker.
- **V1.1 native:** APNs (iOS) + FCM (Android) integration. Either via Composio (if it has push support) OR direct SDK integration (firebase-admin + apns2 Python libs).
- **Both paths:** notification dispatch service triggered by approval-gate events (gap 2 above), task completion, billing alerts.

**Verdict:** ARCHITECTURE PARTIALLY RATIFIED. Web-push for V1 is feasible without new architecture lock (browser-native standard); decision needed on whether V1 ships web-push at all or defers all push to V1.1. Native APNs/FCM is V1.1 (architecture-ratified deferral via `ux.mobile_strategy_web_v1`).

**Flag:** V1.1 mobile schedule depends on `ux.react_native_ingestion_programme` (v2 lock) — fleet RN fluency building. Per my Cat 19 spot-check earlier: 70% RN-Web code reuse claim is realistic, but the 30% native (push, secure storage, OAuth flows) needs RN-specific knowledge the fleet doesn't have yet.

---

## Summary table

| Gap | Verdict | Architecture status | Primary blocker |
| --- | --- | --- | --- |
| 1 cost_visibility_per_task | FEASIBLE | Ratified | Sequenced behind PR #1139 Item 1 build |
| 2 approval_gate_irreversible | NOT-V1 | V3 per inventory | Mitigation: V1 chat-text approval discipline |
| 3 memory_editing_ui | FEASIBLE | Ratified (edit-as-supersede) | UI work (~150-200 LoC frontend) |
| 4 self_correction_loop | FEASIBLE | Row exists, not built | Layer 5 Temporal middleware (Orion PR #1150) |
| 5 style_learning | FEASIBLE V1 | Implicit via existing primitives | Phase A5 backfill aids first-week experience |
| 6 output_format_flexibility | PARTIAL | Email/PDF now; Slack/WhatsApp/Notion gated on Composio POC | `Agency_OS-aynv` POC clearance |
| 7 push_notifications_async | PARTIAL | Web-push V1 substitute feasible; APNs/FCM V1.1 per `ux.mobile_strategy_web_v1` | Decision: ship web-push V1 OR defer all push to V1.1 |

## Three V1 critical-path items recur across the gaps

These keep surfacing across my deep-dive series + this gap check; flag for Elliot aggregation:
- **Composio per-tenant POC `Agency_OS-aynv`** — gates gap 6 (Slack/WhatsApp/Notion delivery) + Cat 16 `infra.secrets_management` Vault path + Layer 9/4 from my deep-dives
- **Temporal middleware (Orion PR #1150 Layer 5)** — gates gap 1 (task_id propagation), gap 2 (approval workflow), gap 4 (post-validation), gap 7 (notification dispatch trigger)
- **Vault (`infra.secrets_management`)** — gates customer onboarding wizard (Cat 19) + BYOK envelope encryption (Layer 9) + tenant credential storage for push notification tokens (gap 7 V1.1)

A3 LlamaIndex retirement remains primary scope per dispatch. This doc is the requested impl-feasibility lens; takes nothing off the A3 critical path.
