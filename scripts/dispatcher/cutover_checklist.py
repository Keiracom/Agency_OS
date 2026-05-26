#!/usr/bin/env python3
"""cutover_checklist.py — §7 piece 6 operational tooling (Agency_OS-7uy6).

Generates a per-callsign markdown cutover checklist with CURRENT systemd
unit names (discovered at runtime via `systemctl --user list-unit-files`
OR via direct directory listing of `~/.config/systemd/user/`). Operator
runs this on cutover-day to get a fresh checklist that reflects whatever
units are actually installed at that moment (not a frozen list that may
have drifted).

Per PR #1140 §7 piece 6: "Cutover-day checklist generator — per-callsign
markdown checklist with current systemd unit names. ~50 LoC. P3
(operational tooling)."

Cutover flow per PR #1140 §6 Stage 4 (destructive cutover):
1. Stop the old per-callsign inbox-watcher service
2. Install the new keiracom-dispatcher@<callsign>.service (PR #1180 template)
3. Start the dispatcher
4. Verify the dispatcher is active + the inbox flow works
5. (rollback) re-enable the old inbox-watcher if needed

CLI:
  python3 scripts/dispatcher/cutover_checklist.py --callsign atlas
  python3 scripts/dispatcher/cutover_checklist.py --callsign atlas --output /tmp/atlas.md
  python3 scripts/dispatcher/cutover_checklist.py --all  # emit all 7 callsigns
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"
CALLSIGNS = ("elliot", "aiden", "max", "atlas", "orion", "scout", "nova")


def discover_callsign_units(
    callsign: str, *, systemd_dir: Path = DEFAULT_SYSTEMD_USER_DIR
) -> list[str]:
    """Return sorted list of currently-installed .service units whose name
    starts with `<callsign>-`. Filters out disabled-rename suffixes like
    `.disabled-...` so the checklist reflects the active surface."""
    if not systemd_dir.exists():
        return []
    units: list[str] = []
    prefix = f"{callsign}-"
    for path in systemd_dir.iterdir():
        name = path.name
        if name.startswith(prefix) and name.endswith(".service") and ".disabled" not in name:
            units.append(name)
    return sorted(units)


def render_checklist(callsign: str, units: list[str]) -> str:
    """Markdown checklist body. ~30 LoC of template."""
    if not units:
        units_block = "_(no current per-callsign units discovered — verify systemd-user-dir)_"
    else:
        units_block = "\n".join(f"- `{u}`" for u in units)

    return f"""# Cutover-day checklist — `{callsign}`

**Generated:** runtime (`scripts/dispatcher/cutover_checklist.py --callsign {callsign}`)
**bd:** Agency_OS-7uy6 (§7 piece 6)
**Cutover stage:** PR #1140 §6 Stage 4 (destructive cutover from tmux-watcher → ephemeral dispatcher)

## Current `{callsign}`-prefixed systemd units (live at generation time)

{units_block}

## Step 1 — Pre-cutover snapshot

```bash
# Capture current state for rollback evidence
systemctl --user list-units --type=service --state=active | grep '^{callsign}-' \\
  > ~/cutover_{callsign}_pre.txt
journalctl --user -u '{callsign}-*' --since '1 hour ago' \\
  > ~/cutover_{callsign}_journal_pre.log
```

## Step 2 — Stop the old per-callsign inbox-watcher

```bash
systemctl --user stop {callsign}-inbox-watcher.service
systemctl --user is-active {callsign}-inbox-watcher.service  # expect: inactive
```

## Step 3 — Install + start the dispatcher (PR #1180 template + PR #1188 binary)

```bash
# Install (idempotent) per PR #1180 installer
bash scripts/install_keiracom_dispatcher.sh {callsign}

# Start the new dispatcher
systemctl --user start keiracom-dispatcher@{callsign}.service
systemctl --user is-active keiracom-dispatcher@{callsign}.service  # expect: active
```

## Step 4 — Verify

```bash
# Dispatcher process running + reading inbox
pgrep -af 'keiracom-dispatcher.*{callsign}'

# Drop a synthetic dispatch envelope + watch the dispatcher pick it up
echo '{{"type":"task_dispatch","from":"elliot","brief":"cutover-smoke"}}' \\
  > /tmp/telegram-relay-{callsign}/inbox/cutover_smoke_$(date +%s).json
journalctl --user -u keiracom-dispatcher@{callsign}.service --follow
# Look for the dispatcher reading the envelope + spawning a Claude subprocess
```

## Step 5 — (rollback if cutover fails)

```bash
systemctl --user stop keiracom-dispatcher@{callsign}.service
systemctl --user disable keiracom-dispatcher@{callsign}.service
systemctl --user start {callsign}-inbox-watcher.service
systemctl --user is-active {callsign}-inbox-watcher.service  # expect: active
```
"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--callsign", help="single callsign")
    g.add_argument("--all", action="store_true", help="emit checklist for all 7 callsigns")
    p.add_argument("--output", type=Path, help="write to file (single-callsign mode)")
    p.add_argument("--systemd-dir", type=Path, default=DEFAULT_SYSTEMD_USER_DIR)
    args = p.parse_args(argv)

    if args.all:
        for cs in CALLSIGNS:
            units = discover_callsign_units(cs, systemd_dir=args.systemd_dir)
            print(render_checklist(cs, units))
            print("\n---\n")
        return 0

    units = discover_callsign_units(args.callsign, systemd_dir=args.systemd_dir)
    body = render_checklist(args.callsign, units)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
