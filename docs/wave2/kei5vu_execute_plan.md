# Agency_OS-5vu Execute Plan (post-Track-1-seal)

**Author:** Aiden
**Status:** Draft — design-note only. NO cp -a or env-flip in this branch.
**Branch:** `aiden/kei5vu-execute-plan-draft`
**Depends on:**
- PR #827 KEI-5vu scaffold merged (LIVE @ 9feaa9c6 — `scripts/migrate_cognee_system_root.py` + safety gate).
- Stream 2 sealed (DONE @ 2026-05-13T08:14 — `done: 1678 ok / 0 failed`).
- Stream 3+4 ingest sealed (IN PROGRESS — Max PID 1620293, ETA 2-3h per 2026-05-13T08:37 launch).
- VQ1 passed (DONE per Max ts ~1778660800).
- VQ2 / VQ3 / VQ4 cross-stream passed (PENDING — Max owns).
- Max re-FINAL on PR #827 with explicit Stream-2-VQ4-pass evidence (PENDING).

This document captures the execution checklist so the post-VQ4 PR is a quick
ship instead of a fresh design pass. The script (`migrate_cognee_system_root.py`)
already exists; this plan documents the operational steps + oracles + rollback.

## 1. Pre-flight checks (must ALL pass before cp -a)

1. **Track 1 sealed.** Confirm by:
   - `git log origin/main --oneline | head` shows `[MAX]` Stream 3+4 close commit OR Max [TASK-COMPLETE] post in `#execution`.
   - VQ1-4 all pass status from Max (#execution).
   - Max re-FINAL on PR #827 with explicit Stream-2-VQ4-pass evidence.
2. **No active cognee process.** Verify via the script's own gate:
   ```
   python3 scripts/migrate_cognee_system_root.py --dry-run
   ```
   Must print `No active cognee processes — migration would be safe NOW.` (NOT `REFUSE`).
3. **Target path does not exist.** `ls /home/elliotbot/.cognee_system` must return ENOENT.
4. **Disk space.** `df -h /home/elliotbot` must show ≥ 3× source size free (1.5 GB source → ≥ 4.5 GB free).
5. **Worktree clean.** `git status` in `/home/elliotbot/clawd/Agency_OS-aiden` shows no uncommitted changes (the `.env` edit lives OUTSIDE the repo at `/home/elliotbot/.config/agency-os/.env` and is operator-edited separately — not a worktree concern).
6. **systemd env-loader audit.** Per Max review ts ~1778663400: services not loading from `/home/elliotbot/.config/agency-os/.env` (i.e. using inline `Environment=` instead of `EnvironmentFile=`) need explicit `SYSTEM_ROOT_DIRECTORY=` added to their unit. Audit per-service:
   ```
   systemctl --user cat aiden-relay-watcher.service atlas-relay-watcher.service orion-relay-watcher.service scout-relay-watcher.service 2>/dev/null | grep -E '^Environment(File)?='
   ```
   Services using `EnvironmentFile=...env` need no unit edit. Services using `Environment=` inline need `SYSTEM_ROOT_DIRECTORY=/home/elliotbot/.cognee_system` added.

## 2. cp -a invocation + size-verify oracle

```bash
python3 scripts/migrate_cognee_system_root.py --execute \
    --dst /home/elliotbot/.cognee_system
```

Script prints:
- `Copying <src> → <dst> (<N> bytes)...`
- `OK: <N> bytes copied. Source preserved at <src> (delete manually after verify).`

**Oracle 1 (size match):** script's internal check `dst_size == src_size` (already in PR #827).

**Oracle 2 (manual verify):**
```
du -sb /home/elliotbot/clawd/Agency_OS/.venv/lib/python3.12/site-packages/cognee/.cognee_system
du -sb /home/elliotbot/.cognee_system
diff <(cd <src> && find . -type f | sort) <(cd <dst> && find . -type f | sort)
```

Both must show same totals + zero diff output.

## 3. .env diff for SYSTEM_ROOT_DIRECTORY

Add to `/home/elliotbot/.config/agency-os/.env`:

```
SYSTEM_ROOT_DIRECTORY=/home/elliotbot/.cognee_system
```

Cognee reads this via `cognee.base_config.system_root_directory` (Pydantic BaseSettings env-mapping at `base_config.py:13`).

**Restart required for any long-running Cognee-using service / process** (per Max review ts ~1778663300):
- `uvicorn cognee.api.client` server (PID 3952420 as of 2026-05-13, running since May 12) — `pkill -f "uvicorn cognee.api.client"` then re-launch.
- Per-callsign inbox-watcher services that invoke `cognee_recall.py` at dispatch-enrich time — restart via `systemctl --user restart <callsign>-inbox-watcher.service` (verify via `systemctl --user list-units --plain | grep cognee`).
- `aiden-relay-watcher.service` (if it imports cognee — verify via `systemctl --user cat aiden-relay-watcher.service`).
- Any cognee_recall.py invocations in agent inbox watchers.

## 4. Post-migrate smoke probe

```bash
python3 /home/elliotbot/clawd/Agency_OS-aiden/scripts/cognee_recall.py \
    --query "Agency OS Manual SSOT directive"
```

Expected: non-zero top-k chunks returned with `belongs_to_set` tags matching governance corpus (`source:ceo_memory` / `source:agent_memories`). Verifies that:
- Cognee can open the relocated Lance dataset.
- Stream 1 corpus is intact post-cp.
- Embedding + search paths still wire correctly.

If smoke returns zero hits OR errors out → IMMEDIATE rollback (§5).

## 5. Rollback recipe

If smoke fails OR Stream 3+4 must resume but can't open relocated dataset:

```bash
# 1. Revert .env edit
sed -i '/^SYSTEM_ROOT_DIRECTORY=/d' /home/elliotbot/.config/agency-os/.env

# 2. Leave the copied tree at /home/elliotbot/.cognee_system in place
#    (Cognee will fall back to venv default — original source preserved per cp -a).

# 3. Restart any services touched in §3.

# 4. Re-run smoke to confirm cognee_recall works against venv-resident original.
```

Source tree is NEVER deleted by the migration script — `shutil.copytree` preserves
the source. Rollback is just an env-flip reversal.

## 6. PR sequence (post-VQ4)

1. Branch: `aiden/kei5vu-execute-postvq4` off main.
2. Single commit: `.env` edit (operator does this; PR documents instructions but doesn't include `.env` itself per `gitignore`).
3. Run §2 invocation locally; capture verbatim output.
4. Run §4 smoke; capture verbatim output.
5. PR body: this design note + verbatim outputs from steps 3 & 4.
6. Dual-CTO concur (Max + Elliot) + Dave restart-readiness ack.
7. Self-merge on triple-bot concur + Max re-FINAL.

## 7. Open questions — answered (Max review ts ~1778663300)

- **Q1: Does Stream 3+4 require the relocated path during ingest, or is cutover post-ingest sufficient?**
  Max: cutover POST-INGEST ONLY. Stream 3+4 launched against venv-resident path; mid-ingest path-flip would either torn-cp with active writes OR diverge Stream writes from env-pointed path. Pre-flight check 2 ("No active cognee process") enforces this.
- **Q2: Other Cognee-using consumers (besides cognee_recall)?**
  Max: yes — uvicorn cognee.api.client server (PID 3952420), per-callsign inbox-watcher services invoking cognee_recall.py. Both folded into §3 restart list.
- **Q3: Should `SYSTEM_ROOT_DIRECTORY` be in systemd unit `Environment=` lines for services outside the agency-os/.env loader?**
  Max: yes for services not loading from `.env`. Folded into pre-flight check 6 (audit via `systemctl --user cat <unit> | grep -E '^Environment(File)?='`). Services using `EnvironmentFile=` need no unit edit; services using `Environment=` inline need explicit `SYSTEM_ROOT_DIRECTORY=...` added.
