# Auditor — Arize Phoenix self-hosted observability

Phase 2 roadmap component. Self-hosted Phoenix instance for governance-event
traces and LLM-call observability. Complement to the COO bot — COO summarises
plain-English; Phoenix shows the raw timeline + drill-down.

## Why Phoenix

- Self-hosted, $0 marginal (Railway compute only)
- OTLP ingest (gRPC 4317, HTTP 4318) — same protocol used by OpenAI tracing
- UI at :6006 — trace inspection, span timing, latency histograms
- SQLite persistence (volume-mounted)

## Ports

| Port | Purpose |
|------|---------|
| 6006 | Web UI + REST API |
| 4317 | OTLP gRPC ingest (Phoenix native + standard OTel SDKs) |
| 4318 | OTLP HTTP ingest |

## Deploying on Railway

```bash
railway up --service auditor-phoenix \
  --dockerfile infra/phoenix/Dockerfile
```

Add a persistent volume mount at `/tmp/phoenix` so trace history survives
restarts. The `railway.json` here points Railway at this Dockerfile +
healthcheck on `/healthz`.

Env vars:
- `PHOENIX_PORT=6006` (UI)
- `PHOENIX_GRPC_PORT=4317`
- `PHOENIX_WORKING_DIR=/tmp/phoenix`
- `PHOENIX_HOST=0.0.0.0` (Railway internal binding)

## Smoke test (post-deploy)

```bash
curl "https://${PHOENIX_PUBLIC_HOST}/healthz"
# Expected: HTTP 200, body {"status":"healthy"}
```

Open `https://${PHOENIX_PUBLIC_HOST}/` for the UI.

## What's not in v1 (follow-up)

- **Python adapter** — `src/observability/phoenix_client.py` to ingest
  `public.governance_events` rows as Phoenix spans. Sketch:
  ```python
  from openinference.instrumentation import OpenInferenceTracer
  tracer = OpenInferenceTracer(endpoint="http://auditor-phoenix.railway.internal:4317")
  tracer.span("gatekeeper_decision", attributes={...}).end()
  ```
- **OpenAI auto-tracing** — `phoenix.otel.register(project_name="agency-os")`
  in service entry points to capture every OpenAI call.
- **CI dashboard** — daily auto-snapshot of Hit Rate / Gatekeeper allow-rate
  / agent token spend.

These are separate directives once Phoenix is verified live.

## Cost estimate

- Phoenix container: ~$5–10/month (small instance + 1GB SQLite volume)
- No external API costs (self-hosted)

Within the Railway spend Dave pre-approved 2026-05-01.

## Status — 2026-05-01

- [x] Dockerfile + railway.json (this PR)
- [x] Deploy spec (this README)
- [ ] Service deployed on Railway
- [ ] Smoke test passing
- [ ] Python adapter (`src/observability/phoenix_client.py`) — follow-up
- [ ] OpenAI auto-tracing wired — follow-up
