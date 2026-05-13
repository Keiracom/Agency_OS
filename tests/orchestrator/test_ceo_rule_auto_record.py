"""Tests for KEI-22 D7 — Slack-relay auto-rule-detect-and-record.

scripts/orchestrator/ceo_rule_auto_record.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "ceo_rule_auto_record.py"
_spec = importlib.util.spec_from_file_location("ceo_rule_auto_record", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["ceo_rule_auto_record"] = mod
_spec.loader.exec_module(mod)


CEO_CH = "C0B2PM3TV0B"
EXEC_CH = "C0B3QB0K1GQ"


# ─── should_fire filter chain ──────────────────────────────────────────


def test_fires_on_dave_ceo_with_standing_rule():
    fire, reason = mod.should_fire(
        channel=CEO_CH,
        author="dave",
        body="Standing rule: Linear is the only source of work.",
    )
    assert fire is True
    assert reason == "governance_trigger_matched"


def test_does_not_fire_outside_ceo_channel():
    fire, reason = mod.should_fire(
        channel=EXEC_CH,
        author="dave",
        body="Standing rule: x.",
    )
    assert fire is False
    assert reason == "wrong_channel"


def test_does_not_fire_for_non_dave_author():
    """Standing rules can only be established by Dave."""
    for author in ("elliot", "aiden", "max", "orion", "atlas", "scout"):
        fire, reason = mod.should_fire(
            channel=CEO_CH,
            author=author,
            body="Standing rule: x.",
        )
        assert fire is False, f"{author} should not establish rules"
        assert reason == "not_dave"


def test_does_not_fire_without_trigger_phrase():
    fire, reason = mod.should_fire(
        channel=CEO_CH,
        author="dave",
        body="Just a chat message, nothing rule-shaped.",
    )
    assert fire is False
    assert reason == "no_trigger_phrase"


def test_each_documented_trigger_phrase_fires():
    """Pins every Dave trigger phrase from the dispatch."""
    for phrase in (
        "standing rule",
        "effective immediately",
        "from now on",
        "no exceptions",
        "hard stop",
        "no build without",
        "must be recorded",
    ):
        fire, _ = mod.should_fire(
            channel=CEO_CH,
            author="Dave",  # case-insensitive
            body=f"prelude. {phrase} the rest.",
        )
        assert fire is True, f"trigger missed: {phrase!r}"


# ─── slug resolution ───────────────────────────────────────────────────


def test_slug_explicit_cli_arg_wins():
    slug = mod.resolve_slug(slug_arg="linear_only_source_of_work", body="body text")
    assert slug == "linear_only_source_of_work"


def test_slug_explicit_in_body_when_no_cli_arg():
    body = "Standing rule. Key pattern: ceo:rule:beads_layer3_enforcement."
    slug = mod.resolve_slug(slug_arg=None, body=body)
    assert slug == "beads_layer3_enforcement"


def test_slug_heuristic_after_trigger_phrase():
    """When neither --slug nor ceo:rule:<x> in body, derive from words after
    the trigger phrase."""
    slug = mod.resolve_slug(
        slug_arg=None,
        body="From now on agents claim before build. No exceptions.",
    )
    # Heuristic: first 6 content words after "from now on" → "agents_claim_before_build_no_exceptions"
    # (stopwords stripped).
    assert "agents" in slug
    assert "claim" in slug
    assert "build" in slug


def test_slug_normaliser_strips_special_chars():
    slug = mod.resolve_slug(slug_arg="Linear-Only Source / Work", body="")
    assert slug == "linear_only_source_work"


# ─── record_rule end-to-end ────────────────────────────────────────────


def test_record_writes_to_ceo_memory_when_fires():
    writes: list[tuple[str, dict]] = []

    def fake_upsert(key, value):
        writes.append((key, value))
        return True

    result = mod.record_rule(
        channel=CEO_CH,
        author="dave",
        body="Standing rule: Linear is the only source of work. No exceptions.",
        slug_arg="linear_only_source_of_work",
        upsert_fn=fake_upsert,
    )
    assert result["fired"] is True
    assert result["key"] == "ceo:rule:linear_only_source_of_work"
    assert result["reason"] == "recorded"
    assert len(writes) == 1
    key, value = writes[0]
    assert key == "ceo:rule:linear_only_source_of_work"
    assert value["author"] == "dave"
    assert value["channel"] == CEO_CH
    assert "Linear is the only source of work" in value["rule_body"]
    assert value["source"] == "kei22_d7_auto_record"


def test_record_does_not_write_when_filter_rejects():
    writes: list[tuple[str, dict]] = []

    result = mod.record_rule(
        channel=EXEC_CH,  # wrong channel
        author="dave",
        body="Standing rule: x.",
        upsert_fn=lambda k, v: writes.append((k, v)) or True,
    )
    assert result["fired"] is False
    assert result["reason"] == "wrong_channel"
    assert writes == []


def test_record_write_failure_returns_fired_false_with_reason():
    """upsert returning False → fired=False, reason='write_failed'. Relay
    can retry on the next dispatch."""
    result = mod.record_rule(
        channel=CEO_CH,
        author="dave",
        body="Standing rule: x.",
        upsert_fn=lambda k, v: False,
    )
    assert result["fired"] is False
    assert result["reason"] == "write_failed"
    assert result["key"] == "ceo:rule:x"


def test_record_write_exception_is_caught():
    def boom(k, v):
        raise RuntimeError("supabase 503")

    result = mod.record_rule(
        channel=CEO_CH,
        author="dave",
        body="Standing rule: x.",
        upsert_fn=boom,
    )
    assert result["fired"] is False
    assert result["reason"].startswith("write_failed")


def test_record_value_carries_full_body_for_audit():
    """Audit trail: the full Dave message body is persisted under
    'rule_body' so future agents can read the exact verbatim language."""
    writes: list[tuple[str, dict]] = []
    body = (
        "Standing rule. Beads must become Layer 3 — infrastructure physically "
        "refuses non-compliant actions. Not Layer 2 voluntary tracking. No exceptions."
    )
    mod.record_rule(
        channel=CEO_CH,
        author="dave",
        body=body,
        slug_arg="beads_layer3_enforcement",
        upsert_fn=lambda k, v: writes.append((k, v)) or True,
    )
    assert "Layer 3" in writes[0][1]["rule_body"]
    assert "voluntary tracking" in writes[0][1]["rule_body"]


# ─── CLI main() with --body-file ───────────────────────────────────────


def test_main_body_file_path(tmp_path, capsys, monkeypatch):
    body_file = tmp_path / "msg.txt"
    body_file.write_text("Standing rule: from now on, no exceptions.")
    # Patch the default upsert so it doesn't try Supabase.
    monkeypatch.setattr(mod, "_default_upsert_fn", lambda k, v: True)

    rc = mod.main(
        [
            "--channel",
            CEO_CH,
            "--author",
            "dave",
            "--body-file",
            str(body_file),
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["fired"] is True
    assert payload["key"].startswith("ceo:rule:")


def test_main_returns_zero_even_when_filter_rejects(capsys):
    """Slack relay calls this on every Dave post — must exit 0 always so
    the relay doesn't error-loop."""
    rc = mod.main(
        [
            "--channel",
            EXEC_CH,
            "--author",
            "elliot",
            "--body",
            "Standing rule: but wrong author + channel.",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["fired"] is False
