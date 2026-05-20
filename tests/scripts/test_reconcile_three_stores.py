"""KEI-230 — tests for reconcile_three_stores.py.

Covers:
- _kei_from_url: handles slug, no-slug, trailing-slash, empty
- build_join_table: composes 3 store views by KEI
- detect_drift: classifies in_all_three / missing_postgres / missing_bd / missing_linear
- _build_create_payload: picks canonical fields (Linear status > postgres)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "reconcile_three_stores.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("reconcile_three_stores", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["reconcile_three_stores"] = m
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------------------
# URL parsing.
# ---------------------------------------------------------------------------


def test_kei_from_url_full_slug(mod) -> None:
    assert mod._kei_from_url("https://linear.app/keiracom/issue/KEI-227/atlas-k1-foo") == "KEI-227"


def test_kei_from_url_no_slug(mod) -> None:
    assert mod._kei_from_url("https://linear.app/keiracom/issue/KEI-227") == "KEI-227"


def test_kei_from_url_none(mod) -> None:
    assert mod._kei_from_url(None) is None
    assert mod._kei_from_url("") is None


def test_kei_from_url_malformed(mod) -> None:
    assert mod._kei_from_url("https://google.com/foo") is None


# ---------------------------------------------------------------------------
# Join table.
# ---------------------------------------------------------------------------


def test_build_join_table_unions_three_stores(mod) -> None:
    linear = [{"identifier": "KEI-1", "title": "t1"}]
    postgres = [
        {
            "id": "KEI-1",
            "bd_id": "Agency_OS-aaa",
            "title": "t1",
            "status": "active",
            "priority": 2,
            "linear_url": "https://linear.app/keiracom/issue/KEI-1",
            "updated_at": None,
        },
        {
            "id": "KEI-2",
            "bd_id": None,
            "title": "t2",
            "status": "available",
            "priority": 3,
            "linear_url": "https://linear.app/keiracom/issue/KEI-2",
            "updated_at": None,
        },
    ]
    bd = [
        {"id": "Agency_OS-aaa", "external_ref": "https://linear.app/keiracom/issue/KEI-1"},
        {"id": "Agency_OS-bbb", "external_ref": "https://linear.app/keiracom/issue/KEI-3"},
    ]
    table = mod.build_join_table(linear, postgres, bd)
    assert "KEI-1" in table
    assert "KEI-2" in table
    assert "KEI-3" in table
    assert "linear" in table["KEI-1"]
    assert "postgres" in table["KEI-1"]
    assert "bd" in table["KEI-1"]
    # KEI-2: postgres only.
    assert table["KEI-2"].get("linear") is None
    assert table["KEI-2"].get("bd") is None


def test_build_join_table_postgres_row_with_agency_id_uses_url(mod) -> None:
    """Row keyed Agency_OS-xxx in tasks.id should still join by linear_url."""
    postgres = [
        {
            "id": "Agency_OS-zzz",
            "bd_id": None,
            "title": "legacy",
            "status": "done",
            "priority": 2,
            "linear_url": "https://linear.app/keiracom/issue/KEI-42/slug-foo",
            "updated_at": None,
        },
    ]
    table = mod.build_join_table([], postgres, [])
    assert "KEI-42" in table
    assert table["KEI-42"]["postgres"]["id"] == "Agency_OS-zzz"


# ---------------------------------------------------------------------------
# Drift detection.
# ---------------------------------------------------------------------------


def test_detect_drift_all_three(mod) -> None:
    table = {"KEI-1": {"linear": {}, "postgres": {}, "bd": {}}}
    drift = mod.detect_drift(table)
    assert len(drift["in_all_three"]) == 1
    assert drift["missing_postgres"] == []


def test_detect_drift_missing_postgres(mod) -> None:
    table = {"KEI-2": {"linear": {}, "bd": {}}}
    drift = mod.detect_drift(table)
    assert len(drift["missing_postgres"]) == 1


def test_detect_drift_missing_bd(mod) -> None:
    table = {"KEI-3": {"linear": {}, "postgres": {}}}
    drift = mod.detect_drift(table)
    assert len(drift["missing_bd"]) == 1


def test_detect_drift_missing_linear(mod) -> None:
    table = {"KEI-4": {"postgres": {}, "bd": {}}}
    drift = mod.detect_drift(table)
    assert len(drift["missing_linear"]) == 1


# ---------------------------------------------------------------------------
# Field drift (KEI-233).
# ---------------------------------------------------------------------------


def test_field_drift_linear_completed_pg_available(mod) -> None:
    """Linear says completed, Postgres says available → flagged as field_drift."""
    table = {
        "KEI-1": {
            "linear": {"state": {"type": "completed"}},
            "postgres": {"status": "available"},
            "bd": {"id": "Agency_OS-aaa"},
        }
    }
    drift = mod.detect_drift(table)
    assert len(drift["field_drift"]) == 1
    assert drift["field_drift"][0]["kei"] == "KEI-1"
    # Also still appears in in_all_three — those buckets overlap.
    assert len(drift["in_all_three"]) == 1


def test_field_drift_skipped_when_status_already_matches(mod) -> None:
    """Linear=completed → expected status='done'; Postgres=done → no drift."""
    table = {
        "KEI-2": {
            "linear": {"state": {"type": "completed"}},
            "postgres": {"status": "done"},
            "bd": {"id": "Agency_OS-bbb"},
        }
    }
    drift = mod.detect_drift(table)
    assert drift["field_drift"] == []


def test_field_drift_done_pg_is_sticky_even_if_linear_reopened(mod) -> None:
    """Postgres `done` is preserved — orchestrator never re-opens done rows."""
    table = {
        "KEI-3": {
            "linear": {"state": {"type": "started"}},
            "postgres": {"status": "done"},
            "bd": {"id": "Agency_OS-ccc"},
        }
    }
    drift = mod.detect_drift(table)
    assert drift["field_drift"] == []


def test_field_drift_skips_postgres_only_buckets(mod) -> None:
    """Postgres `dismissed` / `blocked` have no Linear equivalent — not drift."""
    for status in ("dismissed", "blocked"):
        table = {
            "KEI-x": {
                "linear": {"state": {"type": "completed"}},
                "postgres": {"status": status},
                "bd": {"id": "Agency_OS-x"},
            }
        }
        drift = mod.detect_drift(table)
        assert drift["field_drift"] == [], f"unexpected drift on pg={status}"


def test_field_drift_null_pg_status_counts(mod) -> None:
    """NULL pg.status with a canonical Linear value IS drift — propagate Linear."""
    table = {
        "KEI-4": {
            "linear": {"state": {"type": "backlog"}},
            "postgres": {"status": None},
            "bd": {"id": "Agency_OS-ddd"},
        }
    }
    drift = mod.detect_drift(table)
    assert len(drift["field_drift"]) == 1
    assert drift["field_drift"][0]["kei"] == "KEI-4"


def test_field_drift_unmapped_linear_state_skipped(mod) -> None:
    """If Linear state.type is not in our mapping, we can't decide canonical."""
    table = {
        "KEI-5": {
            "linear": {"state": {"type": "weird-unknown"}},
            "postgres": {"status": "available"},
            "bd": {"id": "Agency_OS-eee"},
        }
    }
    drift = mod.detect_drift(table)
    assert drift["field_drift"] == []


