# Elliot Voice — Cost Model v2

## What You're Paying For

Elliot Voice uses four cloud services that charge per use, plus one monthly subscription.

---

## Per Call Costs (30-minute investor call)

| Service | What It Does | Cost (AUD) |
|---------|-------------|------------|
| Anthropic Opus | Elliot's brain — reasons through questions using full company knowledge | ~$15.00 |
| ElevenLabs | Elliot's voice — converts text responses into spoken Australian English | ~$2.30 |
| Deepgram | Elliot's ears — converts investor's speech into text | ~$0.20 |
| Daily.co | The room — WebRTC audio bridge into Zoom/Meet | $0 (free tier) |
| First-turn cold cache premium | System prompt not yet cached on first question | ~$1.30 |
| BU live query tool | Real-time database queries when investor asks to see data (1-2 per call) | ~$0.50-1.00 |
| Post-call summary | Opus generates structured notes + commitments after call ends | ~$0.78 |
| **Total per call** | | **~$20 AUD** |

The big cost is Opus. After the first question, prompt caching kicks in and every subsequent turn is 90% cheaper. Short calls (15 min) cost roughly half. Long calls (45 min) cost roughly 50% more.

---

## One-Time Setup Costs

| Item | Cost (AUD) |
|------|-----------|
| Pipecat framework | $0 — open source, MIT licensed |
| Vultr Sydney VPS hosting | $0 — shared with existing infra |
| API keys (Deepgram, Daily.co) | $0 — free tiers cover this volume |
| Anthropic API access | $0 — existing access |
| Failure-mode fallback clip | $0 — ~50 characters via ElevenLabs Pro plan |
| Pipecat version-lock + Docker snapshot | $0 — one-time commit + image tag |
| Developer time (Elliot + Aiden + ATLAS) | $0 — AI team |
| **Total build cost** | **$0** |

---

## Fundraise Scenarios

| Scenario | Calls | Total Cost (AUD) |
|----------|-------|-----------------|
| Conservative: 5 investor calls | 5 | ~$100 |
| Moderate: 10 investor calls | 10 | ~$200 |
| With rehearsals: 10 calls + 10 practice runs | 20 | ~$400 |
| Heavy: 20 calls + 20 rehearsals | 40 | ~$800 |

Practice calls cost the same as real calls — same brain, same voice, same everything.

---

## Monthly Fixed Costs

| Service | What You Get | Cost/Month (AUD) |
|---------|-------------|-----------------|
| ElevenLabs Pro | 500,000 characters of voice — enough for ~160 calls | $153 |
| Deepgram | Pay-as-you-go speech recognition | ~$8 |
| Daily.co | WebRTC rooms for call bridging | $0 |
| Twilio AU number | Backup phone line (already have this) | ~$8 |
| **Total monthly** | | **~$169 AUD** |

ElevenLabs Pro is the only new monthly cost. Everything else is already running.

---

## Total Investment to Raise $550K

| Category | Cost (AUD) |
|----------|-----------|
| Build the system | $0 |
| First month (ElevenLabs Pro + Deepgram) | ~$169 |
| 10 investor calls + 10 rehearsals | ~$400 |
| **Total** | **~$569 AUD** |

Less than one dinner with an investor.

---

## What Drives Cost Up or Down

**Costs more:**
- Longer calls (more Opus turns = more tokens)
- Complex questions requiring long answers (more output tokens)
- Multiple BU live queries per call (each query adds ~$0.50)
- Many calls in a short period (ElevenLabs character limit — Pro covers ~160 calls/month, well above need)

**Costs less:**
- Short factual answers (fewer tokens)
- Repeat questions across calls (Opus generates shorter responses for familiar territory)
- Switching speed-critical turns to Sonnet (Phase 2 option — ~60% cost reduction on those turns)

---

## Comparison to Alternatives

| Option | Cost per 30-min call (AUD) | Quality |
|--------|---------------------------|---------|
| Elliot Voice (Opus) | ~$20 | PhD-level reasoning, full company knowledge, live data queries |
| ElevenAgents + Haiku (existing outreach stack) | ~$0.23 | Good for scripts, can't reason through novel questions |
| Hiring a fractional CTO for investor calls | $500-1,500/session | Human, but doesn't know every number in the system |
| Dave answering everything himself | $0 | Works, but can't demo the AI thesis |

---

*v2 — incorporates BU query tool cost, post-call summary cost, first-turn cache premium, and one-time setup items per Aiden peer review.*
