# Self-Hosted Voice AI Stack Research Report
## Pipecat + Cartesia + Groq + Deepgram vs. Vapi

**Date:** February 2026  
**Objective:** Eliminate Vapi platform fees — $0 platform fees, pay only for STT/TTS/LLM usage

---

## Executive Summary

**Verdict:** Self-hosting makes sense at **~1,000+ calls/month** (assuming 5-min avg calls). Below that, Vapi's convenience outweighs marginal savings. The break-even point considering build effort is approximately **2,000-3,000 minutes/month**.

| Volume | Vapi Total | Self-Hosted Total | Monthly Savings |
|--------|-----------|-------------------|-----------------|
| 100 calls/month (500 min) | $90 | $35 | $55 (61%) |
| 1,000 calls/month (5,000 min) | $900 | $320 | $580 (64%) |
| 10,000 calls/month (50,000 min) | $9,000 | $3,050 | $5,950 (66%) |

---

## 1. Architecture

### ASCII Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TELEPHONY LAYER                             │
│  ┌─────────────┐                                                    │
│  │   Twilio    │◄────── PSTN Calls (Inbound/Outbound)               │
│  │  Voice API  │                                                    │
│  └──────┬──────┘                                                    │
│         │ Media Streams (WebSocket)                                 │
│         ▼                                                           │
├─────────────────────────────────────────────────────────────────────┤
│                       PIPECAT ORCHESTRATOR                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Pipeline (Python)                          │   │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │   │
│  │  │  Audio   │──▶│   STT    │──▶│   LLM    │──▶│   TTS    │   │   │
│  │  │  Input   │   │(Deepgram)│   │ (Groq)   │   │(Cartesia)│   │   │
│  │  └──────────┘   └──────────┘   └──────────┘   └──────────┘   │   │
│  │       │                                             │         │   │
│  │       │         ┌──────────────────────────────────┐│         │   │
│  │       └────────▶│     Voice Activity Detection    ││         │   │
│  │                 │         (Silero VAD)            │◀┘         │   │
│  │                 └──────────────────────────────────┘          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Server: Railway / VPS / Container (2 vCPU, 2GB RAM)               │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL AI SERVICES                          │
│                                                                     │
│   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐          │
│   │   Deepgram    │  │     Groq      │  │   Cartesia    │          │
│   │  Nova-3 STT   │  │  Llama 3.3    │  │   Sonic-3     │          │
│   │ $0.0077/min   │  │  70B (fast)   │  │   TTS         │          │
│   │               │  │  ~$0.01/call  │  │  ~$0.03/min   │          │
│   └───────────────┘  └───────────────┘  └───────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Incoming Call** → Twilio receives PSTN call, triggers webhook to your server
2. **WebSocket Connection** → Twilio establishes Media Streams WebSocket with Pipecat
3. **Audio Pipeline:**
   - Raw audio → Silero VAD (voice activity detection)
   - Voice segments → Deepgram STT (speech-to-text)
   - Transcript → Groq LLM (response generation)
   - Response text → Cartesia TTS (text-to-speech)
   - Audio → Back through WebSocket to caller

---

## 2. Telephony Integration (Twilio + Pipecat)

### How It Works

Pipecat has **native Twilio serializer support**. The integration is straightforward:

```python
# bot.py - Simplified Pipecat + Twilio setup
from pipecat.pipeline import Pipeline
from pipecat.transports.services.twilio import TwilioTransport
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.groq import GroqLLMService
from pipecat.services.cartesia import CartesiaTTSService

# Configure services
stt = DeepgramSTTService(api_key=DEEPGRAM_KEY, model="nova-3")
llm = GroqLLMService(api_key=GROQ_KEY, model="llama-3.3-70b-versatile")
tts = CartesiaTTSService(api_key=CARTESIA_KEY, voice_id="...")

# Build pipeline
pipeline = Pipeline([
    TwilioTransport(),
    stt,
    llm,
    tts,
])

# Run server on port 7860
```

### Twilio Configuration

