# Claude Agent SDK Documentation

**Location:** `docs/e2e/SDK/`
**Status:** APPROVED FOR IMPLEMENTATION
**Last Updated:** January 2026
**Priority:** Implement BEFORE E2E testing (test the upgraded system, not legacy)

---

## Document Index

| Document | Purpose | Audience |
|----------|---------|----------|
| [SDK_INTEGRATION_PLAN.md](./SDK_INTEGRATION_PLAN.md) | Comprehensive integration guide | Everyone |
| [SDK_QUICK_REFERENCE.md](./SDK_QUICK_REFERENCE.md) | Developer cheatsheet | Developers |
| [SDK_COST_OPTIMIZATION.md](./SDK_COST_OPTIMIZATION.md) | Cost reduction strategies | Developers, Finance |

---

## What is This?

This folder contains the complete plan for integrating Claude Agent SDK into Agency OS. The SDK enables autonomous AI agents that can:

- Use tools (web search, web fetch)
- Loop until a goal is achieved
- Self-correct their work
- Return structured data

---

## Quick Summary

### Why SDK?

| Current System | With SDK |
|----------------|----------|
| One prompt → one response | Goal → autonomous research → quality output |
| No tool use | Web search, database queries |
| No self-correction | Agent reviews and improves its work |
| Generic emails | Deeply personalized with real research |

### Cost Impact

| Tier | Current Margin | SDK Optimized Margin |
|------|----------------|---------------------|
| Ignition | 60.5% | 52% |
| Velocity | 64.5% | 57% |
| Dominance | 52.7% | 43% |

### Use Cases

1. **ICP Extraction** - Intelligent onboarding with multi-turn research
2. **Deep Lead Enrichment** - Research Hot leads beyond Apollo data
3. **Personalized Emails** - Reference real, specific information
4. **Voice Call KB** - Generate per-call knowledge bases for Vapi
5. **Objection Handling** - Context-aware responses to pushback
6. **Response Classification** - Intent classification with context (Haiku)

---

## Getting Started

1. **Read the full plan:** [SDK_INTEGRATION_PLAN.md](./SDK_INTEGRATION_PLAN.md)
2. **For implementation:** [SDK_QUICK_REFERENCE.md](./SDK_QUICK_REFERENCE.md)
3. **For cost control:** [SDK_COST_OPTIMIZATION.md](./SDK_COST_OPTIMIZATION.md)

---

## Decision: APPROVED

**CEO approved SDK integration on 2026-01-18.**

Rationale: Test the upgraded system, not legacy code.

**Implementation order:**
1. Phase 1: Foundation (sdk_brain.py, sdk_tools.py)
2. Phase 2: ICP Agent (icp_agent.py) ← START HERE for E2E testing
3. Phase 3: Enrichment Agent
4. Phase 4: Email Agent
5. Phase 5: Voice KB Agent
6. Phase 6: Objection Agent

Estimated timeline: 6 weeks to full rollout
Estimated cost impact: -7% margin (optimized)
Expected benefit: +50% meeting booking confidence

---

## Related Documents

- `docs/e2e/sdk.md` - Original SDK concept note
- `docs/e2e/accounting/` - Cost comparison spreadsheets
- `docs/specs/TIER_PRICING_COST_MODEL_v2.md` - Current pricing model