def test_field_drift_only_evaluated_for_in_all_three(mod) -> None:
    """A KEI missing from a store is NOT also flagged as field_drift."""
    table = {
        "KEI-6": {
            "linear": {"state": {"type": "completed"}},
            "postgres": {"status": "available"},
            # bd missing
        }
    }
    drift = mod.detect_drift(table)
    assert drift["field_drift"] == []
    assert len(drift["missing_bd"]) == 1


# ---------------------------------------------------------------------------
# Payload construction.
# ---------------------------------------------------------------------------


def test_build_create_payload_prefers_linear_status(mod) -> None:
    stores = {
        "linear": {
            "title": "Linear title",
            "state": {"type": "started", "name": "In Progress"},
            "priority": 1,
            "url": "https://linear.app/keiracom/issue/KEI-9",
        },
        "postgres": {"title": "Postgres title", "status": "done", "priority": 4},
        "bd": {"id": "Agency_OS-xxx"},
    }
    payload = mod._build_create_payload("KEI-9", stores)
    assert payload["title"] == "Linear title"
    assert payload["status"] == "active"  # started → active
    assert payload["priority"] == 1
    assert payload["bd_id"] == "Agency_OS-xxx"


def test_build_create_payload_falls_back_to_postgres_when_no_linear(mod) -> None:
    stores = {
        "postgres": {
            "title": "PG only",
            "status": "available",
            "priority": 3,
            "bd_id": "Agency_OS-y",
        },
        "bd": {"id": "Agency_OS-y"},
    }
    payload = mod._build_create_payload("KEI-10", stores)
    assert payload["title"] == "PG only"
    assert payload["status"] == "available"
    assert payload["bd_id"] == "Agency_OS-y"


