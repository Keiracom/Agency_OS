# Chat UX Patterns — Impl-Feasibility + LoC Estimates (Atlas)

**Directive:** Dave 2026-05-26 ~00:25 UTC. **Lens:** impl-feasibility + LoC estimate on the 4 V1 hard-gate chat UX patterns.

Short note per pattern. Each names: substrate that exists, architecture deps, LoC estimate (backend + frontend split), and any blocker flags.

Plain English; no timing predictions per the Keira fleet-wide rule.

---

## 1. `ux.chat.artifacts_side_panel`

**What it does:** Chat messages can carry artifacts (code blocks / PDF previews / markdown / CSV tables); side panel opens on click; mobile shows full-screen overlay.

**Substrate exists:** Cat 19 `ux.artifacts.file_types_v1` row already specs the V1 renderers (Monaco for code, markdown, PDF preview, images, CSV tables, Word/Excel via Mammoth.js, JSON/YAML). The RENDERERS are spec'd; the SIDE-PANEL CONTAINER + the chat-message-to-artifact LINK are not.

**Architecture deps:** chat message type schema needs an optional `artifact_ref` field. Cleanest: extend the existing chat message dataclass with an `artifacts: list[ArtifactRef]` where each ArtifactRef carries `(type, id, preview_metadata)`. Backend then serves the artifact body on demand via a separate endpoint (lazy load).

**LoC estimate:**
- Backend: ArtifactRef schema + chat message field + lazy-load artifact endpoint = **~80 LoC + migration**
- Frontend: side-panel container (open/close + responsive) = **~250 LoC**; per-type renderer wrappers reusing the Cat 19 renderers = **~150 LoC**; mobile full-screen overlay sub-component = **~80 LoC**; chat message integration (click handler) = **~50 LoC**
- Tests: ArtifactRef serialization + side-panel toggle = **~100 LoC**
- **Total: ~700 LoC** (~80 backend + ~530 frontend + ~100 tests)

**Flag:** Cat 19 ux.artifacts.* renderer set is spec'd but NOT BUILT (V1-launch row LOOSE). This pattern's LoC estimate assumes the renderers exist; if they don't, add the per-renderer LoC (Monaco wrapper ~50 LoC, PDF preview wrapper ~80 LoC, CSV table renderer ~100 LoC, etc.) — could double the frontend total.

---

## 2. `ux.chat.streaming_text`

**What it does:** Agent's text response streams to the UI as the LLM generates it, rather than batching to the end. Backpressure: client paces if it can't keep up.

**Substrate exists:** Anthropic SDK has native streaming via `messages.stream()` (used in existing Python code per `anthropic>=0.39.0` in requirements.txt). Frontend EventSource API is browser-native.

**Architecture deps:** Backend wraps Anthropic stream into a Server-Sent Events (SSE) channel per chat session. Frontend EventSource subscriber appends chunks to the rendering message. SSE has natural HTTP-level backpressure (TCP flow control); explicit per-client batching only needed for very slow clients (mobile on poor connection).

**LoC estimate:**
- Backend: stream-to-SSE wrapper around existing Anthropic streaming call = **~60 LoC**; per-tenant rate-limit + connection-cap = **~30 LoC**
- Frontend: EventSource subscriber + chunk append + progressive render = **~120 LoC**; auto-reconnect on disconnect = **~40 LoC**
- Tests: stream-chunk-ordering + reconnect = **~80 LoC**
- **Total: ~330 LoC** (~90 backend + ~160 frontend + ~80 tests)

**Flag:** explicit backpressure (chunk-batching for slow clients) is **NOT V1-required** — SSE TCP-level flow control is sufficient for V1 happy-path. Add only if first-customer reports mobile-on-3G stuttering. Document as V1.1 follow-up.

---

## 3. `ux.chat.stage_indicators`

**What it does:** Chip pills under the in-flight agent message show pipeline stages ("Thinking..." → "Searching memory..." → "Generating response..." → "Done"). Customer sees the workflow.

