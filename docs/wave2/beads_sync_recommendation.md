# Beads Cross-Worktree Sync — Recommendation (2026-05-12)

**Author:** atlas
**Companion to:** `docs/wave2/beads_cross_worktree_sync_state.md`
**Beads tracking issue:** `Agency_OS-iji`

## TL;DR

Two distinct problems are tangled in the current setup:

- **P1 (setup bug, fixable in minutes):** Max + Orion are git-worktrees of `/home/elliotbot/clawd/.git`, not Agency_OS. They cannot run `bd` at all because `.beads/` traversal exits their git tree.
- **P2 (architecture, multi-day):** Even after P1 is fixed, all worktrees share Elliot's single embedded Dolt DB via shared FS — no audit isolation, no off-host visibility, no concurrent-write safety guarantees.

Recommended path is **staged**:

| Phase | Scope | Solves | Cost |
|---|---|---|---|
| **0** | Re-add Max + Orion as proper Agency_OS worktrees (P1 fix) | bd is runnable from every worktree | minutes |
| **1** | Adopt upstream's git-`refs/dolt/data` sync — `bd dolt remote add origin git+ref://…` | Off-host visibility, true per-worktree DB, audit trail in Dolt history | ~1-2 PRs |
| **2** | Decide between (a) keep refs-based git-sync as canonical, or (b) stand up a local `bd dolt start` daemon on the Vultr host that all worktrees point at | Concurrency safety / single source of truth | scope after Phase 1 ships |

Dave-callable decisions:
- **D1 (Phase 0 unblock):** OK to re-create Max + Orion worktrees? Branches `max/*` + `orion/*` need to be preserved — confirm the local-only commits we're cataloging before re-add.
- **D2 (Phase 1 commit):** Adopt git-`refs/dolt/data` model (matches upstream, multi-host-ready), or defer until first non-Vultr worker exists?
- **D3 (Phase 2 deferred):** Skip Phase 2 entirely if Phase 1 is sufficient — only revisit when concurrent-write contention becomes empirical.

## Options surveyed

Six candidate architectures were considered. Comparison matrix below.

| # | Option | Solves P1? | Solves P2? | LOC / Ops cost | Multi-host? | Concurrent-write safe? | Reversible? |
|---|---|---|---|---|---|---|---|
| **A** | Re-init Max + Orion as proper Agency_OS git-worktrees | ✓ | partial (still shared FS) | trivial | no (still single host) | no | yes |
| **B** | `BEADS_DIR=/home/elliotbot/clawd/Agency_OS/.beads` env in each agent's shell init | ✓ | no (still single DB) | trivial | no | no | yes |
| **C** | Move `.beads/` to `/home/elliotbot/clawd/.beads` (parent dir shared by all worktrees) | ✓ | no | small | no | no | maybe (non-standard layout) |
| **D** | **Upstream `refs/dolt/data` git-sync** — `bd dolt remote add origin git+ref://github.com/Keiracom/Agency_OS.git` + per-worktree `bd init` + `push`/`pull` cadence | requires A first | **yes** | small-medium | **yes** | yes (Dolt MVCC) | yes |
| **E** | Self-hosted Dolt SQL server daemon (`bd dolt start` on Vultr host); all worktrees set `bd dolt set host 127.0.0.1 port <N>` | requires A first | **yes** | medium | partial (host-bound) | yes | yes |
| **F** | No-DB mode (`no-db: true` in `config.yaml`); JSONL becomes source of truth; commit JSONL on each change | ✓ | partial (loses Dolt entirely) | small | yes (git is the sync) | no (git merge conflicts) | yes |

(A) and (B) are *not* mutually exclusive with (D)/(E) — they're prerequisites or workarounds.

### Why A first (always)

The Max/Orion worktree-misalignment is a **setup defect**, not a design choice. Until it's fixed, every higher-layer option still has these two worktrees as a special case requiring `BEADS_DIR` overrides or `cd` workarounds. Fixing it costs minutes; postponing it makes every subsequent choice more complex.

### Why D over E for Phase 1

- **Multi-host readiness**: D works the moment we add a second machine (a remote checkout pulls Dolt commits via `git fetch`). E pins to one host's port.
- **Audit + revertability**: Every Dolt commit is also a git ref — `git log refs/dolt/data` gives full history and `git revert` semantics on bd state changes. E requires a separate Dolt-side rollback flow.
- **Backup as a side effect**: A git push covers off-host backup automatically. E needs its own backup plan.
- **No daemon to babysit**: D is stateless from the bd-process perspective. E needs a systemd unit for the Dolt server, restart-on-crash, port management.
- **Upstream-canonical**: `Agency_OS-iji` description explicitly cites "per upstream's `refs/dolt/data` git-sync model" as the target. We don't fork from upstream guidance without a reason.