def test_build_create_payload_default_linear_url(mod) -> None:
    payload = mod._build_create_payload("KEI-11", {})
    assert payload["linear_url"] == "https://linear.app/keiracom/issue/KEI-11"
    assert payload["status"] == "available"
    assert payload["title"] == "(no title)"


# ---------------------------------------------------------------------------
# KEI-237 — postgres-canonical payload + emission flip.
# ---------------------------------------------------------------------------


def test_build_postgres_payload_prefers_postgres_status(mod) -> None:
    """Under the new policy, Postgres is canonical — _build_postgres_payload
    must return Postgres's status, NOT Linear's mapped status."""
    stores = {
        "linear": {
            "title": "Linear title",
            "state": {"type": "completed"},  # would map to 'done'
            "priority": 1,
            "url": "https://linear.app/keiracom/issue/KEI-9",
        },
        "postgres": {
            "title": "Postgres title",
            "status": "active",  # canonical under new policy
            "priority": 4,
            "bd_id": "Agency_OS-xxx",
            "linear_url": "https://linear.app/keiracom/issue/KEI-9",
        },
        "bd": {"id": "Agency_OS-xxx"},
    }
    payload = mod._build_postgres_payload("KEI-9", stores)
    assert payload["status"] == "active"  # Postgres wins
    assert payload["title"] == "Postgres title"
    assert payload["bd_id"] == "Agency_OS-xxx"


def test_build_postgres_payload_falls_back_to_linear_url(mod) -> None:
    """If pg.linear_url is missing, fall back to linear_iss.url, then default."""
    stores = {
        "postgres": {"status": "active"},
        "linear": {"url": "https://linear.app/keiracom/issue/KEI-22/explicit-slug"},
    }
    payload = mod._build_postgres_payload("KEI-22", stores)
    assert payload["linear_url"] == "https://linear.app/keiracom/issue/KEI-22/explicit-slug"


def test_build_postgres_payload_default_status_available(mod) -> None:
    """Missing pg.status → defaults to 'available' (KEI-237 ON CONFLICT-safe)."""
    payload = mod._build_postgres_payload("KEI-30", {"postgres": {}})
    assert payload["status"] == "available"


def test_emit_events_field_drift_uses_postgres_origin(mod) -> None:
    """KEI-237: field_drift entries emit origin='postgres' (not 'linear')."""

    class _FakeCursor:
        def __init__(self):
            self.executed = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def execute(self, sql, params=None):
            self.executed.append((sql, params))

    class _FakeConn:
        def __init__(self):
            self.cur = _FakeCursor()

        def cursor(self):
            return self.cur

        def commit(self):
            pass

    drift = {
        "missing_postgres": [],
        "missing_bd": [],
        "missing_linear": [],
        "field_drift": [
            {
                "kei": "KEI-99",
                "stores": {
                    "linear": {"state": {"type": "completed"}},
                    "postgres": {"status": "active", "bd_id": "Agency_OS-xx"},
                    "bd": {"id": "Agency_OS-xx"},
                },
            }
        ],
    }
    conn = _FakeConn()
    emitted = mod._emit_events(conn, drift)
    assert emitted == 1
    sql, params = conn.cur.executed[0]
    assert "fn_emit_sync_event" in sql
    # params = (origin, event_type, task_id, bd_id, payload_json)
    assert params[0] == "postgres", "field_drift must emit origin=postgres under KEI-237"
    assert params[1] == "update"
    assert params[2] == "KEI-99"
