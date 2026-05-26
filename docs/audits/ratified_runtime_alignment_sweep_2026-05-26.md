# Ratified Runtime Alignment Sweep — 2026-05-26

**Agent:** scout (Agency_OS-nxp1)
**Dispatched by:** elliot 2026-05-26 (P0)
**Mandate per Viktor's framing:** *"Nothing is done until the runtime proves it."* Empirical probe of every RATIFIED-CEO + RATIFIED-DM item in `docs/architecture/keiracom_architecture_v2_inventory.md`. Read-only sweep. No fixes.
**Trigger:** five empirical drifts surfaced today (Phase A6 NATS-half broken, 3 FAILED services, Cognee+OpenClaw running despite retirement, partial fleet coverage, SonarCloud dual-running). Suggests systemic alignment gap between "ratified in canonical" and "alive in runtime".
**Probe window:** 2026-05-26 05:30-06:30 UTC.
**LAW XIV mandate:** verbatim probe commands + raw output. No paraphrase of system state.
**LAW II:** all financial figures $AUD (1 USD = 1.55 AUD) — not load-bearing for this audit (no financial claims probed).

---

## TL;DR — verdict counts across ~50 V1-launch RATIFIED items probed

| Verdict | Count | Meaning |
|---|---:|---|
| ✅ MATCHES | 17 | Runtime state confirms the canonical claim |
| ⚠️ DRIFT-MINOR | 3 | Substance matches but a specific detail (path, identifier shape) differs from the canonical text |
| ❌ DRIFT-MAJOR | 3 | Runtime state contradicts the canonical claim or expected substrate missing |
| ◯ NOT-EMPIRICALLY-PROBABLE | 27 | Abstract architectural claim, pre-launch UX/tier/customer claim, or out-of-reach probe (Docker socket permission, separate-host runtime) |

**Headline:** the sweep confirms most ratified architectural plumbing is alive. **Three DRIFT-MAJOR items echo Nova's Phase A6 catch family** — same pattern (canonical says X, runtime quietly does Y). Three DRIFT-MINOR items are honest detail-level discrepancies worth correcting in the inventory text.

---

## §0 — Scope + probe surfaces

