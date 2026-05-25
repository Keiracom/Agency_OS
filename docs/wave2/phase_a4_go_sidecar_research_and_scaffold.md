# Phase A4 — Go Sidecar: Research + Scaffold Findings

**Agent:** scout
**Dispatched by:** elliot (Dave directive: "wake now and continue", Phase A4 — Go Sidecar deployment, RESEARCH + SCAFFOLDING phase)
**Date:** 2026-05-25
**Mandate:** Research-tier ingestion of Go + sidecar patterns; deliver a minimal scaffold (~50-100 LoC) demonstrating shape; name engineer-tier handoff scope. NOT a full implementation. Read-only research + scaffold authoring.
**Build-track:** `infra/keiracom_system/go_sidecar/` (mirrors TEI sidecar at `infra/keiracom_system/embeddings/`).
**LAW XIV mandate:** verbatim evidence, raw output, no summary-only.

---

## NOTES — Canonical-key query gate (per `_orchestrator.md` audit-dispatch checklist, 2026-05-24)

Queried `ceo:keiracom_architecture_v2_locked` (Supabase `public.ceo_memory`, updated_at `2026-05-25 13:17:35Z`). Pulled the V2 inventory at `/home/elliotbot/clawd/Agency_OS/docs/architecture/keiracom_architecture_v2_inventory.md` (62700 bytes). Verbatim relevant rows:

**Cat 10 — `mcp.go_sidecar` (line 149 of inventory):**
> `mcp.go_sidecar | Go sidecar — security interceptor + tool-call validator; static config not knowledge graph; mechanical enforcement | RATIFIED-DM | Viktor verbatim 2026-05-25 + Aiden Phase 1 §3.A item 7 | nothing | V1-launch (BUILD pending)`

Cat 10 Owner: Atlas + Orion (engineer-tier).

**Cat 19 — `ux.files.system_files_hidden` (line 364 of inventory):**
> `ux.files.system_files_hidden | System files (reasoning traces, system prompts, governance configs, Temporal state) NEVER queryable by customer file system | RATIFIED-CEO | Dave directive | nothing | V1-launch`

**Cross-dependency edge (line 461 of inventory, verbatim):**
> `ux.files.system_files_hidden ← mcp.go_sidecar` **currently GAP/pending** — customer file system could leak system files without Go Sidecar enforcement

**Cat 16 — `infra.secrets_management` cross-cite (line 208 of inventory, verbatim partial):**
> "agents call Vault at spawn; **Go Sidecar validates no raw secret leaks into LLM context.** Depends on: mcp.go_sidecar + tenant.table + mem.byok."

**Cat 19 — `ux.mobile_strategy` (line 484, anchoring the research-tier ingestion pattern):**
> RATIFIED-CEO: "V1 ships web-only (Next.js); native mobile follows V1.1 once fleet has ingested React Native knowledge + completed practice phase. … Decision #1 — **fleet research + memory ingestion path chosen over hire-specialist**"

**V2 locks not for redeliberation (from `ceo_memory` value):** `cat_19_5tab_nav_holds`, `cat_19_notifications_header_icon`, `cat_19_mobile_strategy_hybrid_b_plus_c`, `ux.mobile_strategy`, `ux.react_native_ingestion_programme` — i.e. Go Sidecar follows the same research-first ingestion-programme pattern that Dave ratified for React Native.

**Empirical witness — zero existing Go in fleet:** `find /home/elliotbot/clawd -name "*.go" -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/vendor/*"` returned **0 files**. Confirms Aiden's "zero specialisation" assertion empirically.

---

## 1. Go-sidecar shape — three patterns considered

### Shape A — Embedded Go library (in-process call)

OPA (Open Policy Agent) supports embedding via `github.com/open-policy-agent/opa/v1/rego`:

> "OPA can be embedded inside Go programs as a library… the simplest way to embed OPA as a library is to import the github.com/open-policy-agent/opa/rego package." — openpolicyagent.org/docs/integration

Lowest latency (in-process function call), but **the consuming process must be Go.** Keiracom agents are Python (Claude Code subprocess + Python orchestrator), so an embedded Go library cannot be called directly. **REJECTED for V1.**

### Shape B — HTTP sidecar (Envoy `ext_authz`-style) — RECOMMENDED

> "With a sidecar, you configure Envoy's ext_authz filter to call a centralized policy engine on every request. The authorization decision happens in the sidecar before the request ever reaches your application code." — cloud.google.com/service-mesh/docs/gateway/security-envoy-setup

Per-tenant Go HTTP server co-located with the agent container. Agents (Python) POST tool calls to `http://sidecar:4100/validate` before invoking the MCP server. Sidecar validates against static config + returns `allow`/`deny`. Network hop adds ~1-5ms; works regardless of agent language.

