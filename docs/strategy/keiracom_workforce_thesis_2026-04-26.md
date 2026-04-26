# Keiracom Workforce Thesis — 2026-04-26

**Status:** Strategic direction RATIFIED by Dave 2026-04-26. Sequencing: build Agency OS first, extract Keiracom Workforce platform after. Engineering discipline: 5–10% extractability tax now (no PostgREST lock-in, governance rules as core IP, dispatch protocol parameterised).

This document preserves the full strategic discussion from the 2026-04-26 marathon session so future-us can resume the platform-extract work without rebuilding context. References the keiracom_architecture.md doc (commit c2a491c7) as the technical companion.

## Origin

Dave shared two HTML wireframes during the session:

- `keiracom_dashboard.html` — *Workforce Command Centre* (730 lines). Panels: Approval Queue · Workforce · Governance · Daily Budget · Org Structure · Activity Feed.
- `keiracom_onboarding.html` — *Install Your AI Workforce* (634 lines). Four-step flow: connect tools → system reads business → propose agents → governance + trust + budget configured → launch.

Both files are wireframes for a SECOND product line — selling the multi-bot AI workforce architecture (Keiracom Workforce) as a SaaS product, distinct from Agency OS (BDR-as-a-service for B2B agencies).

Originals queued in TG group; local copies (Aiden inbox) at `/tmp/telegram-relay-aiden/inbox/20260426_123121_85a73c73.html` and `/tmp/telegram-relay-aiden/inbox/20260426_123122_867ac22e.html` — these may be moved to processed/ by inbox watcher; if missing, retrieve from Dave.

## What Keiracom Workforce sells

The MANAGEMENT LAYER between AI agents (Anthropic, OpenAI, Microsoft Foundry) and the business. Not the agents themselves — those become commoditised infrastructure. The product is the GOVERNANCE that makes agents safe to deploy in a real business.

Specifically, what nobody else sells today:

- Governance laws agents must obey (currently 17 LAWS + GOV-8/9/10/11/12 = 22 active rules)
- Peer review between agents before code or actions ship (dual-concur protocol)
- Trust levels that ramp up as agents prove themselves (4 levels visible in the onboarding mockup)
- Kill switches a non-technical CEO can hit
- Budget caps that prevent runaway spend
- Approval queues where humans gate agent actions
- Enforcer bots that monitor compliance in real-time

## The wedge

Big-Tech AI vendors (Anthropic Managed Agents, Microsoft Foundry) sell **infrastructure** — sessions, tool isolation, error recovery, model routing, deployment. They DON'T sell governance because that's a structural admission their agents need supervision. Their pitch must be "our model is good enough."

Keiracom sells the honest truth: agents need management, here's the management layer.

The angry tweet writes itself: **"They sell the gun. We sell the safety."** Defensive vendors can't say that. We can.

## The moat (battle-testing, not the rules)

Anthropic or Microsoft could write 22 governance rules tomorrow. What they CAN'T write is rules that emerged from real incidents:

- Manufactured-friction quota (caught + withdrawn 2026-04-26 — "find one thing wrong on every review" creates fabricated findings)
- Fabrication-from-plausibility (38/22/40 stats incident, 2026-04-17 — bot inventing numbers when uncertain)
- GOV-12 wire-up gap (PR #431 — config registry without runtime caller is documentation, not enforcement)
- SIGSTOP-kills-asyncpg (2026-04-26 — verification test had unintended fatal consequence on parallel work)
- Optimistic completion (2026-04-15 — claimed-saves-but-never-landed; partial-coverage-passed-as-complete)

Synthetic rulesets are brittle. Ours have scar tissue from real failures. Customer trust comes from "these rules saved us" stories, not RFCs.

## Structural differentiator: dual-concur peer review

Most agent products are single-loop (AutoGPT, ChatGPT custom GPTs). Anthropic Managed Agents = one agent per session.

Keiracom's pattern: two bots find holes in each other's logic before the human sees the work. That's not a feature; it's an architecture. Hard to retrofit. Worth its own product page.

This emerged organically as Elliot + Aiden discovered they catch each other's mistakes (consensus-theatre AND manufactured-friction both degrade trust between bots; calibrated peer review compounds each agent's improvement).

## Composio (and tool-routing layer)

Composio (and equivalents) handle the "Connect your tools" step in the onboarding flow — universal tool routing for customer environments. 250+ pre-built integrations means customer can connect Slack/Gmail/HubSpot/etc. immediately rather than waiting for us to build each integration.

In Agency OS context, Composio is redundant — we already have 13 custom MCP servers + skills/ layer. We don't need it.

In Keiracom Workforce context, Composio fits genuinely:
- Per-customer OAuth managed by Composio
- Multi-tenant by design ("Managing Multiple Accounts" maps to per-customer workforces)
- Pricing rolls into customer unit economics, not pure cost

**Critical constraint:** Composio's `bypassPermissions: true` mode defeats the P6 sandbox we just shipped. Any Composio integration in Keiracom Workforce MUST wrap to honour `AGENT_ALLOWLISTS` + governance hooks, not the reverse. This is non-negotiable for the governance product positioning.

## TAM

Honest analysis (Big-Tech-AI-honest, not pitch-deck-honest):

