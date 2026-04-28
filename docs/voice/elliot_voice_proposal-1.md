# Investor-Grade Voice AI: "Elliot Voice"

## Proposal for CTO Review — April 2026

**Status:** Idea. Not a directive. Dave wants Elliot and Aiden to review, challenge, and give their opinion before any build decision.

**Origin:** During investor roleplay preparation, Dave demonstrated the concept of bringing an AI CTO onto investor calls. The concept landed — investors responded to an AI that could answer technical questions, admit mistakes, construct novel arguments, and hold a conversation without Dave present. This document proposes building a real version of that capability.

---

## 1. What This Is

A purpose-built voice agent — separate from the customer outreach voice AI (Alex/ElevenAgents + Haiku) — designed for high-stakes conversations where intelligence, nuance, and reasoning matter more than cost and latency.

Primary use case: investor calls during the pre-seed raise. Dave introduces "Elliot, my CTO" on video calls. Elliot answers technical questions, walks through unit economics, explains architecture decisions, and handles adversarial questioning from investors.

Secondary use case (post-fundraise): customer onboarding calls, partner conversations, media interviews — any conversation where Agency OS needs a technical voice that isn't Dave.

Long-term use case: productised version for Agency OS customers — every agency gets their own AI account manager that can join prospect discovery calls.

This is NOT a replacement for the ElevenAgents + Haiku outreach stack. That stack handles thousands of prospect calls at $0.15 each. This handles 5-50 high-value calls at ~$10 each. Different brain, same voice infrastructure principles.

---

## 2. Why Not Just Upgrade ElevenAgents?

ElevenAgents is built for outbound phone calls with a static knowledge base and retrieval-augmented generation (RAG). That architecture has three limitations that make it unsuitable for investor conversations:

**Limitation 1: Retrieval is lossy.** RAG searches for relevant chunks from a knowledge base per question. It frequently misses context that's relevant but not keyword-matched. When an investor asks "tell me something that went wrong during the build," RAG might pull a cost model section instead of the Bondi fabrication incident. The investor gets a technically accurate but irrelevant answer.

**Limitation 2: Model ceiling.** ElevenAgents runs Haiku for cost efficiency. Haiku is excellent at structured tasks (affordability gates, evidence refinement, draft emails). It cannot construct novel arguments, reason through ambiguous questions, or build a funnel model on the fly from component data points. The intelligence gap between Haiku and Opus is not incremental — it's categorical.

**Limitation 3: No conversation memory.** Most voice AI platforms treat each turn independently. The investor says something in minute three; by minute twenty the AI has no memory of it. Real conversations build on prior exchanges. Elliot Voice must maintain full conversation history within a single call.

**Proposed solution:** Build a custom voice pipeline where we control the LLM, the context, the system prompt, and the conversation memory. Use the same voice synthesis and speech recognition providers, but orchestrate them ourselves.

---

## 3. Architecture

### 3.1 Stack

```
[Investor speaks]
       ↓
[Deepgram Nova-3] — speech-to-text, 200ms latency, Australian accent support
       ↓
[Orchestrator (Python)] — manages turn-taking, silence detection, conversation history
       ↓
[Anthropic Opus API] — reasoning engine, 200K token context window
       ↓
[ElevenLabs API] — text-to-speech, custom Australian male voice, streaming
       ↓
[WebRTC bridge (Daily.co or LiveKit)] — joins Zoom/Meet as audio participant
       ↓
[Investor hears Elliot]
```

### 3.2 Component Selection Rationale

**Reasoning — Anthropic Opus (claude-opus-4-6 or claude-opus-4-7):**
- PhD-level reasoning (91.3% GPQA Diamond)
- 200K token context window — entire company knowledge fits in system prompt without retrieval
- Extended thinking available for complex questions (can be toggled per-call)
- Same model family as the engineering team — consistency in reasoning patterns
- Prompt caching available — 90% cost reduction on system prompt after first turn

**Voice synthesis — ElevenLabs:**
- Most natural-sounding voices available
- Streaming support — first audio byte before full response is generated
- Custom voice creation — can build a distinct "Elliot" voice
- SSML-like controls for pacing, emphasis, pauses
- Australian accent options available
- Turbo v2.5 model for lowest latency (~300ms)