**This is the recommended shape** because:
1. **Language-agnostic** — Python agents call via stdlib `urllib`.
2. **Matches mcp.go_sidecar Cat 10 phrasing** — "Go sidecar — security interceptor + tool-call validator". Sidecar = separate process = HTTP boundary.
3. **Mirrors the TEI sidecar pattern** — `infra/keiracom_system/embeddings/docker-compose.tei.yml` is already shipped (Phase 2 wave 2 item 2, PR #1133). Same per-tenant docker-compose project pattern.
4. **MCP Gateway/Interceptor literature converges on this shape** — see §2.

### Shape C — Transparent network proxy (iptables redirect)

> "In the sidecar pattern, Envoy is deployed as a companion container alongside each microservice container in a pod… It **intercepts all inbound and outbound network traffic** to/from the service." — Lukas Niessen, Medium 2026-03

Service-mesh-grade: redirect traffic at L3/L4 so the agent doesn't even know the sidecar exists. Higher infra complexity (Envoy + Istio control plane or equivalent); only worth it when agent code can't be modified. **Overkill for V1.** Re-evaluate at V2 if agent code immutability becomes a constraint.

---

## 2. MCP-ecosystem evidence — interceptor pattern is the converging standard

Verbatim from MCP-gateway literature (2026):

> "An MCP gateway is a specialized middleware layer that sits between MCP clients (AI agents) and MCP servers (tools), acting as a single, centralized policy enforcement point. Its primary function is to intercept every request from an agent, apply a series of security, policy, and routing rules, and then forward the request to the appropriate upstream tool." — tyk.io/learning-center/mcp-gateway-architecture-technical-guide

> "Interceptors act as programmable security filters/middleware that sit between AI clients and MCP tools, functioning as security guards that inspect, modify, or block every tool call in real-time. The interceptor pattern typically involves 'before' interceptors to inspect/modify/block tool calls, tool execution in secure containerized MCP servers, and 'after' interceptors to process/log/transform responses." — ChatForest, MCP Gateway & Proxy Patterns

**Standardisation signal — MCP SEP-1763** (modelcontextprotocol/modelcontextprotocol#1763):
> "SEP-1763: Interceptors for Model Context Protocol" — open proposal to standardise interceptor frameworks in 2025-2026. Our Go Sidecar should *not* deviate from whatever SEP-1763 ratifies; track it as a follow-up risk.

Mapping: our sidecar = a "**before** interceptor" per the ChatForest taxonomy. Engineer-tier adds an "**after** interceptor" for response-side secret scanning (see §3.3).

---

## 3. Three enforcement responsibilities — mapped from V2 lock to scaffold

The V2 inventory load-bears the sidecar across three categories. Scaffold demonstrates all three so engineer-tier doesn't accidentally drop one.

### 3.1 Tool-call whitelist (Cat 10, RATIFIED-DM)

Static config principle: "static config not knowledge graph; mechanical enforcement". No Rego, no OPA, no policy DSL. Just a Go struct keyed by tenant ID with `AllowedTools []string`. String-match at hot path; O(N) for small N (V1 tool counts in the 10s).

> Scaffold: `internal/validator/validator.go` `DefaultValidator.Allow` — `contains(t.AllowedTools, c.Tool)`.

### 3.2 System file isolation (Cat 19 `ux.files.system_files_hidden`, RATIFIED-CEO)

Closes the **named GAP** at inventory line 461: "`ux.files.system_files_hidden ← mcp.go_sidecar` currently GAP/pending — customer file system could leak system files without Go Sidecar enforcement."

Implementation: prefix-deny on `tenant.system_path_deny`. Example deny prefixes (from `config.example.json`):
- `/var/keiracom/system/`
- `/var/keiracom/reasoning_traces/`
- `/var/keiracom/system_prompts/`
- `/var/keiracom/governance/`
- `/var/keiracom/temporal_state/`

Any `read_file`/`write_file` tool call with a `Path` starting with one of these → 403.

> Scaffold: `internal/validator/validator.go` `DefaultValidator.Allow` — `strings.HasPrefix(c.Path, deny)`.

### 3.3 Secret leak prevention (Cat 16 `infra.secrets_management`, LOOSE-BLOCKER, V1 HARD GATE)

> Inventory line 208 verbatim: "Go Sidecar validates no raw secret leaks into LLM context."

Implementation: `ScanResponse` checks response body against tenant-specific + global secret patterns BEFORE the body reaches the agent's LLM context. Example global patterns: `BEGIN RSA PRIVATE KEY`, `BEGIN OPENSSH PRIVATE KEY`, `hvs.` (Vault tokens), `ghp_` (GitHub PATs). Tenant-specific: BYOK provider key prefixes (`sk-ant-`, `sk-proj-`, `AIza`).

> Scaffold: `internal/validator/validator.go` `DefaultValidator.ScanResponse`.

Engineer-tier upgrade path: replace substring match with compiled regex set; consider trufflehog detector library at V1.5 for high-recall pattern catalogue.

---

## 4. Scaffold deliverable

**Files (`infra/keiracom_system/go_sidecar/`):**

| Path | LoC (Go only) | Purpose |
|---|---:|---|
| `cmd/sidecar/main.go` | 57 | HTTP listener — `/health` + `/validate` |
| `internal/config/config.go` | 48 | Static whitelist `Config` struct + JSON load (no external YAML dep) |
| `internal/validator/validator.go` | 80 | `Validator` interface + `DefaultValidator` (tool/path/domain/secret-scan) |
| **Go total** | **185** | (~115 non-blank-non-comment) |
| `config.example.json` | n/a | Tenant config example — allowed tools, denied system paths, secret patterns |
| `Dockerfile` | n/a | Multi-stage → distroless static binary |
| `docker-compose.go-sidecar.yml` | n/a | Per-tenant compose snippet (mirrors TEI sidecar) |
| `go.mod` | n/a | `go 1.22`, **zero external deps** in scaffold |
| `README.md` | n/a | Quick-check curl snippets + responsibilities map |

**LoC honesty note:** dispatch target was 50-100 LoC; scaffold lands at ~115 non-blank-non-comment Go LoC across three files. Trimming would force dropping one of the three V2-lock responsibilities (secret-scan being the easiest to drop). I exceeded the LoC ceiling to preserve responsibility coverage — secret-scan IS in the V2 lock at Cat 16 LOOSE-BLOCKER, so dropping it from the scaffold would misrepresent the work engineer-tier still has to do. Engineer-tier review may opt to trim if they prefer.

**Zero-external-dep choice:** scaffold uses stdlib `encoding/json` instead of `gopkg.in/yaml.v3`. Engineer-tier picks YAML vs JSON for the production config format — both are 1-line swaps. Static config principle holds either way.

**Local verify (engineer-tier runs — Go is not installed in scout's worktree):**

```bash
cd infra/keiracom_system/go_sidecar
go build ./...
docker compose -f docker-compose.go-sidecar.yml up --build
curl -fsS http://localhost:4100/health   # {"ok":true}
```

---

## 5. Existing-Go-in-fleet probe — verbatim

```
$ find /home/elliotbot/clawd -name "*.go" -not -path "*/node_modules/*" \
    -not -path "*/.git/*" -not -path "*/vendor/*" 2>/dev/null | head -30
[zero output — no Go files anywhere in the fleet]
```

Confirms Aiden's Cat 19 §3B "zero specialisation" — no prior Go work exists. This research/scaffold doc is the fleet's first Go memory anchor.

Recommendation: also write a `bd discover` entry tagged `go-sidecar,first-go,scaffold-shape` to seed the Hindsight memory pool for the engineer-tier handoff — they should be able to `bd recall go-sidecar` and find this doc.

---

## 6. Engineer-tier handoff scope (what's left to build)

**In-scope for engineer-tier (Atlas + Orion per Cat 10 ownership):**

1. **Forwarding half** — `/validate` currently returns `{allow:true}` or 403. Production needs `/proxy` that validates THEN forwards to the upstream MCP server, streams the response back through `ScanResponse`, and returns to the agent. ~80 LoC.

2. **Python agent client** — `src/keiracom_system/mcp/sidecar_client.py` with `validate_or_raise(tool_call)` + retry/timeout + circuit-breaker. ~50 LoC.

3. **Hard-gate integration** — wire the client into the Python MCP server at `src/keiracom_system/mcp/server.py` so every `tools/call` request goes through the sidecar BEFORE the tool executes. ~30 LoC of changes.

4. **YAML config format + hot-reload** — engineer-tier may prefer YAML over JSON; add `fsnotify`-based reload so config changes don't require container restart. ~40 LoC + 1 external dep.

5. **Compiled-regex secret patterns** — swap `strings.Contains` for compiled regex set; benchmark cost on 10KB response bodies; cap at ~1ms p99 budget. ~30 LoC.

6. **Metrics + observability** — Prometheus `/metrics` endpoint (deny-rate per tenant, latency histogram, panic counter). ~40 LoC + Prometheus client dep.

7. **HMAC-signed tenant config** — config file integrity check at boot so a tampered config can't silently widen the allow-list. ~25 LoC.

8. **Integration tests** — Go `_test.go` files + Python integration test that spins compose stack, asserts allow/deny matrix, asserts system-path deny, asserts secret-pattern hit. ~150 LoC of test code.

9. **Atomic config swap with rollback** — `SIGHUP` triggers re-read of config; if new config fails validation, keep the old config in memory and log the failure to NATS. ~30 LoC.

10. **Documentation** — runbook at `docs/runbooks/go-sidecar-operate.md` covering: how to add a tenant, how to add a tool to the allowlist, how to drill a deny scenario, how to rotate secret patterns. Mirrors KEI-126 Postgres restore runbook structure.

**Out of scope for V1 (V1.5+):**

- SEP-1763 conformance once MCP standardises interceptor spec.
- Sigstore-signed config bundles.
- WASM-pluggable validators (Envoy WASM pattern).
- Multi-region sidecar replicas — V1 is single-region (syd1) per `vercel.json` regions setting.

**LoC + complexity estimate for full V1 engineer-tier build:**

| Item | Est. LoC | Est. complexity |
|---|---:|---|
| Items 1-3 (proxy, client, MCP wire-up) | ~160 | medium — touches Python MCP server hot-path |
| Items 4-5 (YAML/hot-reload, regex secret patterns) | ~70 + 1 Go dep | low |
| Items 6-7 (metrics, HMAC config) | ~65 + 1 Go dep | low |
| Items 8-10 (tests, atomic swap, runbook) | ~180 + 1 runbook | medium — drills are mandatory per Cat 16 HARD GATE |
| **Total V1 build (excluding scaffold)** | **~475 LoC** | medium |

Compared with the TEI sidecar precedent (PR #1133): TEI shipped ~250 LoC Python client + ~30 LoC compose snippet + ~150 LoC install script + tests. Go Sidecar will be larger (~475 LoC) because the validation surface is broader than TEI's "forward embedding request" job.

**Estimated engineer-tier time:** 2-4 work-days for Atlas + Orion in parallel (Atlas on proxy/MCP-integration, Orion on tests/runbook/config-hot-reload).

---

## 7. Risks + open questions for deliberation

1. **Network-hop tax.** Every MCP tool call gets ~1-5ms added latency. For tool-heavy agents (10+ calls/turn) that's 50ms cumulative. Acceptable for V1; revisit if Cat 17 per-tier-pool benchmarks show contention.
2. **Sidecar SPOF.** If the sidecar dies, MCP tool calls fail. Mitigation per Envoy precedent: `restart: unless-stopped` (in scaffold compose) + health-check gate from caller side. Engineer-tier should choose fail-closed (recommended for security) vs fail-open (recommended for availability). **Aiden + Elliot call.**
3. **Config tampering surface.** Static config file = anyone with disk write on the sidecar host can widen allow-list. Mitigation: HMAC-signed config (item 7 above) + read-only volume mount in compose (already in scaffold). Worth raising as Phase 2 sub-deliberation.
4. **SEP-1763 standardisation drift.** Our sidecar is an ad-hoc HTTP `/validate` endpoint. If MCP SEP-1763 ratifies a different RPC shape (e.g. gRPC), we'll need a v2 protocol layer. Track as P3 risk; low likelihood pre-V1.
5. **Per-tenant sidecar count.** TEI sidecar pattern is per-tenant. If Go Sidecar follows, that's N containers for N tenants → 4 GB+ idle RSS at 100 tenants. Cat 17 hybrid (shared pool for Solo/Pro, dedicated for Team+) likely applies. **Engineer-tier benchmark before V1 launch.**

---

## SOURCES (verbatim probe trail)

- `ceo:keiracom_architecture_v2_locked` ceo_memory key (updated_at `2026-05-25 13:17:35Z`)
- `docs/architecture/keiracom_architecture_v2_inventory.md` (62700 bytes) — lines 143-170 (Cat 10), 199-215 (Cat 16), 289-491 (Cat 19), 461 (cross-dep edge)
- `find /home/elliotbot/clawd -name "*.go" -not -path ...` (empirical zero-Go-files witness)
- `git show origin/main:infra/keiracom_system/embeddings/README.md` + `docker-compose.tei.yml` (TEI sidecar pattern reference)
- Web research (URLs):
  - https://www.openpolicyagent.org/docs/integration — OPA Go embedding
  - https://cloud.google.com/service-mesh/docs/gateway/security-envoy-setup — Envoy ext_authz
  - https://tyk.io/learning-center/mcp-gateway-architecture-technical-guide/ — MCP gateway architecture
  - https://chatforest.com/guides/mcp-gateway-proxy-patterns/ — MCP interceptor taxonomy
  - https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1763 — SEP-1763 Interceptors proposal
  - https://lukasniessen.medium.com/the-sidecar-pattern-why-every-major-tech-company-runs-proxies-on-every-pod-8138d79c597a — Sidecar pattern survey
  - https://medium.com/@monishashah06/the-sidecar-security-microservice-pattern-enforcing-path-aware-security-at-scale-d56d02136da9 — Sidecar security micropattern
  - https://pkg.go.dev/github.com/go-coldbrew/interceptors — Go interceptors reference (gRPC, not adopted)
