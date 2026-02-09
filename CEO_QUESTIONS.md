# CEO Questions Queue
*Created: 2026-02-09*
*Status: Pending deep-dive answers*

---

## 1. Voice AI Stack (Priority)
- Full architecture breakdown of the voice AI pipeline
- What is Vapi's role, what is Telnyx's role, how do they connect?
- What is a "voice KB" that Smart Prompts generates — is it a knowledge base document that gets fed to a voice agent?
- Cat the relevant files: Vapi integration, Telnyx integration, voice KB generation logic in Smart Prompts
- What works, what's broken, what's missing?
- The brief said "landline only, not mobile" — what specifically causes that limitation?

## 2. Outreach Orchestration
- How does multi-channel outreach actually execute?
- When ALS scores a lead and assigns it to a channel (email/SMS/LinkedIn/voice), what happens next?
- Cat the flow that takes an enriched, scored lead and executes outreach
- How does channel sequencing work — does a lead get email first, then SMS if no reply, then voice? Or all at once? What's the logic?

## 3. Email Infrastructure
- Salesforge + Warmforge — how are they integrated?
- How many sending domains/mailboxes are warmed?
- What's the current deliverability status?
- What's the sending volume capacity per client?

## 4. SMS Infrastructure
- ClickSend integration — cat the actual code
- What does one-way SMS look like vs the missing two-way?
- What's the webhook handler gap for inbound replies?

## 5. Response Handling
- When a prospect replies to an email, SMS, or LinkedIn message — what happens?
- Is there an inbound pipeline that captures replies, classifies intent (interested/not interested/meeting request), and routes them?
- Or does the system only send outbound with no reply handling?

## 6. CRM Sync
- The data flow says "→ CRM Push" at the end. Push to what?
- The customer's existing CRM? Our internal system?
- What CRM integrations exist and what data gets synced?

## 7. Onboarding Flow
- When a new customer signs up, what actually happens?
- ICP definition — is that a form, a wizard, an AI-guided process? Cat the onboarding flow
- How does ICP definition translate into ABN search parameters?

## 8. ALS Scoring
- How does it actually work?
- What signals feed into the score?
- What are the thresholds beyond the 85+ for Tier 5?
- How does channel allocation work based on score?

## 9. CIS (Conversion Intelligence System)
- The brief mentioned it learns from outreach patterns
- What does it actually do today?
- Is it built or conceptual?

## 10. Billing & Subscription Management
- How do customers pay? Stripe?
- What enforces tier limits (1,250 leads for Ignition, etc.)?
- Is there usage metering?

## 11. Security & Auth
- How does customer authentication work? Supabase Auth?
- RLS policies — are they tested?
- Multi-tenancy — is customer data properly isolated?

## 12. Monitoring & Observability
- Sentry is listed for logs. What actually gets monitored?
- Error tracking, API call failures, enrichment success rates, outreach delivery rates?
- Or is Sentry just configured but not instrumented?

## 13. The 27 Prefect Flows
- Full list with one-line descriptions
- Which ones are active, which are stale?

---

*These questions require file reads across the codebase. Tackle in fresh session with full context.*