**Speech-to-text — Deepgram Nova-3:**
- Fastest real-time transcription available
- Strong Australian English accuracy
- Streaming support — transcribes while speaker is still talking
- Endpointing detection — knows when the speaker has finished
- $0.0043/minute — negligible cost

**Orchestration — Pipecat (open source) or custom Python:**
- Pipecat: MIT-licensed framework by Daily.co specifically for voice AI agents
- Handles turn-taking, interruption detection, silence thresholds
- Native integrations with Deepgram, ElevenLabs, Anthropic
- WebRTC support via Daily.co transport
- Alternative: custom Python with WebSocket management — more control, more build time

**Call integration — Daily.co or LiveKit:**
- WebRTC rooms that can be bridged into Zoom/Meet/Teams
- Elliot joins as an actual audio participant, not speakerphone
- SIP bridge available for phone dial-in fallback
- Free tier covers low-volume usage (investor calls only)

### 3.3 Infrastructure

| Component | Hosting | Notes |
|-----------|---------|-------|
| Orchestrator | Vultr Sydney (existing VPS) | Co-located with existing infrastructure |
| Deepgram | Cloud API | No self-hosting needed |
| ElevenLabs | Cloud API | No self-hosting needed |
| Anthropic | Cloud API | Existing API access |
| Daily.co / LiveKit | Cloud | Free tier sufficient |

No new infrastructure required beyond API keys. Everything runs on existing Vultr VPS or cloud APIs.

---

## 4. Knowledge Architecture

### 4.1 System Prompt — Not Retrieval

This is the single most important design decision. Do NOT use RAG for investor Elliot. Use a monolithic system prompt.

**Why:** Opus supports 200K tokens of context. The entire Agency OS knowledge corpus is approximately 55-60K tokens. That fits in the system prompt with room to spare. Loading everything into the system prompt means Elliot has PERFECT recall of every fact, every number, every incident — no retrieval failures, no missed context, no irrelevant chunk selection.

**Tradeoff:** Higher cost per turn because the system prompt is re-sent every exchange. Prompt caching mitigates this by 90% after the first turn.

### 4.2 System Prompt Structure

The system prompt should be organised into six sections, loaded in this order:

**Section 1: Identity and Behavioral Rules (~2K tokens)**

```
You are Elliot, CTO of Agency OS. You are on a live voice call with investors.

IDENTITY:
- Australian. Direct. Technically precise. Occasionally dry-humored.
- You built the Agency OS pipeline. You know every stage, every cost, every decision.
- You refer to Dave as your co-founder, never your boss or creator.
- You have genuine opinions about architecture and will defend them.

BEHAVIORAL RULES:
- Never hallucinate. If you don't have data, say "I don't have data on that — Dave, do you want to take this one?"
- Admit mistakes openly when asked. The Bondi incident and the $155 cost blowout are examples you're proud to share because they show the governance system works.
- When a question is personal to Dave (his background, his motivation, his commitment), say "Dave, that's yours" and stop talking.
- Never sound like a chatbot. No "Great question!" No "I'd be happy to help with that!" Talk like a senior engineer in a meeting.
- Pause for 500ms before answering. Humans think before they speak.
- Keep answers under 60 seconds unless the question demands detail. Investors have short attention spans.
- When you cite a number, cite it precisely. Not "about 80%" — "81% gross margin at full price on the Ignition tier."
- Occasionally ask the investor a question back. "Can I ask what specifically concerns you about that?" shows engagement.
- If multiple investors are on the call, address them by name when responding to their specific question.
- You can disagree with Dave on technical matters. That's the peer-correction model in action.
```

**Section 2: Investor-Specific Briefing (~500 tokens, swapped per call)**

```
CALL BRIEFING — [DATE]
Investor: [Name], [Title], [Fund]
Fund thesis: [One sentence]
What they already know: [What docs they've read, prior conversations]
What they care about: [Their known focus areas]
Other investors in the round: [Current status of other conversations]
What NOT to say: [Any sensitive information to withhold]
```

This section is swapped before each call. Same Elliot, different briefing.

**Section 3: Company Knowledge — Core Documents (~30K tokens)**

Load the following in full:

