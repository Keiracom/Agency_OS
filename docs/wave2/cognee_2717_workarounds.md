# Cognee Issue #2717 — Workarounds Deep-Dive

Source: `https://github.com/topoteretes/cognee/issues/2717` (open). Read fresh 2026-05-12.

## The bug, restated

`cognee.cognify()` deadlocks (`sqlite3.OperationalError: database is locked`) on datasets ≥50 docs. Root cause per reporter: **intra-process greenlet parallelism**, not multi-process. The official `--api-url` FastAPI workaround documented in `cognee/cli/api_client.py` does NOT help — the single API process still spawns parallel greenlets inside `cognify()`.

## Reporter's environment vs ours

| Component | Reporter | Us |
|---|---|---|
| Cognee | 1.0.0-local | 1.0.9 |
| Python | 3.12.13 | 3.12.3 |
| **aiosqlite** | **0.21.0** | 0.22.1 |
| OS | CachyOS LTS 6.18.23 | Ubuntu 24.04 6.8.0 |

**Critical finding for Option F:** the reporter was already on `aiosqlite==0.21.0` (our proposed pin candidate) and **still hit the bug**. The version pin is unlikely to resolve our segfault. Earlier `cognee_aiosqlite_pin_candidates.md` caveat is now confirmed.

## What Cognee maintainers shipped since the report

Two merged PRs targeting this class of failure:

1. **PR #2695 — "Feat: Dataset queue in set context async manager"** (merged 2026-04-24, in 1.0.4+). Adds a database queue around the global context-variable system. **We have this** (running 1.0.9). Still failing → not sufficient on its own.
2. **PR #2803 — "Cognee Subprocess mode refactor and fixes"** (merged **2026-05-12 01:24 UTC today**, not yet released on PyPI). Subprocess-mode refactor targeting the same area. **We do NOT have this in 1.0.9.**

```
$ curl -s https://pypi.org/pypi/cognee/json | jq -r '.releases | to_entries | sort_by(.value[0].upload_time) | reverse | .[0:3] | .[] | "\(.key)\t\(.value[0].upload_time)"'
1.0.9   2026-05-08T15:34:19
1.0.8   2026-05-06T04:02:59
1.0.7   2026-05-05T18:42:20
```

Latest PyPI release (1.0.9, 2026-05-08) predates PR #2803 by 4 days. **The fix is in main, not in any released version.**

## Workaround landscape (ranked)

### W1 — Install from main branch (preferred if Phase 0 must ship before next PyPI cut)
```bash
.venv/bin/pip install --upgrade --force-reinstall \
  'cognee @ git+https://github.com/topoteretes/cognee.git@main'
```
Picks up PR #2803 immediately. Caveats: main may have unrelated breakage between 1.0.9 and the next tag; pin to the merge commit `0be0ad3b5c33ab5413423914266e574dcd36160c` if reproducibility matters.

### W2 — Wait for next Cognee PyPI release (>1.0.9)
Lowest risk; main → next tag should arrive within days based on the 1.0.4 → 1.0.9 cadence (≈6 days for 5 patches). Defers Phase 0 smoke.

### W3 — Enable SQLite WAL mode (works regardless of Cognee version)
Reporter's Option C — wrapper-side, no Cognee patch. Apply in our wrapper before `cognee.add/cognify`:
```python
from sqlalchemy import event
from cognee.infrastructure.databases.relational import get_relational_engine
engine = get_relational_engine().engine
@event.listens_for(engine.sync_engine, "connect")
def _set_wal(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA journal_mode=WAL")
    dbapi_conn.execute("PRAGMA synchronous=NORMAL")
    dbapi_conn.execute("PRAGMA busy_timeout=30000")
```
WAL allows concurrent readers + one writer with much lower lock contention than the default `DELETE` journal mode. Does NOT fully eliminate the deadlock under heavy parallel writes but raises the failure threshold significantly (typical ~10× more throughput before locks).

### W4 — Postgres backend (Option E from prior research)
`DB_PROVIDER=postgres` + a `DATABASE_URL` pointing at a local Postgres. Eliminates the SQLite single-writer constraint entirely. Heaviest config change but the only solution that the maintainer (Vasilije1990) explicitly recommends long-term ("PostgreSQL promoted as the production backend").

### W5 — Aiosqlite pin to 0.21.0 (DEPRECATED RECOMMENDATION)
Per reporter's environment table — they ran 0.21.0 and still hit the bug. **Withdraw this from Option F if Dave is choosing.** Pin candidates 0.20.0/0.21.0/0.22.x show no version-specific signal in this issue.

## Net recommendation for Aiden's wrapper

Combine **W3 (WAL pragma)** as a defensive baseline regardless of Cognee version, AND either **W1 (main-branch install)** for fast Phase 0 unblock OR **W2 (wait for next release)** if a few days of slip is acceptable. **W4 (Postgres)** is the long-term answer. **W5 (aiosqlite pin) is dead** — drop from Option F set.

Estimated W3 patch surface: 6 lines in the wrapper's init. W1 = one pip command. W4 = env var + Postgres provisioning.
