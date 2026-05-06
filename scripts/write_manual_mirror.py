#!/usr/bin/env python3
"""
write_manual_mirror.py — Mirror docs/MANUAL.md to Google Drive doc.

Best-effort: logs Drive failures but does NOT raise or block directive
completion. Primary store is docs/MANUAL.md (repo). Google Doc is a mirror.

M11 — staleness check:
    Before mirroring, the script compares the current MANUAL.md fingerprint
    (git blob hash, falling back to mtime + size) against the value stored
    in scripts/.manual_mirror_state. If they match the script EXITS with
    code 2 — the four-store-save check then surfaces the staleness as a
    failure rather than silently re-mirroring identical content.

    Use --force to mirror anyway (e.g. after a Drive doc was manually
    truncated or when re-syncing a known-good copy).

Usage:
    python scripts/write_manual_mirror.py            # checks staleness
    python scripts/write_manual_mirror.py --force    # bypass staleness check
    python scripts/write_manual_mirror.py --check    # check only; no Drive write

Exit codes:
    0  — mirrored successfully (or Drive failure logged best-effort)
    2  — refused: MANUAL.md unchanged since last mirror; pass --force to override
    3  — MANUAL.md missing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

GOOGLE_DOC_ID = os.environ.get(
    "GOOGLE_MANUAL_DOC_ID", "1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho"
)
SERVICE_ACCOUNT_FILE = "/home/elliotbot/google-service-account.json"
MANUAL_PATH = Path(__file__).parent.parent / "docs" / "MANUAL.md"

# M11-2 — state file lives in the shared agency-os config dir, not in any
# single worktree. All clones (atlas/elliot/main + future) share one source
# of truth for "when was MANUAL.md last mirrored". Falls back to the legacy
# per-worktree location during transition for callers who haven't migrated.
_SHARED_STATE_DIR = Path.home() / ".config" / "agency-os"
STATE_PATH = _SHARED_STATE_DIR / ".manual_mirror_state"
_LEGACY_STATE_PATH = Path(__file__).parent / ".manual_mirror_state"

SCOPES = ["https://www.googleapis.com/auth/documents"]
HOOKS_PATH = ".githooks"
REPO_ROOT = Path(__file__).resolve().parent.parent


# ─── fingerprinting ────────────────────────────────────────────────────────


def _git_blob_hash(path: Path) -> str | None:
    """Return the git blob hash of `path`. None if not in a git repo."""
    try:
        out = subprocess.check_output(
            ["git", "hash-object", str(path)],
            cwd=str(path.parent),
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _content_hash(path: Path) -> str:
    """sha256 of file bytes — fallback when git is unavailable."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def fingerprint(path: Path) -> dict:
    """Return a stable fingerprint dict for the file. Prefers git blob
    hash so the check is robust against mtime touches that don't change
    content; falls back to content sha256 + mtime + size."""
    stat = path.stat()
    fp: dict = {
        "path": str(path),
        "size": stat.st_size,
        "mtime": stat.st_mtime_ns,
        "sha256": _content_hash(path),
    }
    blob = _git_blob_hash(path)
    if blob:
        fp["git_blob"] = blob
    return fp


def load_state() -> dict:
    """Load state from the shared config dir. One-shot migrate from the
    legacy per-worktree path if the shared file is missing but the
    legacy file exists (so the first run after this fix doesn't re-mirror
    unnecessarily)."""
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    if _LEGACY_STATE_PATH.exists():
        try:
            data = json.loads(_LEGACY_STATE_PATH.read_text(encoding="utf-8"))
            logger.info("M11-2 — migrating legacy state %s → %s", _LEGACY_STATE_PATH, STATE_PATH)
            save_state(data)
            return data
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def is_unchanged(current: dict, last: dict) -> bool:
    """Equal when the most-stable available identifier matches.
    Prefers git blob hash; falls back to sha256."""
    if "git_blob" in current and "git_blob" in last:
        return current["git_blob"] == last["git_blob"]
    return current.get("sha256") == last.get("sha256")


# ─── M11-1 — hook installation ─────────────────────────────────────────────


