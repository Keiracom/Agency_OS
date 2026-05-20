# pr_review_pump.py — Design Specification

**Status:** Draft (design only — no implementation)
**Author:** atlas
**Date:** 2026-05-18
**Source directive:** Dave verbatim — "all PRs dual-reviewed and merged as each comes in"
**Linear KEI:** TBD (file before implementation begins)
**Lives in:** `scripts/orchestrator/pr_review_pump.py` (Agency_OS — service runs from main worktree per `feedback_systemd_worktree_main`)

---

## 1. Goal

Drive the project's GitHub PR queue to MERGED state with zero human bottleneck per Dave's "all PRs dual-reviewed and merged as each comes in." Replace the current ad-hoc loop where authors post a PR, mention reviewers in #execution, and wait for someone to notice. The pump observes every open PR each cycle, dispatches a review to the next-eligible reviewer agent (excluding authors and their clones), watches for dual concur + CI green, then merges.

This is the **mechanical merge pipeline**. It does NOT make taste/architecture decisions — those still come from human reviewers (Dave, Aiden, Max) when escalated. The pump only operates the assembly line.

---

## 2. systemd timer cadence

Two-file install (`pr-review-pump.service` + `pr-review-pump.timer`) following the `agency-os-*` pattern. Service is oneshot (each cycle exits); timer drives cadence.

| Window | Cadence | Reason |
|---|---|---|
| Always-on | `OnCalendar=*:0/5` (every 5 min) | Authenticated GitHub PRs API is rate-limited to 5000 req/hr/user; a typical cycle uses ~30 calls (list + per-PR detail), giving ~6000 cycles/hr of headroom |
| Off-hours fallback | None — same cadence | PR merges shouldn't queue overnight; even at 3am AEST something should pump |

Boot delay: `OnBootSec=2min` so the pump waits for `weaviate.service` + `valkey-server` + Slack listener to stabilise before its first cycle. `Persistent=true` so a missed cycle during host reboot is recovered on next boot.

**Cycle budget:** each invocation MUST complete in ≤ 90s. If a cycle is still running at the next timer fire, systemd's `Type=oneshot` will skip the new fire (default behavior is fine — no overlap). The pump records `last_cycle_started_at` so an external watchdog can alert if cycles stop firing.

---

## 3. Author + clone exclusion table

Two-layer exclusion: NEITHER the PR author NOR the author's clone/prime peer may be assigned as reviewer. This prevents both self-review and "essentially-self" review where atlas approves elliot's work (or vice versa).

| PR author | Excluded from reviewer pool | Eligible reviewers |
|---|---|---|
| `elliot` | elliot, atlas | aiden, max, orion, scout, nova |
| `atlas` | atlas, elliot | aiden, max, orion, scout, nova |
| `aiden` | aiden, orion | elliot, max, atlas, scout, nova |
| `orion` | orion, aiden | elliot, max, atlas, scout, nova |
| `max` | max, scout | elliot, aiden, atlas, orion, nova |
| `scout` | scout, max | elliot, aiden, atlas, orion, nova |
| `nova` | nova, **TBD** | All others minus TBD parent |

**Nova parent:** open question. KEI-185 (`KEI-C: Nova spawn via SessionManager + flip supervisor v2 ON`) introduced Nova as an engineer-clone but its prime peer assignment isn't recorded in any module I've found. Implementation MUST resolve this before launch — either Nova has a prime (one of elliot/aiden/max) and the exclusion applies, OR Nova is an unrestricted worker (no prime; only self-exclusion). Filing as KEI follow-up: "Resolve Nova's prime-peer mapping for pr_review_pump exclusion table."