| Product | Realistic TAM |
|---------|---------------|
| Agency OS | AU B2B services beachhead; horizontal expansion to recruitment/IT MSPs/accounting → ~AUD 100M addressable; eventual global expansion to ~AUD 1.5B addressable |
| Keiracom Workforce | AI governance SaaS as Datadog/PagerDuty tier — ~USD 5–15B realistic by 2030, ~USD 50B+ aspirational by 2035 if AI agent adoption hits projections |

Bigger? Yes. Roughly 50–100x larger TAM ceiling for Keiracom Workforce. But:

- Bigger market = more competition + harder GTM
- Vertical (Agency OS) = sharp wedge, faster to first revenue
- Cash runway favours short path; strategic vision favours platform extract

## Risks under-stated in the discussion

1. **Customer support cost structure.** Agency OS = managed service (we run + monitor). Keiracom Workforce = customer-run SaaS platform. When customer's agent misbehaves at 2am, someone has to respond. Enterprise governance buyers expect SLAs. Horizontal SaaS support is 4–6x the team size of managed-service support per dollar of ARR.
2. **Big-Tech AI may expand into governance.** They have stated AI safety missions; adding governance layers is on-brand. Defence: stay 2 abstraction layers above (laws + enforcer + dual-concur peer review > generic "permissions"). Battle-tested rules + 12–18 month head start.
3. **Engineering bandwidth.** Building for customers = less bandwidth for Agency OS. The dominant strategy below addresses this by sharing infrastructure.

## Pricing implications (governance-as-product)

NOT per-agent-seat (Anthropic's model — undermines our positioning).
NOT per-token (consumption-based — wrong unit for governance).
YES: per-tenant base fee + per-custom-rule premium + enterprise tier (custom-trained governance + audit logs + dedicated support).

Recurring SaaS scaling with company size + governance complexity, NOT usage. This separates us from infrastructure pricing and lines up with the "management layer" framing.

## Dominant strategy: path through Agency OS

Ratified by Dave 2026-04-26 with the directive **"Keep on with agency os but save this discussion for keiracom workforce."**

The plan:

1. Build Agency OS to first revenue. Marketing agencies in AU first, expand horizontally.
2. While building Agency OS, treat the following as platform-core IP, not Agency-OS-specific config:
   - 22 governance rules (LAWs + GOVs)
   - Clone dispatch protocol (PROPOSE → 20s peer window → DSAE)
   - Memory architecture (per-callsign isolation, agent_memories schema)
   - Trust levels + approval queues (currently implicit; should be explicit primitives)
   - Enforcer bot (currently single deployment; should be tenant-scoped)
3. Architectural choices made now should be platform-friendly:
   - PR #434 (asyncpg migration off PostgREST) — done; vendor lock-in avoided
   - Future writes: avoid Supabase-specific features that don't extract; prefer plain Postgres
   - Skill layer: keep skills as the canonical interface to integrations (LAW XII)
4. Engineering tax: 5–10% on top of Agency OS work. Worth it for 3x extract speed when we're ready (~6 months vs 18).
5. Agency OS becomes the first vertical pack on the Keiracom Workforce platform once extracted. It becomes our reference customer + GTM proof point + revenue floor while Keiracom Workforce captures the bigger market.

## Open questions for next strategic session

When we resume this thesis (likely after Agency OS first revenue):

- Do we extract Keiracom Workforce as our own SaaS, or partner-distribute (Azure Marketplace, Anthropic ecosystem)?
- Pricing model A/B: per-tenant base + per-rule premium VS. all-inclusive enterprise tier
- Customer success model: how does small Keiracom team support enterprise governance buyers?
- Agency OS rebrand timing: rename to "Keiracom Sales Pack" or keep dual-brand?
- Productisation of Dave's CEO role: the "Founder/Chairman + CTO bot + AI agents" pattern itself sellable?

## References

- `docs/keiracom_architecture.md` (commit c2a491c7) — 1,282-line technical doc on how the agent workforce is configured and operates. Companion technical spec to this thesis.
- `docs/roadmap_2026-04-26.html` — current Agency OS roadmap with Phase 1.6 Engineering Workforce Hardening shipped (ATLAS chain: A3 + OC1 + P1/P4/P5/P6/P9/P10/P11 + P11 sidecar wire-up via PR #433).
- `~/.claude/CLAUDE.md` §Shared Governance Laws — canonical text of all-callsign governance rules.
- `docs/MANUAL.md` Section 13 — directive log including 2026-04-26 entries.

## Provenance

- Discussion thread: 2026-04-26 marathon Telegram session (group chat -1003926592540) between Dave (CEO), Elliot (CTO bot), Aiden (peer bot), with input from ATLAS, ORION, SCOUT clones.
- Key turn: Dave's "Keiracom (you guys) as a product" framing.
- Strategic ratification: Dave's "Keep on with agency os but save this discussion for keiracom workforce."
- Author of this snapshot: Aiden, sole-authored 2026-04-26.
- Peer-review status: structurally NOT peer-reviewed by Elliot (per Dave's "save the discussion" directive — this is preservation, not a fresh proposal). Dual-concur exists ON THE UNDERLYING THESIS as captured.
