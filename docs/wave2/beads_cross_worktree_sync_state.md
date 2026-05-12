# Beads Cross-Worktree Sync — Current State (2026-05-12)

**Author:** atlas
**Beads tracking issue:** `Agency_OS-iji` — "Cross-worktree Beads DB sync — CTOs can't run bd locally until resolved"
**Methodology:** read-only empirical inspection of `.beads/` per worktree, `bd where`, `bd dolt show`, `.git` link contents, and Dolt remote/ref state. No mutations.

## TL;DR

The Beads embedded Dolt DB lives at `/home/elliotbot/clawd/Agency_OS/.beads/embeddeddolt/` only. Four of six worktrees can reach it via `bd`'s "walk up to nearest .beads with embeddeddolt/" resolution; **two cannot** — `Agency_OS-max` and `Agency_OS-orion` are git-worktrees of a *different parent repo* (`/home/elliotbot/clawd/.git`), so `bd` does not walk up into Agency_OS and errors with "no beads database found". Today there is **no active sync** — no Dolt remote is configured (`bd dolt show: Remotes: (none)`), no `refs/dolt/data` ref is pushed to GitHub, and no central bd server is running. Sharing happens incidentally because four of six worktrees all touch the same physical DB file via filesystem traversal.

## 1. Per-worktree DB resolution (empirical)

`bd where` (verbatim):

| Worktree | `bd where` result | bd works? |
|---|---|---|
| `/home/elliotbot/clawd/Agency_OS` (elliot) | `/home/elliotbot/clawd/Agency_OS/.beads` — prefix Agency_OS — database `.beads/embeddeddolt` | ✓ |
| `/home/elliotbot/clawd/Agency_OS-aiden` | `/home/elliotbot/clawd/Agency_OS/.beads` (walked up) | ✓ |
| `/home/elliotbot/clawd/Agency_OS-atlas` | `/home/elliotbot/clawd/Agency_OS/.beads` (walked up) | ✓ |
| `/home/elliotbot/clawd/Agency_OS-scout` | `/home/elliotbot/clawd/Agency_OS/.beads` (walked up) | ✓ (no local `.beads/` exists) |
| `/home/elliotbot/clawd/Agency_OS-max` | `/home/elliotbot/clawd/Agency_OS-max/.beads` (did NOT walk up) | ✗ — "Error: no beads database found" |
| `/home/elliotbot/clawd/Agency_OS-orion` | `/home/elliotbot/clawd/Agency_OS-orion/.beads` (did NOT walk up) | ✗ — same error |

## 2. Root cause — git-worktree alignment

`.git` link contents per worktree (verbatim):

| Worktree | `.git` link | Parent repo |
|---|---|---|
| Agency_OS | `(directory)` — primary worktree | self |
| Agency_OS-aiden | `gitdir: /home/elliotbot/clawd/Agency_OS/.git/worktrees/Agency_OS-aiden` | **Agency_OS** ✓ |
| Agency_OS-atlas | `gitdir: /home/elliotbot/clawd/Agency_OS/.git/worktrees/Agency_OS-atlas` | **Agency_OS** ✓ |
| Agency_OS-scout | `gitdir: /home/elliotbot/clawd/Agency_OS/.git/worktrees/Agency_OS-scout` | **Agency_OS** ✓ |
| Agency_OS-max | `gitdir: /home/elliotbot/clawd/.git/worktrees/Agency_OS-max` | **`/home/elliotbot/clawd/`** (different repo) ✗ |
| Agency_OS-orion | `gitdir: /home/elliotbot/clawd/.git/worktrees/Agency_OS-orion` | **`/home/elliotbot/clawd/`** (different repo) ✗ |

`/home/elliotbot/clawd/.git/HEAD` = `ref: refs/heads/main` — confirms `/home/elliotbot/clawd/` is an independent git repository (likely the parent ops/clawd repo), not Agency_OS.

When `bd` resolves the working dir, it walks up looking for `.beads/embeddeddolt/`. For Agency_OS-max and Agency_OS-orion the upward traversal exits the Agency_OS tree before reaching `Agency_OS/.beads/embeddeddolt/` — so resolution stops at the local `.beads/` shell (which contains only the gitignored skeleton, no Dolt DB).

## 3. `.beads/` contents per worktree (verbatim `ls`)

| Worktree | Has `embeddeddolt/`? | Has `issues.jsonl`? | Has `metadata.json`? |
|---|---|---|---|
| Agency_OS (elliot) | **yes** (88 kB total) | yes (live) | yes (`export-state.json` present) |
| Agency_OS-aiden | no | yes (8980 bytes) | yes |
| Agency_OS-atlas | no | yes (8980 bytes) | yes |
| Agency_OS-max | no | yes (8980 bytes) | yes |
| Agency_OS-orion | no | yes (8980 bytes) | yes |
| Agency_OS-scout | **no `.beads/` dir at all** | — | — |