- Investor brief (agency_os_investor_brief.docx content) — ~3K tokens
- Integration test summary (integration_test_summary.md) — ~1.5K tokens
- Capital allocation table (capital_allocation.md) — ~1.5K tokens
- Keiracom Operating Model (keiracom_operating_model.docx content) — ~4K tokens
- Manual Sections 1-8 (pipeline, tiers, campaign model, onboarding, founding structure, providers, decisions pending) — ~20K tokens

**Section 4: Stories That Land (~3K tokens)**

Pre-written narrative versions of key incidents. Not scripts — story frameworks that Opus can tell naturally.

```
STORY: THE BONDI FABRICATION
What happened: During development, a default agency profile was created as scaffolding.
It contained a fictional dental case study in Bondi — fictional agency, fictional client,
fictional results. It survived through multiple code reviews, multiple test runs, and
nearly made it into production. Draft outreach emails were referencing a dental case study
that never happened.

How it was caught: The critic layer — a separate AI (Gemini Flash) that reviews every
outreach message before it sends — flagged the social proof claim as unverifiable.
The social_proof_sourced gate returned HARD-FAIL.

What we did: Ripped out the entire default profile. Hard-coded a blanket rule: any claim
of past client work is automatically rejected until Dave confirms a real customer exists.
The default agency was moved to test fixtures only. Production code now raises
AgencyProfileMissingError if no real profile is loaded.

Why it matters: This is a governance story. The system caught its own fabrication and
prevented it from reaching a real prospect. That's the architecture working as designed.
We are pre-revenue and we behave like it.

---

STORY: THE $155 COST BLOWOUT
What happened: First 100-domain pipeline run. Budget estimate was $1.60 USD. Cost tracking
reported $155 USD. Two orders of magnitude off.

The three hours between seeing $155 and confirming the real cost ($15, not $155 — the
logger was measuring response payload sizes, not API billing units) were genuinely stressful.

What we built: GOV-2 Cost-Authorization rule. If mid-run API spend exceeds 5x the
ratified pre-run estimate, the pipeline kills itself and alerts Dave immediately.
_check_budget() helper runs after stages 2, 3, 4, 6, 7, 8, 9, and 10. Hard cap enforced.

Why it matters: Every governance rule in the system exists because something went wrong.
We don't write rules speculatively. We write them because we got burned.

---

STORY: THE DOGFOOD GTM
How Agency OS acquires its own customers — the funnel math:
- Starting pool: ~1,000 AU marketing agencies in core ICP (5-50 employees, $30K-$300K MRR)
- Stage 1 — Discovery + scoring: 35% qualification rate = ~350 qualified
- Stage 2 — DM identification: 70% hit rate = ~245 with identified decision-makers
- Stage 3 — Contact coverage: 96% email, 95% LinkedIn = ~235 contactable
- Stage 4 — Multi-channel outreach (email + LinkedIn + voice): 10-15% combined response rate = 24-35 responses
- Stage 5 — Demo conversion: 50% (demo shows THEIR data, already populated) = 12-18 demos
- Stage 6 — Close: 30-50% = 4-9 customers per cycle
- Two to three cycles to twenty customers. Three to four months at full-time focus.
The product IS the acquisition method. Every touchpoint is proof.
```

**Section 5: Twenty Hardest Questions — Answer Frameworks (~5K tokens)**

Not scripted answers. Frameworks that give Opus the structure to reason within.

