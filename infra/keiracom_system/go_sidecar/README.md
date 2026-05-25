# Keiracom System — Go Sidecar (scaffold)

Phase A4 research + scaffold. Canonical-key anchor: `ceo:keiracom_architecture_v2_locked` Cat 10 `mcp.go_sidecar` — **RATIFIED-DM**, V1-launch (BUILD pending). Owners: Atlas + Orion (engineer-tier).

This directory is the **research scaffold only.** Engineer-tier builds the production sidecar on this shape; the research doc at `docs/wave2/phase_a4_go_sidecar_research_and_scaffold.md` carries the full findings + handoff scope.

## What's here

| Path | Purpose |
|---|---|
| `cmd/sidecar/main.go` | HTTP listener (`/health` + `/validate`) — entrypoint |
| `internal/config/config.go` | Static whitelist `Config` struct + JSON load |
| `internal/validator/validator.go` | `Validator` interface + `DefaultValidator` (tool / path / domain / secret-scan) |
| `config.example.json` | Example tenant config — allowed tools, denied system paths, secret patterns |
| `Dockerfile` | Multi-stage build → distroless static binary |
| `docker-compose.go-sidecar.yml` | Per-tenant compose snippet (mirrors `embeddings/docker-compose.tei.yml`) |
| `go.mod` / `go.sum` | Module declaration — `go 1.22`, **zero external deps in scaffold** (empty `go.sum`) |
| `internal/validator/validator_test.go` | 8 tests — 5 Allow negative + 1 Allow positive + 2 ScanResponse (one each side) |

## Quick check (engineer-tier will run)

```bash
cd infra/keiracom_system/go_sidecar
go build ./...                              # scaffold compiles, no external deps
docker compose -f docker-compose.go-sidecar.yml up --build  # local sidecar :4100
curl -fsS http://localhost:4100/health      # {"ok":true}

# Validate a sample tool call
curl -fsS -X POST http://localhost:4100/validate \
  -H 'content-type: application/json' \
  -d '{"TenantID":"tenant_demo","Tool":"read_file","Path":"/workspace/tenant_demo/notes.md"}'
# {"allow":true}

# Same call but pointed at a system path → 403
curl -i -X POST http://localhost:4100/validate \
  -H 'content-type: application/json' \
  -d '{"TenantID":"tenant_demo","Tool":"read_file","Path":"/var/keiracom/system/reasoning.log"}'
# HTTP/1.1 403 Forbidden
# validator: system path access denied (ux.files.system_files_hidden)
```

## Three enforcement responsibilities (from V2 lock)

1. **Tool-call whitelist** — `mcp.go_sidecar` Cat 10. Mechanical, static config; agent's MCP tool name must appear in `tenant.allowed_tools`.
2. **System file isolation** — `ux.files.system_files_hidden` Cat 19 (RATIFIED-CEO). System files (reasoning traces, system prompts, governance configs, Temporal state) NEVER queryable. Prefix-deny on `tenant.system_path_deny`. **Cross-dep:** `ux.files.system_files_hidden ← mcp.go_sidecar` is the named GAP closed by this build.
3. **Secret leak prevention** — `infra.secrets_management` Cat 16 LOOSE-BLOCKER. "Go Sidecar validates no raw secret leaks into LLM context." Pattern scan on response bodies before they reach the LLM.

## Engineer-tier handoff scope

Full handoff scope + LoC estimate + complexity assessment in the research doc:
`docs/wave2/phase_a4_go_sidecar_research_and_scaffold.md` §6.

### Architectural defaults — locked

- **Fail-closed on SPOF.** Aiden architectural call 2026-05-25 (research doc §7 risk 2). If the sidecar `/validate` call fails for any reason — timeout, 5xx, connection refused — the upstream MCP tool call is **REJECTED**, not forwarded. Caller surfaces a sanitised denial to the LLM context. Reasoning: sidecar is the security interceptor per Cat 10 "mechanical enforcement"; failing-open silently bypasses security, failing-closed produces visible breakage that is recoverable via customer report + ops response. Consistent with Cat 16 HARD GATE posture (Vault sealed = fail; BYOK invalid = fail; rate limit hit = reject). Engineer-tier item 1 (`/proxy` forwarding half) MUST default fail-closed.

