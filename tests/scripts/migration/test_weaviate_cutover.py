"""tests for scripts/migration/weaviate_cutover.py — Phase 1.2.5 artefact 4.

Coverage:
- snapshot idempotency (rerun → same end state)
- write_to_target deterministic UUID derivation
- verify hard-required: count mismatch + sample-read miss both return False
- repoint apply + backup + dry-run
- purge_old opt-in semantics
- dry-run is read-only (no Weaviate POST/DELETE)

Weaviate is mocked end-to-end — no live broker required for the suite.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "migration" / "weaviate_cutover.py"


@pytest.fixture
def mod():
    spec = importlib.util.spec_from_file_location("weaviate_cutover", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["weaviate_cutover"] = m
    spec.loader.exec_module(m)
    return m


def _sample_rows(n: int) -> list[dict]:
    return [
        {
            "_additional": {"id": f"src-{i:04d}"},
            "content": f"row {i}",
            "context_tag": "product",
            "created_at": "2026-05-24T00:00:00Z",
        }
        for i in range(n)
    ]


def test_snapshot_idempotent(mod, monkeypatch, tmp_path):
    """Re-running snapshot with the same source produces the same file content."""
    rows = _sample_rows(3)
    monkeypatch.setattr(mod, "_fetch_objects", lambda *a, **kw: rows)
    out = tmp_path / "snap.json"

    n1 = mod.snapshot("Decisions", "product", out, 100, dry_run=False)
    body1 = out.read_text()
    n2 = mod.snapshot("Decisions", "product", out, 100, dry_run=False)
    body2 = out.read_text()

    assert n1 == n2 == 3
    assert body1 == body2, "idempotent re-run must produce identical snapshot content"


def test_snapshot_dry_run_writes_nothing(mod, monkeypatch, tmp_path):
    """Dry-run does NOT call _fetch_objects and does NOT create the file."""
    called = []
    monkeypatch.setattr(mod, "_fetch_objects", lambda *a, **kw: called.append(1) or [])
    out = tmp_path / "snap.json"

    mod.snapshot("Decisions", "product", out, 100, dry_run=True)

    assert called == [], "dry-run must not call _fetch_objects"
    assert not out.exists(), "dry-run must not create snapshot file"


def test_write_to_target_uses_deterministic_uuid(mod, monkeypatch, tmp_path):
    """Each row gets a UUID derived from cutover-tag + source id (cross-run stable)."""
    rows = _sample_rows(2)
    snap = tmp_path / "snap.json"
    snap.write_text(
        json.dumps({"source_class": "Decisions", "filter_tag": "product", "rows": rows})
    )
    posted: list[dict] = []
    monkeypatch.setattr(mod, "post_object", lambda obj: posted.append(obj) or True)

    ok, fail = mod.write_to_target("Keiracom_Product", snap, dry_run=False)

    assert (ok, fail) == (2, 0)
    assert len(posted) >= 2, "post_object must have been called once per row"
    expected_id_0 = mod.deterministic_uuid(mod.UUID_SOURCE_TAG, "src-0000")
    expected_id_1 = mod.deterministic_uuid(mod.UUID_SOURCE_TAG, "src-0001")
    assert posted[0]["id"] == expected_id_0
    assert posted[1]["id"] == expected_id_1
    assert posted[0]["class"] == "Keiracom_Product"
    assert "_additional" not in posted[0]["properties"], (
        "internal _additional must not leak to target"
    )


def test_write_to_target_dry_run_no_posts(mod, monkeypatch, tmp_path):
    """Dry-run never calls post_object."""
    rows = _sample_rows(5)
    snap = tmp_path / "snap.json"
    snap.write_text(
        json.dumps({"source_class": "Decisions", "filter_tag": "product", "rows": rows})
    )
    monkeypatch.setattr(
        mod, "post_object", lambda obj: pytest.fail("post_object must not be called in dry-run")
    )

    ok, fail = mod.write_to_target("Keiracom_Product", snap, dry_run=True)

    assert (ok, fail) == (5, 0), "dry-run reports planned count without posting"


def test_verify_count_mismatch_returns_false(mod, monkeypatch, tmp_path):
    """Hard-required gate: count short of snapshot returns False."""
    rows = _sample_rows(10)
    snap = tmp_path / "snap.json"
    snap.write_text(
        json.dumps({"source_class": "Decisions", "filter_tag": "product", "rows": rows})
    )
    monkeypatch.setattr(mod, "aggregate_count", lambda c: 7)  # less than 10

    assert mod.verify("Decisions", "Keiracom_Product", snap) is False


def test_verify_aggregate_none_returns_false(mod, monkeypatch, tmp_path):
    """If aggregate_count cannot reach the broker, treat as verify fail (not pass)."""
    rows = _sample_rows(3)
    snap = tmp_path / "snap.json"
    snap.write_text(
        json.dumps({"source_class": "Decisions", "filter_tag": "product", "rows": rows})
    )
    monkeypatch.setattr(mod, "aggregate_count", lambda c: None)

    assert mod.verify("Decisions", "Keiracom_Product", snap) is False


def test_verify_ok_when_count_and_samples_match(mod, monkeypatch, tmp_path):
    """Happy path — count >= expected AND every sample tgt_id exists in target."""
    rows = _sample_rows(3)
    snap = tmp_path / "snap.json"
    snap.write_text(
        json.dumps({"source_class": "Decisions", "filter_tag": "product", "rows": rows})
    )
    monkeypatch.setattr(mod, "aggregate_count", lambda c: 3)

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None  # protocol-only fake; no cleanup needed

    monkeypatch.setattr(mod, "_http_request", lambda *a, **kw: _Resp())
    assert mod.verify("Decisions", "Keiracom_Product", snap) is True


def test_repoint_applies_edits_with_backup(mod, tmp_path):
    """Repoint writes target with new value AND leaves a .cutover-backup of the original."""
    config = tmp_path / "agent.json"
    original = {"memory": {"collection": "Decisions"}, "other": "unchanged"}
    config.write_text(json.dumps(original))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"edits": [{"file": str(config), "key_path": "memory.collection"}]})
    )

    applied = mod.repoint(manifest, "Keiracom_Product", dry_run=False, confine_root=tmp_path)

    assert applied == 1
    written = json.loads(config.read_text())
    assert written["memory"]["collection"] == "Keiracom_Product"
    assert written["other"] == "unchanged"
    backup = config.with_suffix(config.suffix + ".cutover-backup")
    assert backup.exists()
    assert json.loads(backup.read_text()) == original


def test_repoint_dry_run_writes_nothing(mod, tmp_path):
    """Dry-run leaves the config + filesystem untouched (no backup, no edit)."""
    config = tmp_path / "agent.json"
    original = {"memory": {"collection": "Decisions"}}
    config.write_text(json.dumps(original))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"edits": [{"file": str(config), "key_path": "memory.collection"}]})
    )

    mod.repoint(manifest, "Keiracom_Product", dry_run=True, confine_root=tmp_path)

    assert json.loads(config.read_text()) == original, "dry-run must not mutate target file"
    assert not config.with_suffix(config.suffix + ".cutover-backup").exists()


def test_repoint_missing_manifest_emits_empty_plan(mod, tmp_path, caplog):
    """No manifest file = 0 edits applied with a warning, not a crash."""
    missing = tmp_path / "no-such-manifest.json"
    applied = mod.repoint(missing, "Keiracom_Product", dry_run=False)
    assert applied == 0


def test_repoint_rejects_path_escape_attempt(mod, tmp_path):
    """Negative-path lock for S2083 — manifest paths outside confine_root MUST
    be rejected (no read, no backup, no write). Anchored 2026-05-24 by Max's
    BLOCKER review on PR #1119: a hostile manifest with `{"file": "/etc/passwd"}`
    must not trigger an arbitrary-file overwrite."""
    safe_target = tmp_path / "agent.json"
    safe_target.write_text(json.dumps({"memory": {"collection": "Decisions"}}))
    escape_target = "/etc/passwd"  # absolute path, outside tmp_path confinement
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "edits": [
                    {"file": escape_target, "key_path": "memory.collection"},
                    {"file": str(safe_target), "key_path": "memory.collection"},
                ]
            }
        )
    )

    applied = mod.repoint(manifest, "Keiracom_Product", dry_run=False, confine_root=tmp_path)

    # Escape entry skipped; safe entry applied — partial-progress on per-edit basis.
    assert applied == 1
    # Confirm the escape target was not even read (no backup written there).
    assert not Path("/etc/passwd.cutover-backup").exists()


def test_safe_resolve_accepts_in_root_paths(mod, tmp_path):
    """Happy path — paths inside the confine root resolve cleanly (absolute form)."""
    inside = tmp_path / "agent.json"
    inside.touch()
    resolved = mod._safe_resolve(str(inside), tmp_path)
    assert resolved == inside.resolve()


def test_safe_resolve_accepts_relative_paths(mod, tmp_path):
    """Relative manifest paths compose against confine_root."""
    (tmp_path / "agent.json").touch()
    resolved = mod._safe_resolve("agent.json", tmp_path)
    assert resolved == (tmp_path / "agent.json").resolve()


def test_safe_resolve_rejects_escape_paths(mod, tmp_path):
    """Negative-path lock — absolute escape rejected."""
    with pytest.raises(ValueError, match="escapes confinement root"):
        mod._safe_resolve("/etc/passwd", tmp_path)


def test_safe_resolve_rejects_dotdot_traversal(mod, tmp_path):
    """Negative-path lock — relative ../../etc/passwd resolves outside root → reject."""
    with pytest.raises(ValueError, match="escapes confinement root"):
        mod._safe_resolve("../../etc/passwd", tmp_path)


def test_safe_resolve_rejects_empty_string(mod, tmp_path):
    """Negative-path lock — empty string is invalid manifest data."""
    with pytest.raises(ValueError, match="non-empty string"):
        mod._safe_resolve("", tmp_path)


def test_safe_resolve_rejects_null_byte(mod, tmp_path):
    """Negative-path lock — embedded null byte (classic path-truncation attack)."""
    with pytest.raises(ValueError, match="control characters"):
        mod._safe_resolve("agent.json\x00.bak", tmp_path)


def test_safe_resolve_rejects_home_expansion(mod, tmp_path):
    """Negative-path lock — `~` would be Path.expanduser-ambiguous, reject upfront."""
    with pytest.raises(ValueError, match="home-expansion"):
        mod._safe_resolve("~/secrets", tmp_path)


def test_purge_old_opt_in_only(mod, monkeypatch, tmp_path):
    """Step 5 honours snapshot-driven delete; dry-run never calls DELETE."""
    rows = _sample_rows(4)
    snap = tmp_path / "snap.json"
    snap.write_text(
        json.dumps({"source_class": "Decisions", "filter_tag": "product", "rows": rows})
    )
    called: list[tuple] = []

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None  # protocol-only fake; no cleanup needed

    def _track_http(method, path, body=None):
        called.append((method, path))
        return _Resp()

    monkeypatch.setattr(mod, "_http_request", _track_http)

    ok_dry, fail_dry = mod.purge_old("Decisions", snap, dry_run=True)
    assert (ok_dry, fail_dry) == (4, 0)
    assert called == [], "dry-run must not call _http_request"

    ok, fail = mod.purge_old("Decisions", snap, dry_run=False)
    assert (ok, fail) == (4, 0)
    assert len(called) == 4
    assert all(m == "DELETE" for m, _ in called)
