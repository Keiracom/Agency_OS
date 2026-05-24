# Three-Repo Carve-Out Execution Plan

**Phase 1.2.5 artefact 1** — detailed companion to the high-level three-repo topology in `ARCHITECTURE.md §SECTION 2` (PR #1115).

**KEI:** Agency_OS-jj6m. **Author:** aiden (deliberator-tier governance doc per role-lock exception).
**Status:** authoring 2026-05-24. **Blocks:** Phase 2.0 repo creation.

This artefact answers: **for every top-level directory and key subdir in the current monorepo, which of the three target repos owns it?** Plus: which trees need surgical file-by-file carve-out vs wholesale assignment; the cross-repo dependency map; and the migration manifest schema for the actual Phase 2.0 operation.

---

## 1. Notes — canonical key paste (per audit-dispatch checklist `_orchestrator.md`)

Three canonical keys queried 2026-05-24 ahead of authoring. Pasted verbatim so reviewers can cross-check claims below against the SSOT.

### `ceo:agency_os_keiracom_separation_v1` (updated 2026-05-24T11:04Z)

> **Status:** RATIFIED. **Frame:** Agency OS = the BDR product (retired, archive); Keiracom = the agent fleet that built it.
>
> **3-repo topology (verbatim):**
> - "Internal fleet repo (working name `keiracom-fleet`) — Dave internal agent team configs, NOT customer-facing"
> - "Product repo (working name TBD, rename-ready) — V1.0 AI workforce code shipped to customers; Memory Abstraction Layer + Hindsight self-hosted + Go sidecar + MCP server + tenant onboarding + install script + CLI"
> - "Archive repo (existing URL preserved) — 1100 prior pull requests + dead BDR product code; marked inactive in README"
>
> **Naming resolution:** Keiracom = working name today. Final commercial name TBD post-launch. Architecture is rename-ready — every "keiracom" reference treated as a string variable.
>
> **Consolidated gates relevant to this artefact:**
> - "Phase 1.2.5 architecture doc bundle BEFORE first product-migration PR" ← this artefact is part of the bundle
> - "CI gate: product repo imports nothing from fleet or archive repos"
> - "Cross-repo dependency sync: shared constraints file; CI fails on lockfile drift"
> - "Migration manifest with dynamic exclusion (paths with active PR/KEI work excluded)"
> - "Skills directory ownership manifest drafted before any skill ships in product repo"
> - "Migration runner scope spans 3 repos + shared Supabase"

### `ceo:comm_architecture` (updated 2026-05-24)

> **Status:** CANONICAL. Three distinct comms paths — INBOUND to Elliot via NATS, OUTBOUND inter-agent via NATS+JSON, OUTBOUND elliot-to-Dave via Slack (restricted to elliot-only per Dave 2026-05-19, NOT decommissioned).
>
> **Implication for this artefact:** the Slack relay path is FLEET-only (Dave-facing Elliot endpoint). NATS substrate + bridges are FLEET-only (per-callsign relay infra). The product repo MUST NOT inherit either; product agents communicate via the MCP dispatcher (separate channel from the fleet's Elliot funnel).

### `ceo:memory_abstraction_layer_v1` (updated 2026-05-24T15:12Z)

> **Status:** RATIFIED. Hindsight self-hosted as memory engine (Vectorize.io MIT, per-tenant VPC). V1 primitives are thin wrappers around Hindsight TEMPR + CARA.
>
> **Implication for this artefact:** Memory Abstraction Layer code is PRODUCT-tier. Anything in `src/memory/` that implements MAL primitives (Ingest, Recall, Synthesize, Supersede, Trace, Delete) carves out to product. Fleet-side memory infra (Cognee, agent_memories writes, file-based session memory) stays FLEET. Bucket-assignment rule for memory code: if it's behind the MAL MCP API, PRODUCT; if it's an agent-internal memory consumer, FLEET.

---

## 2. Three-repo topology recap

| Repo | Working name | Contents | Audience |
|---|---|---|---|
| Fleet | `keiracom-fleet` | Agent runtime (CLAUDE.md per worktree, IDENTITY runbooks, enforcer, central listener, NATS bridges, Slack relay, boot services, systemd units, governance docs, deliberator/worker config) | Dave + internal fleet only |
| Product | `keiracom-product` (working name) | V1.0 AI workforce code shipped to customers — MCP dispatcher + Memory Abstraction Layer + Hindsight wrappers + Go sidecar + tenant onboarding + install script + CLI | External tenants |
| Archive | `keiracom/agency-os` (URL preserved) | Dead BDR product — Siege Waterfall, T0-T5 enrichment tiers, CIS/ALS scoring, GMB/ABN/BU, all 11+ dead vendor integrations, Agency OS dashboard | Read-only historical reference |

**Sequencing reminder (per canonical key):** this doc lands Phase 1.2.5; Phase 2.0 executes carve-out via migration runner; Phase 2.1 Hindsight spike; Phase 2.2 first product-migration PRs.

---

## 3. Per-directory ownership matrix

**Classification labels:**
- **F** = Fleet repo
- **P** = Product repo
- **A** = Archive repo
- **SPLIT** = needs per-file/per-subdir carve-out (see §4 file-by-file plan)
- **DROP** = artifact-only directory (`__pycache__`, `app-data/`) — created at runtime, not carved

### 3.1 Top-level directories

**Source-of-truth rule:** the carve-out operates on `git ls-tree -d --name-only origin/main` (tracked directories) — see the table below. Gitignored runtime directories (`logs/`, `.cache/`, `app-data/`, `__pycache__/`, host-side `~/.claude/projects/`) are NOT carved per se; they are recreated per-worktree by the running fleet code in their target repo. Conceptual ownership of these gitignored runtime dirs is documented at end of this section (3.1-gitignored).

| Dir | Classification | Rationale |
|---|---|---|
| `.beads/` | F | Central bd database lives in fleet repo per bd routing policy (PR #1120). |
| `.cache/` | DROP | Tool cache (per-worktree). Recreated per-repo. |
| `.claude/` | F | Per-worktree Claude Code config; modules import in IDENTITY chain. |
| `.clawdbot/`, `.clawdhub/` | F | Fleet bot-runtime metadata directories. |
| `.githooks/` | F | Repo git hooks (commit-msg etc.) — fleet workflow discipline. |
| `.github/` | SPLIT | Workflows split per-repo: stripped product matrix per PR #1118 + fleet's own CI. |
| `.openclaw/` | F | OpenClaw runtime metadata — fleet substrate. |
| `agency-os-html/` | A | Agency OS marketing HTML — dead product surface. |
| `agency-os-prototype/` | A | Agency OS prototype — dead product surface. |
| `agents/` | F | Fleet agent definitions (callsign personas). |
| `alembic/` | SPLIT | Alembic migration history mixes Agency OS schema + cross-product additions (ceo_memory.context). See §4.1. |
| `app-data/` | DROP | Runtime artifact directory. Created at runtime per-repo. |
| `builds/` | A | Agency OS build artifacts. |
| `campaigns/` | A | Agency OS campaign assets. |
| `canvas/` | A | Agency OS UX canvas. |
| `competitive/` | A | Agency OS competitive intel artifacts. |
| `config/` | SPLIT | Mixed: fleet systemd units + product allowlist (PR #1118) + Agency OS pricing config. See §4.2. |
| `data/` | A | Agency OS reference data (vendor lists, ICP fixtures). |
| `docs/` | SPLIT | Heavy split. See §4.3 — every `docs/*` subdir classified individually. |
| `frontend/` | A | Agency OS dashboard frontend. Product V1.0 dashboard is separate codebase (post-Phase-2.0). |
| `governance/` | F | Top-level governance content (mirrors `docs/governance/`). |
| `hooks/` | F | Claude Code per-worktree hooks. |
| `infra/` | SPLIT | NATS server config + Restate (fleet) vs Hindsight per-tenant deploy templates (product, when added). See §4.4. |
| `landing-page-analysis/` | A | Agency OS marketing artifact. |
| `maya-concepts/` | A | Agency OS concept work. |
| `mcp-servers/` | P | MCP server implementations — product-side dispatcher integration. |
| `memory/` | F | Top-level memory directory (callsign daily logs, cognee data). |
| `migrations/` | SPLIT | Mirrors `alembic/` split. See §4.1. |
| `personas/` | F | Fleet persona definitions. |
| `projects/` | F | Per-worktree projects directory. |
| `prompts/` | SPLIT | System prompts: some Agency OS-era CIS scoring, some cross-product agent boot prompts. See §4.5. |
| `research/` | A | Agency OS research artifacts (ICP analysis, vendor diligence). |
| `scripts/` | SPLIT | Heavy split. See §4.6 — every `scripts/*` subdir classified individually. |
| `skills/` | SPLIT | Per the canonical-key gate "Skills directory ownership manifest drafted before any skill ships in product repo" — file-by-file. See §4.7. |
| `SKILLS/` | F | Uppercase variant — likely fleet-only by convention. Confirm in Phase 2.0. |
| `src/` | SPLIT | Heaviest split. See §4.8 — every `src/*` subdir classified individually. |
| `supabase/` | SPLIT | Migrations + edge functions split. See §4.9. |
| `systemd/` | F | Fleet systemd unit definitions. |
| `tests/` | SPLIT | Per PR #1118 stripped allowlist — 27 product paths + remainder fleet/archive. See §4.10. |

### 3.1-gitignored — runtime/operational directories (not git-tracked, ownership rules)

These directories appear in worktrees but are NOT carved (not in `git ls-tree`). The rule documents which target repo's runtime recreates them.

| Dir | Conceptual owner | Rationale |
|---|---|---|
| `logs/` (if present) | F | Fleet operational state (callsign tmux logs, agent journald exports). Per-worktree runtime artefact. |
| `app-data/` | DROP | Runtime artifact directory; recreated per-repo. |
| `__pycache__/`, `*.pyc` | DROP | Python bytecode caches; recreated per-import. |
| `~/.claude/projects/<project-slug>/` (host-side, outside repo) | F | Per-callsign session memory + discovery log + auto-memory MEMORY.md. Fleet-tier — not in repo regardless of carve-out. |
| `/tmp/telegram-relay-<callsign>/` (host-side) | F | Per-callsign relay inbox/outbox dirs — fleet substrate (NATS bridges + watchers). |
| `/tmp/cognee-context-<callsign>.md` (host-side) | F | Per-callsign Cognee session-start context — fleet substrate (pre-Hindsight). |

If a peer review surfaces additional gitignored runtime directories (e.g. a Telegram bot data directory at `src/telegram_bot/` that doesn't appear on `origin/main`), classify them per the same rule: anything fleet-generated → F; anything tool/cache → DROP. Tracking gap: if such a directory becomes tracked in a future PR, add a row to §3.1 (top-level dirs) or the appropriate §4 SPLIT subsection.

---

## 4. File-by-file plan for SPLIT directories

### 4.1 `alembic/` + `migrations/` — schema migrations

Alembic migration files are timestamped; classify by what they touch:
- **F** — touches `ceo_memory`, `agent_memories`, `tasks` (bd backing table), `tool_call_log`, `evo_flow_callbacks`, `agent_status`. These are cross-callsign infra.
- **P** — touches tenant tables (none exist yet; will land in Phase 2.0+).
- **A** — touches `lead_pool`, `business_universe`, `campaigns`, `outreach_*`, `enrichment_*`, `cohort_*`, `cis_*`. All dead Agency OS schema.

**Operational rule:** alembic revision history is linear. The carve-out cannot truly split history — instead, the product repo gets a fresh alembic chain starting from the schema state at Phase 2.0 cutover. The fleet repo keeps the full history. Archive repo gets the full history too (frozen).

### 4.2 `config/`

| Subpath | Classification |
|---|---|
| `config/product_repo_test_allowlist.txt` | P (PR #1118 — moves with the test enforcer) |
| `config/systemd/user/*` | F (per-callsign relay watchers, NATS bridges, agent keepalive) |
| `config/governance/*` | F (governance config) |
| `config/pricing_*` | A (Agency OS pricing) |
| `config/*.json` (Agency OS) | A |

### 4.3 `docs/`

| Subpath | Classification |
|---|---|
| `docs/architecture/` | SPLIT — V1.0 docs (this file, MAL spec, Hindsight design) → P; Agency OS architecture diagrams → A |
| `docs/archive/` | A (already a known archive) |
| `docs/audits/` | F (cross-product audit reports + Stage 0 audit deliverables) |
| `docs/classification/` | F (PR #1121 discovery log classification report — operational artefact) |
| `docs/clones/` | F (clone bringup runbooks) |
| `docs/compliance/` | SPLIT — fleet compliance posture → F; tenant-facing compliance contracts → P (when added) |
| `docs/decomposition/` | F (LLM decomposition pattern docs) |
| `docs/governance/` | F (CONSOLIDATED_RULES.md, bd routing policy, DEFINITION_OF_DONE.md) |
| `docs/integrations/` | A (Agency OS vendor integrations docs) |
| `docs/legal/` | SPLIT — fleet IP/CLA → F; tenant ToS/DPA → P (when added) |
| `docs/marketing/` | A (Agency OS marketing collateral) |
| `docs/migration/` | F (Phase 1.2.5 migration artefacts — this doc is the meta-artefact) |
| `docs/manuals/` | A (Agency OS operator manuals) |
| `docs/operations/` + `docs/ops/` | F (fleet ops runbooks) |
| `docs/runbooks/` | F (callsign IDENTITY runbooks per PR #1116 + #fwdb + e02v) |
| `docs/pitch/` | A (Agency OS sales pitch) |

### 4.4 `infra/`

| Subpath | Classification |
|---|---|
| `infra/nats/` | F (NATS server config + JetStream stream definitions for fleet substrate) |
| `infra/restate/` | A (Agency OS workflow orchestration — Restate was BDR cohort runner) |
| `infra/systemd/` | F (systemd unit templates per callsign) |
| `infra/hindsight/` (when added) | P (per-tenant Hindsight Docker compose templates — Phase 2.0+) |

### 4.5 `prompts/`

Per-file classify:
- Agent boot prompts (Aiden/Max/Elliot deliberator briefs, worker dispatch templates) → F
- Agency OS scoring prompts (CIS/Reachability/Propensity calculation prompts) → A
- Product-side LLM prompts (MCP tool descriptions, tenant onboarding flow) → P (when added)

### 4.6 `scripts/`

| Subpath | Classification | Rationale |
|---|---|---|
| `scripts/alerts/` | F | Fleet alerting (BetterStack integrations, agent-down alerts) |
| `scripts/bd` (binary wrapper) | F | bd shim for KEI-22 SSOT routing |
| `scripts/ci/` | SPLIT | `check_product_test_allowlist.py` → P (PR #1118); fleet CI checks → F |
| `scripts/classifier/` | F (one-shot artefact) | PR #1121 discovery log classifier — runs once in Phase 1.2.5, then becomes archive reference |
| `scripts/common/` | SPLIT | Shared HTTP utils → likely duplicated to both; per-script classify |
| `scripts/git/` | F | Branch hygiene, worktree management |
| `scripts/governance/` | F | enforcer scripts, callsign-discipline gates, Sonar verify helpers |
| `scripts/hooks/` | F | Claude Code stop/PostToolUse hook handlers |
| `scripts/migration/` | F (one-shot artefacts) | weaviate_cutover.py (PR #1119), discovery log classifier, future migration runner — fleet-tier operational |
| `scripts/orchestrator/` | F | Elliot orchestrator runtime (next_work_prompter, supervisor_wake_publish, fleet_supervisor) |
| `scripts/valkey/` | F | Valkey/Redis Whiteboard helpers — fleet inter-agent coordination |
| `scripts/install_*_agent.sh` | F | Per-callsign install scripts |

### 4.7 `skills/`

Per the canonical-key gate "Skills directory ownership manifest drafted before any skill ships in product repo" — every skill needs explicit classification. Sketch:

| Skill | Classification | Rationale |
|---|---|---|
| `skills/drive-manual/` | F | Fleet operator skill — Drive Manual is internal SSOT |
| `skills/mcp-bridge/` | SPLIT | MCP bridge to 11+ vendors: dead Agency OS vendors (dataforseo, salesforge, vapi, telnyx, unipile, resend, prospeo, leadmagic) → A; cross-product (supabase, redis, prefect, railway, vercel, memory) → F or P case-by-case |
| `skills/pr-tool/` | F | PR creation helper for fleet workflow |
| `skills/leadmagic/` | A | Dead vendor |
| `skills/dataforseo/` | A | Dead vendor |
| `skills/loop/`, `skills/schedule/`, `skills/run/`, `skills/init/`, `skills/review/`, `skills/security-review/`, `skills/simplify/`, `skills/verify/` | F | Fleet-side Claude Code skills |
| `skills/claude-api/` | F | Claude API skill — fleet-tier (product agents call MCP, not Claude API directly) |
| `skills/kill/`, `skills/e2e/`, `skills/decomposer/` | F | Fleet-side operational skills |

**File-by-file manifest** for `skills/` ships as a separate artefact in Phase 2.0; the above is the architectural rule.

### 4.8 `src/`

Most consequential split. Classification covers all 34 subpackages tracked on `origin/main` (verified `git ls-tree -d --name-only origin/main src/`; earlier draft cited "38 subpackages" from worktree scan that included `__pycache__` + 3 historical subpackages no longer on main).

| Subpackage | Classification | Rationale |
|---|---|---|
| `src/agents/` | F | Fleet agent code (deliberator/worker process entry points) |
| `src/api/` | A | FastAPI surface for Agency OS dashboard (`/api/routes/campaigns.py` etc. — dead BDR endpoints) |
| `src/bot_common/` | F | Shared bot utilities (Slack relay client, NATS publish helpers, callsign env detection) |
| `src/cognee/` | F | Fleet Cognee integration (memory ingest for callsign discoveries) — pre-Hindsight |
| `src/config/` | SPLIT | Cross-cutting config; per-file classify |
| `src/data/` | A | Agency OS reference data loaders |
| `src/detectors/` | F | Fleet-side anomaly detectors (relay-watcher, callsign-stall) |
| `src/dispatcher/` | P | **V1.0 MCP dispatcher** — primary product code per PR #1118 allowlist (16 dispatcher tests) |
| `src/engines/` | A | Agency OS Siege Waterfall engines (scout, cohort_runner) |
| `src/evo/` | F (?) | EVO protocol implementation — confirm in Phase 2.0; may be cross-product orchestration |
| `src/fixtures/` | SPLIT | Test fixtures — split by what they fixture |
| `src/governance/` | F | Fleet governance enforcement code (CALLSIGN_ENFORCE, etc.) |
| `src/integrations/` | A | Agency OS 3rd-party vendor integrations (dead vendors per ARCHITECTURE.md §3) |
| `src/intelligence/` | A | Agency OS CIS/ALS/Reachability/Propensity scoring |
| `src/memory/` | P | **Memory Abstraction Layer V1** — primary product code per MAL V1 ratification |
| `src/models/` | SPLIT | SQLAlchemy models split per table — see §4.1 rule (mirror alembic split) |
| `src/observability/` | F | Cross-product instrumentation — fleet-tier (product gets its own observability surface in Phase 2.0+) |
| `src/orchestration/` | F | Fleet orchestration runtime (Prefect flows for fleet ops, not for BDR cohorts) |
| `src/outreach/` | A | Agency OS outreach stack (Salesforge/Unipile/ElevenAgents/Telnyx) |
| `src/pipeline/` | A | Agency OS Siege Waterfall pipeline (Flow A/B, T0-T5) |
| `src/prefect_utils/` | F | Prefect helpers used by fleet flows |
| `src/prompts/` | SPLIT | Mirrors `prompts/` split |
| `src/relay/` | F | Inter-agent relay (NATS+JSON inbox/outbox) |
| `src/replay/` | F | Event replay tooling for fleet incident postmortems |
| `src/retrieval/` | A | Agency OS retrieval (lead recall from pool) |
| `src/scraper/` | A | Agency OS web scraping (Bright Data, Camoufox) |
| `src/security/` | SPLIT | Some cross-product (HMAC envelope signing — comes back for Agency_OS-lfyb), some Agency OS-specific |
| `src/services/` | A | Agency OS service layer (campaign_service, lead_service, etc.) |
| `src/session_resumption/` + `src/session_store/` | F | Per-callsign session state — fleet substrate |
| `src/skill_gen/` | F | Skill generation tooling — fleet-tier |
| `src/slack_bot/` | F | Slack bot for Elliot — fleet-tier (Dave-facing endpoint) |
| `src/utils/` | SPLIT | Per-file classify — generic utilities likely cross-product, Agency OS-specific utilities → A |
| `src/voice/` | A | Agency OS voice outreach (ElevenAgents wrapper) |

### 4.9 `supabase/`

| Subpath | Classification |
|---|---|
| `supabase/migrations/*` | SPLIT — mirrors `alembic/` rule. Cross-product schema (ceo_memory, agent_memories, tasks) → F; Agency OS schema (lead_pool, business_universe, cohort_runs) → A; tenant schemas (when added Phase 2.0+) → P |
| `supabase/functions/` (edge functions) | SPLIT — per-function classify by what it serves |

### 4.10 `tests/`

PR #1118 enumerated the 27 product-tier paths (allowlist). Everything NOT in that allowlist defaults to FLEET unless it touches Agency OS-only code (e.g. `tests/scripts/test_cognee_*`, `tests/scripts/test_abn_match_sweep`, `tests/pipeline/*`) — those go ARCHIVE.

---

## 5. Cross-repo dependency map

### 5.1 Allowed cross-repo dependencies

**Product → Fleet:** None at build time. Per the canonical-key gate ("CI gate: product repo imports nothing from fleet or archive repos"), the product repo MUST be importable in isolation. Shared types (Pydantic schemas, enums) live in a fourth lib `keiracom-types/` (small, MIT-licensed, both fleet + product depend on it) — exact mechanism deferred to Phase 2.0 separation deliberation. **CI enforces:** `grep -r 'from agency_os\|from keiracom_fleet' keiracom-product/` returns 0.

**Fleet → Product:** None. Fleet operates independently of any product code. Fleet may CONSUME the product repo's MCP API (over the wire), but does not IMPORT product code.

**Either → Archive:** None. Archive is read-only reference; no live dependency.

**Either → Shared types (keiracom-types):** Yes, via standard package dependency. Lockfile drift surfaces in CI per consolidated gate "Cross-repo dependency sync: shared constraints file; CI fails on lockfile drift".

### 5.2 Shared infrastructure (NOT cross-repo dependency — both repos consume independently)

- **Supabase project (`jatzvazlbusedwsnqxzr`):** both fleet (ceo_memory, agent_memories, tasks) and product (tenant schemas added Phase 2.0+) read/write. MCP-bridge refuses wrong-project-id calls per consolidated gate.
- **NATS substrate:** fleet-only. Product agents communicate via MCP dispatcher, not NATS subjects.
- **Slack relay:** fleet-only. Product has no Dave-facing surface.
- **Redis Whiteboard:** fleet-only for inter-callsign coordination. Product equivalent is per-tenant via the MCP dispatcher.

### 5.3 Forbidden patterns (anti-cross-repo)

- Product PRs that add `from agency_os.<anything>` imports → CI blocks at the `grep` gate (above).
- Fleet code that hardcodes product-repo paths (e.g. `/keiracom-product/src/...`) → governance review HOLD.
- Shared mutable state in `/tmp/` across repos → forbidden; use a documented IPC mechanism (NATS for fleet, MCP for product).

---

## 6. Migration manifest schema (Phase 2.0 input)

The migration runner consumes a JSON manifest. Schema:

```json
{
  "source_repo": "agency-os (current monorepo)",
  "manifest_version": "1.0",
  "generated_at": "2026-05-24T...",
  "entries": [
    {
      "source_path": "src/dispatcher/",
      "target_repo": "product",
      "target_path": "src/dispatcher/",
      "operation": "move",
      "rationale": "V1.0 MCP dispatcher per PR #1118",
      "active_pr_block": null
    },
    {
      "source_path": "src/integrations/leadmagic.py",
      "target_repo": "archive",
      "target_path": "src/integrations/leadmagic.py",
      "operation": "move",
      "rationale": "Dead Agency OS vendor",
      "active_pr_block": null
    },
    {
      "source_path": "src/utils/text_normalisation.py",
      "target_repo": "fleet",
      "target_path": "src/utils/text_normalisation.py",
      "operation": "move",
      "rationale": "Cross-product utility",
      "active_pr_block": "PR #1130 (orion fix-up in progress)"
    }
  ]
}
```

**Dynamic exclusion rule (per consolidated gate):** any `source_path` with `active_pr_block != null` is held out of the migration cycle. The migration runner re-evaluates the manifest each cycle; entries become eligible once their blocking PR merges.

**Idempotency:** the runner records moved files in a state file. Re-runs of the same manifest produce no-ops for already-moved paths.

**Hash discipline:** every `source_path` move records `source_sha256` pre-move and `target_sha256` post-move. Mismatch fails the migration. Same shape as PR #1119 Weaviate cutover verify step.

---

## 7. Open follow-ups (out of scope for this artefact)

Filed for Phase 2.0:

- **`skills/` per-skill manifest** — full file-by-file classification of every skill subpath (this doc has the architectural rule + sketch table; the full manifest is its own bd issue).
- **`src/security/` per-file classify** — HMAC signing, secret rotation utilities mix cross-product and Agency OS-specific. Needs grep+classify pass.
- **Shared-types lib `keiracom-types/`** — separate KEI to author the small shared Pydantic + enum library before any product-migration PR lands.
- **Migration runner implementation** — consumes this doc + the JSON manifest. Per MAL V1 Gate F: P0 critical-path, ships before launch.
- **Phase 2.0 repo creation script** — `gh repo create` + initial commits + branch protection + bot account provisioning (when Agency_OS-57tp lands).
- **`/tmp/telegram-relay-<callsign>/` path stays fleet-only** — when product agents need IPC, they use a different mechanism (MCP dispatcher channels); document explicitly in the product CLAUDE.md when authored.

---

## 8. Acceptance criteria

- [x] Three canonical keys queried + pasted verbatim in §1.
- [x] Per-directory classification covers every top-level dir in the current monorepo (§3).
- [x] SPLIT directories have file-by-file or per-subpath rules (§4).
- [x] Cross-repo dependency map names: allowed paths (none from product to fleet/archive); shared infra (Supabase, NATS, Slack, Redis); forbidden patterns + CI enforcement (§5).
- [x] Migration manifest schema specified with example entries + dynamic-exclusion rule + idempotency + hash discipline (§6).
- [x] Open follow-ups named with sequencing (§7).
- [ ] Elliot impl-feasibility lens concur (per author-exclusion: Aiden authored).
- [ ] Max code-quality lens concur (per author-exclusion: Aiden authored).
- [ ] 2-of-2 author-excluded concur → Elliot admin-merge per orchestrator-merge-after-NATS-concur pattern.

---

_End execution plan. Phase 2.0 repo creation blocks on this artefact + the other 6 Phase 1.2.5 bundle items (5 merged + this PR + 1 in flight)._