`.beads/.gitignore` (committed) lists `dolt/`, `embeddeddolt/`, `bd.sock`, `bd.sock.startlock`, `sync-state.json`, `last-touched`, `.exclusive-lock`, `daemon.*`, `push-state.json`, `*.lock` — i.e. **the Dolt DB itself is intentionally not in git**; only the JSONL passive export plus config + hooks + metadata are committed.

## 4. Sync mechanism today (verbatim `bd dolt show`)

```
Dolt Configuration
==================
  Database: Agency_OS
  Mode:     embedded (in-process Dolt engine)
  Data:     /home/elliotbot/clawd/Agency_OS/.beads/embeddeddolt

Remotes:
  (none)
```

`git for-each-ref refs/dolt/` from Agency_OS root → no output (no `refs/dolt/data` ref locally). `git ls-remote origin` → no `refs/dolt/*` refs on GitHub either.

**No `bd sync` top-level command** exists; the canonical sync surface is `bd dolt push` / `bd dolt pull` (plus `bd dolt remote add <name> <url>` to configure a remote). `bd linear sync --pull/--push` is a separate Linear↔Beads bridge, not Beads↔Beads.

Backup posture: `config.yaml` documents an auto-JSONL-export-with-git-push backup mode, gated on whether a git remote exists. Empirically the `issues.jsonl` files have synchronised mtimes per worktree (all 09:00 on max, atlas, etc.) suggesting they're being refreshed during git operations rather than from live Dolt writes — i.e. **the JSONL export is the only cross-worktree visibility today**, and it's read-only on the consumer side.

## 5. Friction observed in practice

Per `Agency_OS-iji` (Aiden's PR #771 review observation #2):

> "Use bd for ALL task tracking" rule across worktrees doesn't work today because the Beads embedded Dolt DB is per-worktree, not shared. Pragmatic interim: TaskCreate locally for CTOs/clones until cross-worktree Beads sync solved (per upstream's refs/dolt/data git-sync model).

In addition (this audit):

- Max and Orion **physically cannot run `bd create`/`bd update`/`bd ready`** from their own worktrees. Workaround: `cd /home/elliotbot/clawd/Agency_OS && bd …` — but `cd`-ing out of a worktree breaks branch context for the agent.
- Atlas/Aiden/Scout *appear* to work but are actually writing to **Elliot's local Dolt DB** via shared FS — no isolation, no auditable per-agent action trail at the Dolt level.
- A second machine (e.g. CI runner, secondary Vultr host) has no way to read state today — JSONL is the only off-host visibility path, and it's lossy (no audit log, no Dolt rev history).
- `bd close` writes by clones currently surface as actor=`elliotbot` in audit trails because the `BEADS_ACTOR` env doesn't propagate consistently — but that's a separate gap.

## 6. Upstream's intended model (per https://github.com/gastownhall/beads SYNC_CONCEPTS.md, summarised)

- Local Dolt DB per worktree (`bd init` creates it).
- A configured remote (`bd dolt remote add origin <url>`) — can be a real Dolt server (DoltHub or self-hosted) or `file://` path on shared FS.
- `bd dolt push` / `bd dolt pull` ship Dolt revisions between local and remote.
- Optional: enable backup mode to also push JSONL exports to a normal git remote on each flush — this is what makes `.beads/issues.jsonl` an "automatic git-pushed audit trail" alongside Dolt's own commit history.
- The `refs/dolt/data` git ref is *one* possible remote shape: store Dolt commits in the same GitHub repo under a non-branch ref namespace.

We have implemented **none** of this yet. Today's effective architecture is "single-host shared filesystem, hope nobody's writing concurrently".

## 7. Open questions surfaced (for recommendation doc to resolve)

1. Is fixing Max + Orion to be proper Agency_OS git-worktrees in-scope, or is preserving them as worktrees-of-the-clawd-parent intentional?
2. Multi-machine readiness — required pre-revenue, or defer until first non-Vultr worker?
3. Concurrent-write safety — is "elliot writes, everyone else reads" acceptable, or do we need true multi-writer?
4. Audit trail granularity — should `BEADS_ACTOR` per agent become a hard requirement?

Methodology caveats: `bd where` output may differ if `BEADS_DIR` env is set per-worktree (not checked). Permission warnings on max/orion `.beads/` (`0775` instead of `0700`) suggest the dirs were created by a different process than aiden/atlas/scout — possibly hand-`mkdir`'d during clone-onboarding rather than `bd init`'d.
