# Layer 1 Deep-Dive — Customer Surface (chat + dashboard + BYOK)

**Owner:** Aiden (architecture/governance lens)
**Per directive:** KEI-SYSTEM-DEEP-DIVE 2026-05-25 ~1779746500
**Status:** WORKING DRAFT — open for Elliot impl-feasibility cross-pass + Viktor positioning lens

## Notes — Canonical-key gate evidence (audit-dispatch checklist)

Queried `ceo:keiracom_architecture_v2_locked` (15 sub-keys, locked 2026-05-25 13:17:35Z). `v2_locks_not_for_redeliberation` includes `ux.mobile_strategy_web_v1`, `ux.react_native_ingestion_programme`, `cust.pricing_locked`, `cust.multi_channel_communication`. Layer 1 ships against those locks. Cat 19 rows pulled at inventory lines 297-435 (Cat 19 — UX/Product Surface). `ceo:cache_framework_canonical` queried (ratified 2026-05-25 ~1779746500); Layer 1 sits in the Anthropic-prompt-cache band (per-domain stable prompt content cached at 0.10× input cost).

## §1 Designed

**Customer-facing surface = chat + dashboard. BYOK. No agent/fleet/governance language exposed.** Source: `ux.positioning_chat_dash_byok` + `ux.no_agent_language` (both RATIFIED-CEO line 297-298). Apple-grade simplicity over engineering substrate sophistication (`ux.apple_grade_simplicity` line 300). Mobile-primary with desktop-parity via React Native + Next.js shared via React Native Web; one codebase iOS + Android + Web at ~70% code reuse (`ux.platform_mobile_primary` + `ux.tech_stack_rn_next` line 301-302).

**Information architecture:** 5-tab bottom nav (Home / Chat / Projects / Workflows / More) with Notifications as header-icon-with-badge not 6th tab (per my Cat 19 §1C resolution). Secondary surfaces nested under More (Files, Memory Inspector, Integrations Hub, Settings, Approval Queue, Notifications, Audit Log). Project is the primary organisational unit; one primary chat per project default; topic chats branch when needed (Pro tier multi-thread). Cross-project context via explicit @-mention gesture.

**BYOK customer-key surface:** Settings → Account → API Keys. Provider picker (Anthropic Haiku / OpenAI gpt-4o-mini / Gemini Flash / Azure per tier — `gov.customer_byok` line 162 RATIFIED-DM). Customer provides key; Keiracom never has key in plaintext on Postgres (envelope-encrypted via Vault Transit per `infra.secrets_management` line 208).

## §2 Built

**Substrate:** existing Next.js frontend at `frontend/` (Agency_OS-era, partially reusable). React Native + Expo scaffolding NOT yet stood up per my Cat 19 §3C hybrid recommendation (Path b + c: V1 web-only via Next.js; mobile parallel-track, mobile app stores V1.1).

**Wired today:** BYOK provider routing via LiteLLM governance router (`gov.litellm_router` RATIFIED-CEO + running per T0.2 audit). Customer dashboard has cost panel substrate via metering pipeline PR #1137. KeiracomTenantExtension at `src/keiracom_system/tenant/` resolves per-tenant config including BYOK key (Vault decryptor wires in via PR #1146 once Sonar QG clears + admin-merge fires).