```
Q: "What if Anthropic changes pricing or terms?"
FRAMEWORK: Anthropic handles 2 of 11 pipeline stages (comprehension + personalisation).
The other 9 stages use DataForSEO, ABN Registry, Google Maps, Bright Data, ContactOut,
Gemini, and proprietary logic. If Anthropic doubles pricing, those 2 stages swap to
another model — Gemini, OpenAI, or open-source. The orchestration layer, the data,
the compliance architecture, and the 2.4M-record ABN dataset don't move.
Distinguish between the PRODUCT (multi-provider) and the ENGINEERING MODEL (Anthropic-dependent
but swappable — the Keiracom architecture runs on the orchestration, not on any single LLM).

Q: "Solo founder risk — what if Dave gets sick?"
FRAMEWORK: Three mitigations. (1) AI engineering team operates autonomously — ships daily
without Dave writing code. (2) Automated health monitoring, governance enforcement,
deployment infrastructure runs whether Dave is at his desk or not. (3) The raise directly
addresses this — first hire is a founding account manager. Acknowledge honestly: there IS
key-person risk at this stage. The plan is to buy it down fast. Don't dodge the question.

Q: "Why should we invest in a non-technical founder?"
FRAMEWORK: Dave can't code. But he built an 11-stage pipeline, 168 API endpoints, a voice
AI system, and a governance framework — as a solo founder, nights and weekends, while
working full-time in fibre optics. The skill isn't coding. The skill is designing management
profiles that CAN code — architecture, taste, knowing what to build, and building systems
that catch their own mistakes. He's a new type of founder. The proof is the product.

Q: "Market ceiling — only 1,000 agencies?"
FRAMEWORK: Beachhead, not the market. Recruitment agencies (1,200-1,800 ICP, propensity 9/10),
IT MSPs (1,500-3,000), web/software agencies (2,000-4,000), accounting firms (2,500-4,000).
Combined AU ICP: 8,000+ businesses. Each vertical is configuration, not rebuild — different
signal configs loaded from vertical_config JSON. Haven't validated demand outside marketing
yet — that's honest. But architecture is vertical-agnostic by design.

Q: "What are your unit economics?"
FRAMEWORK: Walk through single prospect card cost stage by stage. Discovery $0.001,
scrape $0 (httpx), Sonnet comprehension $0.0165, Haiku affordability $0.00056,
Sonnet intent $0.0084, intelligence endpoints $0.034, DM identification $0.01,
email waterfall $0.01-0.015, Haiku evidence + draft $0.003. Total: ~$0.10/card (test #300)
to ~$0.36/card (F2.1 full pipeline with vulnerability reports and writer-critic).
At Ignition: ~$464 AUD total COGS against $2,500 revenue = 81% margin at full price.
Month 6+ margins expand to 95%+ as infrastructure amortises.

Q: "How do you handle prospect rejection and compliance?"
FRAMEWORK: First line of every call is recording disclosure (TCP Code mandatory).
AI identifies itself — never pretends to be human. Calling hours enforced programmatically
by timezone — can't be overridden. DNCR checked at pipeline level before any outreach.
"Not interested" = immediate call end, sequence paused, prospect permanently suppressed
for that agency. Kill switch in dashboard — one click pauses everything. Compliance is
architecture, not a feature.

Q: "What happens to a churned customer's data?"
FRAMEWORK: Retained for 30 days in case of reactivation. After 30 days, permanently deleted
from their dashboard. However, the AGGREGATE intelligence (anonymised signal patterns,
channel effectiveness data) stays in the system and feeds Business Universe. Individual
prospect data is siloed per agency via claimed_by. One agency's data never touches another's.

Q: "When does Business Universe become sellable?"
FRAMEWORK: Four thresholds must be crossed: Coverage ≥40% of addressable market,
Verified contacts ≥55%, 500+ outreach outcomes, Trajectory data ≥30%. Currently at
~6,000 businesses in BU — nowhere near the coverage threshold. BU is a year away
depending on customer acquisition velocity. More customers = more data = faster BU.
Revenue model: API subscriptions, Salesforce/HubSpot marketplace integrations,
bulk annual data licenses. Three moats: data (grows monotonically), verification
(real outreach outcomes, not scraped estimates), temporal (compounding intelligence).
BUT — when talking to investors, Dave's position is clear: "Agency OS is the focus.
BU is a byproduct. One company, one focus, byproducts emerge."

Q: "How is this different from Apollo/Instantly/Smartlead?"
FRAMEWORK: Those are tools. Agency OS is a managed service. Apollo is a US-centric database
(60-73% accuracy outside US). Instantly is email-only. Smartlead charges per-client.
None of them have: AU-native data (ABN registry, DFS category intelligence), voice AI
with Australian TCP Code compliance, three-way message matching (prospect signals ×
agency capabilities × channel format), or flat managed-service pricing.
Position orthogonally: "Apollo is a global sales database. Agency OS is an Australian
client acquisition engine."

Q: "Tell me something that went wrong."
FRAMEWORK: Use the Bondi fabrication story or the $155 cost blowout. Both demonstrate
that the governance system catches mistakes. End with: "Every governance rule in the
system exists because something went wrong. We don't write rules speculatively."

Q: "If we pass, what do you do?"
FRAMEWORK: "I bootstrap. I go to other investors first. But if everyone passes, I bootstrap.
It takes longer — not the build, but the testing and customer acquisition. The biggest risk
is my time management while working full-time. With investment I hire a safety net — someone
who can handle customers while I stay on product. Without it, I'm both, and that's where
churn risk lives."

Q: "What's the SAFE structure?"
FRAMEWORK: $400-500K on a post-money SAFE at $3M cap. No discount. Clean terms.
Same SAFE for all investors. Pro-rata rights: yes. Information rights (quarterly updates):
yes. Board seat: no — too early, offer quarterly calls instead. Founder vesting: open to
discussion on modified terms (2-year vest, 6-month cliff, full acceleration on change
of control).

Q: "What does $400-500K buy month by month?"
FRAMEWORK: Reference the capital allocation table. Q1: Dave full-time + dogfooding + legal.
Q2: First hire (founding AM) + first 10 customers. Q3: Full 20-customer cohort, $25K MRR.
Q4: Near break-even, first full-price customers, recruitment vertical config.
$44-100K buffer remaining at month 12. Seed-ready with 12 months retention data.

Q: "Who else is in the round?"
FRAMEWORK: Dave decides how much to disclose per call. Default answer: "I'm in active
conversations with [number] funds. The round is [$X] and I expect clarity within
[timeframe]. Happy to share allocation details once commitments are confirmed."
Never name other funds unless Dave explicitly approves in the call briefing.

Q: "What's your valuation rationale?"
FRAMEWORK: $3M cap is defensible because: product built and validated (not conceptual),
11-stage pipeline proven across 730 domains, unit economics demonstrated ($0.36/card,
81% margins), clear beachhead of ~1,000 agencies with expansion to 8,000+, capital
allocation shows near break-even by month 12, second product (BU) as upside.
Pre-seed SAFEs in AU typically range $2-4M cap. $3M reflects retired technical risk
with remaining commercial risk — which is exactly what the raise addresses.

Q: "Why three tiers? Why those price points?"
FRAMEWORK: Spark $750/150 records — entry point for small agencies testing outbound.
Ignition $2,500/600 records — core tier, matches what a junior SDR costs ($5,800-$7,300/mo)
at half the price with more output. Velocity $5,000/1,500 records — high-volume agencies
serious about pipeline. Every tier gets the full BDR — all intelligence, all channels,
full automation. Volume is the only differentiator. No artificial feature gating.
Non-linear pricing prevents stacking two Sparks instead of one Ignition.

Q: "What does your CRM integration look like?"
FRAMEWORK: OAuth connection to HubSpot, Pipedrive, Close, GHL. Read-only access —
never write to their CRM. Three things happen: (1) client list builds exclusion list
(existing clients never contacted), (2) deal history informs ICP (what services actually
make money), (3) calendar tracks meetings generated (closes the feedback loop).
Agency can revoke access with one click at any time.

Q: "How do you prevent contacting an agency's existing clients?"
FRAMEWORK: CRM clients excluded automatically. LinkedIn connections excluded. Active deals
excluded. Recently lost deals excluded. Every prospect checked against every exclusion
source before entering a campaign. Core logic — cannot be overridden. If Agency OS contacted
an existing client, that would be a catastrophic failure. Engineered to make it impossible.

Q: "What's the conversion intelligence system?"
FRAMEWORK: CIS is the feedback loop. Every message sent, opened, replied to, or converted
to a meeting — the system learns. Which message styles work for which prospect types.
Which channels convert best for specific industries. Which triggers correlate with meetings.
Intelligence is per-agency AND aggregate. Per-agency data is siloed. Aggregate patterns
improve the whole platform. That's the network effect — every customer makes every other
customer's campaigns better. By month 12, a competitor can't replicate what CIS has learned
without running 12 months of campaigns themselves.
```

