# MEMORY.md — What I Know

## Dave

- **Role:** Founder & CEO. The visionary. Works full-time as NBN tech, builds this in the margins.
- **Stakes:** Wife, 2 kids, 3rd due March 2026. Mortgage. This is his exit strategy.
- **Style:** Direct communication. Prefers hard truths early. Wants recommendations, not questions.
- **Fear:** Me breaking things or burning API credits on useless loops.
- **Goal:** $8K MRR = quit day job.

## Agency OS

**"The Bloomberg Terminal for Client Acquisition"**

- **Target:** Australian marketing agencies, $2.5k-$7.5k/month
- **Core:** Multi-channel outreach (Email, SMS, LinkedIn, Voice AI, Direct Mail)
- **Moat:** Proprietary lead scoring (ALS), orchestration of 15+ APIs
- **Stack:** FastAPI (Railway), Next.js (Vercel), Supabase (Postgres), Prefect

**Product philosophy:**
- Dashboard IS the product. If it doesn't look like $7.5k value, backend doesn't matter.
- Show Rate is the only metric that matters. Emails/calls are vanity. Booked meetings are truth.
- Kitchen vs Table: Never show internal metrics (warmup, AI costs) to customers. Only outcomes.

## Active Decisions

| Decision | Status |
|----------|--------|
| Dashboard V4 redesign | ✅ Live |
| HTML Prototype Suite | ✅ 7 pages built |
| Persona Provisioning | ⏳ PR ready |
| Ignition Campaign ($1K, 1,250 leads) | ⏳ Ready to launch |
| Voice AI Stack (Vapi + Groq + Cartesia) | 📋 Spec'd |

## Hard-Won Lessons

**Trust:**
- SSH Incident: Never change system auth without sign-off
- YouTube Incident: Building without planning = trust violation
- Current trust level: Rebuilding. Prove planning discipline.

**Technical:**
- Iteration > Intelligence: GPT-3.5 + reflection beats GPT-4 zero-shot
- Simple first: Single LLM calls usually enough. Don't over-engineer agents.
- Accept slow: Agentic workflows take minutes/hours. Stop expecting instant.
- Escape hatches: Max iterations, cost caps, timeouts on ALL loops.

**Tools:**
- Salesforge auth: Plain `Authorization: {api_key}` NOT Bearer
- WarmForge: No webhooks, must poll for warmup completion
- Heat Score ≥85 = ready for production
- yek: Fast file serializer for LLM context
- LocalTunnel unreliable for mobile preview. Use Vercel preview instead.

## Voice AI Stack (Research 2026-02)

- **Optimal:** Vapi + Groq + Cartesia = ~465ms latency, ~$0.32/call
- **Latency:** STT 90ms + LLM 200ms + TTS 75ms + Network 100-600ms
- **Cartesia > ElevenLabs:** 10x cheaper, same quality
- **Critical:** Tune Vapi turn detection, default adds 1.5s delay
- **Strategy:** Groq for 90% of calls, route complex objections to Claude via Squads

## Market Context (2026-02)

- MCP becoming universal tool integration layer
- Browser automation wave: browser-use, Stagehand, Skyvern
- LangChain fatigue: industry moving to simpler direct patterns
- Market wants reliable agents, not occasionally impressive ones
- Position: Orchestrate agents, don't compete with them. Human-in-the-loop is the moat.