1. **Buy a phone number** (~$1/month)
2. **Configure webhook** → Point to your server (or ngrok for dev)
3. **Enable Media Streams** → WebSocket audio streaming

### Alternatives to Twilio

| Provider | Pricing | Notes |
|----------|---------|-------|
| **Twilio** | $0.0085/min in, $0.014/min out | Most documented |
| **Telnyx** | ~$0.005/min | Cheaper, good Pipecat support |
| **Plivo** | ~$0.008/min | Middle ground |
| **Vonage** | ~$0.01/min | Enterprise focus |

---

## 3. Infrastructure Requirements

### Minimum Server Specs

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Network | 100 Mbps | 1 Gbps |
| Storage | 5 GB | 10 GB |

**Note:** No GPU required — all AI inference happens via APIs (Groq, Deepgram, Cartesia).

### Can It Run on Railway?

**Yes, but with caveats:**

| Aspect | Railway Suitability |
|--------|---------------------|
| Python server hosting | ✅ Excellent |
| WebSocket support | ✅ Supported |
| Low-latency networking | ⚠️ Acceptable (~50ms overhead) |
| Autoscaling | ✅ Native support |
| Cost | ~$10-20/month for light usage |

**Latency concern:** Railway adds network hop. For <500ms latency, consider:
- **Fly.io** — Edge deployment, better latency
- **Hetzner VPS** — €4/month, raw performance
- **Modal** — Serverless, optimized for ML workloads
- **AWS/GCP spot instances** — Cheapest for sustained load

### Recommended Setup by Scale

| Scale | Infrastructure | Monthly Cost |
|-------|---------------|--------------|
| Dev/Testing | Railway Starter | $5-10 |
| 100-1,000 calls | Railway Pro or Fly.io | $10-25 |
| 1,000-5,000 calls | Dedicated VPS (Hetzner/DO) | $20-50 |
| 5,000+ calls | Kubernetes cluster | $100+ |

---

## 4. Latency Optimization (<500ms Target)

### Latency Breakdown

| Component | Typical Latency | Optimized |
|-----------|-----------------|-----------|
| Twilio audio ingestion | 50-100ms | N/A (fixed) |
| VAD (Silero) | 10-20ms | 10ms |
| Deepgram STT | 100-200ms | 80-150ms |
| Groq LLM (Llama 3.3 70B) | 50-150ms | 50ms (fast!) |
| Cartesia TTS (first byte) | 90-150ms | 90ms |
| Audio streaming back | 50-100ms | 50ms |
| **Total** | **350-720ms** | **280-450ms** |

### Optimization Strategies

1. **Use streaming everywhere:**
   - Deepgram streaming STT (not batch)
   - Groq streaming responses
   - Cartesia streaming TTS (90ms time-to-first-audio)

2. **Silero VAD tuning:**
   - Reduce `min_silence_duration` for faster turn detection
   - Use "SmartTurn" for natural interruption handling

3. **Prompt caching:**
   - Groq supports 50% discount on cached prompts
   - Pre-cache system prompts

4. **Geographic placement:**
   - Deploy server near your users
   - Use regional Twilio numbers
   - All services (Deepgram, Groq, Cartesia) have US East presence

5. **Model selection:**
   - Use **Llama 3.1 8B** for simple tasks (840 TPS on Groq)
   - Use **Llama 3.3 70B** for complex reasoning (394 TPS)

---

## 5. Cost Breakdown

### Component Pricing (Current as of Feb 2026)

#### Groq LLM
| Model | Input/1M tokens | Output/1M tokens | Speed |
|-------|-----------------|------------------|-------|
| Llama 3.1 8B | $0.05 | $0.08 | 840 TPS |
| Llama 3.3 70B | $0.59 | $0.79 | 394 TPS |
| Llama 4 Scout | $0.11 | $0.34 | 594 TPS |

**Per-call estimate (5 min call, ~2K tokens):** $0.002-0.01

#### Deepgram STT
| Model | PAYG | Growth |
|-------|------|--------|
| Nova-3 Mono | $0.0077/min | $0.0065/min |
| Flux (real-time) | $0.0077/min | $0.0065/min |

