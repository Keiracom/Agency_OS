# Agency OS Cold Email Sequence

**Version:** 1.0  
**Created:** 2026-02-08  
**Owner:** Content Stream E  
**Purpose:** 4-email cold outreach sequence for Australian marketing agencies

---

## Sequence Overview

| Email | Timing | Purpose | Goal |
|-------|--------|---------|------|
| Email 1 | Day 0 | The Hook | Spark curiosity, establish relevance |
| Email 2 | Day 3 | Value Add | Provide value, position expertise |
| Email 3 | Day 7 | Social Proof | Overcome skepticism with results |
| Email 4 | Day 14 | Breakup | Create urgency, soft close |

**Target Personas:** Busy Ben, Scaling Sarah, AI Andy  
**Expected Performance:** 45%+ open rate, 5%+ reply rate

---

## Email 1: The Hook

**Subject Lines (A/B Test):**
- `{{company}} + AI outreach?`
- `Quick question about {{company}}'s growth`
- `Saw {{company}}'s work on {{recent_project}}`

**Preview Text:** `Found something interesting when researching {{company}}...`

**Body:**

```
{{first_name}},

I was researching agencies in {{city}} and {{company}} caught my attention — the {{recent_project_or_client}} work is solid. That kind of creative deserves more visibility.

Quick question: What percentage of your week goes into finding new clients vs. doing the actual work you're brilliant at?

For most agency founders I talk to, it's north of 40%. Which is backwards.

We built Agency OS specifically for Australian agencies like {{company}}. It's an AI system that finds, qualifies, and books meetings with ideal clients — across 5 channels — while you focus on client delivery.

One of our early users called it "having a BDM who works at 3am and never asks for a pay rise."

Worth a 15-min chat to see how it'd work for {{company}}?

[BOOK A 15-MIN CALL →]

— Dave
Founder, Agency OS

PS — We're only working with 20 founding agencies. 17 spots left.
```

---

## Email 2: Value Add

**Subject Lines:**
- `Re: {{company}} + AI outreach?`
- `This might help with {{pain_point}}`
- `Thought you'd find this useful`

**Preview Text:** `Not adding to the noise — sharing something tactical`

**Body:**

```
{{first_name}},

Not trying to clog your inbox — I know you're busy.

But I thought this might be useful: We just published our internal framework for scoring leads before spending any time on them.

"The 47 Signals That Predict Which Leads Will Buy"
[LINK TO LEAD MAGNET]

It's the exact system we use in Agency OS. Factors like:
— Tech stack signals (are they using marketing automation already?)
— Growth signals (hiring? fundraising? new website?)
— Timing signals (fiscal year end, contract renewal periods)
— Engagement signals (opened your email? visited your site?)

Each lead gets a 0-100 score. We only call leads scoring 85+.

If you're curious how we'd score leads for {{company}}, I'm happy to run a quick analysis — no strings attached.

Just hit reply with "score my leads" and I'll pull together a sample.

— Dave

PS — The article takes 4 minutes to read. The framework takes 4 weeks to build yourself. Your call.
```

---

## Email 3: Social Proof

**Subject Lines:**
- `How {{similar_agency}} booked 12 meetings last month`
- `Case study: {{industry}} agency results`
- `This worked for an agency like {{company}}`

**Preview Text:** `Same size, same market, different results`

**Body:**

```
{{first_name}},

Quick case study I thought you'd appreciate:

{{similar_agency}} (a {{agency_type}} agency in {{state}}, similar size to {{company}}) was drowning in outreach.

Their founder was spending 20+ hours a week on business development. Cold emails. LinkedIn stalking. Follow-up calls that went nowhere. Meanwhile, client work was slipping.

Sound familiar?

After 60 days with Agency OS:

📊 Results:
— 12 qualified meetings booked (from cold outreach alone)
— 15 hours/week freed up for billable work
— 2 new retainer clients closed ($8K/month combined)
— 47% demo show rate (industry average is 35%)

Their founder told me: "It's like having a full-time BDM who never takes a sick day, never needs training, and costs a fraction of a hire."

The difference? Agency OS doesn't just send emails. It orchestrates 5 channels — email, LinkedIn, SMS, voice AI, and direct mail — all working together to book meetings with people who actually want to talk.

Want to see if we can replicate this for {{company}}?

I can walk you through exactly how it works in 15 minutes.

[BOOK A QUICK DEMO →]

— Dave

PS — We're Australia-native. ACMA compliant. Local numbers. No dodgy stuff. Your reputation stays intact.
```

---

## Email 4: Breakup

**Subject Lines:**
- `Should I close your file?`
- `Last message from me`
- `Taking you off the list`

**Preview Text:** `No hard feelings — timing is everything`

**Body:**

```
{{first_name}},

I've reached out a few times about Agency OS and haven't heard back.

No stress — I'll assume the timing isn't right for {{company}} right now.

I'm removing you from our outreach sequence. No more emails from me.

But before I go, a quick thought:

The agencies that are winning right now aren't the biggest or the most talented. They're the ones that systematised their growth while everyone else is still doing it manually.

AI is moving fast. The window for early-mover advantage is closing.

If you ever want to explore what AI-powered outreach could do for {{company}}, I'm here. Just reply to this email — I keep an eye on my inbox.

All the best,

Dave
Founder, Agency OS

---

PS — Know another agency owner who's more ready for this? 

I'm happy to offer them the same founding member deal (50% off for life). 

Just reply with their name and I'll reach out on your behalf — no obligation for them, and I'll let them know you recommended them.
```

---

## Personalisation Variables

| Variable | Source | Example |
|----------|--------|---------|
| `{{first_name}}` | Apollo/Enrichment | Sarah |
| `{{company}}` | Apollo/Enrichment | Digital Spark Agency |
| `{{city}}` | Apollo/Enrichment | Melbourne |
| `{{state}}` | Apollo/Enrichment | VIC |
| `{{recent_project_or_client}}` | Manual research / AI scrape | Woolworths rebrand |
| `{{similar_agency}}` | Case study match | Creative Edge |
| `{{agency_type}}` | Apollo industry | digital marketing |
| `{{pain_point}}` | Persona match | scaling without hiring |

---

## Sending Rules

1. **Timing:** Send Tue-Thu, 8-10am recipient local time
2. **Domain:** Rotate across 3 warmed domains
3. **Volume:** Max 50 emails per domain per day
4. **Throttle:** 60-120 second delay between sends
5. **Unsubscribe:** Link in footer (ACMA compliance)
6. **Reply handling:** Monitor within 2 hours during business hours

---

## Performance Benchmarks

| Metric | Target | Alarm |
|--------|--------|-------|
| Open rate | 45%+ | <35% |
| Reply rate | 5%+ | <3% |
| Meeting book rate | 3%+ | <1.5% |
| Bounce rate | <3% | >5% |
| Unsubscribe rate | <0.5% | >1% |

---

*Sequence created for Agency OS launch campaign. Use with Salesforge + InfraForge setup.*