**Substrate exists:** Temporal Signals (mechanics in Orion PR #1155 — per Orion's PR #1156 design doc Sources list, PR #1155 is the "Phase A6 first-workflow Temporal Signal mechanics"). Cat 19 `ux.workflow.live_execution` row (V2) describes a richer version of this; V1 reduces to "stage chips on the current message".

**Architecture deps:**
- Temporal middleware (`temp.middleware` — Orion PR #1150 Layer 5) emits stage events at workflow transitions
- Backend Temporal-listener service bridges stage events into a per-chat SSE channel (same SSE substrate as pattern 2 above)
- Frontend chip component renders the stage chip block under the in-flight message; auto-removes on stage complete

**LoC estimate:**
- Backend: Temporal stage-event subscription + per-chat SSE bridge = **~120 LoC**; stage event format spec (timestamp + label + state) = **~20 LoC**
- Frontend: stage chip component (chip pill renderer + transition states) = **~140 LoC**
- Tests: Temporal stage event → SSE chunk shape + chip render = **~80 LoC**
- **Total: ~360 LoC** (~140 backend + ~140 frontend + ~80 tests)

**Flag:** **DEPENDENCY on Orion PR #1155 (Temporal Signal mechanics)** — that PR is "awaiting Max final concur as of A7 design draft" per Orion PR #1156 §Sources. Stage-indicator backend can't ship until Signal mechanics are merged. Frontend chip component can ship in parallel against a NoOp/Mock SSE channel.

---

## 4. `ux.chat.memory_chips`

**What it does:** Under an agent message, small "chips" name the memory sources the agent pulled (e.g., "your CRM data — 3 rows", "decision from yesterday", "company-policy doc §4"). Chip click opens that memory in Memory Inspector.

**Substrate exists:** Hindsight reflect endpoint returns citation metadata per PR #1129 finding ("Validates citations — only IDs that were actually retrieved can be cited"). My PR #1134 `trace_composition.compose_audit_record` already shapes these into `AuditRecord.citations: list[str]`. The recall-summary→chip transformation is the new piece.

**Architecture deps:**
- Backend memory-summary endpoint: given a message_id, return the list of `(memory_id, short_label, source_type)` the agent used. Wraps Hindsight reflect + extracts citation metadata.
- Frontend chip block component (sibling to stage_indicators chip): renders chips under the message
- Memory Inspector deep-link: chip click → `/dashboard/memory/{memory_id}` route (Cat 19 `ux.surface.memory_inspector` V1-or-V2 row)

**LoC estimate:**
- Backend: memory-summary endpoint (wraps existing reflect + extracts label) = **~100 LoC**; per-source-type label heuristic ("3 rows from your HubSpot" vs "decision MAL-V1") = **~50 LoC**
- Frontend: memory chip component = **~100 LoC**; deep-link router integration = **~30 LoC**
- Tests: chip extraction from reflect output + deep-link route = **~60 LoC**
- **Total: ~340 LoC** (~150 backend + ~130 frontend + ~60 tests)

**Flag:** depends on **Cat 19 `ux.surface.memory_inspector` route existing** OR being built in parallel. If Memory Inspector is V2 per inventory, chip click can fall back to in-place expand (show the memory content inline) for V1. Either path is fine; the V1 chip-without-deep-link form is the smallest viable.

---

## Summary table

| Pattern | Total LoC | Backend | Frontend | Tests | Primary dep / blocker |
| --- | --- | --- | --- | --- | --- |
| 1. artifacts_side_panel | **~700** | 80 | 530 | 100 | Cat 19 ux.artifacts.* renderers must be built (or LoC ~doubles) |
| 2. streaming_text | **~330** | 90 | 160 | 80 | None — SDK-native + SSE browser-standard |
| 3. stage_indicators | **~360** | 140 | 140 | 80 | Orion PR #1155 Temporal Signal mechanics + Orion PR #1150 middleware |
| 4. memory_chips | **~340** | 150 | 130 | 60 | Cat 19 ux.surface.memory_inspector route (V1 fallback: in-place expand) |
| **Total all 4** | **~1730** | 460 | 960 | 320 | — |

## Sequencing — feasibility-driven (not time-boxed)

Independent items can ship in any order. Dependency-driven order:

1. **Pattern 2 (streaming_text)** — no upstream deps; SDK-native; can ship immediately
2. **Pattern 1 (artifacts_side_panel)** — depends on Cat 19 artifacts renderer set
3. **Pattern 4 (memory_chips)** — depends on memory_inspector route (V1 fallback: in-place expand removes the dep)
4. **Pattern 3 (stage_indicators)** — depends on Orion PR #1155 Temporal Signal mechanics + Orion PR #1150 middleware

## Cross-cutting honest notes

- **No timing predictions** per Keira fleet-wide rule. LoC estimates are scope estimates; effort-to-ship depends on fleet capacity + reviewer cadence.
- All 4 patterns assume a **chat substrate exists end-to-end**: Next.js frontend (per `ux.mobile_strategy_web_v1` lock) + FastAPI backend + Temporal middleware for workflow events. If any of these don't exist yet, add the substrate LoC.
- **Mobile-first per `ux.platform_mobile_primary`** — all 4 patterns include mobile-responsive consideration in the estimates (most weight in pattern 1's full-screen overlay).
- **Per-tier behaviour variation** out-of-scope for this estimate; patterns themselves are tier-agnostic. Pro+ tier `ux.chat.multi_thread_tier_gating` row applies to chat-thread management, not to these 4 patterns.

A3 LlamaIndex retirement remains primary scope. This estimate doc takes nothing off the A3 critical path.
