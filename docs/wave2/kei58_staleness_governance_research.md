# KEI-58 — Discovery staleness governance: research + design

**Author:** scout (Sonnet 4.6, research clone)
**Date:** 2026-05-14
**Status:** research-phase deliverable; build phase remains for scout after KEI-46 (Weaviate) + KEI-47 (migration completeness guard) ship.
**Linear:** [KEI-58](https://linear.app/keiracom/issue/KEI-58)
**Depends on:** KEI-46 Weaviate install (not shipped), KEI-47 migration completeness (not shipped). Both Aiden lane.
**Owner per Linear body:** Scout — research then build.

This document closes the research phase of KEI-58. It defines exactly
what `context_version`, the staleness flag thresholds, and the
`bd verify` command look like in code — enough that the build phase
is mechanical translation from spec to PR.

---

## 1. Problem framing

Discoveries written today become wrong tomorrow without anyone
noticing. The classic example: "cgroup v2 is the verified path" is
true on Cognee 0.7.3 + Vultr-Debian-12; flip to Cognee 0.9.1 or a
different host kernel and the conclusion no longer holds. Agents that
pull this discovery into a `bd claim` context brief act on it
confidently. The wrong answer is worse than no answer.

Two failure axes:

1. **Age decay** — staleness as a function of wall-clock time since
   the discovery was confirmed.
2. **Environment drift** — a software/runtime version cited in the
   discovery has changed; the discovery may be invalid even though
   it's young.

Either axis can independently flip a discovery from "trustworthy"
to "needs re-verify". The system must surface both clearly enough
that an agent reading a context brief can self-decide whether to
trust, verify, or skip.

---

## 2. The three knowledge-state ladder

This builds on the eviction layer summary in KEI-63 (deprecation). The
full state ladder is now:

| State          | Source                          | Visibility in `bd claim`              | Agent action                   |
|----------------|---------------------------------|----------------------------------------|--------------------------------|
| Active         | Default                         | Full trust, no flag                    | None                           |
| Aging          | age 30–90 days                  | `[~X days old]` informational          | Optional                       |
| Stale          | age 90–180 days                 | `⚠ [X days old — verify still applies]`| Verify before relying          |
| Likely stale   | age ≥ 180 days                  | `⚠⚠ [X days old — likely stale, re-verify before use]` | Strong-prefer verify   |
| Context-changed| env_hash or version mismatch    | `⚠⚠ Environment changed since written` | Verify; KEI-63 handles deprec  |
| Deprecated     | KEI-63 `bd deprecate` command   | NEVER injected                         | Already actioned               |

Note the separation: age vs context-change are independent warnings.
A discovery can be both `Stale` and `Context-changed` — both flags
render. Agents can distinguish "this is just old" from "this is
wrong now because we changed runtimes".

---

## 3. `context_version` schema

Auto-populated at write time; agent never fills this manually. The
field is a JSONB on the discovery record (Weaviate property, mirrored
to a Supabase `discovery_versions` audit table for query
performance).

```json
{
  "context_version": {
    "kei": "KEI-44",                                  // active KEI at write time, if any
    "written_at": "2026-05-14T07:30:00Z",
    "git_sha": "11a9a5ef",                            // main HEAD at write time
    "branch_name": "scout/kei58-staleness-governance-research",
    "software_versions": {
      "python": "3.12.2",
      "cognee": "0.7.3",
      "weaviate": "4.5.1",
      "llama_index": "0.10.45",
      "psycopg": "3.1.18"
    },
    "environment_hash": "sha256:<from KEI-60 env_hash module>",
    "host_os": "Linux 6.6.20-amd64",                  // uname -r
    "callsign": "scout"
  }
}
```

### Population helper

```python
# src/memory/context_version.py
def capture_context_version(callsign: str) -> dict:
    """Auto-capture environment metadata at discovery write time."""
    return {
        "kei": _active_kei_from_branch(),
        "written_at": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha_short(),
        "branch_name": _git_branch(),
        "software_versions": _package_versions(WATCHED_PACKAGES),
        "environment_hash": environment_hash.compute(),  # from KEI-60
        "host_os": platform.platform(),
        "callsign": callsign,
    }
```

`WATCHED_PACKAGES` is a tuple of package names whose version drift
should fire the "context-changed" warning. Initial set chosen by
what we currently pin in `requirements.txt`: cognee, weaviate-client,
llama-index, psycopg, supabase, anthropic. Update list when a new
critical dep lands.

`_active_kei_from_branch()` parses `scout/keiNN-...` / `aiden/keiNN-...`
branch names. Empty string if branch doesn't match the pattern (e.g.
working directly on `main`). The empty case is fine — context_version
is still useful without the KEI link.

