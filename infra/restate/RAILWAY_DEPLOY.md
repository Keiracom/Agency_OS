# Track C1 — Restate Deploy on Railway

Two-service deploy:
1. **Restate server** — durable execution engine (official Docker image)
2. **Python service** — `governance` VirtualObject that registers with the server

## Service 1: Restate server

```bash
railway up --service restate-server \
  --image docker.io/restatedev/restate:1.4
```

Required ports (private to the project):
- `9070` — admin / ingress (HTTP)
- `8080` — service registration (gRPC)

Env vars:
- `RESTATE_BASE_DIR=/restate-data` (persistent volume mount required)

## Service 2: Python service

`infra/restate/Dockerfile` builds the **Restate server** image — do not reuse for the Python service. The Python service needs its own container that runs `uvicorn src.governance.restate_service:asgi_app --host 0.0.0.0 --port 9070`. A `Dockerfile.service` plus dedicated `railway.service.json` is a follow-up artefact (not in this PR — code-only ship).

Sketch (for the follow-up):
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir "restate-sdk>=0.17.0,<0.18.0" "uvicorn[standard]>=0.27"
COPY src /app/src
ENV PYTHONUNBUFFERED=1
EXPOSE 9070
CMD ["uvicorn", "src.governance.restate_service:asgi_app", "--host", "0.0.0.0", "--port", "9070"]
```

Env vars:
- `RESTATE_HOST=restate-server.railway.internal` (Railway private DNS)
- `RESTATE_ADMIN_PORT=9070`

Health check: `GET /health` returns `200 OK` once the SDK has handshaked with the server.

## Service registration

Once both services are running, register the Python service with the Restate server:

```bash
curl -X POST "https://${RESTATE_PUBLIC_HOST}/deployments" \
  -H "Content-Type: application/json" \
  -d '{"uri": "http://restate-py-service.railway.internal:9070"}'
```

Verify registration:
```bash
curl "https://${RESTATE_PUBLIC_HOST}/services" | jq '.services[] | .name'
# Expected: includes "governance"
```

## Smoke test

Invoke `directive_start` against the deployed service:
```bash
curl -X POST "https://${RESTATE_PUBLIC_HOST}/governance/SYNTH-C1-TEST/directive_start" \
  -H "Content-Type: application/json" \
  -d '{"directive_id": "SYNTH-C1-TEST", "scope": "deploy verification", "started_at": "2026-05-01T13:00:00Z"}'
```

Expected response: `{"ok": true, "state": {...}}`.

## Rollback

```bash
railway service delete restate-py-service
railway service delete restate-server
```

Removing both services frees Railway spend. The Python code remains in the repo for future redeploy.

## Cost estimate

- Restate server: ~$5–10/month (small instance, persistent volume)
- Python service: ~$5/month (small instance, no volume)
- Total: ~$10–15/month, within the Railway spend Dave pre-approved 2026-05-01.

## Status — 2026-05-01

- [x] Code: SDK 0.17.x compatibility (this PR)
- [x] Dockerfile: built, not yet pushed to Railway
- [ ] Service 1 deployed
- [ ] Service 2 deployed
- [ ] Service registered
- [ ] Smoke test passing

Deploy is a follow-up directive — this PR ships the code + infra spec only.
