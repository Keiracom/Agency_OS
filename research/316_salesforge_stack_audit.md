# Directive #316 — Salesforge Stack Audit & Megaforge Evaluation

**Date:** 2026-04-07  
**Type:** Research only — no signups, no purchases, no API calls  
**Branch:** research/316-salesforge-audit

---

## QUESTION 1 — SUBSCRIPTION MAP

Full product family under the Forge brand. All prices USD unless noted; AUD = USD × 1.55.

| Product | Purpose | Lowest Paid Tier | Included with Salesforge? | Self-signup or Sales-gated? |
|---------|---------|-----------------|--------------------------|----------------------------|
| **Salesforge** | Multi-channel outreach sequencer (email + LinkedIn) with unlimited mailboxes | $48/mo (Pro — 5,000 emails/mo, 1,000 active contacts) | — (the core product) | Self-signup, 14-day trial |
| **Infraforge** | Private dedicated email infrastructure: domain purchase, mailbox provisioning, DNS automation, dedicated IPs | $33/mo (10 mailbox slots, annual billing); ~$40/mo quarterly | Separate purchase | Self-signup |
| **Mailforge** | Shared email infrastructure (pooled IPs, similar to Gmail-scale shared pools) — cheaper than Infraforge, higher spam tolerance | $3/mailbox slot/mo (monthly); $30/mailbox slot/yr (annual, tier 1) | Separate purchase | Self-signup |
| **Warmforge** | Email deliverability and warmup centre — AI-driven warmup, health checks, blacklist monitoring | $9–$12/mailbox/mo (bulk rates to $3/mailbox) | **Included free** with all Salesforge subscriptions | Self-signup |
| **Megaforge** | Premium multi-ESP distribution — splits sending across Gmail, Outlook, Mailforge, and Infraforge; automatic failover if one ESP burns | $69/mo (20 mailboxes base) | Separate add-on | Self-signup (selectable during Salesforge onboarding) |
| **Primeforge** | Native Google Workspace and MS365 mailboxes with US IPs and automated DNS | $4.50/mailbox/mo (quarterly, slots 1–100); annual ~$45/slot | Separate purchase | Self-signup |
| **Leadsforge** | AI-powered lead search engine — finds enriched leads by prompt, exports to CSV or Salesforge sequences | $49/mo Essential (2,000 credits); 1 credit = 1 email or LinkedIn URL; 10 credits = 1 mobile | Separate purchase | Self-signup, 100 free credits on signup |
| **Primebox** | Unified inbox — consolidates all email + LinkedIn replies, sentiment analysis, reply assistance | Free | **Included free** with all Salesforge subscriptions | N/A |
| **Agent Frank** | Fully autonomous AI SDR — prospecting, personalised email sequences, meeting booking, 24/7 operation | $499/mo (annual); $599/mo (quarterly) — covers 1,000 active contacts | Separate; Salesforge subscription not required | Self-signup (sales-assisted onboarding offered) |

**Sources:**
- https://www.salesforge.ai/pricing
- https://www.infraforge.ai/pricing
- https://www.mailforge.ai/pricing
- https://www.warmforge.ai
- https://www.leadsforge.ai/pricing
- https://www.primeforge.ai/pricing
- https://help.salesforge.ai (Primebox article)
- https://syncgtm.com/blog/salesforge-review

---

## QUESTION 2 — CURRENT USAGE

### Raw Command Output

