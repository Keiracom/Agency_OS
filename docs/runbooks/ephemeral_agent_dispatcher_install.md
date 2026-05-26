# Ephemeral-Agent Dispatcher — Install Runbook

**Filed under:** Agency_OS-awec (§7 piece 4 of PR #1140 ephemeral-agent scoping)
**Status:** SCAFFOLD ONLY — runtime activation gated on §7 pieces 1 + 5
**Owner:** scout (author), Elliot (orchestrator merge)

## What this is

Per-callsign systemd template unit `keiracom-dispatcher@<callsign>.service`. One template file, instantiated 7 times (one per callsign: elliot / aiden / max / atlas / orion / scout / nova).

This is the scaffold side of the §7 piece-4 dispatch. The template references a dispatcher binary at `scripts/dispatcher/dispatcher_main.py` which is filed as §7 piece 1 (a separate P1 KEI not yet shipped). The template installs cleanly today but **will not start until piece 1 + 5 binaries are in place** — `ExecStartPre=/usr/bin/test -x …` blocks startup until then.

## Files in this PR

| Path | Purpose | LoC |
|---|---|---:|
| `systemd/keiracom-dispatcher@.service` | template unit, instantiated by `@<callsign>` | 47 |
| `systemd/dispatcher-env/dispatcher-<callsign>.env` × 7 | per-callsign overrides (worktree + inbox + outbox + tier) | ~12 each, 84 total |
| `scripts/install_keiracom_dispatcher.sh` | install / uninstall script (idempotent) | ~110 |
| `docs/runbooks/ephemeral_agent_dispatcher_install.md` | this runbook | ~80 |

## Install (post-piece-1 activation)

After §7 pieces 1 + 5 land (`scripts/dispatcher/dispatcher_main.py` + the spawn-with-context composer library it imports), an operator runs:

```bash
# Install template + env files + enable all 7 callsigns:
bash scripts/install_keiracom_dispatcher.sh

# OR install + enable for a subset:
bash scripts/install_keiracom_dispatcher.sh elliot scout

# OR install but don't enable yet (just stage):
bash scripts/install_keiracom_dispatcher.sh --no-enable
```

The script:
1. Copies the template to `~/.config/systemd/user/keiracom-dispatcher@.service`
2. Copies per-callsign env files to `~/.config/agency-os/dispatcher-<callsign>.env`
3. Runs `systemctl --user daemon-reload`
4. Runs `systemctl --user enable keiracom-dispatcher@<callsign>.service` for each callsign (NOTE: `enable` not `enable --now` — the unit is enabled but not started until you `systemctl --user start ...` manually, since the binary may not exist at install time)

## Start (after binaries land)

Once `scripts/dispatcher/dispatcher_main.py` is in place and executable, start each callsign:

```bash
for c in elliot aiden max atlas orion scout nova; do
    systemctl --user start keiracom-dispatcher@${c}.service
done
systemctl --user status keiracom-dispatcher@elliot.service  # spot-check
```

## Verify

```bash
# Check unit is loaded + enabled
systemctl --user is-enabled keiracom-dispatcher@elliot.service     # → enabled

# Check unit is running (once binary lands)
systemctl --user is-active keiracom-dispatcher@elliot.service      # → active

# Tail per-callsign log
tail -f /home/elliotbot/clawd/logs/keiracom-dispatcher-elliot.log
```

## Uninstall

```bash
# Disable + remove for a specific callsign:
bash scripts/install_keiracom_dispatcher.sh --uninstall elliot

# Disable + remove for all 7:
bash scripts/install_keiracom_dispatcher.sh --uninstall
```

## Why template-unit + per-callsign env files (not 7 separate units)

systemd template instance units (`<name>@.service`) are the canonical pattern for "same service shape, parameterised by an instance string". One file describes the contract; 7 enablements bring 7 instances online. Saves 6× file duplication + makes a future "rename a callsign" or "add an 8th callsign" a 1-line change.

Per-callsign env files capture the only things that legitimately differ per callsign:
- `DISPATCHER_WORKTREE_PATH` (elliot's worktree is `/home/elliotbot/clawd/Agency_OS` with no suffix; the clones have `-<callsign>` suffixes)
- `DISPATCHER_INBOX_DIR` / `DISPATCHER_OUTBOX_DIR` (per-callsign telegram-relay paths)
- `DISPATCHER_TIER` (orchestrator / deliberator / worker / research — for piece 1's role-gating)

Everything else (`CALLSIGN`, log path) derives from `%i` in the template.

## Dependency graph

```
§7 piece 4 (THIS PR)         §7 piece 1 (P1 KEI, not yet filed)
  template + env files          scripts/dispatcher/dispatcher_main.py
        |                                |
        +--------- ExecStartPre ---------+
                  blocks until piece 1 ships

§7 piece 5 (P1 KEI, not yet filed)
  spawn-with-context composer library (imported by piece 1)
        |
        +---- imported by piece 1 binary at runtime
```

This PR is unblocked-by-design — landing it does NOT require pieces 1 or 5 to exist. Operators can install the unit + env files today; the unit will refuse to start until the binary lands.

## Acceptance criteria

- [x] Template `.service` file parses cleanly (manual + `systemd-analyze --user verify` post-install)
- [x] 7 per-callsign env files exist with correct paths
- [x] Install script is idempotent + supports `--no-enable` + `--uninstall`
- [x] Runbook covers install / start / verify / uninstall
- [ ] (post-pieces-1+5) `systemctl --user start keiracom-dispatcher@elliot.service` → active
- [ ] (post-pieces-1+5) Dispatcher reads inbox JSON + spawns ephemeral Claude per design §3
