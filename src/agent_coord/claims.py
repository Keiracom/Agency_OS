"""
File-claim system for multi-agent coordination.

Claims are keyed by repo-relative path (SHA-256 hash, first 16 hex chars) so both
worktrees (Agency_OS and Agency_OS-aiden) see the same claim for the same file.

All claim files are stored under CLAIMS_DIR as JSON with atomic tmp+rename writes.
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

CLAIMS_DIR = "/tmp/agent-claims"
DEFAULT_TTL_SECONDS = 900  # 15 minutes

os.makedirs(CLAIMS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _path_to_key(repo_relative_path: str) -> str:
    """Hash repo-relative path → first 16 hex chars."""
    return hashlib.sha256(repo_relative_path.encode()).hexdigest()[:16]


def _atomic_write(path: str, payload: dict) -> None:
    """Write JSON to path.tmp.<uuid4> then rename into place."""
    tmp_path = f"{path}.tmp.{uuid.uuid4().hex}"
    with open(tmp_path, "w") as f:
        json.dump(payload, f)
    os.rename(tmp_path, path)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts_str: str) -> datetime:
    """Parse ISO-8601 UTC string → aware datetime."""
    dt = datetime.fromisoformat(ts_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _claim_path(repo_relative_path: str) -> str:
    return os.path.join(CLAIMS_DIR, _path_to_key(repo_relative_path) + ".json")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def claim(
    repo_relative_path: str,
    callsign: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    branch: str | None = None,
) -> bool:
    """
    Attempt to claim a file.

    Returns True if the claim was acquired or refreshed (re-entrant for same callsign).
    Returns False if the file is actively claimed by a different callsign.
    """
    claim_file = _claim_path(repo_relative_path)
    now = _now_utc()

    try:
        with open(claim_file) as f:
            existing = json.load(f)
        holder = existing.get("callsign")
        ts = _parse_ts(existing["timestamp_utc"])
        elapsed = (now - ts).total_seconds()
        existing_ttl = existing.get("ttl_seconds", DEFAULT_TTL_SECONDS)
        expired = elapsed >= existing_ttl

        if not expired and holder != callsign:
            # Active claim held by someone else
            return False
        # Either expired or same callsign → fall through to overwrite/refresh
    except FileNotFoundError:
        pass  # No existing claim — proceed to write

    payload = {
        "path": repo_relative_path,
        "callsign": callsign,
        "timestamp_utc": now.isoformat(),
        "ttl_seconds": ttl_seconds,
        "branch": branch,
    }
    _atomic_write(claim_file, payload)
    return True


def release(repo_relative_path: str, callsign: str) -> bool:
    """
    Release a claim.

    Returns True if the claim belonged to callsign and was removed.
    Returns False if the file isn't claimed, or the holder is a different callsign.
    """
    claim_file = _claim_path(repo_relative_path)
    try:
        with open(claim_file) as f:
            existing = json.load(f)
    except FileNotFoundError:
        return False

    if existing.get("callsign") != callsign:
        return False

    try:
        os.unlink(claim_file)
    except FileNotFoundError:
        return False
    return True


def is_claimed(repo_relative_path: str) -> dict | None:
    """
    Return the active claim dict (with added `seconds_remaining` key) or None.

    Returns None if absent or expired.
    """
    claim_file = _claim_path(repo_relative_path)
    try:
        with open(claim_file) as f:
            data = json.load(f)
    except FileNotFoundError:
        return None

    now = _now_utc()
    ts = _parse_ts(data["timestamp_utc"])
    elapsed = (now - ts).total_seconds()
    ttl = data.get("ttl_seconds", DEFAULT_TTL_SECONDS)

    if elapsed >= ttl:
        return None

    result = dict(data)
    result["seconds_remaining"] = ttl - elapsed
    return result


def scan_stale() -> list[dict]:
    """
    Return a list of dicts for every expired claim in CLAIMS_DIR.

    Each dict: {path, callsign, timestamp_utc, elapsed_seconds}
    """
    stale = []
    try:
        entries = os.listdir(CLAIMS_DIR)
    except FileNotFoundError:
        return []

    now = _now_utc()
    for entry in entries:
        if not entry.endswith(".json"):
            continue
        full = os.path.join(CLAIMS_DIR, entry)
        try:
            with open(full) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue

        ts = _parse_ts(data["timestamp_utc"])
        elapsed = (now - ts).total_seconds()
        ttl = data.get("ttl_seconds", DEFAULT_TTL_SECONDS)

        if elapsed >= ttl:
            stale.append({
                "path": data.get("path", ""),
                "callsign": data.get("callsign", ""),
                "timestamp_utc": data["timestamp_utc"],
                "elapsed_seconds": elapsed,
                "_claim_file": full,
            })

    return stale
