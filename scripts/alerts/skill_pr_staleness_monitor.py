#!/usr/bin/env python3
"""skill_pr_staleness_monitor.py — KEI-11 Outcome 2: skill-PR 48h breach alert.

Per Linear KEI-11 outcome 2:
  "Skill PR review pipeline defined and mechanically enforced (48h breach alert)"

Sweeps open GitHub PRs that touch src/skill_gen/, posts a Slack alert to
#execution for any PR whose age exceeds SKILL_PR_BREACH_HOURS (default 48h).
Per-PR dedupe: one alert per PR per SKILL_PR_DEDUPE_HOURS (default 24h).

Best-effort: a Slack-post failure does NOT raise. The monitor's job is
breach reporting; failures in reporting must not cascade.

Wires via timer: infra/alerts/agency-os-skill-pr-staleness-monitor.timer
(OnCalendar *:0/15 = every 15 min, sufficient granularity for 48h breach).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("skill_pr_staleness_monitor")

EXECUTION_CHANNEL = "C0B3QB0K1GQ"
SKILL_PR_BREACH_HOURS = 48
SKILL_PR_DEDUPE_HOURS = 24
SKILL_GEN_PATH_PREFIX = "src/skill_gen/"
DEFAULT_STATE_PATH = Path("/tmp/agency-os-skill-pr-staleness-state.json")
GH_REPO = os.environ.get("GH_REPO", "Keiracom/Agency_OS")


def gh_list_open_prs() -> list[dict]:
    """Return open PRs as a list of dicts (number, title, headRefName, createdAt,
    author, files). Empty list on any failure."""
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                GH_REPO,
                "--state",
                "open",
                "--limit",
                "100",
                "--json",
                "number,title,headRefName,createdAt,author,files,url",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.warning("gh pr list invocation failed: %s", exc)
        return []
    if result.returncode != 0:
        logger.warning("gh pr list returned %d: %s", result.returncode, result.stderr)
        return []
    try:
        return json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        logger.warning("gh pr list JSON parse failed: %s", exc)
        return []


def touches_skill_gen(pr: dict) -> bool:
    """True if any of the PR's files is under src/skill_gen/."""
    for f in pr.get("files") or []:
        path = f.get("path", "")
        if path.startswith(SKILL_GEN_PATH_PREFIX):
            return True
    return False


def pr_age_hours(pr: dict, now: datetime | None = None) -> float:
    now = now or datetime.now(UTC)
    created = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
    return (now - created).total_seconds() / 3600


def load_state(state_path: Path) -> dict[str, str]:
    """Return {pr_number_str: last_alerted_iso} or {} on miss/corrupt."""
    if not state_path.is_file():
        return {}
    try:
        return json.loads(state_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("state file unreadable, treating as empty: %s", exc)
        return {}


def save_state(state_path: Path, state: dict[str, str]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True))


def should_alert(pr_number: int, state: dict[str, str], now: datetime | None = None) -> bool:
    """True if this PR has not been alerted within the dedupe window."""
    now = now or datetime.now(UTC)
    last = state.get(str(pr_number))
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
    except ValueError:
        return True
    return (now - last_dt) >= timedelta(hours=SKILL_PR_DEDUPE_HOURS)


def format_alert(breached: list[dict]) -> str:
    lines = [
        f":warning: *Skill PR staleness breach* — {len(breached)} PR(s) > "
        f"{SKILL_PR_BREACH_HOURS}h old touching `src/skill_gen/`"
    ]
    for pr in breached:
        age = pr_age_hours(pr)
        author = (pr.get("author") or {}).get("login", "unknown")
        lines.append(
            f"  • #{pr['number']} `{pr['headRefName']}` — {age:.1f}h by @{author} — {pr['url']}"
        )
    lines.append(f"_KEI-11 outcome 2 enforcement. Dedupe window: {SKILL_PR_DEDUPE_HOURS}h._")
    return "\n".join(lines)


def post_to_slack(text: str, channel: str = EXECUTION_CHANNEL) -> bool:
    """Best-effort Slack post. Returns True on success, False otherwise."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        logger.warning("SLACK_BOT_TOKEN not set — cannot post skill-PR breach alert")
        return False
    payload = json.dumps(
        {
            "channel": channel,
            "text": text,
            "username": "SkillPRStaleness",
            "icon_emoji": ":hourglass:",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read())
            return bool(body.get("ok"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Slack post failed: %s", exc)
        return False


def run_once(
    state_path: Path | None = None,
    *,
    gh_fn=None,
    post_fn=None,
    now: datetime | None = None,
) -> dict:
    """One sweep. Returns {scanned, skill_prs, breached, alerted}.

    All side-effects (gh, slack, state file) are injectable for tests.
    """
    state_path = state_path or DEFAULT_STATE_PATH
    gh_fn = gh_fn or gh_list_open_prs
    post_fn = post_fn or post_to_slack
    now = now or datetime.now(UTC)

    prs = gh_fn()
    skill_prs = [p for p in prs if touches_skill_gen(p)]
    breached = [p for p in skill_prs if pr_age_hours(p, now=now) >= SKILL_PR_BREACH_HOURS]

    state = load_state(state_path)
    to_alert = [p for p in breached if should_alert(p["number"], state, now=now)]

    posted = False
    if to_alert:
        posted = post_fn(format_alert(to_alert))
        if posted:
            for p in to_alert:
                state[str(p["number"])] = now.isoformat()
            save_state(state_path, state)
    return {
        "scanned": len(prs),
        "skill_prs": len(skill_prs),
        "breached": len(breached),
        "alerted": len(to_alert) if posted else 0,
    }


def main() -> int:
    summary = run_once()
    logger.info("skill_pr_staleness_monitor: %s", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
