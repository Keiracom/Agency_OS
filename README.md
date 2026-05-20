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