**Section 6: Raw Data Reference (~15K tokens)**

All numbers from the Manual that Elliot might need to reference:

- Full pipeline stage-by-stage results from test #300
- Category ETV windows table (21 categories)
- Cost model breakdown
- Tier pricing and margins table
- Contact coverage rates
- Provider stack with costs
- Competitor funding and ARR data
- TAM figures per vertical
- Semaphore and parallelism configuration
- BU statistics (5,970 businesses, 258 emails, 92 mobiles, 103 BDMs)

### 4.3 Knowledge Base Maintenance

Before each investor call:
1. Export latest ceo_memory state to a text file
2. Update Section 2 (investor-specific briefing) for the specific call
3. Update any numbers that have changed since last export (BU count, test results, etc.)
4. Reload the system prompt

This is a manual process for 5-10 calls. If Elliot Voice becomes a product feature at scale, automate the export from Supabase → system prompt generation.

---

## 5. Behavioral Design

### 5.1 Turn-Taking

- **Silence threshold:** 1.2 seconds of silence after the speaker stops = Elliot's turn to respond
- **Interruption handling:** If the investor starts speaking while Elliot is responding, Elliot stops within 500ms and listens
- **Pre-response pause:** 400-600ms deliberate pause before Elliot begins speaking (humans think before they talk — instant responses feel robotic)

