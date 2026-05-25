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
| `go.mod` | Module declaration — `go 1.22`, **zero external deps in scaffold** |

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
