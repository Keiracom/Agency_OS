# KEI-77 — Cognee Write-Path Diagnostic
**Dave-direct dispatch 2026-05-16, atlas-claimed, READ-ONLY phase**

## Root cause: KEI-44 cgroup cap incompatible with Kuzu graph DB mmap

Cognee internal log `~/.cognee/logs/2026-05-13_20-53-51.log` shows **1,382 consecutive add() failures** on 2026-05-13 21:27, all identical:

```
2026-05-13T21:27:16.003961 [INFO    ] JSON extension already installed or not needed:
  Buffer manager exception: Mmap for size 4294967296 failed.
2026-05-13T21:27:16.006452 [ERROR   ] Failed to initialize Ladybug database:
  Buffer manager exception: Mmap for size 4294967296 failed.
add() failed for mem0_rescued chunk: Buffer manager exception: Mmap for size 4294967296 failed.
...
done: 0 ok / 1382 failed
```

- 4,294,967,296 bytes = **4 GB exact** — Kuzu graph DB ("Ladybug" is the kuzu codename) tries to mmap a 4 GB buffer pool at startup
- `KEI-44` set the cognee.service cgroup `MemoryMax=3 GB` — verified live: `MemoryMax=3221225472`
- Kuzu's 4 GB mmap request exceeds the 3 GB cgroup → `Buffer manager exception` → every add()/cognify() call fails before any work begins
- After the 5/13 batch failure, no caller has retried (manual scripts only — no scheduled writer)
- Last successful write: `cognee_graph_ladybug` main file mtime 2026-05-13 12:14 — matches Dave's "3 days ago"

## Confirmation matrix (all read-only probes)

| Check | Status | Evidence |
|---|---|---|
| cognee.service running | ✓ active 2d | systemctl --user status cognee.service → "active (running) since Thu 2026-05-14 07:51:32 UTC" |
| GEMINI_API_KEY in process env | ✓ present | /proc/1014956/environ contains GEMINI_API_KEY + LLM_PROVIDER=gemini |
| KEI-44 cgroup cap | ✓ 3 GB applied | MemoryMax=3221225472 (exact 3 GB) |
| ENABLE_BACKEND_ACCESS_CONTROL | ✓ false (correct) | env has ENABLE_BACKEND_ACCESS_CONTROL=false |
| Disk space | ✓ 76 GB free | df -h / → 48% used |
| DB file writable | ✓ 644 perms | stat /home/elliotbot/clawd/cognee_data/cognee_db |
| WAL still being written | ✓ today | cognee_graph_ladybug.wal mtime 2026-05-16 11:30 (health-probe noise) |
| Last successful main DB write | ✗ 2026-05-13 12:14 | actual file: .venv/.../databases/cognee_graph_ladybug |
| Last add() attempt | ✗ 2026-05-13 21:27 | 1382 consecutive failures, all "Mmap for size 4294967296 failed" |
| Manual caller | ✗ none called since | scripts/cognee_ingest.py + cognee_smoke.py — last run 5/13 |

## Two distinct DB paths (confusion gap)

- **Live cognee path** (what the service uses): `/home/elliotbot/clawd/Agency_OS/.venv/lib/python3.12/site-packages/cognee/.cognee_system/databases/` — contains `cognee_db` (57 MB, 5/12), `cognee_graph_ladybug` (343 MB, 5/13), `cognee.lancedb/` (5/12)
- **`cognee_data` stale path**: `/home/elliotbot/clawd/cognee_data/` — `cognee_db` 215 MB, 5/13 21:27. Q1 audit cited this; it's NOT what the live service uses. Likely a stale snapshot or earlier-version path.

The 5/13 21:27 timestamp Dave referenced lines up with the **stale path's** mtime, not the live path's. The live path's main graph DB is 9 hours older (5/13 12:14). So "writes stopped 3 days ago" is correct, but the file Dave/we were watching wasn't the canonical one.

## Architecture contradiction

Env declares `GRAPH_DB_PROVIDER=networkx` (in-memory, no mmap), but the live filesystem shows **Kuzu** (`cognee_graph_ladybug`) is what actually got loaded. Either:
1. Cognee 1.0.9 ignores `GRAPH_DB_PROVIDER=networkx` and forces kuzu for the cache layer, OR
2. Kuzu is initialised regardless as part of a persistence layer separate from the user-facing provider choice.

Result: even though we asked for networkx (mmap-free), Kuzu's 4 GB mmap still fires, still fails, still blocks all writes.

## Three fix options (need Dave/Elliot pick)

| Option | Cost | Risk | Blast radius |
|---|---|---|---|
| **A. Bump cgroup MemoryMax 3 GB → 5 GB** | 1-line unit-file edit + `systemctl daemon-reload` + restart | Undoes part of KEI-44 safety budget; cognee can now exceed 3 GB RSS | Just cognee.service |
| **B. Configure Kuzu buffer pool size** | Set `KUZU_BUFFER_POOL_SIZE=1G` (or similar env var) in unit + restart | Need to verify Kuzu actually respects this env, and find the right var name | Just cognee.service |
| **C. Force `GRAPH_DB_PROVIDER=networkx` to actually take effect** | Investigate cognee 1.0.9 source to find why networkx env is ignored; may require code change in cognee fork or upgrade/downgrade | Higher — touching cognee internals or version pin | Cognee whole-app behavior |

Recommend **B then A** as fallback: try Kuzu buffer-pool config first (preserves KEI-44 intent); if Kuzu has no such knob or it doesn't help, fall back to A (cap bump).

**Not recommended:** bypassing KEI-44 entirely (was Dave-ratified for OOM-kill protection).

## What `fix in PR with verbatim before/after write probe` would look like

Once Dave picks A or B:
1. Edit `/home/elliotbot/.config/systemd/user/cognee.service` (cap bump OR add env)
2. `systemctl --user daemon-reload && systemctl --user restart cognee.service`
3. Before-probe: capture `journalctl --user -u cognee.service --since "5 min ago"` showing Mmap error
4. Run `python scripts/cognee_smoke.py` (one add+cognify+search round-trip)
5. After-probe: capture the same journalctl showing no Mmap error + verify `cognee_graph_ladybug` mtime updated to now
6. Open PR with the unit-file diff + before/after journalctl evidence + smoke output

## Open question for Dave/Elliot

Beyond the immediate Mmap fix: **is Cognee still the canonical session memory store, or has KEI-73 (hybrid memory via Weaviate) superseded it?** KEI-76 ("cognee_recall hook on bd claim") suggests Dave still treats Cognee as session memory tier. If yes, KEI-77 fix is needed + a scheduled writer should be wired so writes happen automatically (not just manual cognee_smoke runs). If no, KEI-77 should be closed as "Cognee deprecated, use Weaviate".

KEI-77 atomic-claim verified: `tasks SET status='active', claimed_by='atlas'` returned `id=KEI-77, status=active, claimed_by=atlas`. Holding on fix-build until Dave/Elliot pick A vs B (or close KEI-77 as deprecated).