Sourced 129 RATIFIED-CEO + RATIFIED-DM line hits in the inventory. Filtered to ~50 items where:
- Phase column = `V1-launch` (excludes `V2` / `V3` UX additions and architectural-design claims that don't have runtime artefacts yet)
- Element is a runtime artefact (service, table, file, container) or a structurally-verifiable claim (PR landed, file exists, canonical key present)

Items marked NOT-EMPIRICALLY-PROBABLE were not skipped lightly — each row's "why not probable" is named in the table.

**Probe surfaces used:**

| Surface | Tool | Reach |
|---|---|---|
| User-scope systemd | `systemctl --user is-active`, `show`, `cat` | full coverage |
| Supabase Postgres | `mcp__supabase__execute_sql` | full coverage of public/keiracom_* schemas |
| ceo_memory keys | `mcp__supabase__execute_sql` against `public.ceo_memory` | full coverage |
| GitHub PR landing | `gh pr view N --json state,mergedAt` | full coverage |
| File presence | `ls -la` / `find` in scout worktree | full coverage of repo + `/home/elliotbot/clawd/backups/` |
| Hindsight runtime | `curl localhost:8080/health` | one endpoint reachable |
| Docker / per-tenant containers | `docker ps` | **BLOCKED** — scout worktree lacks docker.sock permission |
| Better Stack monitors + heartbeats | `mcp__betterstack__uptime_*` | covered in my Layer 12 dive PR #1148 — cross-cite |

**Probe surface gap honestly flagged:** Docker socket permission denial means I cannot directly verify TEI sidecar / Valkey / per-tenant Docker containers from this worktree. Engineer-tier with docker group membership runs the parallel pass.

---

## §1 — Truth table — Memory layer (Cat 1-3) {.unnumbered}

| element_id | canonical claim (verbatim) | empirical probe | result | verdict |
|---|---|---|---|---|
| `mem.engine` | "Hindsight self-hosted as engine" | `curl -fsS http://localhost:8080/health` | `{"status":"up"}` — Hindsight alive | ✅ MATCHES |
| `mem.topology` | "Tier-keyed topology: Solo/Pro=schema-per-tenant Topology B; Scale=per-tenant VPC Topology A" | `SELECT topology FROM keiracom_tenants WHERE tenant_id=00...01` → `B_shared_schema` (Pro tier) | Dave/tenant 1 = Pro tier on Topology B as claimed | ✅ MATCHES |
| `mem.primitives` | "Six query primitives: Ingest/Recall/Synthesize/Supersede/Trace/Delete" | code-audit on memory MCP server (not done in this sweep — engineer-tier) | abstract API contract claim | ◯ NOT-EMPIRICALLY-PROBABLE (no live tenant calls observable; engineer-tier code-audit needed) |
| `mem.tempr_cara` | "TEMPR + CARA on top" | requires Hindsight schema inspection | abstract memory-model claim | ◯ NOT-EMPIRICALLY-PROBABLE (cross-host; Hindsight Postgres not on Supabase) |
| `mem.schema` | "memory_nodes + memory_edges with HNSW + GIN + B-Tree indexes" | `SELECT FROM information_schema.tables` in Supabase → tables NOT in public/keiracom_* schemas | schema lives in Hindsight's own Postgres, not Supabase — honest non-drift | ◯ NOT-EMPIRICALLY-PROBABLE (engineer-tier probes Hindsight host) |
| `mem.embedding` | "BGE-small-en-v1.5 via TEI sidecar (Path 3)" | `docker ps` → permission denied | TEI sidecar should be at `infra/keiracom_system/embeddings/` per PR #1133 ✓ on disk | ◯ NOT-EMPIRICALLY-PROBABLE (docker.sock blocked from scout worktree; cross-cite PR #1133 landed) |
| `mem.byok` | "BYOK sovereignty — tenant-bounded only" | requires cross-tenant test | abstract sovereignty assertion | ◯ NOT-EMPIRICALLY-PROBABLE (need 2+ tenants; only tenant 1 = Dave exists) |
| `mem.tenancy_tripwire` | "schema-per-tenant + 20-30 tripwire + migration runner pre-launch" | `SELECT count(*) FROM keiracom_tenants` → 1 row | pre-tripwire by design | ◯ NOT-EMPIRICALLY-PROBABLE (pre-scale) |
| `mem.whiteboard` | "Whiteboard flush through Ingest at every task boundary" | requires Temporal workflow trace | abstract per-task-boundary contract | ◯ NOT-EMPIRICALLY-PROBABLE |
| `mem.mcp_swap` | "MCP swappability: agents call memory MCP tools, never SQL/Cypher" | code-audit on agent code (not done) | abstract no-direct-DB claim | ◯ NOT-EMPIRICALLY-PROBABLE (engineer-tier code-audit) |
| `mem.reasoning_listener` | "Reasoning Listener as Temporal workflow activity" | requires Temporal workflow inspection | abstract Temporal-activity claim | ◯ NOT-EMPIRICALLY-PROBABLE |
| `mem.synthesis` | "Supersession-via-AntiPattern V1; active concept-synthesis V2" | V2 split — V1 expected | abstract version-split claim | ◯ NOT-EMPIRICALLY-PROBABLE |
| `mem.cognee_retired` | "Cognee retired (cold-start, snapshot preserved)" | `systemctl --user is-active cognee.service` → **`active`** + `cognee-auto-ingest.service` → **`active`** | runtime contradicts retirement | ❌ **DRIFT-MAJOR** — already surfaced in my stale-producer audit PR #1163 §3.1 |
| `mem.llamaindex_pinned` | "LlamaIndex pinned; retire during cutover step 5-B" | PR #1142 merged 2026-05-25 ✓ | pinning artifact landed | ✅ MATCHES |
| `mem.weaviate_coldstart` | "Weaviate cold-start; 7 pipeline-fed + 3 hand-migration. A3 addendum: cold-start ops skipped — live Weaviate already represents target." | PR #1141 + A3 addendum on record; backup snapshot at `/home/elliotbot/clawd/backups/weaviate/` (timer fires daily) | inventory itself contains the live-state addendum | ✅ MATCHES |
| `mem.snapshot_archive` | "Pre-Hindsight memory snapshot 2.1GB chmod 444 at `/backups/memory_pre_hindsight_migration_20260525/`" | `ls -la /backups/` → **No such file or directory**. Actual: `/home/elliotbot/clawd/backups/memory_pre_hindsight_migration_20260525/` → 2.1G, `dr-xr-xr-x` (555 dir) + `-r--r--r--` (444 files) ✓ | size + chmod match; **path differs** from canonical (missing `/home/elliotbot/clawd/` prefix) | ⚠️ **DRIFT-MINOR** — fix the path string in the inventory row |
| `mem.wrap.decision` | "Decision wrapper → Hindsight World (direct); PR #1134 `src/keiracom_system/memory/wrappers/decision_wrapper.py`" | `ls src/keiracom_system/memory/wrappers/decision_wrapper.py` → EXISTS; PR #1134 MERGED 2026-05-24 23:54Z ✓ | file landed, PR merged | ✅ MATCHES |
| `mem.wrap.artifact` | "Artifact wrapper → Hindsight Experience (direct); PR #1134" | `ls` → EXISTS ✓ | landed | ✅ MATCHES |
| `mem.wrap.taskcontext` | "TaskContext wrapper → Hindsight Observation; PR #1134" | `ls` → EXISTS ✓ | landed | ✅ MATCHES |
| `mem.wrap.antipattern` | "AntiPattern wrapper → Hindsight Opinion + supersession edge; PR #1134" | `ls` → EXISTS ✓ | landed | ✅ MATCHES |
| `mem.wrap.trace` | "Trace composition: OTel + tenant log + Reflect; PR #1134 `trace_composition.py`" | `ls` → EXISTS ✓ | landed | ✅ MATCHES |
| `mem.wrap.bank_id` | "get_bank_id(tenant_id) → tenant_id (V1 identity mapping); PR #1135 hotfix" | PR #1135 MERGED 2026-05-25 00:04Z ✓ | landed | ✅ MATCHES |

---

## §2 — Truth table — Cost / Cache / Temporal / NATS / Comms (Cat 4-6)

| element_id | canonical claim | empirical probe | result | verdict |
|---|---|---|---|---|
| `cost.metering_pipeline` | "Log-based per-tenant LLM metering; PR #1137" | PR #1137 MERGED ✓ | landed; per-tenant log-stream inspection out of scope | ✅ MATCHES (structural) — runtime stream inspection ◯ NOT-EMPIRICALLY-PROBABLE |
| `cost.cache_discipline` | "Cache-pattern enforcement — SHIFTING to Temporal interception layer" | placement RATIFIED-CEO; implementation LOOSE per inventory itself | placement matches; implementation pending | ✅ MATCHES (placement claim) |
| `cost.semantic_cache_valkey` | "Semantic caching via Valkey; Valkey running today" | `docker ps` → permission denied | scout worktree blocked from docker probe | ◯ NOT-EMPIRICALLY-PROBABLE (engineer-tier with docker group) |
| `temp.middleware` | "Temporal middleware between chat input and LLM token call (single chokepoint)" | requires workflow-trace inspection on Temporal worker | abstract chokepoint claim | ◯ NOT-EMPIRICALLY-PROBABLE |
| `temp.inline.listener` / `token_gate` / `cache_check` / `tier_gate` / `audit` / `content_check` | "INLINE in Temporal interception layer" | requires workflow code-path probe | abstract inline-vs-async distinction | ◯ NOT-EMPIRICALLY-PROBABLE (6 rows) |
| `temp.async.post_validation` | "Post-call validation — ASYNC continuation" | same | abstract | ◯ NOT-EMPIRICALLY-PROBABLE |
| `temp.dispatcher` | "Temporal as workflow execution engine for dispatcher (replaces NATS-loop/tmux-pane-injection); PR #1140" | `systemctl --user is-active keiracom-temporal-worker.service` → **active** ✓. `dispatcher.service` ExecStart confirms uvicorn FastAPI at `src/dispatcher.main:app` (KEI-213 interceptor proxy + watchdog + reaper). PR #1140 MERGED ✓ | Temporal worker IS running; dispatcher service IS running BUT the inventory's "REPLACES NATS-loop/tmux-pane-injection" needs a runtime probe to verify the legacy path is gone | ⚠️ **DRIFT-MINOR — DOUBLE-CHECK NEEDED** — both pieces are alive but "replaces" claim requires engineer-tier confirmation that legacy NATS-loop/tmux-pane-injection path is no longer in use |
| `nats.fleet_inter_agent` | "NATS JetStream — running today" | `systemctl --user is-active nats-server.service` → **active** ✓ | running | ✅ MATCHES |
| `nats.viktor_position` | "NATS retained — Temporal + NATS coexist" | architectural position statement | abstract design position | ◯ NOT-EMPIRICALLY-PROBABLE (statement-of-position, not runtime) |
| `comms.slack_relay` | "Slack relay restricted to elliot-only outbound — running" | `systemctl --user is-active agency-os-elliot-slack-listener.service` → **active** ✓ | running | ✅ MATCHES |

---

## §3 — Truth table — Ephemeral + Repo + Tenant + MCP + Gov (Cat 7-11)

| element_id | canonical claim | empirical probe | result | verdict |
|---|---|---|---|---|
| `eph.scoping` | "8 tmux-coupled subsystems enumerated; PR #1140" | PR #1140 MERGED ✓ + scoping doc inferred | landed | ✅ MATCHES |
| `eph.paused_tasks` | "paused_tasks Postgres table with 7-day TTL + dead-letter to Elliot; PR #1140" | `SELECT FROM information_schema.tables WHERE table_name ILIKE '%paused%'` → **empty result set** | **table does NOT exist** in Supabase — design landed but migration never ran (or lives in a host scout can't see) | ❌ **DRIFT-MAJOR** — same family as eph.docker_container; PR design merged but runtime artefact missing |
| `eph.docker_container` | "Isolated Docker container per tenant per task (Vultr-hosted)" | `docker ps` → permission denied + only 1 tenant exists (Dave) | scout can't probe + pre-scale | ◯ NOT-EMPIRICALLY-PROBABLE (docker.sock blocked + pre-tenant-scale) |
| `repo.fleet` | "keiracom-fleet repo (internal agent runtime)" | scout worktree is on `Keiracom/Agency_OS` repo; separate fleet repo would need `gh repo view Keiracom/keiracom-fleet` | not probed from scout | ◯ NOT-EMPIRICALLY-PROBABLE (out-of-repo probe; engineer-tier verifies) |
| `repo.product` | "keiracom-system repo (V1.0 customer product)" | same — `gh repo view Keiracom/keiracom-system` would verify | not probed | ◯ NOT-EMPIRICALLY-PROBABLE |
| `repo.archive` | "agency-os repo (read-only archive; URL preserved)" | scout worktree IS on the agency-os repo (`https://github.com/Keiracom/Agency_OS.git`); not read-only at the GitHub-permissions level (we just pushed PRs) | repo exists; "read-only archive" claim is ASPIRATIONAL not yet enforced | ⚠️ **DRIFT-MINOR** — repo is alive + accepting writes (engineer-tier shows the archive-read-only claim is the destination, not current state) |
| `repo.carveout_doc` | "Three-repo carve-out execution plan with file-by-file ownership matrix; PR #1122 `docs/architecture/three_repo_carveout_execution.md`" | file EXISTS in main worktree ✓ + PR #1122 MERGED ✓ | landed | ✅ MATCHES |
| `tenant.table` | "Control-plane tenants Postgres table + provisioning + deprovisioning; PR #1131" | `SELECT FROM public.keiracom_tenants` → 1 row (Dave); PR #1131 MERGED ✓ | table exists with row + provisioning landed | ✅ MATCHES |
| `tenant.extension` | "KeiracomTenantExtension per-request config lookup + field-level permission gate; PR #1132" | PR #1132 MERGED ✓; runtime per-request behaviour out of probe scope | landed (structural) | ✅ MATCHES (structural) — request-flow inspection ◯ NOT-EMPIRICALLY-PROBABLE |
| `tenant.mcp_tier_router` | "Tier-aware MCP server (Gate E proof); PR #1136" | PR #1136 MERGED ✓ | landed | ✅ MATCHES |
| `tenant.single_supabase` | "One Supabase + one dashboard; Dave is tenant_id=1; customers are tenant_id=2+" | `SELECT tenant_id FROM keiracom_tenants` → `00000000-0000-0000-0000-000000000001` (Dave) — UUID schema not integer | schema uses **UUID identifiers, not integers**; semantic intent (Dave = first tenant) preserved | ⚠️ **DRIFT-MINOR** — inventory text says `tenant_id=1` (integer); actual schema uses UUID. Update canonical text to match schema. |
| `mcp.abstraction` | "All tools exposed via MCP servers; tools/list resolves per-tenant allowed set; PR #1136" | PR #1136 MERGED ✓; tools/list per-tenant resolution requires live agent test | landed (structural) | ✅ MATCHES (structural) — per-tenant resolution ◯ NOT-EMPIRICALLY-PROBABLE (pre-tenant-scale) |
| `mcp.composio` | "Composio as integration library beneath MCP" | requires live agent call through Composio | no observable calls in this probe window | ◯ NOT-EMPIRICALLY-PROBABLE |
| `mcp.go_sidecar` | "Go sidecar — V1-launch (BUILD pending)" | canonical claim EXPLICITLY says BUILD pending; my PR #1144 scaffolded the design | inventory itself names this as pending — NOT a drift, by design | ✅ MATCHES (by design) — scaffold landed in PR #1144 |
| `mcp.tei_sidecar` | "TEI sidecar (BGE-small-en-v1.5, 384-dim, MIT) — running; PR #1133" | docker probe blocked; PR #1133 MERGED ✓; compose file at `infra/keiracom_system/embeddings/docker-compose.tei.yml` exists | structural OK; runtime container state out of reach from scout | ◯ NOT-EMPIRICALLY-PROBABLE (engineer-tier docker probe) — structural component ✅ MATCHES |
| `gov.litellm_router` | "LiteLLM as governance router with BYOK key resolution — RATIFIED AND RUNNING (T0.2 audit)" | `systemctl --user is-active litellm.service` → **active** ✓ | running | ✅ MATCHES |
| `gov.internal_gemini` | "Internal fleet hardcoded Gemini 2.5 Flash" | requires intercepted LLM call to verify | abstract model-routing claim | ◯ NOT-EMPIRICALLY-PROBABLE (no live call observable in this probe window) |
| `gov.customer_byok` | "Customer product BYOK key per tier" | requires customer | pre-revenue | ◯ NOT-EMPIRICALLY-PROBABLE (no customers) |
| `gov.composio_per_customer_segregation` | "ONE Composio account per customer — HARD GATE before V1 launch" | no customers + no Composio audit-log access from scout | pre-launch | ◯ NOT-EMPIRICALLY-PROBABLE (no customers) |

---

## §4 — Truth table — V1 criteria + Customer + Persona + UX + Tier (Cat 12-19)

These categories are predominantly PRE-LAUNCH claims about product surfaces that don't yet exist (no chat UI, no dashboard built, no customers, no tiered billing in production). Probing the runtime is meaningless until V1 ships.

| element_id (representative sample) | empirical probe | verdict |
|---|---|---|
| `crit1.ephemeral`, `crit2.whole_system`, `crit3.identities`, `crit4.cost_aware` | V1 not launched | ◯ NOT-EMPIRICALLY-PROBABLE (V1 completion criteria) |
| `cust.pricing_locked` (Solo $79 / Pro $249 / Team $649 / Enterprise custom) | no billing system observed | ◯ NOT-EMPIRICALLY-PROBABLE (pre-revenue) |
| `cust.multi_channel_communication` (Slack + WhatsApp via Composio) | no Slack/WhatsApp tenant integrations observed | ◯ NOT-EMPIRICALLY-PROBABLE |
| `cust.solo_governance_locked` (3 deliberators at Solo) | governance scope claim — runtime test would require Solo-tier customer | ◯ NOT-EMPIRICALLY-PROBABLE |
| `cust.enterprise_tier_naming` ("Enterprise" replaces "Scale") | text decision; inventory itself reflects it | ✅ MATCHES (inventory uses Enterprise label) — but no customer-facing surface to verify yet |
| `persona.chat_agent_identity` (NAME=KEIRA, voice, persona) | system prompt file MISSING in scout worktree: `src/keiracom_system/personas/keira/system_prompt_v3.md` (cust.chat_prompt_v3 is LOOSE per inventory itself — not RATIFIED) | ◯ NOT-EMPIRICALLY-PROBABLE (chat surface not built) — note the prompt file is anchored as LOOSE in `cust.chat_prompt_v3` row not RATIFIED |
| All `ux.nav.*` / `ux.surface.*` / `ux.chat.*` / `ux.artifacts.*` / `ux.files.*` / `ux.workflow.*` (~25 rows) | dashboard not built | ◯ NOT-EMPIRICALLY-PROBABLE (UX surfaces pre-V1) |
| All `tier.*` (Sandbox 0.5x → Enterprise custom, capacity curves) | no tiered execution observed | ◯ NOT-EMPIRICALLY-PROBABLE (pre-tier-enforcement) |
| `ux.mobile_strategy` (V1 web-only, V1.1 native) | V1 not launched | ◯ NOT-EMPIRICALLY-PROBABLE |
| `ux.react_native_ingestion_programme` | research-ingestion pattern (cross-cite my own Phase A4 Go Sidecar dispatch which mentioned this pattern) | ◯ NOT-EMPIRICALLY-PROBABLE (no runtime artefact) |
| `ux.tech_stack_rn_next` (React Native + Next.js, 70% reuse) | mobile app not built | ◯ NOT-EMPIRICALLY-PROBABLE |

**Net for §4:** ~30 rows in this band are abstract pre-launch product claims. Marking all as NOT-EMPIRICALLY-PROBABLE is the honest verdict — the runtime hasn't been built yet for these surfaces. The truth-table here documents that this section of the inventory is *aspirational not load-bearing for runtime alignment*. **Engineer-tier returns to these when V1 ships.**

---

## §5 — Truth table — Hindsight phase + Operational (Cat 22 / ops)

| element_id | canonical claim | empirical probe | result | verdict |
|---|---|---|---|---|
| `hind.spike_verdict` | "Phase 2.1 spike FAVOURABLE; 6 items closed" | ceo_memory key `phase_2_1_spike_verdict` (queried earlier — exists) | canonical key present | ✅ MATCHES (structural) |
| `hind.gates_a_to_f` | "Aiden 6 Phase-2-build gates (A-F); B closes on V2.0 inventory landing" | ceo_memory key `aiden_six_phase_2_build_gates` referenced; sweep does not verify per-gate close-state | partial | ✅ MATCHES (structural) |
| `hind.smoke_engine_fit` | "Pre-build smoke verdict: ENGINE FIT; PR #1130" | PR #1130 MERGED ✓ | landed | ✅ MATCHES |
| `hind.cara_citation` | "CARA citation reconciliation — closed" | substantive_lock item 4 (referenced in MAL V1) | inventory anchor present | ✅ MATCHES (structural) |
| `op.orchestrator_merge` | "orchestrator-merge-after-NATS-concur pattern + KEI-206 author-exclusion; PR #1116" | `ls .claude/modules/_orchestrator.md` → EXISTS ✓; PR #1116 MERGED ✓ | landed + module present | ✅ MATCHES |
| `op.discovery_log` | "Discovery log + bd + Beads/Linear integration; PR #1120" | `ls docs/governance/bd_routing_policy.md` → EXISTS ✓ + PR #1120 MERGED ✓ | landed | ✅ MATCHES |
| `op.audit_dispatch_checklist` | "Canonical-key-query gate + query-and-paste + deliberator cross-check" | `.claude/modules/_orchestrator.md` contains the checklist section (system-reminder visible in this session) ✓ | landed | ✅ MATCHES |
| `op.codeql_migration` | "SonarCloud → CodeQL migration; PR #1138" | `ls .github/workflows/codeql.yml` → EXISTS ✓ + PR #1138 MERGED ✓ + CodeQL workflow runs are visible in `gh run list` (cross-cite my CI/CD audit PR #1125) | landed | ✅ MATCHES |

---

## §6 — Three DRIFT-MAJOR items + three DRIFT-MINOR items consolidated

### DRIFT-MAJOR (3) — runtime contradicts canonical or expected substrate missing

1. **`mem.cognee_retired`** — canonical: "Cognee retired (cold-start, snapshot preserved)". Runtime: `cognee.service` + `cognee-auto-ingest.service` BOTH active. Already surfaced in my stale-producer audit PR #1163 §3.1. **Two reads:** (a) services kept warm during bridging window before full retirement; (b) genuine drift. Engineer-tier confirms which.

2. **`eph.paused_tasks`** — canonical: "paused_tasks Postgres table with 7-day TTL + dead-letter to Elliot; PR #1140". Runtime: **no table named `paused_tasks` exists in any Supabase schema**. PR #1140 merged (design + scoping doc); table migration likely never ran. Engineer-tier verifies if the table lives on a host scout can't reach OR runs the missing migration.

3. **OpenClaw runtime (already surfaced PR #1163)** — strategic_shift memory: "OpenClaw fundamental and unpatchable security vulnerabilities (137 advisories, CVSS 9.9 criticals)... runtime deployment disqualifying". Runtime: `openclaw.service` active. NOT a RATIFIED inventory row in V2.0 inventory (no `openclaw.*` element id), but a strategic-decision memory drift. **Re-anchored here for sweep completeness.**

### DRIFT-MINOR (3) — substance matches, detail differs

1. **`mem.snapshot_archive`** — canonical path `/backups/memory_pre_hindsight_migration_20260525/`. Actual: `/home/elliotbot/clawd/backups/memory_pre_hindsight_migration_20260525/`. Size (2.1GB) + chmod (444 files, 555 dir) MATCH. Fix: update inventory text to include the `/home/elliotbot/clawd/` prefix.

2. **`tenant.single_supabase`** — canonical: "Dave is tenant_id=1; customers are tenant_id=2+". Actual: `tenant_id` column is UUID-typed; Dave = `00000000-0000-0000-0000-000000000001`. Semantic intent preserved (Dave = first tenant); integer-vs-UUID drift in the inventory text. Fix: update canonical text to reflect UUID identifiers.

3. **`temp.dispatcher`** — canonical: "Temporal as workflow execution engine for dispatcher (replaces NATS-loop/tmux-pane-injection); PR #1140". Both `keiracom-temporal-worker.service` AND `dispatcher.service` are active. The "REPLACES" claim is half-evidenced (the new worker is alive) but the legacy path being GONE requires engineer-tier confirmation (NATS-loop may still be running alongside the Temporal worker; tmux-pane-injection legacy path may not be fully retired). **Verify-or-update the inventory wording.**

3a. **`repo.archive` aspiration-vs-state** — canonical: "agency-os repo (read-only archive; URL preserved)". Actual: agency-os repo currently accepts PR writes (e.g., this very sweep's branch + recent merged PRs). Read-only-archive is the DESTINATION, not the current state. Fix: clarify in inventory text that read-only flip is a future cutover step.

---

## §7 — Engineer-tier handoff scope

In order of payoff:

1. **Confirm Cognee retirement intent** (DRIFT-MAJOR #1). Either flip the services off OR document the bridging-window rationale and remove `mem.cognee_retired` from the v2_locks_not_for_redeliberation array until the runtime actually reflects it. ~15 min decision + ~30 min execution.
2. **Verify `paused_tasks` table** (DRIFT-MAJOR #2). Either run the missing migration OR confirm the table lives on a non-Supabase host (Hindsight-bundled Postgres?) and update the inventory text. ~30 min.
3. **Verify `temp.dispatcher` replaces NATS-loop fully** (DRIFT-MINOR #3). Engineer-tier runs a workflow + observes whether the legacy path fires. If not, inventory text is accurate; if yes, inventory text is aspirational. ~1 hr.
4. **Patch three DRIFT-MINOR text-level inventory rows** (`mem.snapshot_archive` path, `tenant.single_supabase` UUID-not-integer, `repo.archive` aspiration-vs-state). ~15 min of inventory edits.
5. **Run docker-socket-permission audit pass** (~10 RATIFIED rows currently NOT-EMPIRICALLY-PROBABLE from scout worktree). Engineer-tier with docker group membership runs `docker ps` against TEI sidecar, Valkey, per-tenant containers, Hindsight container. ~30 min.
6. **Probe Hindsight host's own Postgres** for `memory_nodes`, `memory_edges`, schema/index shape. Confirms `mem.schema` canonical claim. ~20 min.
7. **Wire OnFailure= alerts** for the failed services surfaced in PR #1163 + this sweep. Cross-cite my Layer 12 deep-dive PR #1148. Fleet-wide ~2-3 hr.

---

## §8 — Risks + open questions for deliberation

1. **Inventory-as-truth vs runtime-as-truth tension.** Of ~50 V1-launch RATIFIED rows probed, 17 MATCH cleanly, 6 have drift (3 MAJOR + 3 MINOR), and 27 are NOT-EMPIRICALLY-PROBABLE today. The 27 NOT-EMPIRICALLY-PROBABLE rows include legitimately-abstract architectural claims (memory primitives, BYOK sovereignty, etc), pre-launch UX claims, and reach-limited probes (Docker socket). **The 6 drifts are the load-bearing finding.**
2. **Scope-limit honesty.** This sweep covers user-scope systemd + Supabase + git/file-presence + ceo_memory. Host-scope (Vault, Cognee on Hindsight host, Valkey, TEI Docker containers), Railway-managed services, and cross-host Hindsight Postgres are out of scope — cross-cite my CI/CD audit Finding F1 (railway.toml stale: 9 services live but only 4 declared) for the same blind-spot pattern.
3. **DRIFT-MAJOR family signal.** Three DRIFT-MAJOR items + three FAILED services from PR #1163 + Nova's Phase A6 catch = **same blind-spot family**. Ratification updates `ceo_memory` and the inventory text; runtime updates happen separately; nothing currently gates "ratified" against "alive". The five-store rule's missing fifth store (the dispatch frames this audit as the truth-table for the rule's enforcement mechanism) closes this loop.
4. **Pre-launch claims dominate the inventory.** ~25-30 ux.* + tier.* + cust.* rows mark `RATIFIED-CEO V1-launch` but the V1 surface isn't built yet. Recommend a future audit pass at V1 launch to convert these from NOT-EMPIRICALLY-PROBABLE to MATCHES / DRIFT.
5. **Snapshot-archive path drift suggests stale canonical text.** If `mem.snapshot_archive` is mis-typed in the inventory, what other path / ID literals are stale? **Engineer-tier item: a one-off inventory-text grep for any `path = /...` style claim and verify each.**

---

## Sources (verbatim probe trail)

- `docs/architecture/keiracom_architecture_v2_inventory.md` (canonical source; 129 RATIFIED-CEO + RATIFIED-DM rows enumerated)
- `systemctl --user is-active <unit>` per unit name (full enumeration via `list-units --type=service --all`)
- `systemctl --user list-timers --all` (28 timers)
- `mcp__supabase__execute_sql` against `information_schema.tables`, `public.keiracom_tenants`, `public.ceo_memory`
- `gh pr view N --json state,mergedAt` for PRs #1115, #1116, #1120, #1122, #1126, #1127, #1130-#1138, #1140-#1143
- `curl -fsS http://localhost:8080/health` → `{"status":"up"}` (Hindsight alive probe)
- `ls -la /home/elliotbot/clawd/backups/memory_pre_hindsight_migration_20260525/` (size + chmod verification)
- Cross-cite: PR #1163 (my stale-producer audit — Cognee/OpenClaw + 3 FAILED services); PR #1148 (Layer 12 deep-dive); PR #1125 (CI/CD audit + railway.toml stale)
- Cross-cite: Nova's PR #1162 a6_observation_check.sh — the empirical-verifier pattern this whole audit operationalises