### Engineer-tier NITs (non-blocking, track in build dispatch)

Aiden surfaced 5 NITs against the scaffold during architectural review 2026-05-25. Non-blocking for scaffold merge; engineer-tier addresses during the production build:

- **NIT-1 — Typed deny errors.** Replace `errors.New("...")` strings with typed sentinel errors (`ErrUnknownTenant`, `ErrToolNotAllowed`, `ErrSystemPathDenied`, `ErrDomainNotAllowed`, `ErrSecretLeak`). Improves caller branch logic + structured logging.
- **NIT-2 — Compiled-regex secret patterns + p99 benchmark.** Swap `strings.Contains` for compiled regex set in `ScanResponse`. Benchmark on 10KB response body; cap at p99 ≤ 1ms.
- **NIT-3 — Config.Load validates `len(Tenants) > 0`.** An empty `Tenants` map deserialises silently and denies every call — load should return an explicit error so misconfigured boots fail loud, not silent.
- **NIT-4 — `SchemaVersion` field on `Config`.** Add `SchemaVersion int` so future HMAC-signed config migrations have a compat axis. Mirror Vault token schema versioning.
- **NIT-5 — Request-ID propagation.** `/validate` reads `X-Request-ID` header (or generates one) and threads through logs + denial messages. Lets the agent-side caller correlate the denial back to the originating LLM turn for traceability.

### Security posture (V1 build targets — Max review note)

- **TLS posture.** Sidecar↔agent traffic V1: localhost-only loopback (intra-pod / intra-`docker-compose-network`), no TLS required. V1.1: mTLS once sidecar moves cross-pod (or once Cat 17 hybrid-pool surfaces sidecars on a shared subnet).
- **Request size cap.** Engineer-tier MUST wrap incoming bodies with `http.MaxBytesReader` — default cap 64 KB on `/validate`, configurable per tenant. Prevents memory-exhaustion DoS on malformed payloads.
- **Auth pattern.** Per-tenant HMAC bearer token on the `/validate` request (`Authorization: Bearer <hmac>`); secret material loaded from the same static config (`config.example.json` adds `auth_secrets[<tenant_id>]`). Upgrade to mTLS client-cert auth at V1.1 when cross-pod.

### Known unknowns (engineer-tier resolves during build)

- **Test strategy boundary** — unit tests live in `internal/validator/validator_test.go` (this PR); integration tests (compose-up + curl matrix) are engineer-tier item 8. Decide whether to run Go integration tests inside CI or only in a pre-merge smoke environment.
- **Deployment secret material** — config files mounted read-only from `/etc/keiracom/sidecar.json`. Where does the config originate (Vault static-mount? K8s Secret? GitOps-templated)? Engineer-tier picks one path and documents it in the operate runbook.
- **GitOps wiring** — which CD picks up sidecar config diff. If it's the same Railway+Vercel pipeline (per CI/CD audit `docs/cicd_gap_audit_findings.md`), engineer-tier wires the sidecar redeploy on `infra/keiracom_system/go_sidecar/**` paths-filter.
- **Structured logging library** — `log/slog` (stdlib, Go 1.21+) vs `zap` (faster, more featureful). Default to `slog` for zero-dep posture unless benchmarks force `zap`. PII redaction policy: never log tenant payload bodies; log only `tenant_id + tool + denial_reason`.
- **Liveness vs readiness probes** — `/health` currently serves both. Engineer-tier separates: `/health/live` (process up) vs `/health/ready` (config loaded + first config-validation pass succeeded). Critical for fail-closed: a not-ready sidecar must not receive traffic from upstream callers.