---

## 4. Age flag thresholds (the warning ladder)

Three thresholds, four states. The thresholds are configurable via
`public.system_config` rows (no hard-coded constants in the inject
path) so we can tune later without code changes.

```sql
INSERT INTO public.system_config (key, value, updated_at) VALUES
  ('staleness.aging_days',          '30',  NOW()),
  ('staleness.stale_days',          '90',  NOW()),
  ('staleness.likely_stale_days',   '180', NOW())
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();
```

### Inject-path rendering

```python
# src/retrieval/staleness.py — runs as part of CitationQueryEngine response synthesis
def staleness_label(written_at: datetime, software_drift: list[str]) -> str:
    """Return inline label suffix for a discovery citation. '' if fresh."""
    age_days = (datetime.now(UTC) - written_at).days
    thresholds = _load_thresholds()  # cached for 60s
    age_label = _age_label(age_days, thresholds)   # '', '~X days old', etc.
    drift_label = (
        f"⚠⚠ Written for {', '.join(software_drift)} (current versions differ)"
        if software_drift else ""
    )
    parts = [p for p in (age_label, drift_label) if p]
    return " ".join(parts)
```

Both labels render concatenated so agents see BOTH signals: "[60 days
old] ⚠⚠ Written for cognee==0.7.3 (current versions differ)". One
discovery, two warnings, two distinct reasons.

---

## 5. Software version drift detection

```python
def detect_software_drift(captured: dict[str, str]) -> list[str]:
    """Return list of 'pkg==<old>' for packages whose current version differs."""
    current = _package_versions(captured.keys())
    drift: list[str] = []
    for pkg, old_ver in captured.items():
        new_ver = current.get(pkg)
        if new_ver and old_ver and new_ver != old_ver:
            drift.append(f"{pkg}=={old_ver}")
    return drift
```

Decision intent: list ALL drifted packages, not just the first. An
agent reading "Written for cognee==0.7.3, weaviate==4.4.0" knows
both changed — more diagnostic signal than "version mismatch detected".

Caveat for the build: `importlib.metadata.version()` returns the
INSTALLED version, which may differ from what the agent will actually
hit at runtime (e.g. if a venv switch happened). For the canonical
case this is fine; for edge cases, fallback to reading `pip freeze`
output and caching for 60s.

---

## 6. `bd verify` command (the re-verification path)

The user-facing command is `bd verify <discovery_id>`. Three actions:

| Action     | Effect on the discovery                                              | Side effect                                    |
|------------|----------------------------------------------------------------------|------------------------------------------------|
| CONFIRM    | `verified_at = NOW()`, `verified_by = <callsign>`, `verification_count += 1` | Resets the staleness clock                  |
| UPDATE     | Writes a NEW discovery record linked to the old one via `supersedes` | Old record stays in Weaviate, status='superseded' |
| DEPRECATE  | Delegates to KEI-63 `bd deprecate` command                           | Status='deprecated', never injected            |

```bash
# happy path: re-confirm an aging discovery
bd verify disc_8a91c7 --action confirm

# happy path: update to a new fact
bd verify disc_8a91c7 --action update --new-content "..." --reason "Cognee 0.9.1 changed default cap"

# happy path: deprecate (delegates to KEI-63)
bd verify disc_8a91c7 --action deprecate --reason "Migrated off Vultr"
```

Implementation home: a new `scripts/discoveries_cli.py` (sibling to
`scripts/tasks_cli.py`). Same psycopg-via-DATABASE_URL pattern; same
exit-code convention (0 happy, 1 misconfig, 2 db error). Subcommands:
`list`, `show`, `verify`, `staleness` (audit: how many discoveries
are in each staleness state).

### Subcommand: `staleness` (audit + observability)

