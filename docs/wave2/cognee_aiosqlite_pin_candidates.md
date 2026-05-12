# Cognee Option F — aiosqlite Pin Candidates

## Current state (verified live 2026-05-12)

```
$ /home/elliotbot/clawd/Agency_OS/.venv/bin/pip show aiosqlite
Name: aiosqlite
Version: 0.22.1
Required-by: cognee, prefect

$ python3 --version
Python 3.12.3        # Ubuntu 24.04 (kernel 6.8.0-100-generic)
```

## Cognee 1.0.9 constraint

From `https://pypi.org/pypi/cognee/1.0.9/json` (verbatim `requires_dist`):

```
aiosqlite<1.0.0,>=0.20.0
```

Available pin targets in range: `0.20.0`, `0.21.0`, `0.22.0`, `0.22.1`.

## aiosqlite changelog — the breaking change

From `https://github.com/omnilib/aiosqlite/blob/main/CHANGELOG.md`:

- **v0.22.0** — breaking. `aiosqlite.Connection` **no longer inherits from `threading.Thread`**. "Clients must `await connection.close()` or call `connection.stop()` to ensure the helper thread is completed and terminated correctly."
- **v0.22.1** — bug-fix. Added synchronous `stop()` method (#370) to enable cleanup without an active event loop.
- **v0.21.0** — last pre-threading-refactor release. Tested on Python 3.13. Drops 3.8.
- **v0.20.0** — performance improvements in connection thread and event loop (#213, #271).

## Open issues that match our failure mode

1. **aiosqlite #316 — "Segmentation Fault Ubuntu 24.04"** (`https://github.com/omnilib/aiosqlite/issues/316`). Exact OS match (Ubuntu 24.04 / Python 3.12). Stack trace identical: `aiosqlite/core.py` `run()` → `threading.py` `_bootstrap_inner`. **Closed with comment "Issue was not caused by aiosqlite" — no version fix identified.** This weakens the version-pin hypothesis.
2. **aiosqlite #371 — "Alembic(SQLAlchemy) migration hangs on exit with aiosqlite ≥0.22.0"** (`https://github.com/omnilib/aiosqlite/issues/371`). Different failure mode (deadlock-on-exit, not segfault) but the reporter writes: *"Downgrading to `aiosqlite<=0.21.0` resolves the issue immediately."* Strong testimony for 0.21.0 as known-good.
3. **Cognee #2717 — "SQLite deadlock during cognify() — still reproducible in v1.0.2"** (`https://github.com/topoteretes/cognee/issues/2717`, **open**, 2026-04-24). Root cause per issue body: *"Cognee's pipeline spawns parallel greenlets that all attempt to write to the same SQLite relational database simultaneously. SQLite supports only one concurrent writer. The greenlets deadlock."* This is **architectural**, not an aiosqlite-version bug — pinning won't fix it.

## Recommendation

**Primary pin: `aiosqlite==0.21.0`.** It's the last pre-threading-refactor release, sits in Cognee's allowed range, and is the only version with first-party "downgrade resolved it" testimony for related (deadlock) failures.

**Conservative fallback: `aiosqlite==0.20.0`** if 0.21.0 doesn't resolve. Both are in range.

**Caveat — Option F may not fix the actual issue.** Two signals push back on a pure version-pin solution:
- aiosqlite #316 (exact OS + stack-trace match) was closed as "not caused by aiosqlite" with no resolution recorded.
- Cognee #2717 attributes the SQLite class of failures to parallel-writer architecture, not the async wrapper.

If a 0.21.0 pin still segfaults on the smoke run, escalate to Option E (swap relational backend to Postgres) rather than pinning further down. Cognee supports Postgres for its relational store via `DB_PROVIDER=postgres` — see `cognee/infrastructure/databases/relational/`.

## Patch sketch

```toml
# pyproject.toml or requirements.txt addendum
aiosqlite==0.21.0  # OptF: pin pre-threading-refactor (issue #371 testimony)
```

```bash
.venv/bin/pip install 'aiosqlite==0.21.0'
.venv/bin/pip check  # confirm cognee + prefect both still satisfied
```

`aiosqlite==0.21.0` released 2025-02-03; well-tested. Patch is reversible by re-pinning to `==0.22.1`.