```
=== SALESFORGE FILES ===
src/api/routes/webhooks.py
src/config/settings.py
src/engines/email.py
src/integrations/infraforge.py
src/integrations/salesforge.py
src/orchestration/flows/daily_digest_flow.py
src/orchestration/flows/infra_provisioning_flow.py
src/services/deliverability_service.py
src/services/domain_provisioning_service.py
src/services/email_events_service.py
src/services/jit_validator.py

=== INFRAFORGE FILES ===
src/config/settings.py
src/integrations/infraforge.py
src/orchestration/flows/infra_provisioning_flow.py
src/services/domain_provisioning_service.py
src/services/resource_assignment_service.py

=== WARMFORGE FILES ===
src/config/settings.py
src/engines/email.py
src/integrations/infraforge.py
src/integrations/salesforge.py
src/integrations/warmforge.py
src/orchestration/flows/infra_provisioning_flow.py
src/orchestration/flows/warmup_monitor_flow.py
src/services/deliverability_service.py
src/services/domain_provisioning_service.py
src/services/email_events_service.py
src/services/jit_validator.py

=== MAILFORGE FILES ===
src/orchestration/flows/infra_provisioning_flow.py
src/services/deliverability_service.py

=== ENV VARS ===
# --- INFRAFORGE (Domains & Mailboxes) ---
INFRAFORGE_API_KEY=...REDACTED
INFRAFORGE_API_URL=...REDACTEDge.ai/public
INFRAFORGE_API_DOCS=...REDACTEDge.ai/public/swagger/index.html
# --- WARMFORGE (Email Warmup) ---
WARMFORGE_API_KEY=...REDACTED
WARMFORGE_API_URL=...REDACTEDe.ai/public/v1
WARMFORGE_API_DOCS=...REDACTEDe.ai/public/swagger
# --- SALESFORGE (Campaign Sending) ---
SALESFORGE_API_KEY=...REDACTED
SALESFORGE_API_URL=...REDACTEDge.ai/public/v2
SALESFORGE_API_DOCS=...REDACTEDge.ai/public/v2/swagger

=== SALESFORGE INTEGRATION (head -30) ===
src/integrations/salesforge.py — Salesforge v2 API, sends email via /emails/send, handles
threading via In-Reply-To headers, mailbox selection, batch send

=== INFRAFORGE INTEGRATION (head -30) ===
src/integrations/infraforge.py — InfraForge API, domain purchase, mailbox creation,
export-to-salesforge pipeline, workspace IDs for infraforge/salesforge/warmforge

=== WARMFORGE INTEGRATION (head -30) ===
src/integrations/warmforge.py — WarmForge v1 API (!not v2), mailbox warmup status,
heat score monitoring, domain-level aggregate warmup checks

NOT FOUND: megaforge.py, mailforge.py (Mailforge used via InfraForge API, not separate client)
```

### Summary

| Product | Integration File | Credentials | Notes |
|---------|-----------------|-------------|-------|
| Salesforge | `src/integrations/salesforge.py` | Present | Active. Primary email send layer. API v2. |
| Infraforge | `src/integrations/infraforge.py` | Present | Active. Domain purchase + mailbox provisioning. |
| Warmforge | `src/integrations/warmforge.py` | Present | Active. Warmup status monitoring. API v1 (not v2 — important). |
| Mailforge | No dedicated file | N/A | Referenced in `infra_provisioning_flow.py` and `deliverability_service.py` as a provider label; provisioned through InfraForge API, not a separate client. |
| Megaforge | No file, no credentials | Absent | Not integrated. No code references. |
| Primeforge | No file, no credentials | Absent | Not integrated. |
| Leadsforge | No file, no credentials | Absent | Not integrated. |
| Agent Frank | No file, no credentials | Absent | Not integrated. |

### Architecture Context

The current email infrastructure path (FCO-001 / Phase 19 decision, validated 2026-02-05):

```
InfraForge API
  → buy_domains() — .com domains at $14 USD/yr
  → create_mailboxes() — 2 mailboxes per domain
  → export_to_salesforge() — pushes to Salesforge workspace + triggers WarmForge warmup
  → WarmForge monitors heat score until ≥ 85

Salesforge API
  → /emails/send — sends outbound cold email using warmed mailboxes
  → mailbox selection by email address or mailbox_id
  → threading via In-Reply-To headers
```

Platform uses a **pre-warmed domain pool** model: domains and mailboxes are provisioned ahead of time against persona identities (names like `{firstname}{lastname}.io`, `team{firstname}.com`), warmed to heat score ≥ 85, then assigned to customers at onboarding from `resource_pool` table. This is the #312 custom domain pool referenced in the directive brief.

**Cost baseline (FCO-001):** 20 mailboxes + 10 domains = **$111 AUD/month** (at current Mailforge/Infraforge rates via InfraForge API).

---

## QUESTION 3 — MEGAFORGE DEEP DIVE

### What Megaforge Is

Megaforge is a managed multi-ESP bundle offered by Salesforge. Rather than provisioning a single infrastructure type, it automatically distributes sends across four provider types simultaneously:

