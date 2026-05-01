# Restate — Durable Execution Engine

## What is Restate?

Restate is a durable execution engine that provides reliable, exactly-once execution of distributed workflows.
It persists execution state to a durable log so that services can resume from exactly where they left off after
crashes, restarts, or network failures. It replaces ad-hoc retry logic with structured, persistent virtual objects.

Agency OS uses Restate as the backbone for the Governance layer — tracking directive lifecycle (start, in-progress,
complete) with durable state and enforced completion evidence checks.

## Ports

| Port | Purpose |
|------|---------|
| 8080 | HTTP ingress — Python services register here; clients invoke handlers here |
| 9070 | Admin/meta API — register services, inspect invocations, cancel stuck runs |

## Deploying on Railway

1. Add a new Railway service pointing to this repo.
2. Set the **Dockerfile path** to `infra/restate/Dockerfile`.
3. Railway will build and expose port 8080 (ingress) and 9070 (admin).
4. Set the `RESTATE_INGRESS_URL` env var in any Python service that needs to invoke Restate handlers.

## How Python Services Connect

Python services use the `restate-sdk` package:

```python
from restate import VirtualObject, ObjectContext
from restate.server import app
import hypercorn.asyncio

service = VirtualObject("governance")

@service.handler()
async def my_handler(ctx: ObjectContext, payload: dict) -> dict:
    ...

asgi_app = app([service])
# Run with: hypercorn src/governance/restate_service:asgi_app --bind 0.0.0.0:9080
```

The Python service registers itself with the Restate server via:
```bash
curl -X POST http://localhost:9070/deployments \
  -H 'Content-Type: application/json' \
  -d '{"uri": "http://<python-service-host>:9080"}'
```

After registration, callers invoke handlers through the Restate ingress (port 8080), not directly.