def _current_hooks_path() -> str | None:
    """Return the value of `git config core.hooksPath` for REPO_ROOT,
    or None if unset / git unavailable."""
    try:
        out = subprocess.check_output(
            ["git", "config", "--get", "core.hooksPath"],
            cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def install_hook() -> int:
    """Run `git config core.hooksPath .githooks` for REPO_ROOT. Verifies
    that the post-commit hook exists + is executable. Returns 0 on
    success, non-zero otherwise."""
    hook = REPO_ROOT / HOOKS_PATH / "post-commit"
    if not hook.exists():
        logger.error("post-commit hook missing at %s", hook)
        return 4
    if not os.access(str(hook), os.X_OK):
        logger.warning("post-commit hook not executable — fixing chmod +x")
        try:
            hook.chmod(hook.stat().st_mode | 0o111)
        except OSError as exc:
            logger.error("chmod failed: %s", exc)
            return 4
    try:
        subprocess.check_call(
            ["git", "config", "core.hooksPath", HOOKS_PATH],
            cwd=str(REPO_ROOT),
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.error("git config failed: %s", exc)
        return 4
    logger.info("post-commit hook installed — core.hooksPath=%s", HOOKS_PATH)
    logger.info("Future MANUAL.md commits will auto-mirror to Drive.")
    return 0


def warn_if_hook_not_installed() -> None:
    """Emit a single non-fatal warning when core.hooksPath is not
    pointing at .githooks — most commits will then bypass the auto-mirror."""
    current = _current_hooks_path()
    if current == HOOKS_PATH:
        return
    if current is None:
        logger.warning(
            "post-commit hook not installed — run `python scripts/write_manual_mirror.py "
            "--install` (or `git config core.hooksPath .githooks`) so MANUAL.md commits "
            "auto-mirror.",
        )
    else:
        logger.warning(
            "core.hooksPath = %s (not .githooks). The M11 auto-mirror hook will "
            "NOT fire on commits. Run --install to switch.",
            current,
        )


# ─── mirror impl ───────────────────────────────────────────────────────────


def read_manual() -> str:
    if not MANUAL_PATH.exists():
        raise FileNotFoundError(f"MANUAL.md not found at {MANUAL_PATH}")
    return MANUAL_PATH.read_text(encoding="utf-8")


def mirror_to_drive(content: str) -> None:
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        logger.error(
            "google-api-python-client not installed. "
            "Run: pip install google-api-python-client google-auth"
        )
        logger.warning(
            "Mirror skipped — Drive write unavailable. Primary store (docs/MANUAL.md) is up to date."
        )
        return

    if not Path(SERVICE_ACCOUNT_FILE).exists():
        logger.error(f"Service account not found: {SERVICE_ACCOUNT_FILE}")
        logger.warning("Mirror skipped. Primary store (docs/MANUAL.md) is up to date.")
        return

    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build("docs", "v1", credentials=creds)

        doc = service.documents().get(documentId=GOOGLE_DOC_ID).execute()
        body_content = doc.get("body", {}).get("content", [])
        end_index = body_content[-1].get("endIndex", 2)

        requests = []
        if end_index > 2:
            requests.append(
                {"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index - 1}}}
            )
        if requests:
            service.documents().batchUpdate(
                documentId=GOOGLE_DOC_ID, body={"requests": requests}
            ).execute()

        doc = service.documents().get(documentId=GOOGLE_DOC_ID).execute()
        body_content = doc.get("body", {}).get("content", [])
        end_index = body_content[-1].get("endIndex", 2)

        service.documents().batchUpdate(
            documentId=GOOGLE_DOC_ID,
            body={
                "requests": [
                    {"insertText": {"location": {"index": end_index - 1}, "text": content}}
                ]
            },
        ).execute()

        doc = service.documents().get(documentId=GOOGLE_DOC_ID).execute()
        body_content = doc.get("body", {}).get("content", [])
        total_chars = sum(
            len(e.get("textRun", {}).get("content", ""))
            for b in body_content
            for e in b.get("paragraph", {}).get("elements", [])
        )
        logger.info(f"Mirror written successfully. Google Doc: {total_chars} chars.")

    except Exception as exc:
        logger.error(f"Drive mirror failed: {exc}")
        logger.warning(
            "Primary store (docs/MANUAL.md) is up to date. "
            "Google Doc mirror will be stale until next save-trigger directive."
        )


# ─── entrypoint ────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Mirror docs/MANUAL.md to Google Drive.")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Mirror even if MANUAL.md hasn't changed since last mirror.",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Print staleness verdict and exit. No Drive write.",
    )
    ap.add_argument(
        "--install",
        action="store_true",
        help="Install the post-commit hook (git config core.hooksPath .githooks) and exit.",
    )
    args = ap.parse_args(argv)

    # M11-1 — handle install first; it doesn't need MANUAL.md.
    if args.install:
        return install_hook()

    # M11-1 — startup advisory if the hook isn't wired (non-fatal).
    warn_if_hook_not_installed()

    if not MANUAL_PATH.exists():
        logger.error(f"MANUAL.md not found at {MANUAL_PATH}")
        return 3

    current_fp = fingerprint(MANUAL_PATH)
    state = load_state()
    last_fp = state.get("last_fingerprint", {})

    unchanged = bool(last_fp) and is_unchanged(current_fp, last_fp)

    if args.check:
        if unchanged:
            logger.warning(
                "MANUAL.md UNCHANGED since last mirror "
                "(git_blob=%s sha=%s) — staleness check would refuse mirror.",
                current_fp.get("git_blob", "n/a"),
                current_fp["sha256"][:12],
            )
            return 2
        logger.info("MANUAL.md CHANGED since last mirror — mirror would proceed.")
        return 0

    if unchanged and not args.force:
        logger.error(
            "MANUAL.md unchanged since last mirror "
            "(git_blob=%s, sha=%s). Refusing to re-mirror identical content. "
            "Pass --force to override (e.g. recovering from a manual Drive edit).",
            current_fp.get("git_blob", "n/a"),
            current_fp["sha256"][:12],
        )
        return 2

    if args.force and unchanged:
        logger.warning("--force: re-mirroring even though MANUAL.md is unchanged.")

    logger.info(f"Reading MANUAL.md from {MANUAL_PATH}")
    content = read_manual()
    logger.info(f"MANUAL.md: {len(content)} chars")
    logger.info("Mirroring to Google Drive...")
    mirror_to_drive(content)

    # Persist the new fingerprint regardless of Drive success — Drive failures
    # are best-effort and we don't want a stuck DRIVE outage to permanently
    # block the staleness check.
    state["last_fingerprint"] = current_fp
    state["last_mirrored_at"] = subprocess.check_output(["date", "-Iseconds"]).decode().strip()
    save_state(state)
    logger.info(f"State persisted to {STATE_PATH}")
    logger.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