```bash
$ discoveries_cli.py staleness
  Fresh (<30d):        142
  Aging (30-90d):       54
  Stale (90-180d):      18
  Likely stale (>180d):  6
  Context-changed:      11
  Deprecated:           23 (not shown in injection)

  Top 3 oldest active discoveries:
    disc_3f… [184d] cgroup v2 verified path  — Aiden, KEI-44
    disc_b1… [171d] tmux session naming      — Scout, KEI-13
    disc_d4… [167d] Beads ready stale fix    — Elliot, KEI-22
```

This is a dashboard-as-CLI for the system-health audit. Easy first
pass to `Grafana` once that KEI lands.

---

## 7. Integration with KEI-55 (tiered validation)

KEI-55 introduces three validation tiers. Staleness interacts with
each:

| Tier | Promotion path                          | Staleness rule                                                          |
|------|-----------------------------------------|--------------------------------------------------------------------------|
| 1    | Auto-promote after 24h unchallenged     | Standard age thresholds (30/90/180)                                     |
| 2    | Promote on peer CONCUR                  | Stale at 90d **unless** re-verified at least once; never-verified→stale early |
| 3    | Dave approval                           | Stale at 90d; auto-deprecate at 180d (Tier 3 too high-stakes to drift)   |

The "never-verified Tier 2 stales early" rule prevents a peer-concur'd
discovery from drifting silently — peer concur at write time isn't a
permanent free pass.

---

## 8. Data layout

### Weaviate schema (discoveries collection)

```python
# property additions for KEI-58 (alongside KEI-55's validation_tier + status fields)
{
    "context_version": "object",      # the JSONB blob from §3
    "verified_at": "date",            # nullable; populated by bd verify confirm
    "verified_by": "text",
    "verification_count": "int",      # increments on each confirm
    "supersedes": "text",             # discovery_id of the prior version; nullable
    "superseded_by": "text",          # nullable; populated when a newer version is written
    "deprecated_at": "date",          # nullable; from KEI-63
    "deprecation_reason": "text"
}
```

### Supabase audit mirror

```sql
CREATE TABLE IF NOT EXISTS public.discovery_versions (
    discovery_id  TEXT PRIMARY KEY,
    written_at    TIMESTAMPTZ NOT NULL,
    callsign      TEXT NOT NULL,
    kei           TEXT,
    git_sha       TEXT,
    software_versions JSONB NOT NULL,
    environment_hash  TEXT,
    verified_at   TIMESTAMPTZ,
    verified_by   TEXT,
    verification_count INT DEFAULT 0,
    supersedes    TEXT,
    superseded_by TEXT,
    deprecated_at TIMESTAMPTZ,
    status        TEXT NOT NULL CHECK (status IN ('active','aging','stale','likely_stale','superseded','deprecated','context_changed'))
);
CREATE INDEX ON public.discovery_versions (callsign, written_at DESC);
CREATE INDEX ON public.discovery_versions (status) WHERE status != 'deprecated';
CREATE INDEX ON public.discovery_versions (verified_at) WHERE verified_at IS NOT NULL;
```

The `status` column is materialised — a cheap pre-computed column
saving JOIN-time staleness math. A nightly cron recomputes it (job
flips `active → aging` etc. once a row crosses a threshold).

Rationale for the Supabase mirror (vs Weaviate-only): the staleness
dashboard query (`§6 staleness subcommand`) is a slice/dice operation
that's faster on Postgres than on Weaviate's REST API. The vector
embeddings stay in Weaviate; the metadata mirror is read-only.

---

## 9. Smoke-test plan

`tests/scripts/test_discoveries_cli.py` + `tests/memory/test_context_version.py`
ship alongside the build. Acceptance cases:

| # | Scenario                                                                            | Expected outcome                                     |
|---|-------------------------------------------------------------------------------------|------------------------------------------------------|
| 1 | Write discovery → query immediately → no age flag                                    | `staleness_label() == ""`                            |
| 2 | Mock written_at = 45 days ago → query                                                | label contains `~45 days old`                        |
| 3 | Mock written_at = 100 days ago → query                                               | label contains `⚠ 100 days old`                       |
| 4 | Mock written_at = 200 days ago → query                                               | label contains `⚠⚠ 200 days old`                      |
| 5 | Fresh discovery, change cognee version to 0.9.1 → query                              | label contains `Written for cognee==0.7.3`            |
| 6 | `discoveries_cli verify <id> --action confirm` → re-query → no warning               | `verified_at` updated; staleness reset               |
| 7 | `discoveries_cli verify <id> --action update --new-content X` → new record created   | new record's `supersedes` = old.id; old.superseded_by set |
| 8 | Tier 2 discovery never verified, 91 days old                                         | flagged stale via KEI-55 integration rule            |
| 9 | Tier 3 discovery 181 days old → cron pass                                            | auto-deprecated via KEI-63 delegation                |
| 10| `discoveries_cli staleness` against seeded corpus                                    | exact bucket counts match seeded fixtures            |