**Not yet built (V1 critical path):** onboarding wizard (`ux.add.onboarding_wizard` BLOCKED on Vault per Cat 16 item 2 + my Cat 19 §5B); customer file system + `ux.files.system_files_hidden` enforcement (BLOCKED on Go Sidecar `mcp.go_sidecar` line 149, scaffold in PR #1144); React Native mobile shell; Memory Inspector UX; Workflow live-status visualisation.

## §3 Measured

**No production data yet.** Pre-revenue per `feedback_pre_revenue_reality`; zero paying customers. Existing Agency_OS dashboard has internal-use telemetry (BU funnel metrics, campaign stats) but those are pre-pivot signals not Keiracom V1 customer-surface signals.

**Honest gap to name:** when first-10-customer cohort onboards, drop-off-per-onboarding-step measurement is the highest-value early telemetry (per my Cat 19 §7 behavioral-design lens). Budget alerts, tier-cap upgrade prompts, file-search latency at customer scale all need calibration against real usage. None observed today.

## §4 Token budget / cost behaviour at this layer

Layer 1 surfaces don't directly burn LLM tokens — they're the input/output framing. **Token cost lives downstream** at Layer 2 (Keira chat agent runs the prompt) + Layer 3 (deliberator-CONCUR triggers if surfaced for Pro+ trust-theatre). Layer 1's cost responsibilities:

- **Display the cost:** Token Budget Visualisation is V1 essential per `ux.scope.v1_essentials`. Customer sees per-month token consumption vs budget cap + alerts at 80% per `cost.cache_discipline` framework.
- **Trigger tier-upgrade prompt:** when tier cap hits (per Cat 17 capacity allocation), Layer 1 shows the "5 of 5 slots in use — upgrade to Pro" prompt (`tier.capacity_behaviour`).
- **Account management UX:** upgrade/downgrade/cancel/refund flows route through Settings (the V1 essential I flagged in Cat 19 §4A item 6).

Cost behaviour at Layer 1 is observability + control-surface, not consumption.

## §5 Cache strategy

Per `ceo:cache_framework_canonical`: Layer 1 sits in the **Anthropic prompt cache band (0.10× input cost)** for the chat agent's stable system-prompt content. Customer-rendered UI is not a cache-target — it's the surface where cached LLM output is displayed.

**Stable content cached at Layer 1:** Keira system prompt v3 (loaded once per session; cached across turns within the 5-min Anthropic cache TTL). Per-tenant Memory Inspector "what we know about your business" recalled-context (could leverage Valkey semantic cache `cost.semantic_cache_valkey` for repeated lookups during a chat session).

**Cache strategy NOT applicable at Layer 1:** customer-typed input (always fresh); workflow live-status view (real-time render); notifications header-icon badge (real-time count).

## §6 LOOSE items / open questions

- **Onboarding wizard 6-step flow** — design surfaced in my Cat 19 §2.5; needs implementation. BLOCKED on Vault.
- **React Native scaffolding stood up?** — V1 web-only is acceptable per Cat 19 §3C hybrid; mobile-primary positioning vs reality needs honest customer-facing messaging until V1.1.
- **Multi-thread chat UX affordance** — Solo single-chat vs Pro tab-bar — design exists in Cat 19 §2.6 but pixel-level mockup pending.
- **Error states + loading states + empty states** — 3 of 10 missing-surface items I flagged in Cat 19 §4A.1-3 — patterns named, components not built.
- **Memory Inspector visualisation choice TBD** — list view? graph view? table view? Customer-facing presentation needs design pass.
- **System status page customer-friendly naming** — per my Cat 19 §6B-5: "Memory service / Chat service / File storage / Notification delivery" naming used; not "Hindsight / NATS / Vultr Object Storage / APNs".
- **Trust-theatre paid-tier differentiator** — "Reviewed by 2 specialists" badge on Pro+ outputs (Cat 19 §6C optional opportunity) — pending Dave + Viktor positioning decision.

## §7 Per-tier behaviour variation

Per `ceo:cache_framework_canonical.per_tier_multipliers_proposal` + Cat 17 capacity allocation:

| Tier | Layer 1 multiplier | Surface behaviour |
|---|---:|---|
| Sandbox | 0.5× | Single chat, no multi-thread affordance; visible "evaluate mode" framing; 10-tasks/day rate-limit indicator |
| Solo | 1.0× | Single primary chat per project, no multi-thread "+" button, upgrade-to-Pro CTA on cap |
| Pro | 1.5× | Multi-thread chat tab-bar visible, dashboard cost-panel richer (per-tenant metering granularity) |
| Team | 2.0× | Per-user chat slots (per my Cat 17 §5B resolution), admin user-management surface |
| Enterprise | custom | Per-VPC isolation surface, dedicated tenant-config dashboard, compliance audit-log primary surface |

**Architectural note (pressure-test of proposal):** Layer 1 multipliers are SURFACE-density not COST-density. The 0.5× / 1.0× / 1.5× / 2.0× pattern describes how much UI sophistication each tier sees, not how many LLM tokens are burned. Pure cost differentiation happens at Layer 2 (chat agent calls) + Layer 6 (memory operations) + Layer 11 (cost optimization layer that Atlas owns).

## §8 Per-agent-type variation

Layer 1 is customer-only; no internal-agent variation applies. Customer sees Keira (the chat agent) as a single persona; internal fleet personas (Aiden / Atlas / Max / Orion / etc.) are NEVER surfaced to Layer 1 per `ux.no_agent_language` lock.

## Cross-cutting concerns touched

- **Multi-tenancy enforcement (API not UI):** Layer 1 displays tenant-scoped data only; real isolation at Layer 6 (Hindsight TenantExtension PR #1132) + Layer 7 (Go Sidecar path-deny PR #1144). UI decoration is necessary-not-sufficient.
- **Security (BYOK custody):** customer key entered in Settings, immediately envelope-encrypted at write time via Vault Transit (`infra.secrets_management`). Plaintext NEVER persisted on server; NEVER returned in API responses; NEVER logged.
- **Customer file system (`ux.files.*`):** dashboard Files surface; storage at Vultr Object Storage + Postgres hierarchy; system-file deny enforced at Go Sidecar (BLOCKED until PR #1144 engineer-tier build).
- **Reasoning trace + audit trail:** Layer 1 exposes `ux.diff.audit_trail_viewer` + `ux.diff.reasoning_trace_viewer` surfaces. Compliance verticals (legal/health/accounting per `mem.v1_verticals`) are V1.x post-Vault.

## Connects to

`[[layer_02_chat_agent_keira]]`, `[[layer_06_memory]]`, `[[layer_07_governance]]`, `ceo:cache_framework_canonical`, `ceo:keiracom_architecture_v2_locked.v2_locks_not_for_redeliberation`.
