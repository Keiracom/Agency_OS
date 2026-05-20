"""KEI-133 — Postgres OOM chaos scenario.

Simulates a Postgres OOM-kill condition. psycopg surfaces this as a
specific OperationalError shape — usually `out of memory` in the error
text. The contract: callers must catch psycopg.OperationalError, fire an
alert to the agreed channel (#ceo per `feedback_close_loop_to_ceo`), and
fail closed — never silently swallow.
"""

from __future__ import annotations

import pytest


class _FakePsycopgOpError(Exception):
    """Stand-in for psycopg.OperationalError. The real exception carries
    the same shape — diagnostic message + severity — and the contract under
    test does not depend on the psycopg dependency itself."""


def _query_with_oom_alert(
    execute_fn,
    alert_fn,
) -> bool:
    """Canonical contract for any Postgres call that could OOM under load:
    1. Run the query.
    2. On _FakePsycopgOpError with 'out of memory' in message — fire alert
       to #ceo via alert_fn, return False, do NOT propagate.
    3. On other OperationalErrors — log + return False (transient).
    4. Returns True iff the query succeeded.
    """
    try:
        execute_fn()
        return True
    except _FakePsycopgOpError as exc:
        message = str(exc).lower()
        if "out of memory" in message:
            alert_fn(f"#ceo POSTGRES-OOM — {exc}")
        return False


@pytest.mark.timeout(10)
def test_oom_fires_ceo_alert_and_fails_closed() -> None:
    """OOM-shape OperationalError → #ceo alert fires + query returns False."""
    alerts: list[str] = []

    def fake_execute() -> None:
        raise _FakePsycopgOpError(
            "FATAL: out of memory (54000): cannot allocate 64MB",
        )

    ok = _query_with_oom_alert(fake_execute, alerts.append)

    assert ok is False
    assert len(alerts) == 1
    assert "#ceo POSTGRES-OOM" in alerts[0]
    assert "out of memory" in alerts[0]


@pytest.mark.timeout(10)
def test_non_oom_operational_error_does_not_alert_ceo() -> None:
    """Other transient psycopg errors (deadlock, serialisation failure)
    return False but do NOT page #ceo — only OOM is the page-worthy class."""
    alerts: list[str] = []

    def fake_execute() -> None:
        raise _FakePsycopgOpError(
            "40001: could not serialize access due to concurrent update",
        )

    ok = _query_with_oom_alert(fake_execute, alerts.append)

    assert ok is False
    assert alerts == []


@pytest.mark.timeout(10)
def test_successful_query_does_not_alert_or_fail() -> None:
    """Happy path: no alert, returns True."""
    alerts: list[str] = []

    ok = _query_with_oom_alert(lambda: None, alerts.append)

    assert ok is True
    assert alerts == []
