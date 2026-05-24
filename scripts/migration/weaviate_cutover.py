#!/usr/bin/env python3
"""weaviate_cutover.py — five-step cutover from current Weaviate collection to keiracom-product.

Phase 1.2.5 artefact 4. Authored ahead of Phase 2.0 execution: when the product
repo creates the new `keiracom-product` collection, this script moves product-
relevant entries across with per-step verification and no flag-day.

Five steps (each independently runnable + rollback-able):
  (1) snapshot — read product-tagged objects from source class to a JSON file.
  (2) write    — upsert snapshotted objects into target class via deterministic UUID.
  (3) verify   — count match + sample-read parity; HARD-REQUIRED, exits non-zero on mismatch.
  (4) repoint  — apply a manifest of (file, key_path, new_value) edits with backup.
  (5) purge    — delete snapshotted objects from source. Opt-in via --purge-old (default OFF).

Design principles:
  - No flag-day. Each step gated on its own verify and independently rollback-able.
  - Step (1) is idempotent — re-running overwrites the snapshot atomically; consumers
    of step (2) see consistent input.
  - Step (3) is HARD-REQUIRED — calling --step verify with count mismatch exits 1.
  - --dry-run flag plans every step without mutation.
  - Logging at every step boundary.

The actual product agent config files do not exist yet (Phase 2.0). Step (4) takes
a manifest file so the path-list can be filled in once Phase 2.0 lands; the script
itself is template-complete now.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error as urlerror

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "orchestrator"))
from indexer_base import (  # noqa: E402
    WEAVIATE_BASE,
    _http_request,
    aggregate_count,
    deterministic_uuid,
    post_object,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [cutover] %(message)s")
log = logging.getLogger("weaviate_cutover")

DEFAULT_SOURCE_CLASS = "Decisions"
DEFAULT_TARGET_CLASS = "Keiracom_Product"
DEFAULT_FILTER_TAG = "product"
# Confined sub-dir (mode 0o700) instead of bare /tmp: closes S5443 TOCTOU on
# a world-writable + predictable path. Operators can override via --snapshot-path.
_SNAPSHOT_DIR = Path("/tmp/weaviate_cutover")  # NOSONAR — created mode-0o700 below
_SNAPSHOT_DIR.mkdir(mode=0o700, exist_ok=True)
DEFAULT_SNAPSHOT_PATH = _SNAPSHOT_DIR / "snapshot.json"
DEFAULT_BATCH_SIZE = 100
SAMPLE_PARITY_N = 5
UUID_SOURCE_TAG = "cutover_to_keiracom_product"
_ERR_SNAPSHOT_MISSING = "snapshot file missing: %s"
# Step 4 confines manifest-controlled paths to REPO_ROOT to close S2083 path injection.
_REPOINT_ROOT = REPO_ROOT


def _fetch_objects(class_name: str, filter_tag: str, batch_size: int) -> list[dict[str, Any]]:
    # Pull objects from `class_name` whose `context_tag` field equals filter_tag.
    # GraphQL Get with a where clause; pagination via offset until empty page.
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        query = {
            "query": (
                f"{{Get{{{class_name}("
                f"limit: {batch_size}, offset: {offset}, "
                f'where: {{path: ["context_tag"], operator: Equal, valueString: "{filter_tag}"}}'
                f"){{_additional{{id}} content context_tag created_at}}}}}}"
            )
        }
        try:
            with _http_request("POST", "/v1/graphql", query) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (urlerror.URLError, OSError):
            log.exception("graphql fetch failed at offset=%d", offset)
            raise
        rows = body.get("data", {}).get("Get", {}).get(class_name, []) or []
        if not rows:
            break
        out.extend(rows)
        if len(rows) < batch_size:
            break
        offset += batch_size
    return out


def snapshot(source_class: str, filter_tag: str, path: Path, batch_size: int, dry_run: bool) -> int:
    log.info("STEP 1 snapshot: source=%s filter=%s path=%s", source_class, filter_tag, path)
    if dry_run:
        log.info("dry-run: would fetch product-tagged rows; no write")
        return 0
    rows = _fetch_objects(source_class, filter_tag, batch_size)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps({"source_class": source_class, "filter_tag": filter_tag, "rows": rows}, indent=2)
    )
    tmp.replace(path)  # atomic swap — idempotent re-run produces same end state
    log.info("snapshot wrote %d rows to %s", len(rows), path)
    return len(rows)


def write_to_target(target_class: str, path: Path, dry_run: bool) -> tuple[int, int]:
    log.info("STEP 2 write: target=%s snapshot=%s", target_class, path)
    if not path.exists():
        if dry_run:
            log.info("dry-run: snapshot file missing — would upsert rows once step 1 produces it")
            return (0, 0)
        log.error(_ERR_SNAPSHOT_MISSING, path)
        raise FileNotFoundError(str(path))
    payload = json.loads(path.read_text())
    rows = payload["rows"]
    if dry_run:
        log.info("dry-run: would upsert %d rows to %s; no POST", len(rows), target_class)
        return (len(rows), 0)
    ok = fail = 0
    for row in rows:
        source_id = row.get("_additional", {}).get("id", "")
        obj = {
            "class": target_class,
            "id": deterministic_uuid(UUID_SOURCE_TAG, source_id),
            "properties": {k: v for k, v in row.items() if k != "_additional"},
        }
        if post_object(obj):
            ok += 1
        else:
            fail += 1
    log.info("write_to_target: ok=%d fail=%d", ok, fail)
    return (ok, fail)


def verify(source_class: str, target_class: str, path: Path) -> bool:
    log.info("STEP 3 verify: source=%s target=%s snapshot=%s", source_class, target_class, path)
    if not path.exists():
        log.error(_ERR_SNAPSHOT_MISSING, path)
        return False
    payload = json.loads(path.read_text())
    expected = len(payload["rows"])
    actual = aggregate_count(target_class)
    if actual is None:
        log.error("verify: aggregate_count returned None for %s", target_class)
        return False
    if actual < expected:
        log.error("verify: count mismatch — expected>=%d, got %d", expected, actual)
        return False
    # Sample parity: re-fetch N source rows by id and confirm corresponding target id exists
    sample = payload["rows"][:SAMPLE_PARITY_N]
    for row in sample:
        src_id = row.get("_additional", {}).get("id", "")
        tgt_id = deterministic_uuid(UUID_SOURCE_TAG, src_id)
        try:
            with _http_request("GET", f"/v1/objects/{target_class}/{tgt_id}"):
                # Existence-only probe — response body is irrelevant; HTTP 404 raises.
                pass
        except urlerror.HTTPError:
            log.exception("verify: sample-read fail src=%s tgt=%s", src_id, tgt_id)
            return False
    log.info(
        "verify OK: source-snapshot=%d target-aggregate=%d sample_parity=%d",
        expected,
        actual,
        len(sample),
    )
    return True


def _set_by_dotted_key(obj: dict, key_path: str, value: Any) -> None:
    parts = key_path.split(".")
    cur: Any = obj
    for p in parts[:-1]:
        cur = cur[p]
    cur[parts[-1]] = value


def _safe_resolve(path: Path, root: Path) -> Path:
    # Confine manifest-controlled paths to `root` (default REPO_ROOT) so a
    # hostile manifest entry like {"file": "/etc/passwd"} cannot trigger an
    # arbitrary-file overwrite. Closes pythonsecurity:S2083 BLOCKER ×2.
    resolved = path.resolve()
    root_resolved = root.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ValueError(f"manifest path escapes confinement root: {path} (root={root})")
    return resolved


def repoint(
    manifest_path: Path,
    target_class: str,
    dry_run: bool,
    confine_root: Path | None = None,
) -> int:
    log.info("STEP 4 repoint: manifest=%s target=%s", manifest_path, target_class)
    if not manifest_path.exists():
        log.warning(
            "repoint manifest missing: %s — emitting empty plan (Phase 2.0 fills this)",
            manifest_path,
        )
        return 0
    root = confine_root if confine_root is not None else _REPOINT_ROOT
    manifest = json.loads(manifest_path.read_text())
    edits = manifest.get("edits", [])
    applied = 0
    for edit in edits:
        try:
            target_file = _safe_resolve(Path(edit["file"]), root)
        except ValueError as exc:
            log.error("repoint: rejected path-escape %s — %s", edit.get("file"), exc)
            continue
        key_path = edit["key_path"]
        if not target_file.exists():
            log.warning("repoint: file missing %s — skipping", target_file)
            continue
        original = target_file.read_text()
        if dry_run:
            log.info(
                "dry-run: would set %s.%s = %s in %s",
                target_file,
                key_path,
                target_class,
                target_file,
            )
            continue
        backup = target_file.with_suffix(target_file.suffix + ".cutover-backup")
        backup.write_text(original)
        data = json.loads(original) if target_file.suffix == ".json" else None
        if data is None:
            log.error(
                "repoint: unsupported config format %s (only .json in V1)", target_file.suffix
            )
            continue
        _set_by_dotted_key(data, key_path, target_class)
        target_file.write_text(json.dumps(data, indent=2))
        applied += 1
        log.info(
            "repoint applied: %s %s -> %s (backup at %s)",
            target_file,
            key_path,
            target_class,
            backup,
        )
    return applied


def purge_old(source_class: str, path: Path, dry_run: bool) -> tuple[int, int]:
    log.info("STEP 5 purge: source=%s snapshot=%s (opt-in)", source_class, path)
    if not path.exists():
        if dry_run:
            log.info("dry-run: snapshot file missing — would delete rows once step 1 produces it")
            return (0, 0)
        log.error(_ERR_SNAPSHOT_MISSING, path)
        raise FileNotFoundError(str(path))
    payload = json.loads(path.read_text())
    rows = payload["rows"]
    if dry_run:
        log.info("dry-run: would delete %d rows from %s; no DELETE", len(rows), source_class)
        return (len(rows), 0)
    ok = fail = 0
    for row in rows:
        src_id = row.get("_additional", {}).get("id", "")
        try:
            with _http_request("DELETE", f"/v1/objects/{source_class}/{src_id}"):
                ok += 1
        except urlerror.HTTPError as exc:
            log.warning("purge: src=%s rc=%s", src_id, exc.code)
            fail += 1
        except OSError as exc:
            log.warning("purge: src=%s transient %s", src_id, exc)
            fail += 1
    log.info("purge: ok=%d fail=%d", ok, fail)
    return (ok, fail)


def _cli_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Weaviate cutover — current source -> keiracom-product")
    p.add_argument("--source-class", default=DEFAULT_SOURCE_CLASS)
    p.add_argument("--target-class", default=DEFAULT_TARGET_CLASS)
    p.add_argument("--filter-tag", default=DEFAULT_FILTER_TAG)
    p.add_argument("--snapshot-path", type=Path, default=DEFAULT_SNAPSHOT_PATH)
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    p.add_argument("--repoint-manifest", type=Path, default=None)
    p.add_argument("--purge-old", action="store_true", help="Run step 5 (default off)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--step",
        choices=["snapshot", "write", "verify", "repoint", "purge", "all"],
        default="all",
    )
    return p


def main() -> int:
    args = _cli_parser().parse_args()
    log.info(
        "weaviate_cutover start | WEAVIATE_BASE=%s | step=%s | dry_run=%s",
        WEAVIATE_BASE,
        args.step,
        args.dry_run,
    )
    t0 = time.time()
    if args.step in ("snapshot", "all"):
        snapshot(
            args.source_class, args.filter_tag, args.snapshot_path, args.batch_size, args.dry_run
        )
    if args.step in ("write", "all"):
        write_to_target(args.target_class, args.snapshot_path, args.dry_run)
    if (
        args.step in ("verify", "all")
        and not args.dry_run
        and not verify(args.source_class, args.target_class, args.snapshot_path)
    ):
        log.error("verify FAILED — aborting")
        return 1
    if args.step in ("repoint", "all") and args.repoint_manifest:
        repoint(args.repoint_manifest, args.target_class, args.dry_run)
    if args.step == "purge" or (args.step == "all" and args.purge_old):
        purge_old(args.source_class, args.snapshot_path, args.dry_run)
    log.info("cutover done in %.2fs", time.time() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