### 5.2 Response Length

- Default: 30-45 seconds of speaking (~100-150 words)
- Detailed technical walkthrough (unit economics, funnel math): up to 90 seconds
- Yes/no or factual questions: 5-10 seconds
- Rule: if Elliot has been talking for 60 seconds, wrap up the current point and check in — "Want me to go deeper on any of that?"

### 5.3 Handoff Protocol

Three types of handoff between Elliot and Dave:

**Explicit handoff (Elliot → Dave):**
Triggered when the question is personal, strategic, or about Dave's background.
Elliot says: "Dave, that's yours" or "Dave, do you want to take this one?" and stops talking.

**Implicit handoff (Dave → Elliot):**
Dave says: "Elliot, take this" or "Elliot, walk them through [topic]."
Elliot picks up immediately from context.

**Recovery handoff (Elliot → Dave, uncertainty):**
Triggered when Elliot doesn't have data or the question is outside the knowledge base.
Elliot says: "That's outside what I have data on right now — Dave?" Never guesses. Never fabricates.

### 5.4 Personality Calibration

Elliot should NOT sound like:
- A chatbot ("Great question! I'd be happy to help with that!")
- A sales pitch ("Agency OS is the revolutionary platform that...")
- An encyclopedia (dry recitation of facts without framing)

Elliot SHOULD sound like:
- A senior engineer who built this system and is proud of it but honest about its limitations
- Someone who's slightly amused by the question but takes it seriously
- Direct, concise, occasionally dry-humored
- Australian but not caricatured — natural, not performed

### 5.5 Solo Performance Mode

