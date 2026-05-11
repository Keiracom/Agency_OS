"""Tests for scripts/tg LEGACY_TG_CHAT_MAP — Orion's add-on to Atlas's shim base.

Atlas's PR #712 shipped the core tg → slack_relay shim and exhaustive flag
mapping coverage in tests/scripts/test_tg_shim.py. This file covers ONLY the
orion-leg add-on: legacy Telegram numeric chat ID translation in `tg -c`,
which preserves backward compat for older scripts that hardcode the old
group/DM IDs.
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TG_PATH = REPO_ROOT / "scripts" / "tg"


def _load_tg():
    # `tg` has no .py extension, so importlib can't infer a loader from the
    # path — pass SourceFileLoader explicitly.
    loader = SourceFileLoader("tg_shim_legacy_under_test", str(TG_PATH))
    spec = importlib.util.spec_from_loader("tg_shim_legacy_under_test", loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_legacy_group_chat_id_translates_to_execution():
    tg = _load_tg()
    assert tg.translate(["-c", "-1003926592540", "msg"], "elliot") == [
        "-c",
        "execution",
        "msg",
    ]


def test_legacy_dm_chat_id_translates_to_ceo():
    tg = _load_tg()
    assert tg.translate(["-c", "7267788033", "msg"], "elliot") == ["-c", "ceo", "msg"]


def test_unknown_channel_id_passes_through_untranslated():
    """Anchor: LEGACY_TG_CHAT_MAP must not false-positive on real Slack IDs."""
    tg = _load_tg()
    assert tg.translate(["-c", "C0XXXXXX", "msg"], "elliot") == ["-c", "C0XXXXXX", "msg"]


def test_channel_flag_missing_arg_exits_2():
    tg = _load_tg()
    with pytest.raises(SystemExit) as excinfo:
        tg.translate(["-c"], "elliot")
    assert excinfo.value.code == 2
