#!/usr/bin/env python3
"""
A3 — SessionEnd hook: auto four-store save.

Wired in .claude/settings.json under hooks.SessionEnd. Reads the hook
input from stdin (JSON: session_id, transcript_path, cwd, hook_event_name,
reason). Performs three best-effort steps:

  1. If docs/MANUAL.md changed since the last successful mirror (state file
     at ~/.config/agency-os/.manual_mirror_state), runs
     `python3 scripts/write_manual_mirror.py --force` to push the
     fresh content to the Drive doc.
  2. Writes a compact session-end summary into public.ceo_memory keyed
     `ceo:session_end_<YYYY-MM-DD>`.
  3. Writes a daily_log row into elliot_internal.memories so the next
     session's start-up query finds the trail.

Non-blocking: every step is wrapped in try/except so a failure in one
step does NOT prevent the next from running, and the hook ALWAYS exits
0 (so Claude Code never blocks the SessionEnd transition on us).

Logs go to stderr with the [session-end-hook] prefix so they show in
the hook output without polluting Claude's stdout contract.

Hook input contract (Claude Code SessionEnd, current docs):
  {
    "session_id": "<uuid>",
    "transcript_path": "/path/to/.jsonl",
    "cwd": "/abs/path",
    "hook_event_name": "SessionEnd",
    "reason": "exit|disconnect|...",
  }

We tolerate missing keys.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[session-end-hook] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
MANUAL_PATH = REPO_ROOT / "docs" / "MANUAL.md"
MIRROR_SCRIPT = REPO_ROOT / "scripts" / "write_manual_mirror.py"
STATE_PATH = Path.home() / ".config" / "agency-os" / ".manual_mirror_state"
ENV_FILE = "/home/elliotbot/.config/agency-os/.env"
VENV_PY = "/home/elliotbot/clawd/venv/bin/python3"


# ── Step 1: mirror MANUAL.md if it changed since last mirror ───────────────

def _git_blob_hash(path: Path) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "hash-object", str(path)],
            cwd=str(REPO_ROOT), stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _last_mirrored_blob() -> str | None:
    try:
        if not STATE_PATH.exists():
            return None
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return (data.get("last_fingerprint") or {}).get("git_blob")
    except (OSError, json.JSONDecodeError):
        return None


def maybe_mirror_manual() -> dict:
    """Trigger the mirror script when the working-tree MANUAL.md differs
    from the last mirrored fingerprint. Returns a small report."""
    report = {"manual_present": False, "changed": None, "mirror_invoked": False, "exit_code": None}
    if not MANUAL_PATH.exists():
        logger.info("MANUAL.md not present at %s — skipping mirror step", MANUAL_PATH)
        return report
    report["manual_present"] = True

    current = _git_blob_hash(MANUAL_PATH)
    last    = _last_mirrored_blob()
    changed = bool(current and current != last)
    report["changed"] = changed

    if not changed:
        logger.info("MANUAL.md unchanged since last mirror — no mirror trigger")
        return report

    if not MIRROR_SCRIPT.exists():
        logger.warning("mirror script missing at %s — skipping", MIRROR_SCRIPT)
        return report

    try:
        result = subprocess.run(
            [VENV_PY if Path(VENV_PY).exists() else "python3",
             str(MIRROR_SCRIPT), "--force"],
            cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=20,
        )
        report["mirror_invoked"] = True
        report["exit_code"] = result.returncode
        if result.returncode != 0:
            logger.warning("mirror exited %d. stderr tail: %s",
                           result.returncode, (result.stderr or "")[-200:])
        else:
            logger.info("mirror succeeded — Drive doc updated")
    except subprocess.TimeoutExpired:
        logger.warning("mirror timed out after 20s — best-effort skip")
    except Exception as exc:  # noqa: BLE001
        logger.warning("mirror invocation failed: %s", exc)
    return report


# ── Steps 2 + 3: write to ceo_memory + daily_log ───────────────────────────

def _supabase_dsn() -> str | None:
    """Resolve a postgres DSN for asyncpg.

    Resolution order so the hook works equally well in dev shells, the
    Claude Code SessionEnd runtime, and Railway deploys:
      1. DATABASE_URL  (Railway / generic)
      2. SUPABASE_DB_URL  (some deploy templates use this name)
      3. ENV_FILE → src.config.settings.database_url  (local dev)

    Strips the SQLAlchemy 'postgresql+asyncpg://' prefix because
    asyncpg.connect rejects it.
    """
    raw = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("SUPABASE_DB_URL")
        or ""
    ).strip()
    if raw:
        return raw.replace("postgresql+asyncpg://", "postgresql://")
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
        from src.config.settings import settings  # type: ignore[import-not-found]
        return (settings.database_url or "").replace(
            "postgresql+asyncpg://", "postgresql://"
        ) or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("DSN unavailable (%s) — skipping memory writes", exc)
        return None


def _build_summary(hook_input: dict, mirror_report: dict) -> dict:
    return {
        "session_id":     hook_input.get("session_id"),
        "ended_at":       datetime.now(UTC).isoformat(),
        "reason":         hook_input.get("reason", "unknown"),
        "cwd":            hook_input.get("cwd"),
        "transcript":     hook_input.get("transcript_path"),
        "hook_event":     hook_input.get("hook_event_name", "SessionEnd"),
        "manual_mirror":  mirror_report,
    }


def write_memory(summary: dict) -> dict:
    """Write to ceo_memory + elliot_internal.memories. Returns counts."""
    out = {"ceo_memory_upserted": False, "daily_log_written": False}
    dsn = _supabase_dsn()
    if not dsn:
        return out

    try:
        # Use psycopg2 if asyncpg/asyncio inside a hook runtime is dicey;
        # but asyncpg with asyncio.run is fine — keep one path.
        import asyncio

        import asyncpg

        async def _go():
            conn = await asyncpg.connect(dsn, statement_cache_size=0)
            try:
                key = f"ceo:session_end_{datetime.now(UTC).date().isoformat()}_{os.environ.get('CALLSIGN', 'unknown')}"
                await conn.execute(
                    """
                    INSERT INTO ceo_memory (key, value, updated_at)
                    VALUES ($1, $2::jsonb, NOW())
                    ON CONFLICT (key) DO UPDATE
                      SET value = EXCLUDED.value, updated_at = NOW()
                    """,
                    key, json.dumps(summary),
                )
                out["ceo_memory_upserted"] = True

                content = (
                    f"Session ended ({summary.get('reason')}). "
                    f"MANUAL mirror: changed={summary['manual_mirror'].get('changed')}, "
                    f"invoked={summary['manual_mirror'].get('mirror_invoked')}."
                )
                await conn.execute(
                    """
                    INSERT INTO elliot_internal.memories
                      (id, type, content, metadata, created_at)
                    VALUES (gen_random_uuid(), 'daily_log', $1, $2::jsonb, NOW())
                    """,
                    content, json.dumps(summary),
                )
                out["daily_log_written"] = True
            finally:
                await conn.close()

        asyncio.run(_go())
    except Exception as exc:  # noqa: BLE001
        logger.warning("memory writes failed (non-fatal): %s", exc)
    return out


# ── entry-point ────────────────────────────────────────────────────────────

def read_hook_input() -> dict:
    """Read JSON hook input from stdin. Returns {} on any failure."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not parse hook input from stdin: %s", exc)
        return {}


