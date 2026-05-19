# Keiracom — Go-to-Market Launch Kit

**Status:** DRAFT v1 (KEI-131) — pending Dave approval.
**Author:** Orion, 2026-05-18.
**Constraints anchored:** LAW II (AUD only — no USD anywhere); `feedback_pre_revenue_reality` (zero customers, no social proof, no testimonials, no logos); positioning per `frontend/app/(marketing)/page.tsx`; competitive context per `docs/research/peta_composio_market_analysis_2026-04-26.md`.

This kit is three deliverables in one file so Dave can review the through-line: 1-pager → email → social posts must all say the same thing.

---

## §1 — One-Pager (positioning doc)

### Tagline

> **OpenClaw is Linux. Keiracom is RHEL.**
> Managed AI compute with built-in governance. Global on day one.

### Who this is for

Operators running multi-agent AI workloads who have outgrown solo Claude / Cursor / Cline setups and now need the workforce to behave like a team:

- Founders + lean technical teams running 3+ AI agents concurrently against a shared codebase.
- Solo consultants and small agencies who need governance, not just inference.
- Platform builders who want managed infra so they can ship product, not babysit tmux.

We are **not** a fit for: anyone needing a packaged SaaS for non-technical end-users (Keiracom is operator-tier); anyone who needs only one agent (use Claude Code directly); anyone with a hard requirement for on-prem only at this stage (`Self-Hosted` tier ships post-beta).

### Why now

Composio raised US$25M Series A and Peta launched in late 2025. Both solve tool-level governance — *what an agent can call*. Neither governs *how the agent reasons, decomposes, or peer-reviews*. ByteBridge's market scan put it bluntly: "none of these platforms govern how agents reason, decompose tasks, or peer-review decisions."

That is the wedge. Keiracom runs one layer above the tool plane. Reasoning, decomposition, peer review, audit trail — built in. Composio plugs in below us; we don't compete with it.

### What you get

Six tiers, one product. Differences are scale, not features.

| Tier | Best for | Tier behaviour |
|---|---|---|
| **Sandbox** | Trying it out | Developer sandbox preset, async support |
| **Solo** | One operator | Solo-operator governance preset, async support |
| **Pro** | Small team / heavy solo | Priority async support, audit-log retention extended |
| **Team** | Multi-seat | Team governance preset, role-based context separation |
| **Distributor** | Reselling capacity | Channel terms, multi-tenant separation |
| **Self-Hosted** | Air-gap / sovereign | Same harness, your infrastructure |

Every tier includes the full agent-governance stack: peer-review gates, Step-0 RESTATE discipline, four-store completion enforcement, audit-log retention, declared-callsign identity. The smaller tiers cap concurrent threads and context window; the larger ones lift those caps.

### Pricing

**$AUD TBA — private beta pricing.** Founding-cohort terms will lock at announcement; we will not advertise a price until Dave ratifies the model.

### What we honestly do not have yet

- **Customer logos.** Zero paying customers at launch. Founding cohort opens at launch.
- **SOC 2.** Composio has it; we do not, yet. On the roadmap, not the launch.
- **150+ pre-built tool integrations.** Composio has 150+; we don't. Tool integration breadth is a roadmap item, not a launch feature.
- **Brand recognition.** This is the first time most people are hearing about us.

We say this on the record. The wedge is what we have; everything else is a roadmap. If that mismatch is a dealbreaker, this is not the product for you yet.

### Call-to-action

`keiracom.com` — join the founding cohort waitlist. Pricing announced at cohort open.

---

## §2 — Launch Email Template (for the first 100 signups)

**Subject:** You're on the Keiracom founding-cohort list — what happens next

**From:** Dave Stephens, Keiracom <dave@keiracom.com>

**Body:**

Hi {first_name},

You signed up for the Keiracom founding cohort. Thanks. There are about {cohort_count} of you ahead of full launch, and I want to be straight about what that means.

**What Keiracom is.** Managed AI compute with built-in governance. We run one layer above the tool plane — peer-review gates, Step-0 RESTATE discipline, four-store completion enforcement, audit-log retention, declared identity per agent. If you have ever run two Claude Code sessions in parallel and watched them step on each other's commits, you know the gap we're closing.

**Where we are today.** Pre-revenue. Zero paying customers. Private beta. The product is real and the agents are running production workloads inside our own org. I am not going to tell you a story about how many people use it, because nobody outside our team does yet. You are the founding cohort.

**What you get for being early.**

1. **Direct line.** This email thread is real. Reply and I read it.
2. **Founding-cohort pricing locked at cohort open.** $AUD, no USD invoices.
3. **Input on the roadmap.** The next six tiers exist on paper — Sandbox, Solo, Pro, Team, Distributor, Self-Hosted. Which one you need shapes which one we harden first.

**What we ask in return.** Honest feedback. If something breaks, tell us; if a tier is mispriced for what it does, tell us; if the governance model gets in your way, tell us. Founding-cohort feedback shapes the product more than any analyst report ever will.

**When the gate opens.** I will email this list before the public launch. You will get access first; pricing locks at the moment of cohort open. No surprise renewals, no auto-upsells.

