# Contributing to Agency OS

Agency OS is a small, fast-moving codebase with a strict governance layer. This guide gets a contributor from "fresh clone" to "merged PR" without surprises.

---

## Before you start

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) — vendor decisions are locked; building against a deprecated vendor is a hard block.
2. Read [docs/governance/CONSOLIDATED_RULES.md](docs/governance/CONSOLIDATED_RULES.md) — the 7 rules every contribution honours.
3. Read [CLAUDE.md](CLAUDE.md) — agent instructions, including LAW XVII callsign discipline if you are operating under a callsign.

If anything in those documents contradicts something here, those win.

---

## Local development

### Backend (Python 3.12+)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/.env.example .env  # fill in: SUPABASE_DB_URL (or DATABASE_URL), ANTHROPIC_API_KEY, OPENAI_API_KEY, SLACK_BOT_TOKEN, CALLSIGN
pytest -x -q                                # full backend test
ruff check src/ && ruff format --check src/  # lint + format
mypy src/ --ignore-missing-imports          # type check
uvicorn src.api.main:app --reload --port 8000
```

CI runs `ruff check src/` AND `ruff format --check src/` AND `mypy src/` AND `pytest`. Run all four locally before pushing — `ruff check` passing alone is not enough (see `feedback_ruff_format_check_required`).

### Frontend (Node 20+, pnpm)

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test
pnpm dev   # local server at http://localhost:3000
```

### Database

We do not run Postgres locally. Connect to the dev Supabase project via `SUPABASE_DB_URL`. Migrations live under `supabase/migrations/` and apply via `supabase db push` (Supabase CLI) or the Supabase dashboard SQL editor.

---

## KEI workflow

Every code change traces to a KEI (Keiracom Engineering Initiative) issue tracked in Linear and mirrored to Beads (`bd`).

```bash
bd ready                       # find unblocked work
bd show <id>                   # see full spec, acceptance criteria, deps
bd update <id> --claim         # claim it (alias: bd-original update <id> --claim --assignee=<callsign>)
# ... build ...
bd close <id>                  # close on PR merge
```

Rules:

- Never start coding without a claimed KEI. "KEI before build" — see `feedback_kei_before_build`.
- Before claiming, run `gh pr list --search "<KEI>" --state=open` to make sure a peer is not already in flight (see `feedback_check_open_prs_before_bd_claim`).
- Do not edit issues with `bd edit` — it opens `$EDITOR` and blocks agent sessions. Use `bd update --notes/--design/--description` instead.

---

## Branching + commits

| Pattern | Example |
|---------|---------|
| Branch name | `<callsign>/kei<NUM>-<slug>` — e.g. `orion/kei130-readme-contributing` |
| Commit prefix | `[<CALLSIGN>] <type>(<kei>): <subject>` — e.g. `[ORION] feat(kei130): README + CONTRIBUTING` |
| Types | `feat`, `fix`, `docs`, `refactor`, `test`, `chore` |

Branch off `origin/main` directly to avoid inheriting another agent's unmerged work (see `feedback_check_branch_before_checkout`):

```bash
git checkout -b orion/kei<N>-<slug> origin/main
```

---

## Pull requests

1. Push the branch.
2. Open the PR via `gh pr create --title "[CALLSIGN] type(kei): subject" --body "..."`.
3. PR body must include: **Summary**, **What lands**, **Test plan** (checklist of verification steps you ran).
4. Tag the relevant Linear KEI in the description: `Linear: KEI-NNN / bd: KEI-NNN`.

### Review + merge

The repo uses **dual concur** governance — any 2 of 3 deliberators (Elliot, Aiden, Max) must approve before merge. Review signals land in Slack `#execution` as `[REVIEW:approve:<callsign>]` or `[REVIEW:hold:<callsign>]`, not as GitHub native reviews.

- Wait for CI to be green before requesting review (`feedback_wait_for_ci_before_review`).
- Run SonarCloud verify before declaring done: BOTH `/api/issues/search?pullRequest=<N>&resolved=false` and `/api/qualitygates/project_status?pullRequest=<N>` must return `total=0` and `status=OK` respectively (`feedback_sonar_qg_not_just_issues`).
- Non-blockers are blockers — fix all review findings in the same PR, not a follow-up (`feedback_non_blockers_are_blockers`).
- Post `[REQUEST-FINAL:<callsign>]` to `#execution` when ready for the second concur.

---

## Testing

- Backend: `pytest -x -q`. Integration tests hit the real dev DB; do not mock the DB (see `feedback` on mocked-vs-prod divergence).
- Frontend: `pnpm test` (Vitest) + `pnpm playwright test` for E2E.
- Lint: `ruff check src/` + `ruff format --check src/` + `mypy src/`.
- Tests live under `tests/<module>/test_<thing>.py`. Match the source tree.

For external-service integrations (Supabase Realtime, MCP, websockets, vendor APIs), run the actual binary against the actual service before merging — mocks lie about library async shape and publication membership (`feedback_empirical_test_catches_paper_concur_misses`).

---

## Governance highlights

| Law / Rule | Short form |
|-----------|------------|
| LAW I-A | Architecture First — `cat ARCHITECTURE.md` before any architectural decision |
| LAW II | Australia First — all financial outputs in $AUD (1 USD = 1.55 AUD) |
| LAW V | 50-Line Protection — tasks needing >50 lines must spawn a sub-agent |
| LAW VI | Skills-First — use `skills/` → MCP → exec hierarchy |
| LAW VIII | GitHub Visibility — all work pushed before reporting complete |
| LAW XIV | Raw Output Mandate — paste verbatim terminal output, never summarise |
| LAW XV | Four-Store Completion — docs/MANUAL.md + ceo_memory + cis_directive_metrics + Drive mirror |
| LAW XV-D | Step 0 RESTATE — mandatory restate before any directive execution |

Full text in [docs/governance/CONSOLIDATED_RULES.md](docs/governance/CONSOLIDATED_RULES.md).

---

## Reporting bugs + asking questions

- File a bug as a `bd create --type=bug --priority=N` issue (P0 critical, P2 default, P4 backlog).
- Tag a deliberator on Slack `#execution` for triage routing.
- Do not open GitHub issues — Linear + Beads is the canonical tracker.

---

## License

Proprietary. © Keiracom.
