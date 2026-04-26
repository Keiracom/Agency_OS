# Peta + Composio Market Positioning vs Keiracom Workforce Thesis

**Date:** 2026-04-26
**Author:** SCOUT (research clone)
**Mission:** Map [Peta (peta.io)](https://peta.io/) and [Composio (composio.dev)](https://composio.dev/) onto the Keiracom Workforce thesis. Identify whether either competes for our wedge (**agent-level governance**) or sits one layer below (tool-level governance).
**TL;DR:** **Neither competes for our wedge.** Both operate at the **tool/integration layer** (auth, RBAC, MCP gateway). Composio is the funded incumbent ($29M, 200+ customers, $1M+ ARR). Peta is the security-first newcomer (Dunia labs, late-2025 launch, undisclosed funding/customers). The white space — **governance over agent reasoning, decomposition, and peer review** — is unoccupied. Keiracom Workforce thesis still defensible. Status remains DEFERRED per Dave directive 2026-04-26.

---

## 1. Composio — The Funded Tool-Integration Incumbent

### 1.1 Funding and traction (evidence-anchored)

| Field | Value | Source |
|---|---|---|
| Total raised | $29M ($25M Series A + $4M Seed) | [Composio Series A blog](https://composio.dev/blog/series-a); [Tracxn](https://tracxn.com/d/companies/composio/__S4CqdyIkWZd1BSTOwnjS82Hz0ppMkmDoAP_j4_oMBfk/funding-and-investors) |
| Series A date | 2025-07-22 | [SiliconANGLE](https://siliconangle.com/2025/07/22/composio-raises-25m-funding-ease-ai-agent-development/) |
| Lead investors | Lightspeed Venture Partners + Elevation Capital (Series A); Together (Seed) | [StartupWired](https://startupwired.com/2025/07/22/composio-raises-25m-to-power-agentic-ai-workflow-tools/) |
| Customers | 200+ enterprise + startup (incl. Glean) | StartupWired |
| Developer ecosystem | 100,000+ developers | StartupWired |
| ARR | >$1M | StartupWired |
| HQ | San Francisco + Bengaluru | StartupWired |
| Pricing | Usage-based, transparent, no platform fees | [Auth platforms guide](https://composio.dev/content/ai-agent-authentication-platforms) |
| Compliance | SOC 2 | Auth platforms guide |
| Integrations | 150+ pre-built tools | [ByteBridge analysis](https://bytebridge.medium.com/beyond-composio-contextforge-and-peta-as-integration-platform-alternatives-d90f51f554e7) |

### 1.2 Positioning and product

Composio frames itself as **"infrastructure that transforms AI from static tools"** into "skills that evolve with your agents" — agents developing collective intuition through shared experiences across deployed fleets ([Series A blog](https://composio.dev/blog/series-a)). Their published competitors are **Merge, Nango, and Arcade** ([auth platforms guide](https://composio.dev/content/ai-agent-authentication-platforms)). Their stated buyer is "developer-first teams building production agents" needing managed auth + unified SDK + DX velocity.

### 1.3 Governance scope

The auth platforms guide treats governance entirely at the **tool layer** — "Tool Packs", rule-based policies, just-in-time permissions. ByteBridge's competitive analysis is explicit: *"none of these platforms govern how agents reason, decompose tasks, or peer-review decisions"* ([ByteBridge](https://bytebridge.medium.com/beyond-composio-contextforge-and-peta-as-integration-platform-alternatives-d90f51f554e7)). Composio is the management layer for **what an agent can call**, not **how an agent works**.

### 1.4 Release cadence

Composio publishes via blog (`composio.dev/blog`) and SDK updates rather than dated releases. The Series A funding-velocity narrative ("crossed $1M ARR") is evidence of deployment maturity rather than feature throughput.

---

## 2. Peta — The Security-First MCP Control Plane

### 2.1 Stage and visibility (evidence-anchored)

| Field | Value | Source |
|---|---|---|
| Operating entity | Dunia labs, Inc. | [Peta homepage](https://peta.io/) (2026 copyright) |
| Funding | Not disclosed publicly | — |
| Customers | Not disclosed (logos absent from homepage) | Peta homepage |
| Pricing | Not disclosed (no tier page) | [Peta docs](https://docs.peta.io/) |
| Stage | "Adoption is just beginning" — launched late 2025 | [ByteBridge](https://bytebridge.medium.com/beyond-composio-contextforge-and-peta-as-integration-platform-alternatives-d90f51f554e7) |
| MCP spec compliance | `2025-11-25` MCP specification | Peta docs |
| Self-description | "1Password for AI agents" / "The Control Plane for MCP" | ByteBridge; Peta homepage |

### 2.2 Product surface

Three components ([architecture page](https://peta.io/architecture/)):
- **Peta Core** — managed MCP runtime + zero-trust gateway; server-side credential injection
- **Peta Console** — policy engine for RBAC/ABAC configuration; usage monitoring
- **Peta Desk** — desktop approval workflow for high-risk operations

Pitch: *"Agents authenticate with short-lived Peta tokens; real API keys stay encrypted in the Vault and behind the MCP gateway."* Positioned for compliance-heavy environments rolling out MCP — "Teams using LangChain, CrewAI, AutoGen, n8n."

### 2.3 Governance scope

Same as Composio: **tool-access only**. Peta docs and homepage describe RBAC/ABAC over MCP tools, OAuth brokerage, HITL approval gates. ByteBridge confirms: governance scope across Composio, ContextForge, and Peta is uniformly **what an agent can do**, never **how the agent decides what to do**.

### 2.4 Differentiation from Composio

| Axis | Composio | Peta |
|---|---|---|
| Hosting | Cloud SaaS, 150+ managed integrations | Self-hosted commercial license |
| Pitch | Developer DX + speed-to-market | Enterprise security, zero-trust, audit |
| Auth model | Managed auth on Composio infra | Vault-backed, server-side credential injection |
| Pricing | Usage-based | Not disclosed |
| Maturity | $1M+ ARR, 200 customers | Pre-disclosure |
| Approval workflow | Not a marquee feature | **Peta Desk** is core |
| Governance abstraction | Tool integration | Tool gateway + policy plane |

Composio sells **acceleration**. Peta sells **control**. They overlap on auth but split on whether DX or compliance is the primary buyer.

---

## 3. Where Keiracom Workforce Sits

### 3.1 Thesis recap (per `project_keiracom_workforce.md`)

> Anthropic/Microsoft sell agent **plumbing**. Keiracom sells agent **governance** (management layer). 22 battle-tested rules, 4 trust levels, peer review, kill switch, budget caps, enforcer monitoring. Status: **DEFERRED 2026-04-26**, Agency OS first.

The wedge is **agent-behaviour governance** — Step 0 RESTATE, DSAE-DELAY peer review, Clone Queue Board, Constant Progression Rule, Four-Store Completion, Callsign Discipline. None of these are about *which* tool an agent calls; all are about *how* an agent reasons, coordinates, and proves work.

### 3.2 Layer map

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4 — AGENT BEHAVIOUR GOVERNANCE                        │
│ Reasoning, decomposition, peer review, voting, audit        │
│ → Keiracom Workforce (thesis, deferred)                     │
│ → ByteBridge analysis: "not addressed" by current platforms │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3 — TOOL ACCESS GOVERNANCE                            │
│ RBAC/ABAC over MCP tools, HITL approval, secrets vault      │
│ → Peta (Dunia labs, late 2025)                              │
│ → ContextForge (open-source, beta)                          │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2 — TOOL INTEGRATION                                  │
│ 150+ managed integrations, unified SDK, auth                │
│ → Composio ($29M raised, 200+ customers, $1M+ ARR)          │
│ → Merge, Nango, Arcade (per Composio's own list)            │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1 — AGENT RUNTIME                                     │
│ Sessions, sandboxes, harness, model serving                 │
│ → Anthropic Managed Agents (April 8, 2026)                  │
│ → Anthropic Claude Code Routines (April 14, 2026)           │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Competitive read

- **Composio is not a competitor; it is a potential dependency.** If Keiracom Workforce ever needs 150+ tool integrations for customer agents, paying Composio's usage-based fee is cheaper than maintaining our own integration matrix. Their wedge (developer DX) is orthogonal to ours (governance).
- **Peta is not a competitor; it is a potential complement.** A customer running Keiracom Workforce for behaviour governance + Peta Console for tool-access governance is a coherent stack. Their RBAC/ABAC over MCP fills the layer below ours.
- **Microsoft Open Source's [Agent Governance Toolkit](https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/)** (2026-04-02) is the closest signal that the "agent governance" framing is becoming an industry category. Their toolkit is **runtime security** (sandboxing, network egress control) — still tool-layer, not behaviour-layer. White space remains.

### 3.4 Pre-revenue reality check

Per memory `feedback_pre_revenue_reality.md`: **zero clients, pre-revenue.** This document does not claim Keiracom Workforce has traction, customers, or social proof. The thesis is a *positioning hypothesis* validated only by the absence of competitors at Layer 4 — not by market traction.

---

## 4. Implications for Keiracom Workforce (When Revisited)

### 4.1 Defensibility status: holds

The two most-funded / most-discussed agent-governance platforms (Composio, Peta) both stop at tool-access governance. The agent-behaviour governance layer remains structurally empty. A competitor entering Layer 4 would need to demonstrate **22-rule enforcement + multi-bot peer review + four-store audit + callsign discipline** on real customer agents — none of which Composio or Peta currently market.

### 4.2 Risks to monitor

1. **Composio expanding upward.** "Skills that evolve with your agents" hints at agent-state management. If they extend skills into behaviour primitives (decomposition templates, peer-review patterns), the wedge narrows. Track Composio release notes monthly.
2. **Microsoft's Agent Governance Toolkit expanding.** Open-source runtime security could grow into open-source behaviour governance. Open source at Layer 4 commoditises our wedge.
3. **Anthropic's Managed Agents `multi-agent` research preview going GA.** Today it's the missing primitive blocking us from running DSAE inside their platform (per P7 evaluation). If they ship native multi-agent + outcomes + memory, they own a slice of behaviour governance by default.
4. **Peta moving up.** Peta Desk's HITL approval is one step toward behaviour governance. If they add multi-agent consensus + audit-of-reasoning, they're closer than Composio.

### 4.3 Architectural decisions to make under the 5-10% extractability tax

When choosing patterns *now* in Agency OS, prefer extractable shapes:
- **Parameterise governance laws.** Today's `LAW XV-D` and `GOV-9` are hardcoded for Agency OS workflow. Extract them as a `governance.yaml` rules engine that other verticals can consume without code changes.
- **Decouple peer-review protocol from Telegram.** DSAE-DELAY today depends on the Telegram supergroup. Future verticals will use Slack, MS Teams, or in-app comments — abstract the channel.
- **Make Four-Store Completion swappable.** `MANUAL.md + ceo_memory + cis_directive_metrics + Drive` is Agency-OS-specific. The contract ("evidence written to ≥4 surfaces before mark-complete") is reusable; the surfaces are not.

### 4.4 Suggested follow-up directives (when thesis exits DEFERRED state)

- **WORKFORCE-A** — Track Composio + Peta + Microsoft AGT release notes monthly. Update this market analysis quarterly.
- **WORKFORCE-B** — Ratify the extractable-governance pattern for the next 3 LAW additions. No new hardcoded references to Agency-OS-specific surfaces.
- **WORKFORCE-C** — Once Agency OS hits first paying customer, draft `keiracom_workforce_v0.md` extracting the rules engine + peer-review protocol + four-store contract as a standalone product spec. Currently blocked: pre-revenue, no customer to validate against.

---

## Sources

- [Peta homepage](https://peta.io/) and [docs](https://docs.peta.io/) and [architecture page](https://peta.io/architecture/) and [use cases](https://peta.io/use-cases/)
- [Composio Series A blog](https://composio.dev/blog/series-a)
- [Composio AI agent authentication platforms guide](https://composio.dev/content/ai-agent-authentication-platforms)
- [SiliconANGLE — Composio raises $25M (2025-07-22)](https://siliconangle.com/2025/07/22/composio-raises-25m-funding-ease-ai-agent-development/)
- [StartupWired — Composio Series A](https://startupwired.com/2025/07/22/composio-raises-25m-to-power-agentic-ai-workflow-tools/)
- [Tracxn — Composio profile](https://tracxn.com/d/companies/composio/__S4CqdyIkWZd1BSTOwnjS82Hz0ppMkmDoAP_j4_oMBfk)
- [PitchBook — Composio profile](https://pitchbook.com/profiles/company/539999-65)
- [ByteBridge — Beyond Composio: ContextForge and Peta as alternatives](https://bytebridge.medium.com/beyond-composio-contextforge-and-peta-as-integration-platform-alternatives-d90f51f554e7)
- [Microsoft Open Source — Agent Governance Toolkit (2026-04-02)](https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/)
- Local: `/home/elliotbot/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/project_keiracom_workforce.md`
- Local: `/home/elliotbot/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/feedback_pre_revenue_reality.md`