- **Gmail** (Google Workspace mailboxes)
- **Outlook** (Microsoft 365 mailboxes)
- **Mailforge** (Salesforge's shared IP infrastructure)
- **Infraforge** (Salesforge's private dedicated infrastructure)

### Key Technical Details

| Attribute | Finding | Confidence |
|-----------|---------|------------|
| **ESPs used** | Gmail + Outlook + Mailforge + Infraforge (4-way split) | High — multiple sources confirm |
| **Daily send volume** | ~15 emails/mailbox/day at base (20-mailbox plan = ~300 emails/day total) | High |
| **Automatic failover** | Yes — if one ESP burns, sends route through remaining ESPs automatically | High |
| **Warmup included** | WarmForge warmup is included free with all Salesforge subscriptions; applies to Megaforge mailboxes | High |
| **Domain provisioning** | Managed by Salesforge/Megaforge (no BYO domain requirement stated at base tier) | Medium — detail not confirmed in public docs |
| **Per-customer isolation** | Unknown. Megaforge appears to be a workspace-level product, not a per-tenant isolated deployment. No documentation found confirming customer-level separation. | Low confidence — research gap |
| **Pricing at 20 mailboxes** | $69/mo USD ($107 AUD) | High |
| **Pricing at 50 mailboxes** | Not published — extrapolating from base rate suggests ~$170 USD ($263 AUD); likely volume discount applies | Low confidence |
| **Pricing at 100 mailboxes** | Not published | Unknown |

### What Is Not Confirmed

- Whether Megaforge allows custom domain names (e.g., `dave@teamsmith.co`) vs Salesforge-managed domains
- Exact tiers at 50 and 100 mailboxes — pricing page shows $69/mo as base only
- Per-customer isolation model — critical unknown for a multi-tenant SaaS platform
- Whether domains purchased under Megaforge are owned by the Agency OS account or by Salesforge

### Sources

- https://www.salesforge.ai/pricing (Megaforge listed as $69/mo add-on, 20 mailboxes base)
- https://prospeo.io/s/salesforge-pricing (multi-ESP description, 4-way split, ~15 emails/day/mailbox)
- https://syncgtm.com/blog/salesforge-review (failover confirmation, $69/mo)
- https://www.salesforge.ai/email-infrastructure (30-50 emails/day per inbox guideline; Warmforge included)

---

## QUESTION 4 — COMPARISON TABLE: MEGAFORGE vs #312 CUSTOM DOMAIN POOL

The #312 custom domain pool uses InfraForge to buy named domains (e.g. `teamjames.io`), creates mailboxes, warms via WarmForge, and assigns from a platform-level `resource_pool` to customers at onboarding.

| Dimension | #312 Custom Domain Pool (Current) | Megaforge |
|-----------|----------------------------------|-----------|
| **Build effort** | Already built and deployed. `infra_provisioning_flow.py`, `domain_provisioning_service.py`, `resource_assignment_service.py`, `warmup_monitor_flow.py` all exist. | Net-new integration. No Megaforge API documented publicly. Likely UI-only management or undocumented API. Estimated 5–10 days to integrate + test. |
| **Cost — 20 mailboxes** | ~$111 AUD/mo (InfraForge $93 + domains $18) | $107 AUD/mo ($69 USD × 1.55). Marginally cheaper. |
| **Cost — 50 mailboxes** | ~$265 AUD/mo (InfraForge volume rate ~$3.50/slot + domains) | Unknown — no published 50-mailbox tier. Risk of being more expensive. |
| **Cost — 100 mailboxes** | ~$500 AUD/mo (estimated) | Unknown. |
| **Resilience (ESP diversity)** | Single ESP type at a time (Infraforge = dedicated IPs). No automatic failover to other ESP types if a domain burns. | 4-way split across Gmail, Outlook, Mailforge, Infraforge. Automatic failover when one ESP burns. Materially stronger deliverability resilience. |
| **Per-customer naming control** | Full control. Domain names are generated to match persona names (e.g. `teamjames.io`, `jsmith.co`). Customer sees branded sender names. | Unknown. Megaforge may use Salesforge-managed generic domains. Per-customer naming unconfirmed — likely not available at $69/mo. |
| **Customer-agnostic pre-purchase** | Yes. Domains are bought from a pool before customer assignment. Customer gets a pre-warmed inbox on day 1. | Unknown. Megaforge likely provisions on-demand per workspace, not pre-pooled. Customer may wait for warmup. |
| **Platform-level isolation** | Full. Each customer gets their own named domain, tracked in `resource_pool` table, isolated in DB. | Unclear. Multi-tenant isolation not documented. Risk of shared reputation pools across Salesforge accounts. |
| **Ownership of domains** | Agency OS owns all domains. Portable if we leave InfraForge. | Likely Salesforge-owned or managed. Exit cost unknown. |
| **Risks and unknowns** | Single-ESP risk (all dedicated Infraforge IPs). No automatic failover. If one domain burns, only that domain is affected — not cross-customer. | (1) Per-customer isolation unconfirmed — shared reputation risk. (2) Custom domain naming unconfirmed. (3) Pricing at scale unpublished. (4) No public API — integration may require sales contact. (5) Salesforge vendor lock-in increases. |

---

## QUESTION 5 — RECOMMENDATION SCAFFOLD

Three options. No preference expressed — for Dave's decision.

---

### Option A: Continue #312 Custom Domain Pool

**What stays the same in #312:**
- No changes. Continue building InfraForge pool with persona-named domains.
- `infra_provisioning_flow.py` runs on schedule to keep buffer full.
- WarmForge monitors heat scores.
- Customers get pre-warmed, named domains at onboarding.

**New dependencies:** None.

**Dave actions needed:**
- Monitor InfraForge domain pool buffer as customer count grows.
- Consider adding a second ESP type (Mailforge shared + Infraforge dedicated) to the pool manually, to partially replicate Megaforge's resilience without using Megaforge.
- Decision: add dedicated IPs ($99 USD/IP/mo via InfraForge) for higher-volume customers or not.

**Trade-off:** Single-ESP exposure remains. Resilience gap vs Megaforge is real.

---

### Option B: Pivot to Megaforge

**What changes in #312:**
- `infra_provisioning_flow.py` partially retired or repurposed — Megaforge handles provisioning.
- New integration: `src/integrations/megaforge.py` required (no public API docs found — requires Salesforge sales contact to confirm API availability).
- `resource_assignment_service.py` would need to map Megaforge workspace mailboxes to customers instead of InfraForge domains.
- `domain_provisioning_service.py` persona-naming logic likely unusable — Megaforge likely uses Salesforge-managed domain names.
- Loss of custom domain naming (e.g. `teamjames.io`) unless Megaforge supports BYO domains (unconfirmed).

**New dependencies:**
- Megaforge API access (not publicly documented — may require enterprise tier or sales).
- Salesforge product roadmap dependency — if Megaforge pricing or features change, we are exposed.

**Dave actions needed:**
- Contact Salesforge sales to confirm: (1) Megaforge API availability, (2) per-customer isolation model, (3) pricing at 50 and 100 mailboxes, (4) BYO domain support, (5) customer-agnostic pre-provisioning capability.
- Get written confirmation of domain ownership.
- Evaluate whether per-customer naming (a differentiator we built) can be preserved.

**Trade-off:** Gains 4-ESP resilience and automatic failover. Loses domain naming control, likely loses pre-purchase pool model, increases Salesforge vendor dependency.

---

### Option C: Hybrid — Custom Domains for Naming, Megaforge for Sending

**Concept:** Buy and name domains via InfraForge (preserving persona naming control), then route those domains into Megaforge for multi-ESP distribution and sending instead of using Salesforge single-path.

**What changes in #312:**
- `domain_provisioning_service.py` unchanged — still buys persona-named domains via InfraForge.
- New integration: Megaforge ingests our BYO domains (unconfirmed — needs validation).
- `infra_provisioning_flow.py` export step changes from `export_to_salesforge()` to `import_to_megaforge()` (requires API).
- WarmForge warmup phase — need to confirm if Megaforge includes warmup for BYO domains or if WarmForge still handles it separately.

**New dependencies:**
- Megaforge BYO domain support (unconfirmed — highest-priority question).
- Megaforge API for programmatic domain import.
- Potentially: Megaforge charges per-domain rather than flat rate if we bring our own domains.

**Dave actions needed:**
- Same Salesforge sales questions as Option B, plus specifically: does Megaforge support BYO domains from InfraForge?
- Confirm warmup flow: does Megaforge include warmup for BYO domains, or must WarmForge still run?
- Get pricing for hybrid scenario (BYO domain Megaforge rate vs managed-domain Megaforge rate).

**Trade-off:** If BYO domains are supported, this is the best of both worlds — named domains with multi-ESP resilience. If BYO domains are not supported, this option collapses to Option A or B.

---

## CRITICAL UNKNOWNS (Pre-Decision Research Gaps)

Before any decision involving Megaforge, these must be answered by Salesforge directly:

1. **Per-customer isolation:** Do Megaforge accounts share sending reputation pools across customers, or is each workspace fully isolated?
2. **BYO domains:** Can we import InfraForge-provisioned, persona-named domains into Megaforge, or does Megaforge only use Salesforge-managed domains?
3. **Pricing at scale:** What is Megaforge pricing at 50, 100, and 200 mailboxes?
4. **API availability:** Is there a Megaforge API for programmatic provisioning, or is it UI-only management?
5. **Domain ownership:** If we provision domains through Megaforge, do we own them or does Salesforge?
6. **Pre-purchase pool model:** Can Megaforge pre-provision and warm mailboxes before customer assignment, or is it always on-demand per workspace?

---

*Research completed: 2026-04-07. Read-only. No signups, no purchases, no API calls made.*
