# Keiracom System — Go Sidecar

Phase A4 research → Wave 1 production build. Canonical-key anchor: `ceo:keiracom_architecture_v2_locked` Cat 10 `mcp.go_sidecar` — **RATIFIED-DM**, V1-launch. Wave 1 dispatch: `Agency_OS-2c7m` (systemd deploy + circuit breakers per MCP-server + per-tenant token-bucket rate limiter).

Research history: `docs/wave2/phase_a4_go_sidecar_research_and_scaffold.md`.

## What's here

| Path | Purpose |
|---|---|
| `cmd/sidecar/main.go` | HTTP listener — `/health`, `/validate`, `/proxy` (forwarding) |
| `cmd/sidecar/proxy_test.go` | 7 black-box handler tests — validate / proxy / breaker / rate-limit / secret-scan paths |
| `internal/config/config.go` | Static whitelist `Config` struct + JSON load (extended with `rate_limit` + `mcp_servers`) |
| `internal/validator/validator.go` | `Validator` interface + `DefaultValidator` (tool / path / domain / secret-scan) |
| `internal/validator/validator_test.go` | 8 tests — 5 Allow negative + 1 Allow positive + 2 ScanResponse |
| `internal/breaker/breaker.go` | Per-MCP-server circuit breaker (Closed / Open / HalfOpen) — Wave 1 |
| `internal/breaker/breaker_test.go` | 6 tests — closed allow, threshold trip, cooldown→half-open, probe success/failure, manager isolation |
| `internal/ratelimit/ratelimit.go` | Per-tenant token-bucket rate limiter — Wave 1 |
| `internal/ratelimit/ratelimit_test.go` | 7 tests — unregistered, zero-spec, burst, refill, cap, isolation, reset |
| `config.example.json` | Example tenant config — allowlists, deny paths, secret patterns, rate-limit spec, MCP server map |
| `keiracom-go-sidecar.service` | systemd unit (user-scope) — Wave 1 deploy |
| `scripts/build.sh` | Builds the binary into `./bin/sidecar` (idempotent; invoked by `ExecStartPre`) |
| `scripts/install-systemd.sh` | Installs + enables + restarts the systemd unit (idempotent) |
| `Dockerfile` | Multi-stage build → distroless static binary (alternative deploy path) |
| `docker-compose.go-sidecar.yml` | Per-tenant compose snippet (mirrors `embeddings/docker-compose.tei.yml`) |
| `go.mod` / `go.sum` | Module declaration — `go 1.22`, **stdlib only** (empty `go.sum`) |

## Quick check

```bash
cd infra/keiracom_system/go_sidecar
./scripts/build.sh                                          # produces ./bin/sidecar
SIDECAR_CONFIG_PATH=./config.example.json \
  SIDECAR_ADDR=127.0.0.1:4100 ./bin/sidecar &               # run locally
curl -fsS http://127.0.0.1:4100/health                      # {"ok":true}

# Validate a sample tool call (validate-only path, no forwarding)
curl -fsS -X POST http://127.0.0.1:4100/validate \
  -H 'content-type: application/json' \
  -d '{"TenantID":"tenant_demo","Tool":"read_file","Path":"/workspace/tenant_demo/notes.md"}'
# {"allow":true}

# /proxy — validate + rate-limit + circuit-break + forward to MCP server
curl -fsS -X POST http://127.0.0.1:4100/proxy \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant_demo","tool":"read_file","server":"search","body":{"q":"hi"}}'
```

## Install as systemd service

```bash
cd infra/keiracom_system/go_sidecar
sudo install -d -m 0755 /etc/keiracom
sudo install -m 0600 -o $USER config.example.json /etc/keiracom/sidecar.json   # or your tenant config
./scripts/install-systemd.sh                                                   # daemon-reload + enable + restart
systemctl --user status keiracom-go-sidecar
```

## Wave 1 dispatch deliverables (Agency_OS-2c7m)

1. **systemd service** — `keiracom-go-sidecar.service` + `scripts/install-systemd.sh`. User-scope, fail-loud on missing binary (`ExecStartPre` calls `scripts/build.sh`), 128M MemoryMax, `ProtectSystem=strict`, append-only log to `~/clawd/logs/keiracom-go-sidecar.log`.
2. **Per-MCP-server circuit breakers** — `internal/breaker`. `Manager.Get(serverName)` lazy-instantiates one breaker per logical upstream; 5 consecutive failures → `Open`, 30s cooldown → `HalfOpen` single probe → `Closed` on success / `Open` on failure. `/proxy` 503s on `ErrBreakerOpen`.
3. **Per-tenant token-bucket rate limiter** — `internal/ratelimit`. Spec loaded from `tenant.rate_limit` (`{rps, burst}`); continuous refill, hard cap at `burst`; bucket-empty → `/validate` and `/proxy` return 429. Zero spec = unlimited (explicit opt-out by absence in config).

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