E becomes attractive **only if** concurrent-write contention shows up empirically in Phase 1 (multiple agents push-pushing to the same Dolt branch fast enough that conflicts overwhelm Dolt's merge logic). Default assumption: 6 agents writing at human-paced cadence won't hit this.

### Why not F (no-db / JSONL-only)

JSONL is line-append friendly, but Beads issues mutate (state transitions, comments, dependency edges, label changes). Concurrent multi-agent edits to the same `issues.jsonl` produce git merge conflicts on a normal file basis — Dolt's row-level merge is the whole reason it exists. We'd lose:
- Concurrent-write safety
- Query power (`bd ready`, `bd graph`)
- Audit trail (no per-event history; only end state)
- Dependency-edge integrity

F is a fallback if upstream Beads becomes unmaintained, not a forward path.

## Recommended Phase 0 (Dave D1 to authorise)

**Step-by-step**:

1. Catalog in-flight work in `Agency_OS-max` and `Agency_OS-orion`:
   ```bash
   for wt in /home/elliotbot/clawd/Agency_OS-{max,orion}; do
     cd "$wt"
     git status --short                       # uncommitted changes
     git log --oneline @{u}..HEAD             # unpushed commits
     git for-each-ref refs/heads/             # local branches
   done
   ```
2. Push any unpushed commits / stash any uncommitted changes to a safe branch.
3. Remove the worktree records from `/home/elliotbot/clawd/.git`:
   ```bash
   cd /home/elliotbot/clawd
   git worktree remove Agency_OS-max
   git worktree remove Agency_OS-orion
   ```
4. Re-add as proper Agency_OS worktrees:
   ```bash
   cd /home/elliotbot/clawd/Agency_OS
   git worktree add ../Agency_OS-max -b max/restored-2026-05-12
   git worktree add ../Agency_OS-orion -b orion/restored-2026-05-12
   ```
5. Verify: `cd ../Agency_OS-max && bd where` should now resolve to `/home/elliotbot/clawd/Agency_OS/.beads/embeddeddolt`.
6. Verify: identical check from `Agency_OS-orion`.

Cost: ~10 minutes incl. branch-state preservation. Risk: any local-only branches need to be force-pushed somewhere before remove. **No code changes required.**

## Recommended Phase 1 (Dave D2 to authorise)

After Phase 0 is green:

1. Add the Dolt git-refs remote on Elliot's worktree:
   ```bash
   cd /home/elliotbot/clawd/Agency_OS
   bd dolt remote add origin https://ghp_…@github.com/Keiracom/Agency_OS.git
   bd dolt push origin main
   ```
   First push creates `refs/dolt/data` on GitHub.
2. Per-worktree `bd init` (each clone gets its own Dolt DB):
   ```bash
   for wt in /home/elliotbot/clawd/Agency_OS-{aiden,max,atlas,orion,scout}; do
     cd "$wt"
     bd init  # creates local .beads/embeddeddolt/
     bd dolt remote add origin <same URL>
     bd dolt pull origin main
   done
   ```
3. Adopt a sync cadence:
   - **Pre-write hook**: `bd dolt pull` before any `bd create`/`bd update`/`bd close`
   - **Post-write hook**: `bd dolt push` after the same
   - Conflicts: Dolt's row-level merge handles non-overlapping edits; semantic conflicts surface as `bd dolt status` dirty state — agent must resolve via `bd dolt commit` before re-push.
   - Wire as a git pre-commit hook AND/OR a bd-native hook in `.beads/hooks/`.
4. Add a CI check: `bd dolt verify` on PR — ensures `.beads/issues.jsonl` matches the Dolt source of truth (catches manual JSONL edits, drift, etc.).
5. Update `~/.claude/CLAUDE.md` global session-start to include `bd dolt pull` before any `bd ready` call.

Cost: ~1 PR for the per-worktree init + sync-hook script; ~1 PR for the CI verification + CLAUDE.md update. **Doc-and-config-heavy, low risk.**

## Phase 2 (deferred — only if Phase 1 contention shows up)

Indicators that would trigger Phase 2:
- `bd dolt push` rejected by remote ≥1×/day due to non-fast-forward conflicts that aren't trivially auto-mergeable.
- Two agents observed completing the same `bd close` racily and producing divergent Dolt branches.
- Latency on `bd ready` (which requires a pull first) becomes a real coordination tax (>10s per call).

Phase 2 options at that point:
- (E) Switch to a `bd dolt start` daemon on Vultr — all worktrees point at `127.0.0.1:<port>`.
- Adopt a fan-in pattern: only Elliot (orchestrator) writes; other worktrees use a thin proxy that posts intents to Elliot's queue.
- Hosted DoltHub if multi-region becomes a real requirement.

## Open questions / explicit non-decisions

- **Actor attribution** (`BEADS_ACTOR=<callsign>` per worktree) is a separate bug worth fixing in the same Phase 0 sweep but is not strictly required to make `bd` runnable.
- **Permissions** on max/orion `.beads/` are `0775` (vs recommended `0700`). The Phase 0 re-add fixes this incidentally since `bd init` creates fresh dirs.
- **`/home/elliotbot/clawd/.git` purpose** — Phase 0 doesn't change what that repo is; the max/orion worktrees are simply removed *from* it. If that parent repo has Agency_OS files staged, those would need to be staged elsewhere.
- **No claim** in this doc that Phase 1 is required *now*. Default position: Phase 0 alone is enough to unblock `Agency_OS-iji`; Phase 1 is the right next step but its urgency is gated on D2.

## Recommendation summary

1. **Do Phase 0 now** (Dave D1 confirm). Closes `Agency_OS-iji` for practical purposes.
2. **Schedule Phase 1 within the next 1-2 sessions** (Dave D2 confirm). Match upstream's intended sync model; gain off-host visibility + audit trail.
3. **Treat Phase 2 as a contingency**, not a roadmap item, until empirical contention forces it.