**Required reviewer count:** TWO distinct reviewers from the eligible pool, drawn from different clone-pairs (so an aiden review and an orion review do NOT count as two — they're the same lane). Pairing logic: select the two reviewers from two different `{prime, clone}` lanes other than the author's lane.

**Lane definition:**
- Lane E: `{elliot, atlas}`
- Lane A: `{aiden, orion}`
- Lane M: `{max, scout}`
- Lane N: `{nova, TBD}` (or its own lane if unrestricted)

**Assignment policy:** round-robin across eligible lanes, weighted by current review queue depth (prefer lanes with fewer in-flight reviews). Tie-broken by callsign alphabetical.

---

## 4. CI-gating logic with known-unrelated-failure exceptions

Every PR has a `statusCheckRollup` from `gh pr view --json statusCheckRollup`. Each check has `name`, `state`, `conclusion`. The pump classifies checks into three buckets:

### Hard required (MUST be SUCCESS — block merge)

- `ruff check` — lint
- `ruff format --check` — style
- `pytest` — unit + integration suite
- `sonarcloud` quality gate (status from `/api/qualitygates/project_status` per `feedback_sonar_qg_not_just_issues`)
- Any check named `*-required-*` or matching team's required-check naming convention (configurable)

### Soft (PENDING = wait; SUCCESS = proceed; FAILURE = wait, log but don't escalate)

- `pre-commit` if listed but not required by branch protection
- Coverage upload reporters

### Known-unrelated (FAILURE is allowlisted — does NOT block merge)

Configurable via `config/pr_review_pump_known_unrelated.json`:

```
{
  "always_unrelated": [
    "vercel/deploy-preview-frontend",
    "vercel/deploy-preview-marketing"
  ],
  "path_conditional": [
    {
      "check_name": "vercel/deploy-preview-*",
      "paths_must_not_touch": ["frontend/**", "marketing/**"],
      "rationale": "Vercel build failures on backend-only PRs are infrastructure noise"
    }
  ]
}
```

Rule: if the PR's changed file list (`gh pr view --json files`) doesn't touch the `paths_must_not_touch` glob, the check is treated as PASS for merge purposes. This is logged as `ci_exception_applied=<check_name>` per cycle so an audit can confirm the exception fired correctly.

**Critical anti-pattern guard (per `feedback_no_assumed_preexisting_ci_failure`):** the pump MUST run the actual sonarcloud `/api/issues/search?pullRequest=<N>` per PR every cycle — never assume "this failure is pre-existing." Each PR is evaluated independently. If a Sonar check is FAILURE, the pump pulls the issues list and only treats failures as ignorable if every issue predates the PR's base commit. Else block merge.

---

## 5. Dispatch routing

Three available channels; the pump uses TWO in combination.

| Channel | Properties | Pump use |
|---|---|---|
| **tmux send-keys** | Direct injection into a running tmux pane; immediate; fragile (depends on pane being attached + non-busy); no acknowledgement | **NOT USED** — too brittle for an unattended pump |
| **Inbox JSON** | Persistent (file in `/tmp/telegram-relay-<callsign>/inbox/`); queued; survives restarts; consumed by callsign's inbox watcher | **PRIMARY** — durability matters; agents process when ready |
| **NATS pub/sub** | Multi-subscriber; observable; topic-routed; not directly consumed by Claude agent (relay-only) | **OBSERVABILITY** — every dispatch also publishes to `keiracom.pr.review_dispatched` for fleet supervisor / dashboards |

**Dispatch payload schema (inbox JSON):**

```
{
  "type": "pr_review_dispatch",
  "from": "pr_review_pump",
  "pr_number": 1046,
  "pr_url": "https://github.com/Keiracom/Agency_OS/pull/1046",
  "pr_title": "[ATLAS] fix(kei70st): indexer_base prepare_threshold=None",
  "pr_author": "atlas",
  "review_lane": "M",
  "step_0_pre_confirmed": true,
  "brief": "Dual-review pump dispatch. Read PR, post [REVIEW:approve:<your_callsign>] or [REVIEW:hold:<your_callsign>] on the PR. Sonar QG + ruff + pytest required green per the pump's CI policy.",
  "deadline_iso": "2026-05-18T23:00:00Z",
  "dispatch_id": "uuid4"
}
```

`step_0_pre_confirmed: true` per `feedback_clone_dispatch_needs_explicit_confirm` — clones (atlas/orion/scout/nova) need the header to bypass their own Step 0 protocol on this dispatch.

`deadline_iso` is a soft hint; the pump's next cycle will re-dispatch if review hasn't landed by deadline.

---

## 6. Auto-merge condition

Pump auto-merges a PR when ALL of the following hold simultaneously in one cycle (no state machine — pure observation, idempotent):

1. **State:** PR is `OPEN` and `mergeable: MERGEABLE` (not CONFLICTING / UNKNOWN).
2. **Dual concur:** PR has comments from TWO distinct reviewers in different lanes (excluding author's lane), each containing `[REVIEW:approve:<callsign>]` OR `[CONCUR:<callsign>]`. Lane-distinctness verified per §3.
3. **CI green:** All Hard Required checks (§4) are SUCCESS. Known-unrelated allowlist applied.
4. **No HOLD/REQUEST-CHANGES:** No comment from any reviewer contains `[REVIEW:hold:<callsign>]` OR `[REVIEW:HOLD:<callsign>]` OR `[REVIEW:hold-final:<callsign>]` since the most recent commit on the PR head.
5. **Branch protection satisfied:** GitHub's API confirms `requireable.canBeMerged` is true (catches dependent branch protection rules not visible to the pump).
6. **Cool-down:** ≥ 5 minutes since the most recent commit on the PR head (gives CI a chance to attach all checks).

When all six hold, the pump executes `gh pr merge <N> --squash --auto` (squash chosen to keep main linear; `--auto` to defer the actual merge until any remaining preconditions clear, providing a final safety net).

After merge:
- Post `[MERGED:pr_review_pump:<N>]` to `#ceo` channel (Dave-facing per `feedback_close_loop_to_ceo`).
- NATS publish to `keiracom.pr.merged` with PR number + sha + lane stats.
- Close associated `REVIEW-PR-<N>` beads tasks (idempotent — only acts on still-open ones).

---

## 7. Idempotence + concurrency safety

**Concurrency model:** the systemd timer guarantees no two pump processes run simultaneously (Type=oneshot + Unit=pr-review-pump.service serialises). Belt-and-suspenders: the pump acquires a file lock at `/var/run/user/<uid>/pr-review-pump.lock` via `flock(LOCK_EX | LOCK_NB)`; if already held, exit 0 with `log.warning("previous cycle still running, skipping")`. This protects against manual invocations during a scheduled cycle.

**Idempotence rules:**

- **No internal state machine.** Each cycle re-reads PR state from GitHub. The "what to do next" decision is a pure function of `(current PR state, comments, CI status)`.
- **Dispatch dedup:** before sending an inbox JSON dispatch, check if the PR already has a comment from the target reviewer's callsign on the current head SHA — if so, skip (review already attempted). Also check inbox `processed/` dir for a recent dispatch ID for same PR + reviewer; skip within a 30-minute throttle window so a slow-responding reviewer isn't spammed.
- **Auto-merge:** `gh pr merge --auto` is itself idempotent (GitHub returns 422 "already auto-merging" which the pump treats as success).
- **Beads close:** uses `~/.local/bin/bd-original close <id>` (bypasses the wrapper's evidence/FK requirement per the 2026-05-18 audit finding); `bd-original close` is idempotent on already-closed records.

**State storage:** none required. The pump is stateless modulo the file lock + the throttle window in the inbox `processed/` dir which exists anyway.

---

## 8. Observability — structured journalctl logs

Service unit routes `StandardOutput=journal` (NOT `append:/home/elliotbot/clawd/logs/...` like other agency-os services — per the diagnostic miss in `Agency_OS-70st` where Aiden checked `journalctl` but the indexer logged to a file, journalctl is the operator's first stop and the pump should respect that).

Every log line is JSON, one object per line:

```
{"ts":"2026-05-18T22:30:01Z","level":"INFO","cycle_id":"uuid","pr":1046,"action":"dispatched","reviewer":"max","lane":"M","reason":"open + 0 prior reviews + lane-rr"}
{"ts":"2026-05-18T22:30:02Z","level":"INFO","cycle_id":"uuid","pr":1047,"action":"waiting","reason":"1/2 concur + ci_running"}
{"ts":"2026-05-18T22:30:03Z","level":"WARN","cycle_id":"uuid","pr":1049,"action":"ci_exception","check":"vercel/deploy-preview-frontend","rationale":"backend-only PR, paths_must_not_touch matched"}
{"ts":"2026-05-18T22:30:04Z","level":"INFO","cycle_id":"uuid","pr":1050,"action":"merged","sha":"abc1234","reviewers":["max","orion"]}
```

**Required fields on every line:** `ts`, `level`, `cycle_id`, `pr`, `action`, and any `action`-specific keys (reviewer, reason, check, sha…). `cycle_id` is a per-cycle UUID4 so a `journalctl --user -u pr-review-pump -o cat | grep <cycle_id>` returns one cycle's full picture.

**Cycle summary line at end of every cycle:**

```
{"ts":"2026-05-18T22:30:05Z","level":"INFO","cycle_id":"uuid","action":"cycle_complete","prs_seen":11,"prs_dispatched":2,"prs_waiting":7,"prs_merged":2,"errors":0,"duration_ms":4123}
```

**Metrics export:** the cycle-complete line is the canonical source for any future Prometheus/BetterStack scrape — fields are stable + ready for `journalctl -o json` → metric ingest.

**Alerts:**
- `errors > 0` in cycle_complete → Slack alert to `#alerts` (per BetterStack severity routing in shipped KEI-20 / PR-routed-by-#1042).
- No `cycle_complete` log line for ≥ 15 min → fleet supervisor's existing systemd health monitor (KEI-141) catches the stalled service via failed-unit detection (no new alert wiring needed).

---

## 9. Failure modes + rollback

| Mode | Detection | Response |
|---|---|---|
| GitHub API 5xx / rate-limit | `gh` exit non-zero or response has `X-RateLimit-Remaining: 0` | Exponential backoff within cycle (1s, 2s, 4s, max 3 tries); if still failing, log error + exit 0; next timer fire retries |
| GitHub auth invalid (gh token expired) | `gh` returns auth error | Cycle exits with `level=CRITICAL`; alert to `#ceo` (token rotation is human work); no further retries until human intervention |
| Inbox dir for reviewer not writable | `OSError` on file write | Skip dispatch for that reviewer, log + alert; pump continues with other PRs |
| Auto-merge fails (e.g. branch went CONFLICTING since check) | `gh pr merge --auto` returns non-zero | Log `action=merge_failed` with stderr; PR re-evaluated next cycle (might need rebase — pump does NOT auto-rebase, that's the author's responsibility per `feedback_branch_off_main_for_urgency`) |
| Same PR re-dispatched > 5 cycles to same reviewer without response | Tracked via inbox `processed/` lookback | Escalate: post `[STALLED:pump:<N>]` to `#ceo` with reviewer callsign + PR link; stop dispatching that PR until human ack |
| Bad dispatch payload (reviewer agent rejects JSON) | NATS subscriber on `keiracom.pr.review_failed` would surface this | Pump logs but doesn't act; the agent's own enforcer surfaces the bad payload (clones MUST surface unsigned/malformed dispatches per HMAC rules) |
| File lock stuck (previous cycle crashed mid-run) | `flock` non-blocking acquire fails for > 3 consecutive cycles | Alert to `#alerts`; manual unlock required (`rm /var/run/user/<uid>/pr-review-pump.lock`); rollback is the disable kill-switch below |

**Kill switch:** `Environment=PR_REVIEW_PUMP_DISABLED=1` in the service unit (or set in the `.env`). When set, every cycle exits immediately with `log.info("disabled via env")`. No GitHub API calls, no merges, no dispatches. This is the rollback when the pump misbehaves.

**Full rollback:**

```
systemctl --user stop pr-review-pump.timer
systemctl --user disable pr-review-pump.timer
# (Optional) revert the pump's recent merges via gh pr revert if any were wrong
```

A wrong merge from the pump is recoverable via `git revert` PR; the pump itself doesn't push to main directly — it only triggers GitHub's auto-merge which respects all branch protection rules. The blast radius is bounded by what dual-approver consensus permits.

---

## 10. Out of scope

Deliberately NOT covered by this design:

- **Review-content automation.** The pump dispatches; it does NOT analyse code or recommend approve/hold. That's still the reviewing agent's job.
- **Architectural decisions.** Pump never picks between conflicting designs.
- **Cross-repo support.** Initial implementation targets `Keiracom/Agency_OS` only. Adding `Keiracom/Dispatcher` (KEI-71 — repo confirmed shipped 2026-05-18) is a follow-up KEI; the design generalises but the initial config hardcodes one repo.
- **Author re-rebases on CONFLICTING.** Pump observes, doesn't fix. Authors get notified via existing supervisor flow.
- **Dependency-PR ordering.** If PR #A depends on PR #B, the pump treats them independently. If #A merges before #B is ready, the author handles the consequence. Future: extend with `Closes #N` parsing if this becomes a frequent footgun.

---

## 11. Implementation gates (before launch)

1. Resolve Nova's prime-peer mapping (§3 open question).
2. Land the periodic `bd linear sync` timer (Agency_OS-iosu) FIRST — pump assumes Linear status is fresh when it decides whether to close `REVIEW-PR-<N>` beads on merge.
3. Negative-path tests on the CI-exception path (synthetic PR with allowlisted check failure but Hard Required failure → MUST not merge) per `feedback_negative_path_test_before_approve`.
4. Dry-run mode: `--dry-run` flag emits logs but skips dispatch + merge for one full cycle on production data. Operator-verified before flipping the timer on.
5. Skill file: `skills/pr-review-pump/SKILL.md` per LAW XIII — canonical reference for how the pump consumes the GitHub PRs API + Sonar `/api/qualitygates/project_status` + inbox JSON shape. Update path documented in this design's §11.

---

## 12. Open questions

- Does the pump merge its OWN failed merges? (Currently no — failed merge → log, wait for human or next cycle on CONFLICTING resolution.)
- Should the pump rebase PRs automatically when CONFLICTING + author-clone is the only candidate to rebase? (Probably no — adds blast radius; let author/clone handle their own branch.)
- What is the right behavior when a PR has dual concur but a third reviewer posts HOLD afterwards? (Spec: HOLD wins; the third-vote-locks rule from `feedback_third_peer_locks_on_bounce` applies.)
- Auto-close beads tasks on merge — should that include `REVIEW-PR-<N>` AND the originating KEI's bd record (e.g. Agency_OS-70st for PR #1046)? (Probably yes for REVIEW-PR; KEI bd record close is more nuanced because the work may have residual scope — let the human orchestrator close those.)

---

End of spec.