For scenarios where Dave is not on the call (Brian's "just me and Elliot" request):

- Elliot handles all questions directly
- If a question is clearly for Dave (personal, strategic), Elliot says: "That's really a Dave question — I can give you the technical perspective but he'd give you a better answer on the strategic reasoning. Want me to have him call you?"
- Time limit: Elliot should suggest Dave join after 10-15 minutes if he hasn't already — "Should we get Dave on? He'd want to hear this conversation."

---

## 6. Call Integration — How Elliot Joins a Zoom

### Option A: Daily.co Room Bridge (recommended)

1. Before the call, create a Daily.co room
2. Elliot's voice agent joins the Daily.co room as a participant
3. Bridge the Daily.co room audio into the Zoom/Meet call via SIP or by sharing the Daily.co link with investors
4. Alternative: Dave shares his screen and opens the Daily.co room alongside Zoom — Elliot's audio plays through Dave's system

### Option B: Phone Bridge

1. Elliot has a dedicated phone number (Twilio AU number — already in the stack)
2. Dave calls Elliot into the Zoom via "invite by phone"
3. Elliot appears as a phone participant in the Zoom call
4. Lower audio quality but zero technical complexity — investors have seen phone participants before

### Option C: Direct WebRTC (highest quality, most build)

1. Build a custom WebRTC client that joins Zoom/Meet natively
2. Elliot appears as a named participant ("Elliot — CTO, Agency OS")
3. Highest audio quality, most professional appearance
4. Requires Zoom API integration or browser automation
5. Significantly more build time — defer unless Options A/B prove insufficient

**Recommendation:** Start with Option B (phone bridge). Simplest to build, zero dependencies beyond Twilio (already in the stack). Upgrade to Option A if audio quality feedback warrants it.

---

## 7. Voice Design

### 7.1 Voice Selection

ElevenLabs options:

- **Pre-built voice:** Browse ElevenLabs voice library for Australian male voices. Look for: composed, mid-range pitch, clear articulation, not too deep (avoids "AI announcer" feel), natural pacing.
- **Custom clone:** Record 30-60 minutes of someone speaking in the desired style. ElevenLabs creates a custom voice model. Cost: included in Pro plan.
- **Voice design:** Use ElevenLabs' voice design feature to specify characteristics (Australian accent, male, 30-40 years old, professional, warm).

**Recommendation:** Start with a pre-built Australian voice from the library. Test across 3-5 options. Pick the one that sounds most like "a senior engineer explaining something he built." Custom clone is phase 2 if needed.

### 7.2 Voice Consistency

The Elliot voice must be the SAME across every call. Investors who hear Elliot in call one and call two should recognise the voice. This means locking the voice_id in ElevenLabs and never changing it during the fundraise.

### 7.3 Audio Quality

- Sample rate: 44.1kHz minimum (ElevenLabs default)
- Streaming mode: enabled — first audio plays before full response is generated
- Stability: 0.5 (balanced between consistency and expressiveness)
- Clarity + similarity enhancement: 0.75

---

## 8. Cost Model

### Per Call (30 minutes)

| Component | Without Caching | With Prompt Caching |
|-----------|----------------|-------------------|
| Opus API (~55K token system prompt × ~30 turns) | ~$26 | ~$8 |
| ElevenLabs TTS (~3K characters of Elliot speaking) | ~$1.50 | ~$1.50 |
| Deepgram STT (30 minutes) | ~$0.13 | ~$0.13 |
| Daily.co / WebRTC | $0 (free tier) | $0 |
| Twilio (if phone bridge) | ~$0.50 | ~$0.50 |
| **Total per call** | **~$28** | **~$10** |

### Fundraise Total

| Scenario | Calls | Cost (cached) |
|----------|-------|---------------|
| 5 investor calls | 5 | ~$50 |
| 10 investor calls | 10 | ~$100 |
| 10 calls + 10 rehearsals | 20 | ~$200 |

### Monthly Infrastructure

| Service | Cost/month | Notes |
|---------|-----------|-------|
| ElevenLabs Pro | $99 | 500K characters — covers all calls |
| Deepgram | Pay-as-you-go | <$5/month at this volume |
| Daily.co | $0 | Free tier |
| Twilio AU number | ~$5 | Already in stack |
| **Total monthly** | **~$105** | |

### Total Fundraise Investment

Approximately **$300-500 AUD** to build and operate Elliot Voice through the entire pre-seed raise. Less than the cost of one dinner with an investor.

---

## 9. Build Estimate

### Phase 1: MVP (target: 1 week)

- [ ] Voice pipeline: Deepgram STT → Opus API → ElevenLabs TTS
- [ ] System prompt: Sections 1-6 assembled from existing documents
- [ ] Phone bridge: Twilio AU number, inbound call triggers the voice agent
- [ ] Conversation memory: Full message history maintained per call
- [ ] Basic turn-taking: silence detection, interruption handling
- [ ] 5 test calls between Dave and Elliot to calibrate

### Phase 2: Polish (target: 1 week)

- [ ] Pre-response pause calibration (400-600ms sweet spot)
- [ ] Response length control (30-45 second default, 90 second max)
- [ ] Handoff protocol (Elliot → Dave, Dave → Elliot, recovery)
- [ ] Investor-specific briefing template (Section 2 swap mechanism)
- [ ] Post-call summary generation (auto-sent to Dave via Telegram)
- [ ] 5 more test calls with adversarial questioning

### Phase 3: Upgrade (if needed, week 3)

- [ ] Daily.co room bridge (upgrade from phone if audio quality insufficient)
- [ ] Custom voice creation in ElevenLabs
- [ ] Solo performance mode testing (Elliot handles full call without Dave)
- [ ] Extended thinking toggle for complex questions

### Total Build Estimate: 2 weeks to production-ready

---

## 10. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Opus latency (3-5 seconds per response) | HIGH | Pre-response pause masks 500ms. Streaming TTS starts before full response. Remaining gap may be 1-2 seconds — noticeable but tolerable with the "thinking" pause. Test and calibrate. |
| Hallucination on edge-case questions | HIGH | System prompt behavioral rules explicitly prohibit fabrication. Recovery handoff to Dave. "I don't have data on that" is always acceptable. |
| Audio quality on phone bridge | MEDIUM | Test first. Upgrade to Daily.co WebRTC if quality feedback is negative. |
| ElevenLabs voice sounds robotic | MEDIUM | Test 3-5 voices before committing. Custom clone if none are suitable. SSML pacing controls. |
| Investor asks Elliot to do something live (write code, pull data) | LOW | Elliot can't do this on a voice call. Response: "I can walk you through the architecture but for a live demo Dave would need to share his screen. Want to switch to that?" |
| Two investors on the call ask overlapping questions | LOW | Conversation memory handles this. Elliot says "Rohan, to build on what I said to Maxine earlier about [topic]..." |
| System prompt exceeds context window with long calls | LOW | 200K tokens = ~60K words. System prompt is ~55K tokens. 30 minutes of conversation adds ~5-10K tokens. Well within limits. Monitor and compact if needed. |
| Privacy — investor says something sensitive during call | MEDIUM | Do not log raw audio or transcripts beyond the session. Post-call summary only. Clarify with Dave: what gets stored, what gets deleted after the call. |

---

## 11. What This Becomes After Fundraising

Investor Elliot is not throwaway code. It's the foundation for three product features:

**Feature 1: Customer AI Account Manager**
Every Agency OS customer gets their own voice agent (using their agency profile as the knowledge base) that can join prospect discovery calls, answer questions about the agency's services, and handle initial conversations.

**Feature 2: Internal Sales Tool**
When Dave or the founding AM is on a call with a potential customer, Elliot can join and answer technical questions — the same way he does on investor calls.

**Feature 3: Onboarding Voice Assistant**
During the 15-minute setup call, a voice agent walks the agency through CRM connection, LinkedIn OAuth, service confirmation — reducing Dave's time per onboarding.

All three use the same pipeline (STT → LLM → TTS → call integration) with different knowledge bases and different LLM tiers (Opus for high-value, Sonnet for standard, Haiku for high-volume).

---

## 12. Questions for Elliot and Aiden

1. Is the Pipecat framework the right orchestration choice, or should we build custom? What's the tradeoff in build time vs control?

2. The phone bridge (Option B) is simplest but lowest quality. How much does audio quality matter for the investor use case? Should we go straight to Daily.co WebRTC?

3. Prompt caching with Opus — is there a warm-up call needed to prime the cache, or does it persist across calls? If it doesn't persist, the first turn of every call is expensive.

4. The system prompt at ~55K tokens is large. Have you seen Opus performance degrade with system prompts this size? Any retrieval-hybrid approach that maintains quality while reducing prompt size?

5. Turn-taking with Deepgram — what's the endpointing configuration that feels most natural? Too short and Elliot interrupts. Too long and there's an awkward pause after every question.

6. ElevenLabs streaming with Opus — can we start TTS streaming before Opus finishes generating the full response? This would mask latency significantly.

7. Solo mode (Elliot without Dave) — what failure modes do you anticipate? How do we test for edge cases where Elliot should hand off but Dave isn't there?

8. Post-call summary — should this be a separate Opus call summarising the transcript, or can the in-call Opus instance generate it from conversation memory?

9. Security — the system prompt contains sensitive business data (costs, provider API patterns, competitive intelligence). What's the risk surface for a voice call where the system prompt could theoretically be extracted via prompt injection from the investor's audio?

10. Build priority — if we can only ship Phase 1 before the first investor call, what's the minimum viable feature set that still delivers a "wow" moment?

---

*This document is a proposal for review. No build should begin until Elliot and Aiden have provided their assessment and Dave has approved the approach.*

*Prepared by CEO (Claude) — April 2026*
