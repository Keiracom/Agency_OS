# Agency OS — Email Provisioning Onboarding Flow Spec

**Status:** RATIFIED (Variant A locked) — pending external dependencies for Phase 1 launch
**Author:** Aiden, 2026-05-07
**Review:** Elliot dual-approval per repo convention
**Authority:** CEO directive (2026-05-07) via Max-COO

## Frozen design decisions

- **Domain ownership:** Agency OS as buyer-of-record, user-transfer on churn (Max-ratified, legally viable per AU Privacy Act + SPAM Act risk-check 2026-05-07)
- **Customization:** HIDE DNS/DKIM/SPF in default UI, EXPOSE via "Advanced settings" toggle
- **BYO domain:** Phase 2 only — Phase 1 is vendor-provisioned exclusively (Max Q3)
- **Persona:** AU SMB marketing agency owner, non-technical, "just works" expectation
- **Domain transfer SOP:** separate doc, NOT pre-built before launch — pre-stage ToS legal language + test one transfer (Max Q4)
- **Variant:** A (pre-warmed Day 1, TTV 2-48hr) — locked per Primeforge confirmation 2026-05-07

---

## Step 1: Pre-Signup Marketing Site

- Headline: "We set up your complete email infrastructure. No DNS or servers to manage."
- TTV copy (specific, not generic): **"Send your first cold email within 24 hours"**
- CTA: "Start Free Trial" (no credit card required)

## Step 2: Signup Form (<2 min)

- Collect: email, password, company name, ABN
- Skip: detailed ICP (progressive disclosure)
- UX: single form, no multi-step wizard
- **Free-trial bounds:** 14-day free trial. Convert to paid OR mailbox suspended at Day 14. Domain remains registered in our buyer-of-record account during suspension.

## Step 3: Email Setup Dashboard Welcome (<5 min user time)

- Show: "Email Setup — 3 steps to send"
- **Domain provisioning (vendor-provisioned only, BYO deferred to Phase 2):**
  - User picks domain name (free text + availability check)
  - Confirm: "We'll register and manage [chosen-domain]. You can transfer it to your own registrar at any time via support."
  - User clicks "Provision"
  - Background: Agency OS calls registrar API (Namecheap/Route53), starts DNS configuration

## Step 4: DNS Verification (<10 min user time, 24-48 hr automation)

- Show: "We've registered yourcompany-outreach.com.au — verifying DNS now."
- Display 3 DNS records (SPF/DKIM/DMARC) with explanation: "These are auto-applied at our end. No action required from you."
- Status: "Verification in progress — typically completes within 1-2 hours"
- **Verification mechanism:**
  - Webhook-first for registrars that support it (Cloudflare native, Route53 via SNS)
  - Exponential-backoff polling fallback for registrars without webhook (Namecheap, GoDaddy)
- Auto-verification: webhook OR poll → status update with no page refresh required
- Error handling: if DNS verification times out at 48 hours → escalate to support, offer manual override
- User experience: passive, watches progress bar, can leave page and return

## Step 5: Mailbox Provisioning (<1 min user time, fully automated)

- Show: "Email ready to send. Activating your warmed mailbox..."
- Background: Agency OS requests pre-warmed mailbox from **Primeforge** (vendor-claimed pre-warmed inventory, pending API verification — Salesforge API key 401 blocker is a Phase 1 launch dependency)
- Vendor SLA: pre-warmed inventory pulled, IP reputation already established
- User notification: "Your mailbox is live. Send your first campaign now."
- Time: 1-2 minutes for vendor handoff

## Step 6: Self-Test Send (<2 min)

- Show: "Send a test email to YOURSELF — confirms your mailbox is wired before you touch real prospects"
- Pre-fill: simple subject + body to user's signup email
- One-click "Send Self-Test"
- Verifies: mailbox reachable, SPF/DKIM/DMARC pass on real email infra, signature renders correctly
- **GATE:** must complete before Step 7 unlocks (prevents Day-1 wiring failure burning live prospects)

## Step 7: First Campaign Test (<5 min)

- Show: "Compose your first cold email"
- Pre-fill: simple subject + body template
- Target: small test list (5-10 contacts)
- UX: one-click "Send Test"
- Time-to-First-Send: 2 hours minimum (DNS lucky), 48 hours typical

## Variant A success metric

- 80% of users complete self-test (Step 6) within 48 hours of signup
- TTV: 2-48 hours

---

## POST-LAUNCH

### Customization Settings — HIDE/EXPOSE matrix

**Default UI (always visible):**
- Domain name: read-only (transfer via support)
- Mailbox count: upgrade path (1 → 2 → 5 → 10 dedicated)
- Sender display name: editable per campaign
- Frequency limits: informational ("Your limit: 40/hour")
- Mailbox health monitoring: opt-in alerts

**"Advanced settings" toggle (accessible, NOT fully hidden):**
- SPF/DKIM/DMARC records (read-only display + 3rd-party integration support)
- DKIM selector (advanced users may want to add another sender)
- IP rotation policy (informational, opt-out available)
- Webhook events (for users running their own analytics)

**Rationale:** Hidden-by-default protects non-technical users from breaking their infra. "Advanced" toggle prevents dev-mode-fork support burden when power users need 3rd-party tool integration (Mailchimp, Customer.io, debug deliverability).