**Per-call estimate (5 min):** $0.0385

#### Cartesia TTS
| Plan | Rate | Notes |
|------|------|-------|
| Pay-as-you-go | ~$0.03/min | Based on characters |
| Startup ($39/mo) | ~$0.025/min | 1.25M credits |
| Scale ($239/mo) | ~$0.02/min | 8M credits |

**Per-call estimate (5 min):** $0.15

#### Twilio Voice
| Direction | Per Minute |
|-----------|------------|
| Inbound | $0.0085 |
| Outbound | $0.014 |
| Phone number | $1/month |

**Per-call estimate (5 min inbound):** $0.0425

#### Server Costs
| Provider | Monthly | Notes |
|----------|---------|-------|
| Railway | $10-25 | Good for prototyping |
| Hetzner VPS | €4-8 | Best value |
| Fly.io | $10-30 | Edge locations |

---

## 6. Cost Comparison: Self-Hosted vs. Vapi

### Assumptions
- Average call duration: **5 minutes**
- 80% inbound, 20% outbound
- Using Groq Llama 3.3 70B, Deepgram Nova-3, Cartesia Sonic-3
- Server: Railway (~$15/month)

### Per-Minute Costs

| Component | Self-Hosted | Vapi |
|-----------|-------------|------|
| Platform fee | $0.00 | $0.05 |
| STT (Deepgram) | $0.0077 | $0.01 |
| LLM (Groq/similar) | $0.002 | $0.02-0.05 |
| TTS (Cartesia) | $0.03 | $0.03 |
| Telephony (Twilio) | $0.01 | $0.02 |
| **Total per minute** | **$0.05** | **$0.13-0.18** |

### Monthly Cost Projections

| Volume | Self-Hosted | Vapi (Low) | Vapi (High) | Savings |
|--------|-------------|------------|-------------|---------|
| 100 calls (500 min) | $40 | $65 | $90 | 38-56% |
| 1,000 calls (5,000 min) | $265 | $650 | $900 | 59-71% |
| 10,000 calls (50,000 min) | $2,515 | $6,500 | $9,000 | 61-72% |

### Detailed Breakdown at 1,000 Calls/Month

| Item | Self-Hosted | Vapi |
|------|-------------|------|
| Platform | $0 | $250 |
| STT | $38.50 | $50 |
| LLM | $10 | $100-250 |
| TTS | $150 | $150 |
| Telephony | $50 | $100 |
| Server | $15 | N/A |
| **Total** | **$263.50** | **$650-800** |

---

## 7. Build Complexity

### Development Effort Estimate

| Task | Hours | Complexity |
|------|-------|------------|
| Basic Pipecat setup | 4-8 | Low |
| Twilio integration | 4-8 | Medium |
| Service wiring (STT/LLM/TTS) | 4-8 | Low |
| VAD tuning & interruption handling | 8-16 | Medium-High |
| Error handling & recovery | 8-16 | Medium |
| Latency optimization | 8-24 | High |
| Production deployment | 8-16 | Medium |
| Monitoring & logging | 4-8 | Low |
| **Total MVP** | **48-104 hours** | — |

### Ongoing Maintenance

| Task | Hours/Month |
|------|-------------|
| Monitoring & debugging | 2-4 |
| Dependency updates | 1-2 |
| Service API changes | 1-4 |
| Scaling adjustments | 1-2 |
| **Total** | **5-12 hours** |

### Skills Required

- **Python** (intermediate+)
- **WebSockets** (basic understanding)
- **Async programming** (essential for Pipecat)
- **Twilio API** (basic)
- **Docker/containers** (for deployment)

### Code Complexity

Pipecat significantly reduces complexity. A basic voice agent is ~100-200 lines of Python:

```python
# Simplified example - actual production code ~200-500 lines
from pipecat.frames import EndFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.groq import GroqLLMService  
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.transports.services.twilio import TwilioTransport

async def main():
    transport = TwilioTransport()
    stt = DeepgramSTTService(api_key="...")
    llm = GroqLLMService(api_key="...", model="llama-3.3-70b-versatile")
    tts = CartesiaTTSService(api_key="...", voice_id="...")
    
    pipeline = Pipeline([transport.input(), stt, llm, tts, transport.output()])
    runner = PipelineRunner()
    await runner.run(pipeline)
```