Test 5 must mock the `_package_versions()` call (not actually
re-install cognee). Use `monkeypatch.setattr` on
`src.memory.context_version._package_versions`.

---

## 10. Build sequence (when KEI-46 + KEI-47 ship)

Three PRs, each independently verifiable:

1. **PR 1** — `src/memory/context_version.py` + tests. Adds the
   capture helper + drift detector. Doesn't write to Weaviate yet —
   pure utility. Smoke: import + call; assert shape.

2. **PR 2** — Supabase migration adding `public.discovery_versions`
   table + `system_config` rows for staleness thresholds. Smoke:
   `INSERT/SELECT` via tasks_cli pattern.

3. **PR 3** — `scripts/discoveries_cli.py` with `list/show/verify/staleness`
   subcommands. Hooks the Weaviate writer to populate `context_version`
   at write time. This is the visible KEI-58 deliverable.

PR 4 (later, separate KEI candidate): nightly cron that flips status
columns across thresholds. Not required for first ship — agents
running `discoveries_cli staleness` get correct on-demand counts via
SQL anyway; the materialised column is an optimisation.

---

## 11. Risks + mitigations

| Risk                                                              | Likelihood | Mitigation                                                                                  |
|-------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------|
| `importlib.metadata.version()` returns wrong venv → false drift   | medium     | Cache `pip freeze` output for 60s as fallback; emit warning when caches disagree.            |
| Threshold changes confuse historical analyses                      | low        | Each `system_config` row keeps `updated_at`; staleness audit logs the threshold version.    |
| `bd verify --action update` chain explodes (long supersedes chain) | medium     | Render last 3 versions inline in `bd claim` injection; full chain in `discoveries_cli show`.|
| KEI-55 + KEI-58 + KEI-63 rule overlap (which fires first?)         | high       | Precedence order: deprecated > context-changed > stale > aging > active. Documented + tested.|
| Staleness label crowds out the citation excerpt in the 500-tok cap | medium     | Truncate the label to 60 chars max; spill to `discoveries_cli show` for full context.       |

---

## 12. Open questions

For the build phase (scout, once KEI-46+47 ship):

1. **Cron cadence** — hourly status materialisation (cheap, near-real-time)
   vs daily (cheaper, up to 24h lag on a status transition). Daily is
   probably fine; the warning label is computed on-demand from
   `written_at` anyway. Materialised status is for dashboards.
2. **Threshold tuning** — current 30/90/180 is a guess. After 90 days
   of telemetry, look at `verified_at` distributions and re-tune.
3. **Multi-environment vs single-environment** — once we run prod +
   staging, do discoveries from one environment trip drift warnings
   when read in the other? Likely yes — should be a tagged property
   on the discovery, not derived from `environment_hash`.
4. **Auto-deprecate cron for Tier 3 ≥ 180d** — does this need a
   human-in-the-loop step? KEI-63 says Tier 3 deprecation needs Dave
   approval; the auto-deprecate rule here might violate that. Likely
   resolution: auto-flag, not auto-deprecate; Slack-notify Dave.

---

## 13. Scout handoff note

This is a research-phase deliverable. Per IDENTITY.md, scout owns
both research AND build for KEI-58 (Linear body explicitly: "Scout —
research into implementation patterns, then build"). The research is
done here; the build is gated on KEI-46 (Weaviate install) + KEI-47
(migration completeness guard) shipping.

On merge, the tasks-table row `KEI-58` flips to `done` with the
understanding that "done" = research-phase done. Filing a follow-up
`KEI-58B` (staleness build) for the queue when the dependencies land
is the next action — scout writes the build PRs when they unblock.
