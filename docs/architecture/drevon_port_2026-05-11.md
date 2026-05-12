# Drevon Port — Architecture Retrospective

**Compiled:** 2026-05-12 (post-PR-A.5 listener-integration cutover staging)
**Author:** ORION
**Scope:** Internal Claude Code tooling stack. NOT Agency OS pipeline (Stage 7/10/keyword_expander/anthropic_batch remain on the API).

## Why "Drevon"

Audit + replay + auto-skill-gen + session resumption stack — read sessions, replay claims, generate skills, resume context. Internal to Claude Code agent operations; OAuth-only ($0 incremental under Max plan).

## Four Stages

| # | Stage | PRs | Status |
|---|-------|-----|--------|
| 1 | Schema foundation | [#715](https://github.com/Keiracom/Agency_OS/pull/715), [#718](https://github.com/Keiracom/Agency_OS/pull/718) | MERGED |
| 2 | Replay-on-claim | [#719](https://github.com/Keiracom/Agency_OS/pull/719), [#724](https://github.com/Keiracom/Agency_OS/pull/724) | MERGED |
| 3 | Auto skill-gen | [#720](https://github.com/Keiracom/Agency_OS/pull/720), [#728](https://github.com/Keiracom/Agency_OS/pull/728) | MERGED |
| 4 | UUID resumption | [#725](https://github.com/Keiracom/Agency_OS/pull/725) | MERGED |

## Stage 1 — Schema Foundation (PR-A)

5-table audit/replay store. Every Claude Code action is recorded best-effort.

```
sessions ──┬─< messages       (user/assistant per session)
           └─< turns ──┬─< turn_logs ──< turn_files
                       │                  (tool I/O files)
                       │
                       └ atomic assistant turn (one user msg → tool calls → response)
```

All tables: `id UUID PK`, `started_at TIMESTAMPTZ`, soft-delete via `deleted_at TIMESTAMPTZ`, RLS-gated to platform admins. Partial indexes filter `deleted_at IS NULL`.

**Recording side** ([`src/session_store/recorder.py`](../../src/session_store/recorder.py)): `record_session_start`, `record_message`, `record_turn_start`, `record_tool_call`, `record_turn_complete`, `record_session_end`, `mark_session_stuck`. All wrap `_safe_post`/`_safe_patch` — log+swallow on failure (never block the agent).

**Hook wiring** (PR #718 → [`.claude/settings.json`](../../.claude/settings.json)):

| Hook event | Script | Purpose |
|---|---|---|
| PostToolUse (matcher `*`) | `.claude/hooks/session_store_posttooluse.sh` | Append `turn_logs` row per tool call |
| Stop (matcher `*`) | `.claude/hooks/session_store_stop.sh` | Close `sessions` row + flush trailing `turns` |

No retroactive backfill — new sessions only.

## Stage 2 — Replay-on-Claim (PR-A.5)

Three-layer R3 (completion-claim) defense. Replay is the structural after-the-fact audit:

1. **Discipline** (PR #717 module) — agents are reminded to verify before claiming.
2. **Gate** (PR #703 verify_gate) — pre-LLM regex blocks obvious unverified claims.
3. **Replay** (PR #719 — this stage) — post-LLM scan of `turn_logs` for verification evidence; suppresses LLM-flagged R3 violations when evidence exists.

**Public entry** ([`src/replay/claim_verifier.py`](../../src/replay/claim_verifier.py)):

```python
def verify_completion_claim(text: str, callsign: str | None = None) -> tuple[bool, str]:
    """Return (verified, reason). Conservative: True when uncertain."""
```

Extraction: PR# regex (`\bPRs?\s*#?\s*(\d+)\b` + `pull request N` + orphan `#N`) and 7–40 char hex commit hashes. Evidence patterns scanned in `turn_logs.tool_args_json`:

- PR evidence: `verify_pr.sh`, `gh pr view`, `gh pr merge`, `gh pr checks`, `gh api repos`
- Commit evidence: `git cat-file`, `git log`, `git show`

Per-pattern query is `ilike.*pattern*` on `tool_args_json->>command` (scoped to `tool_name=Bash`), `limit=20`, ordered `started_at desc`. The PR# / hash must appear as a substring in the matched row's args.

**Listener integration** (PR #724, OPEN): wires `verify_completion_claim` into the Slack central listener behind env flag `REPLAY_ON_CLAIM_ENABLED` so cutover is reversible.

## Stage 3 — Auto Skill-Gen (PR-B)

Reads a directive-bounded slice of `turn_logs`, compresses to a prompt, invokes `claude --print --session-id <uuid>` via subprocess to synthesise a `SKILL.md`, writes to `skills/<derived-name>/SKILL.md`, opens a PR for human review.

**Critical pattern — env-marker recursion guard** (PR #728): the spawned `claude` process gets `CLAUDE_CODE_SKILL_GEN=1` in its environment. The session_store hooks (`.claude/hooks/session_store_posttooluse.sh`, `session_store_stop.sh`) check this variable at script entry and `exit 0` on match — preventing nested `turn_logs` writes / infinite loops. The earlier `--no-hooks` flag was a phantom (doesn't exist in Claude CLI v2.1.139); `--bare` exists but forces API-key auth (incompatible with OAuth). (Atlas chose Option B — per-call subprocess — over Option A long-lived worker; one-shot nature, simpler tests, fits the clone lifecycle.)

OAuth-only — $0 incremental under Max plan. No API key required. NO Agency OS pipeline code touched.

## Stage 4 — UUID Resumption (PR-C)

Long-lived terminals preserve accumulated context across watchdog-restarts and `/clear` cycles by resuming on the prior `session_uuid`.

**Public entry** ([`src/session_resumption/`](../../src/session_resumption/)):

```python
resolve_session_uuid(callsign, fresh_minutes=30) -> str | None
claim_session_uuid(callsign, uuid, cwd, **opts) -> UUID | None     # delegates to recorder
clear_stuck_sessions(callsign=None, stuck_minutes=60) -> int        # delegates to mark_session_stuck
```

Resolver query: `status=active AND ended_at IS NULL AND session_uuid IS NOT NULL AND deleted_at IS NULL AND started_at >= now() - INTERVAL fresh_minutes`, ordered `started_at desc`, limit 1. Watchdog: complementary sweep marks `ended_at IS NULL AND started_at < now() - INTERVAL stuck_minutes` as `status='stuck'` so stale rows fall out of the resolver.

**Launcher** ([`scripts/agent_session_launcher.sh`](../../scripts/agent_session_launcher.sh)): bash wrapper. Calls resolver → picks `--resume` vs `--session-id` → `exec claude`. Best-effort: any DB failure falls through to a fresh UUID rather than blocking startup. `SESSION_LAUNCHER_DRY=1` skips ALL Supabase I/O for safe CLI testing.

## Env-Flag Gates

| Var | Default | Effect |
|---|---|---|
| `REPLAY_ON_CLAIM_ENABLED` (PR #724) | unset = off | Wires `verify_completion_claim` into listener post-LLM check |
| `SESSION_LAUNCHER_DRY` (PR #725) | unset = live | Launcher skips resolve+claim, emits fresh UUID, prints would-exec |
| `SESSION_FRESH_MINUTES` (PR #725) | 30 | Override resolver freshness window |
| `SESSION_STUCK_MINUTES` (PR #725) | 60 | Override watchdog stale threshold |
| `SESSION_WATCHDOG_SCOPE` (PR #725) | unset = all | Scope watchdog to a single callsign |

## End-to-End Data Flow

```
agent terminal startup
    └─→ scripts/agent_session_launcher.sh <callsign>          ── PR-C
            │
            ├─ resolve_session_uuid(callsign)                  ── PR-C
            │     └─ sb_get sessions WHERE callsign=X AND fresh
            │
            ├─ claim_session_uuid(callsign, uuid, cwd)         ── PR-C → recorder.record_session_start (PR-A)
            │
            └─ exec claude --resume <uuid> | --session-id <uuid>
                    │
                    ├─ PostToolUse hook ── session_store_posttooluse.sh ── recorder.record_tool_call (PR-A)
                    │                                                           │
                    │                                                           └─→ turn_logs row appended
                    │
                    ├─ assistant claims "PR #N merged" in #execution
                    │     └─ central_listener (if REPLAY_ON_CLAIM_ENABLED)
                    │           └─ verify_completion_claim(text)               ── PR-A.5
                    │                 └─ sb_get turn_logs WHERE tool_args ILIKE '%verify_pr.sh%' AND contains '#N'
                    │
                    └─ Stop hook ── session_store_stop.sh ── recorder.record_session_end (PR-A)

watchdog (cron / systemd timer / agent loop)
    └─→ .claude/hooks/session_resumption_watchdog.sh           ── PR-C
            └─ clear_stuck_sessions(stuck_minutes=60)
                  └─ mark_session_stuck per stale row          ── PR-A

skill-gen (manual invocation)
    └─→ python -m skill_gen <directive>                        ── PR-B
            ├─ sb_get turn_logs WHERE session_id IN (directive bounds)
            └─ subprocess: claude --no-hooks --print "..."     (recursion guard mandatory)
                  └─ writes skills/<name>/SKILL.md
                  └─ opens PR for human review
```

## Non-goals & open items

- **No retroactive backfill**: all four stages assume new sessions only. Older Claude Code activity is invisible.
- **PR #724 cutover**: replay-on-claim is shipped but not yet behind the listener flag in main. Concur pending.
- **PR #725 cutover**: launcher is shipped but not yet wired into tmux startup. Concur pending; phased rollout per callsign expected.
- **Watchdog cadence**: hook is operator-installed, not auto-wired into `settings.json`. Cron / systemd timer / agent loop — operator's call.
- **Test isolation**: integration tests against real Supabase MUST use disposable callsigns + soft-delete cleanup (see `tests/integration/test_drevon_port_smoke.py`). Direct writes against real callsigns pollute the resolver until `mark_session_stuck` runs.

## Discovered issues (logged from this retrospective's integration test)

- **claim_verifier ilike-on-JSONB returns 404** ([`src/replay/claim_verifier.py`](../../src/replay/claim_verifier.py) `_query_turn_logs_for_pattern`): PostgREST cannot apply `ilike.*pattern*` directly to the JSONB column `turn_logs.tool_args_json` — server returns `42883 No operator matches`, function catches the exception, and every claim resolves to `(False, "no evidence")`. **Effect:** replay-on-claim currently never *finds* evidence; it only ever *fails to find*. Combined with the conservative-true semantics, this means R3 violations are correctly suppressed when claims have no PR/hash refs, but never suppressed when claims do have refs (over-firing). Fix path: extract a `command` field via `tool_args_json->>command` or add a generated text column for ilike. Tracked in PR body of `[ORION] feat(docs): drevon port retrospective`. Out-of-scope for this PR; flagged for Aiden + the PR-A.5 maintainer.