def main() -> int:
    hook_input = read_hook_input()
    logger.info(
        "SessionEnd fired — session_id=%s reason=%s",
        (hook_input.get("session_id") or "unknown")[:8],
        hook_input.get("reason", "unknown"),
    )

    mirror_report = maybe_mirror_manual()
    summary = _build_summary(hook_input, mirror_report)
    memory_report = write_memory(summary)

    # ── Step 4: Gatekeeper soft-validation (observe-only, never blocks) ────────
    # F3: only fire when a real DIRECTIVE_ID is set — skip for routine sessions
    gatekeeper_report = {"checked": False, "allow": None}
    directive_id = os.environ.get("DIRECTIVE_ID", "")
    try:
        from src.governance.gatekeeper import check_completion_claim, opa_health
        if directive_id and opa_health():
            callsign = os.environ.get("CALLSIGN", "unknown")
            result = check_completion_claim(
                callsign=callsign,
                directive_id=directive_id,
                claim_text=f"Session ended: {summary.get('reason', 'unknown')}",
                evidence=f"$ session_end auto-check\nceo_memory={memory_report.get('ceo_memory_upserted')}, daily_log={memory_report.get('daily_log_written')}",
                target_files=[],
                store_writes=[sw for sw in [
                    {"directive_id": directive_id, "store": "ceo_memory"} if memory_report.get("ceo_memory_upserted") else None,
                    {"directive_id": directive_id, "store": "manual"} if mirror_report.get("mirror_invoked") else None,
                ] if sw is not None],
                frozen_paths=[],
            )
            gatekeeper_report["checked"] = True
            gatekeeper_report["allow"] = result.allow
            if not result.allow:
                logger.warning("Gatekeeper DENY (observe-only): %s", result.reasons)
                try:
                    from src.governance.tg_alert import alert_on_deny
                    import hashlib
                    claim_hash = hashlib.sha256(f"session-end-{callsign}".encode()).hexdigest()[:16]
                    alert_on_deny(
                        callsign=callsign,
                        directive_id=directive_id,
                        reasons=result.reasons,
                        claim_text_sha256_16=claim_hash,
                    )
                except Exception:
                    pass
    except Exception as exc:
        logger.info("Gatekeeper check skipped (non-fatal): %s", exc)

    logger.info(
        "Done. mirror_invoked=%s ceo_memory=%s daily_log=%s gatekeeper_allow=%s",
        mirror_report.get("mirror_invoked"),
        memory_report.get("ceo_memory_upserted"),
        memory_report.get("daily_log_written"),
        gatekeeper_report.get("allow"),
    )
    # Always exit 0 so Claude Code never blocks SessionEnd on us.
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        logger.exception("unexpected hook failure (non-fatal): %s", exc)
        sys.exit(0)