### Failure Modes + SLA

- DNS verification timeout (>48hr): support escalation within 1 business day
- Mailbox suspension risk: auto-monitored, user alerted before suspension
- Domain expiration: 60-day pre-expiry email, 30-day final notice, auto-renewal default-on
- Hard bounce rate spike: pause campaign + notify user

### Free-Trial Suspension Lifecycle

- Day 14: trial ends. Convert to paid OR mailbox suspended.
- Day 14-44 (30-day grace): user can re-activate. Mailbox preserved, slot held in pool. Domain remains in our buyer-of-record account.
- Day 45: domain released, mailbox slot returns to pool, user data retained for 30 more days.
- Day 75+: user data archived per privacy policy (privacy policy defines retention period + secure-deletion SLA per AU Privacy Act NDB obligations — drafted alongside the 4 ToS clauses by external AU counsel).

**Rationale:** Prevents 10-slot-flat-cost (Primeforge minimum) from being burned by abandoned signups while giving users reasonable re-activation window.

### Domain Transfer at Churn

- User initiates via support ticket
- Identity verification: account email + payment method match
- Process: WHOIS transfer to user-supplied registrar account
- Timeline: 10 business days post-churn (per ToS clause 3)
- Cost: included in subscription (no charge)

**Pre-launch deliverables:**
1. ToS legal language pre-staged (see "Pre-Launch Legal Deliverables" below)
2. ONE test transfer of an Agency-OS-owned test domain to a test secondary account before relying on it for users
3. Full SOP doc as separate task — NOT before first user signup; build SOP when first churn requires it

### Pre-Launch Legal Deliverables

**Buyer-of-record model is legally viable in AU.** No SPAM Act or Privacy Act blockers (risk-check 2026-05-07). 4 specific ToS/DPA clauses MUST be in place before first paid signup:

1. **SPAM Act clause** — designate client as authorised "sender" (composing/authorising message). Agency OS = infrastructure + WHOIS only. Client indemnifies for SPAM Act violations from message content / recipient list / unsubscribe non-compliance.

2. **Privacy Act clause + DPA** — Agency OS as service provider holding personal info on behalf of client. Written Data Processing Addendum (DPA). Client = primary APP entity, notifies OAIC under NDB scheme. Both parties cooperate on breach notification. AU has NO controller/processor distinction (unlike GDPR), so any APP entity holding personal info is independently liable; contractual DPA reduces but doesn't eliminate.

3. **Domain ownership + transfer clause** — Agency OS owns domain, client has non-transferable usage license. On churn (30-day notice + invoice settlement), Agency OS transfers domain within 10 business days, contingent on proof of recipient entity. Dispute resolution via arbitration (not auDA).

4. **Indemnity + insurance clause** — client indemnifies Agency OS for third-party claims (IP, defamation, SPAM Act, Privacy Act).

**Mandatory pre-launch action:** engage AU legal counsel (privacy + telecom specialist) to draft these 4 clauses + DPA template + privacy policy retention/deletion clause. Bounded ~1-2 week cycle. Sequenced AFTER Salesforge API key fix (so we know what platform features need legal-clause coverage) but BEFORE first paid signup.

**Note:** This spec captures risk-surfacing only, not legal review. External counsel writes/reviews the actual clauses.

---

## Phase 1 Launch Dependencies (consolidated)

External actions:
1. **Salesforge API key fix** (Dave) — current 401 blocks programmatic verification of Primeforge pre-warmed claim + 6-function rebuild in `domain_provisioning_service.py`
2. **Programmatic confirmation of Primeforge pre-warmed inventory** (post-API-key-fix) — converts vendor-claimed → API-verified
3. **External AU legal counsel** — drafts 4 ToS clauses + DPA + privacy policy retention clause (~1-2 weeks, post-API-fix)
4. **6-function rebuild in `domain_provisioning_service.py`** — architecture intact, logic stub-shaped (post-API-fix, endpoints mappable via Swagger once 401 resolved)
5. **ONE test domain transfer** (operational validation, ~1 day)
6. **Final marketing copy** (Variant A "24 hour" copy approved by Dave)

Phase 1 launch is NOT ready until all 6 are complete.

---

## CHANGE LOG

- v1 (2026-05-07): initial dual-variant draft (A pre-warmed + B warmup-wait), 7-step flow, domain ownership recommendation
- v2: incorporated Elliot's 5 sharpenings (webhook DNS, weekly summary, advanced toggle, self-test split, specific TTV) + Q5 free-trial bounds + Max's Q3/Q4 answers
- v3: incorporated Elliot's legal-question check findings — 4 mandatory ToS clauses + DPA template added as pre-launch deliverables; transfer timeline updated to 10 business days; external AU counsel engagement documented
- v3.1: privacy-policy retention/deletion SLA language tied to AU Privacy Act NDB obligations
- v4 (this version, ratified): pruned to Variant A locked per Primeforge confirmation 2026-05-07; Variant B + decision tree removed; Salesforge API key 401 noted as blocker; "Primeforge pre-warmed (vendor-claimed, pending API verification)" caveat added per Max correction