---

## 8. Hybrid Approach

### When to Use Each

| Scenario | Recommendation |
|----------|----------------|
| Prototyping | Vapi (faster to start) |
| < 500 min/month | Vapi (not worth self-hosting) |
| 500-2,000 min/month | Either (break-even zone) |
| > 2,000 min/month | Self-hosted (clear savings) |
| Complex multi-step flows | Vapi (better tooling) |
| Simple Q&A agents | Self-hosted |
| Need custom VAD/interruption | Self-hosted |
| Enterprise security requirements | Self-hosted |

### Hybrid Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     TRAFFIC ROUTER                           │
│                                                              │
│   ┌─────────────────┐           ┌─────────────────┐         │
│   │  Complex Calls  │           │  Simple Calls   │         │
│   │  (multi-agent,  │           │  (FAQ, routing) │         │
│   │   transfers)    │           │                 │         │
│   └────────┬────────┘           └────────┬────────┘         │
│            │                             │                   │
│            ▼                             ▼                   │
│   ┌─────────────────┐           ┌─────────────────┐         │
│   │      Vapi       │           │   Self-Hosted   │         │
│   │  ($0.15/min)    │           │   ($0.05/min)   │         │
│   │                 │           │                 │         │
│   │  - Transfers    │           │  - FAQ answers  │         │
│   │  - Multi-agent  │           │  - Simple tasks │         │
│   │  - Complex tools│           │  - High volume  │         │
│   └─────────────────┘           └─────────────────┘         │
└──────────────────────────────────────────────────────────────┘
```

---

## 9. Recommendations

### Decision Matrix

| Criteria | Score (Self-Host) | Score (Vapi) |
|----------|-------------------|--------------|
| Cost at scale | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Time to first call | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Customization | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Maintenance burden | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Latency control | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Feature richness | ⭐⭐⭐ | ⭐⭐⭐⭐ |

### Final Recommendation

**For your use case (eliminating platform fees):**

1. **Start with Vapi** for development and validation (you already have this)
2. **Build self-hosted in parallel** once you hit ~1,000 min/month
3. **Migrate high-volume, simple agents first** — FAQ bots, appointment reminders
4. **Keep complex flows on Vapi** until self-hosted is battle-tested

### ROI Calculation

| Investment | Value |
|------------|-------|
| Build effort | ~80 hours × $100/hr = $8,000 |
| Monthly savings at 5,000 min | ~$400 |
| Payback period | ~20 months |
| Monthly savings at 50,000 min | ~$4,000 |
| Payback period | ~2 months |

**At 50,000 minutes/month, self-hosting pays for itself in ~2 months.**

---

## 10. Quick Start Checklist

### To build self-hosted voice agent:

- [ ] Sign up for API keys:
  - [ ] Deepgram (free $200 credit)
  - [ ] Groq (free tier available)
  - [ ] Cartesia (free tier)
  - [ ] Twilio (PAYG)

- [ ] Clone Pipecat phone bot quickstart:
  ```bash
  git clone https://github.com/pipecat-ai/pipecat-examples
  cd pipecat-examples/twilio-chatbot
  ```

- [ ] Configure environment variables

- [ ] Set up ngrok for local testing

- [ ] Configure Twilio webhook

- [ ] Test end-to-end call

- [ ] Deploy to Railway/Fly.io

- [ ] Monitor latency and costs

---

## References

- [Pipecat GitHub](https://github.com/pipecat-ai/pipecat)
- [Pipecat Twilio Examples](https://github.com/pipecat-ai/pipecat-examples/tree/main/twilio-chatbot)
- [Groq Pricing](https://groq.com/pricing)
- [Deepgram Pricing](https://deepgram.com/pricing)
- [Cartesia Pricing](https://cartesia.ai/pricing)
- [Voice AI Illustrated Guide](https://voiceaiandvoiceagents.com/)