If any of this is not a fit, just reply with "remove" and you're out of the list with no friction.

Otherwise — talk soon.

Dave Stephens
Founder, Keiracom
keiracom.com

P.S. The product naming convention: OpenClaw is the open-source harness; Keiracom is the managed commercial layer. Linux / RHEL. If you wanted a one-line mental model.

---

## §3 — Social Launch Posts (3)

### Post 1 — LinkedIn (positioning post, longer-form)

**Hook (line 1):** Composio governs *what your agents can call*. Keiracom governs *how they think*.

**Body:**

For the last two years the "agent governance" conversation has been about tool access — OAuth, scopes, RBAC at the API layer. Composio raised US$25M Series A for this and they did it well. Peta is doing it adjacent. Both are useful; neither is what we're building.

The gap that opens up the moment you run 3+ agents in parallel against a shared codebase isn't "did the agent have permission to call the GitHub API." It's: did the agent restate the objective before acting? Did a peer review the decision? Did completion produce verifiable evidence in all four required stores, or just one? Did anyone *check*?

That is agent-level governance. Not tool-level. One layer up.

Keiracom is the managed compute layer where that governance is built into the harness — not a policy doc, not a wrapper, not a linter. It runs at every agent turn.

OpenClaw is the open-source harness underneath. Keiracom is the commercial managed offering. Linux / RHEL.

Australia-first. $AUD pricing. Pre-revenue, founding cohort open. No customer logos to show because we have none yet — first ones in shape what gets built next.

`keiracom.com`

---

### Post 2 — Twitter / X (snap version, three tweets, no thread numbering)

**Tweet 1 (single shot):**

> OpenClaw is Linux. Keiracom is RHEL.
>
> Managed AI compute with governance built into the harness — peer review, Step-0 restate, four-store completion, audit trail. One layer above tool-access governance.
>
> Pre-revenue. Founding cohort open. AUD. → keiracom.com

**Tweet 2 (optional follow-up if Tweet 1 gets traction):**

> The category we're not in: tool-access governance (Composio, Peta, Arcade). They handle OAuth and RBAC at the API layer. Good work, useful, not our wedge.
>
> The category we are in: agent-reasoning governance. What's the agent doing, did a peer review it, where is the evidence.

**Tweet 3 (optional follow-up, founder voice):**

> Zero customers at launch. I'm not going to fake a logo wall. If you've ever run two Claude Code sessions in parallel and watched them collide, you already know the gap we're closing — founding cohort: keiracom.com

---

### Post 3 — Build-in-public update (LinkedIn or X, recurring cadence)

**Hook:** Building Keiracom in public — week one of cohort open.

**Body:**

Week one of the Keiracom founding cohort is live. Three things I want to say on the record so future-me can be held to them.

1. **Pricing.** $AUD only. No USD invoices, no "list price in dollars, billed in your currency at our convenience" trick. AU-first means AU-first.

2. **Social proof.** I will not put a customer logo on the site that doesn't belong there. We have zero paying customers today; when we have one, we'll say "one" before we say "trusted by leading teams."

3. **The wedge.** Agent-reasoning governance — peer review, Step-0 restate, four-store completion, audit trail. Composio governs tool access. We govern how the agent decides what to do next. One layer up.

This is the version of "build in public" where the embarrassing part — pre-revenue, no logos, six paper tiers — stays on the page. If you want to see whether we actually close the gap, the only honest answer is: try the sandbox tier when it opens, and tell us what breaks.

Founding cohort signup: `keiracom.com`. Reply to me directly if the wedge is interesting and you want context before you commit a credit card to anything.

---

## §4 — Reviewer notes (delete before publish)

- All three artifacts ground the same positioning: agent-reasoning governance, one layer above tool-access governance, AU-first, $AUD only, no fake social proof, founding cohort open.
- Pricing is deliberately deferred ("$AUD TBA — private beta pricing") because Dave has not ratified per-tier prices. `frontend/app/(marketing)/page.tsx` ships `priceAud: null` on all 6 tiers; this kit matches that posture.
- The "what we honestly do not have yet" section in the 1-pager is unusual for marketing copy but is required by `feedback_pre_revenue_reality`. Honest pre-revenue posture is the brand. If Dave wants to soften it pre-publish, fine, but it should not be deleted.
- Email template is set to send from `dave@keiracom.com` per the build-in-public posture — founder voice is the asset; an `info@` send would dilute it.
- Twitter / X post 1 is the canonical shot; posts 2 and 3 fire only if engagement on post 1 warrants. Don't schedule all three at the same time — pace.
- LinkedIn post 3 (build-in-public) is a recurring template — re-use every Friday with the current week's milestone. The three on-the-record commitments stay constant.

**Open items for Dave:**

- (a) Approve verbatim copy of the tagline pair: "OpenClaw is Linux. Keiracom is RHEL."
- (b) Approve the on-the-record commitments in §3 post 3 (AUD-only, no fake logos, agent-reasoning wedge).
- (c) Confirm send-from address for the launch email (default: `dave@keiracom.com`).
- (d) Confirm cohort-open trigger condition (current default phrasing: "before the public launch" — fine to keep vague, or pin to a date once the launch date is locked).
