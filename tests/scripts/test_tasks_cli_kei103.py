"""KEI-103 — retrieval_query wired into cmd_claim.

Three acceptance tests:
  1. Successful claim fires retrieval_query once with task title + callsign.
  2. retrieval_query exception is swallowed; cmd_claim still returns 0.
  3. Claim race-loss (row=None) does NOT invoke retrieval_query.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "tasks_cli.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("tasks_cli_kei103", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["tasks_cli_kei103"] = m
    spec.loader.exec_module(m)
    return m


sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db_mocks import FakeCursor, make_patch_connect  # type: ignore[import-not-found]  # noqa: E402

_Cursor = FakeCursor


@pytest.fixture
def patch_connect(mod, monkeypatch):
    return make_patch_connect(monkeypatch)


# ─── helpers ────────────────────────────────────────────────────────────────


def _claim_row(title: str = "My Task Title") -> tuple:
    """Return a 7-column RETURNING row matching the claim SELECT projection.

    RETURNING id, title, priority, status, claimed_by, linear_url, tags
               0    1         2       3         4           5        6
    """
    return ("KEI-103", title, 1, "active", "max", "https://linear.app/x", [])


# ─── test 1: success path fires retrieval_query ────────────────────────────


def test_claim_fires_retrieval_query_on_success(mod, patch_connect, monkeypatch) -> None:
    """On a successful claim cmd_claim calls retrieval_query(title, agent=cs, ...)."""
    monkeypatch.setenv("CALLSIGN", "max")

    cur = _Cursor(fetchone_row=_claim_row("Implement the thing"))
    patch_connect(cur)

    mock_query = MagicMock(return_value=None)

    # Patch at the import target inside tasks_cli's namespace.  The lazy import
    # inside cmd_claim uses `from src.retrieval.agent_query import query as
    # _retrieval_query`, so we patch the source module's attribute and also
    # pre-populate sys.modules so the import resolves to our mock.
    fake_aq = MagicMock()
    fake_aq.query = mock_query
    monkeypatch.setitem(sys.modules, "src.retrieval.agent_query", fake_aq)
    # Also ensure the src.retrieval namespace exists.
    if "src.retrieval" not in sys.modules:
        monkeypatch.setitem(sys.modules, "src.retrieval", MagicMock())
    if "src" not in sys.modules:
        monkeypatch.setitem(sys.modules, "src", MagicMock())

    rc = mod.main(["claim", "--id", "KEI-103", "--json"])

    assert rc == 0
    mock_query.assert_called_once()
    call_args = mock_query.call_args
    # Positional arg 0 is the task title
    assert call_args.args[0] == "Implement the thing"
    # keyword arg agent matches callsign
    assert call_args.kwargs["agent"] == "max"
    # collections tuple present
    assert "collections" in call_args.kwargs
    assert "Keis" in call_args.kwargs["collections"]


# ─── test 2: retrieval_query exception is swallowed ────────────────────────


def test_claim_swallows_retrieval_query_exception(mod, patch_connect, capsys, monkeypatch) -> None:
    """If retrieval_query raises, cmd_claim still returns 0 and prints the row."""
    monkeypatch.setenv("CALLSIGN", "max")

    cur = _Cursor(fetchone_row=_claim_row("Exploding task"))
    patch_connect(cur)

    def _boom(*a, **kw):
        raise RuntimeError("weaviate down")

    fake_aq = MagicMock()
    fake_aq.query = _boom
    monkeypatch.setitem(sys.modules, "src.retrieval.agent_query", fake_aq)
    if "src.retrieval" not in sys.modules:
        monkeypatch.setitem(sys.modules, "src.retrieval", MagicMock())
    if "src" not in sys.modules:
        monkeypatch.setitem(sys.modules, "src", MagicMock())

    rc = mod.main(["claim", "--id", "KEI-103", "--json"])

    assert rc == 0
    import json

    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "KEI-103"


# ─── test 3: claim race-loss does NOT invoke retrieval_query ───────────────


def test_claim_failure_path_does_not_call_retrieval_query(
    mod, patch_connect, capsys, monkeypatch
) -> None:
    """When the UPDATE returns no row (race lost), retrieval_query is not called."""
    monkeypatch.setenv("CALLSIGN", "max")

    cur = _Cursor(fetchone_row=None)
    patch_connect(cur)

    mock_query = MagicMock(return_value=None)
    fake_aq = MagicMock()
    fake_aq.query = mock_query
    monkeypatch.setitem(sys.modules, "src.retrieval.agent_query", fake_aq)
    if "src.retrieval" not in sys.modules:
        monkeypatch.setitem(sys.modules, "src.retrieval", MagicMock())
    if "src" not in sys.modules:
        monkeypatch.setitem(sys.modules, "src", MagicMock())

    rc = mod.main(["claim", "--json"])

    assert rc == 0
    assert capsys.readouterr().out.strip() == "null"
    mock_query.assert_not_called()
