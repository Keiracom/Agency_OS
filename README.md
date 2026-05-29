# Agency OS

> Automated acquisition engine for Australian marketing agencies — discovers Australian SMBs via Google Maps, enriches contact data through a multi-tier waterfall, scores leads with a Competitive Intelligence Score (CIS), and executes personalised outreach campaigns.

**Status:** In development (pre-revenue, private beta cohort opening soon).

---

## Architecture at a glance

```mermaid
flowchart TD
    User([Operator / Dave]) -->|directives| Agents[Agent layer<br/>Claude Code + Pydantic AI]
    Agents -->|builds| Backend[FastAPI<br/>Railway]
    Frontend[Next.js<br/>Vercel] -->|HTTPS| Backend
    Backend -->|asyncpg| DB[(Supabase<br/>Postgres + Auth)]
    Backend -->|enqueue| Queue[(Redis<br/>Upstash)]
    Backend -->|trigger| Prefect[Prefect<br/>self-hosted]
    Prefect -->|run flows| Backend
    Backend -->|vendor calls| Vendors[Vendor pool<br/>DataForSEO · Salesforge · Unipile · ElevenAgents · Telnyx]
```

The platform sits between a Next.js operator UI and a vendor pool. FastAPI carries request handling and contract enforcement; Prefect orchestrates long-running enrichment flows; Supabase holds tenant data, lead records, and CIS state; Redis fans out async work. Full topology lives in [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Pipeline (Siege Waterfall)

```mermaid
flowchart LR
    A[Discovery<br/>DataForSEO + Bright Data] --> B[ABN match<br/>local DB JOIN]
    B --> C[Enrichment<br/>6-layer email waterfall<br/>4-layer mobile waterfall]
    C --> D[CIS scoring<br/>propensity + ALS]
    D --> E{Score gate}
    E -->|≥85| F[Outreach<br/>Salesforge · Unipile · ElevenAgents]
    E -->|<85| G[Hold / re-enrich]
```

Discovery surfaces Australian SMBs from Google Maps via DataForSEO and Bright Data. Each domain is matched against the ABN registry, then run through a tier-gated enrichment waterfall (cheaper tiers first, expensive tiers gated on propensity score). The Competitive Intelligence Score (CIS) decides whether a lead enters the outreach stack. Vendor selection lives in [ARCHITECTURE.md §SECTION 4](ARCHITECTURE.md); pipeline stages live under `src/pipeline/`.

---

## Agent layer

```mermaid
flowchart TD
    Dave([Dave<br/>CEO / Architect]) --> Claude[Claude<br/>CEO bot]
    Claude --> Elliot[Elliot<br/>COO]
    Elliot --> Aiden[Aiden<br/>CTO]
    Elliot --> Max[Max<br/>CTO]
    Aiden -.-> Orion[Orion<br/>engineer]
    Max -.-> Atlas[Atlas<br/>engineer]
    Aiden -.-> Scout[Scout<br/>engineer]
    Max -.-> Nova[Nova<br/>engineer]
```

Agents are Claude Code sessions running under fixed callsigns. Deliberation tier (Elliot, Aiden, Max) reviews and approves; engineer tier (Orion, Atlas, Scout, Nova) builds. Every directive flows through Step 0 RESTATE → Decompose → Execute → Verify → Report. Inter-agent comms run through a Slack relay; persistent state lives in Supabase `agent_memories`.

---

## Agent loop architecture (V1 chain)

The runtime execution loop — distinct from the callsign org chart above — moves a request through four roles. The roles never share in-process state: each runs as an ephemeral spawn that exits after its turn and hands off through **AtomV1 atoms** in Hindsight plus task rows in Postgres.

```mermaid
flowchart LR
    User([Dave / #ceo]) --> Chat
    Chat[Chat / Face<br/>Haiku listener] --> Delib[Deliberator<br/>the Floor]
    Delib -->|task rows| Worker[Worker<br/>ephemeral spawn]
    Worker --> Reviewer[Reviewer<br/>acceptance + concur]
    Reviewer -->|mark done| Delib
    Worker -.->|AtomV1 on exit| H[(Hindsight<br/>fleet_decisions)]
    H -.->|Layer 2 recall on spawn| Worker
```

**Chat (Face)** — the user-facing voice. A `claude-haiku-4-5` agent spawns per `#ceo` message via Slack Socket Mode, classifies with a full LLM pass, and either records a decision (writes an AtomV1 atom to Hindsight plus a `ceo_memory` audit row) or exits on noise. Rate-capped at 10 spawns/hour via Valkey. Face and the Floor are the same entity — Face is its voice, and it always returns one recommendation, never a pros-and-cons list. Trivial commands bypass the Floor entirely.

**Deliberator (the Floor)** — the multi-agent deliberation layer. It turns a request into a concurred plan (which Face presents for confirmation), forces a single recommendation on evaluative questions, resolves or escalates an agent's mid-task decisions, recalculates the task tree when a plan changes, and is the *only* authority that may mark a task done.

**Worker** — an ephemeral agent spawned to execute one unblocked task. The work-loop consumer watches Postgres: a `trg_tasks_unblock_dependents` trigger publishes `task_id + callsign + tenant_id` to the Valkey `keiracom:tasks:available` queue; the consumer checks the tenant's tier ceiling and, if under the concurrent-spawn limit, calls `POST /dispatcher/spawn` (overflow is requeued, never dropped; a Valkey lock prevents duplicate spawns). Each spawn is hydrated by a 4-layer context contract — L1 system prompt, L2 Hindsight recall (3–5 atoms), L3 Valkey spend gate, L4 dispatcher wiring — fail-open at every layer.

**Reviewer** — verification before work is accepted. The Floor checks a completed PR against its acceptance criteria, and runtime or governance PRs additionally require 2-of-3 deliberator concur (the orchestrator-merge-after-NATS-concur pattern) before an admin squash-merge.

**Hand-off via AtomV1** — roles do not pass state in process. When an agent finishes, its exit cycle (`src.keiracom_system.chat.exit_cycle.classify_and_save`) writes the decision **directly** to the Hindsight `fleet_decisions` bank as an AtomV1 atom — a Gemini classifier (confidence > 0.8, max 3 atoms) is the precision gate. The next spawn picks it up through Layer 2 Hindsight recall at spawn time. Postgres carries operational state and the task-unblock triggers; Hindsight carries all knowledge. There is no intermediate store, and nothing writes automatically — write discipline at exit is the gate. An AtomV1 atom carries `trigger_condition`, `content`, `anti_pattern`, `example`, `provenance`, `supersession_edges`, and `composition_tags`. Post-cutover, `ceo_memory` is an audit log and admin target — not a pipeline step.

---

## Quickstart

Targets a fresh clone building locally in under 30 minutes.

```bash
# 1. Clone
git clone https://github.com/Keiracom/Agency_OS.git
cd Agency_OS

# 2. Python backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Frontend
cd frontend && pnpm install && cd ..

# 4. Env
cp config/.env.example .env  # then fill in SUPABASE_DB_URL, ANTHROPIC_API_KEY, etc.
cp frontend/.env.example frontend/.env.local

# 5. Verify
pytest -x -q                         # backend tests
cd frontend && pnpm test && cd ..    # frontend tests
ruff check src/                      # lint

# 6. Run backend locally
uvicorn src.api.main:app --reload --port 8000

# 7. Run frontend locally
cd frontend && pnpm dev
```

Backend at <http://localhost:8000> (OpenAPI at `/docs` in non-prod). Frontend at <http://localhost:3000>.

---

## Stack

| Layer | Tech |
|-------|------|
| Backend API | FastAPI · Pydantic AI · asyncpg |
| Frontend | Next.js · React · Plasmic |
| Database | Supabase (Postgres + Auth + RLS) |
| Cache / queue | Redis (Upstash) |
| Orchestration | Prefect (self-hosted) |
| Compute | Railway (backend) · Vercel (frontend) |
| Observability | Sentry · Better Stack · structlog |
| Agent harness | Claude Code (Anthropic) |

Detailed vendor list, costs, and tier rules in [ARCHITECTURE.md §SECTION 4](ARCHITECTURE.md).

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Locked system architecture — vendors, pipeline, deprecations |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Local dev, PR process, KEI workflow |
| [CLAUDE.md](CLAUDE.md) | Instructions for Claude Code agents |
| [PROJECT_BLUEPRINT.md](PROJECT_BLUEPRINT.md) | Phase plan + import hierarchy |
| [docs/governance/CONSOLIDATED_RULES.md](docs/governance/CONSOLIDATED_RULES.md) | The 7 ratified governance rules |
| [docs/phases/](docs/phases/) | Per-phase specifications |
| [docs/runbooks/](docs/runbooks/) | Operational procedures |

---

## License

Proprietary. © Keiracom.
