"""KEI-230 / KEI-237 — tests for reconcile_three_stores.py.

Covers:
- _kei_from_url: handles slug, no-slug, trailing-slash, empty
- build_join_table: composes 3 store views by KEI
- detect_drift: classifies in_all_three / missing_postgres / missing_bd / missing_linear
- _has_field_drift: stale-status detection + KEI-237 normalised comparison
- _format_drift_alert / _post_drift_alert: flag-only drift alert (KEI-237)
- post_to_slack: token-absent guard
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

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
# Field drift (KEI-233 + KEI-237 normalised comparison).
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
    """NULL pg.status with a canonical Linear value IS drift — surface it."""
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


def test_field_drift_comparison_is_case_and_whitespace_insensitive(mod) -> None:
    """KEI-237 (c) — format noise (casing / whitespace) must NOT raise a flag.

    Linear=started → canonical 'active'. Postgres status '  ACTIVE  ' differs
    only in case + surrounding whitespace — normalised, it matches, so no
    false field_drift flag.
    """
    table = {
        "KEI-7": {
            "linear": {"state": {"type": "started"}},  # canonical 'active'
            "postgres": {"status": "  ACTIVE  "},
            "bd": {"id": "Agency_OS-fff"},
        }
    }
    drift = mod.detect_drift(table)
    assert drift["field_drift"] == [], "case/whitespace noise must not drift-flag"


# ---------------------------------------------------------------------------
# KEI-237 — flag-only drift alert (no auto-fix, no new table).
# ---------------------------------------------------------------------------


def _drift(**buckets: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    base: dict[str, list[dict[str, Any]]] = {
        "in_all_three": [],
        "missing_postgres": [],
        "missing_bd": [],
        "missing_linear": [],
        "field_drift": [],
    }
    base.update(buckets)
    return base


def test_format_drift_alert_none_when_no_drift(mod) -> None:
    """No drift in any actionable bucket → no alert text (None)."""
    assert mod._format_drift_alert(_drift(in_all_three=[{"kei": "KEI-ok", "stores": {}}])) is None


def test_format_drift_alert_lists_buckets_and_keis(mod) -> None:
    drift = _drift(
        missing_postgres=[{"kei": "KEI-20", "stores": {"linear": {}}}],
        field_drift=[
            {
                "kei": "KEI-21",
                "stores": {
                    "linear": {"state": {"type": "completed"}},
                    "postgres": {"status": "active"},
                    "bd": {"id": "Agency_OS-x"},
                },
            }
        ],
    )
    text = mod._format_drift_alert(drift)
    assert text is not None
    assert "[DRIFT]" in text
    assert "2 KEI(s)" in text
    assert "missing_postgres (1): KEI-20" in text
    # field_drift entries carry the linear-vs-pg detail.
    assert "KEI-21 (linear=completed pg=active)" in text
    assert "no auto-fix" in text.lower()


def test_format_drift_alert_truncates_long_bucket(mod) -> None:
    """A bucket with >20 KEIs shows the first 20 + a (+N more) marker."""
    drift = _drift(missing_bd=[{"kei": f"KEI-{i}", "stores": {"linear": {}}} for i in range(25)])
    text = mod._format_drift_alert(drift)
    assert text is not None
    assert "(+5 more)" in text


def test_post_drift_alert_no_drift_posts_nothing(mod, monkeypatch) -> None:
    posted: list = []
    monkeypatch.setattr(mod, "post_to_slack", lambda t, c: posted.append((t, c)) or True)
    n = mod._post_drift_alert(_drift())
    assert n == 0
    assert posted == [], "no drift → no Slack post"


def test_post_drift_alert_posts_consolidated_alert(mod, monkeypatch) -> None:
    posted: list = []
    monkeypatch.setattr(mod, "post_to_slack", lambda t, c: posted.append((t, c)) or True)
    monkeypatch.delenv("DRIFT_ALERT_CHANNEL", raising=False)
    drift = _drift(
        missing_linear=[{"kei": "KEI-30", "stores": {"bd": {}}}],
        missing_bd=[{"kei": "KEI-31", "stores": {"linear": {}}}],
    )
    n = mod._post_drift_alert(drift)
    assert n == 2
    assert len(posted) == 1, "exactly one consolidated alert"
    text, channel = posted[0]
    assert "KEI-30" in text and "KEI-31" in text
    assert channel == mod._CEO_CHANNEL_DEFAULT  # defaults to #ceo


def test_post_drift_alert_channel_is_env_overridable(mod, monkeypatch) -> None:
    posted: list = []
    monkeypatch.setattr(mod, "post_to_slack", lambda t, c: posted.append((t, c)) or True)
    monkeypatch.setenv("DRIFT_ALERT_CHANNEL", "C-CUSTOM")
    mod._post_drift_alert(_drift(missing_bd=[{"kei": "KEI-40", "stores": {"linear": {}}}]))
    assert posted[0][1] == "C-CUSTOM"


def test_post_to_slack_returns_false_without_token(mod, monkeypatch) -> None:
    """No SLACK_BOT_TOKEN → best-effort no-op, returns False, never raises."""
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    assert mod.post_to_slack("hello", "C-X") is False


def test_field_drift_detail_formats_linear_vs_pg(mod) -> None:
    entry = {
        "kei": "KEI-50",
        "stores": {
            "linear": {"state": {"type": "completed"}},
            "postgres": {"status": "active"},
        },
    }
    assert mod._field_drift_detail(entry) == "KEI-50 (linear=completed pg=active)"
