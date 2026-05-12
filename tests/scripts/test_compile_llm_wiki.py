"""tests/scripts/test_compile_llm_wiki.py — hermetic tests for the LLM Wiki compiler.

Verifies:
  - generated output stays under the 2000-token cap (LAW: compressed cold-start brief)
  - all 11 expected section headers appear
  - tiktoken counter agrees with the script's own counter
  - --check exits 0 on healthy compile
  - compile_wiki() is pure (no side effects on disk)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "compile_llm_wiki.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("compile_llm_wiki", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["compile_llm_wiki"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_compile_under_token_cap():
    mod = _load_module()
    text = mod.compile_wiki()
    tokens = mod.count_tokens(text)
    assert tokens <= mod.TOKEN_CAP, (
        f"compiled wiki exceeds {mod.TOKEN_CAP}-token cap "
        f"(got {tokens}). Re-tune section budgets in compile_wiki()."
    )


def test_compile_has_all_expected_sections():
    mod = _load_module()
    text = mod.compile_wiki()
    missing = [h for h in mod.EXPECTED_SECTIONS if h not in text]
    assert not missing, f"missing section headers: {missing}"


def test_compile_is_pure_no_disk_writes(tmp_path, monkeypatch):
    """compile_wiki() must not write to disk — only main(--check)/main() writes."""
    mod = _load_module()
    monkeypatch.chdir(tmp_path)
    sentinel = tmp_path / "should_not_exist.md"
    monkeypatch.setattr(mod, "OUTPUT_PATH", sentinel)
    _ = mod.compile_wiki()
    assert not sentinel.exists()


def test_check_mode_exits_zero(capsys):
    mod = _load_module()
    rc = mod.main(["--check"])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert "tokens=" in captured.out
    assert "sections=11/11" in captured.out


def test_token_counter_uses_tiktoken_when_available():
    mod = _load_module()
    # tiktoken is in our requirements — assert we get a non-fallback count
    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")
    sample = "Agency OS — Compiled LLM Wiki test sentence."
    assert mod.count_tokens(sample) == len(enc.encode(sample))


def test_expected_sections_list_matches_emitted_text():
    """Guards against drift between EXPECTED_SECTIONS and compile_wiki() output."""
    mod = _load_module()
    text = mod.compile_wiki()
    # Every section in the list must appear; every "## N." in text must be in the list.
    emitted = [line for line in text.splitlines() if line.startswith("## ") and line[3:4].isdigit()]
    assert len(emitted) == len(mod.EXPECTED_SECTIONS)
    for header in emitted:
        # Trim the section title — only the "## N. Foo" prefix needs to match
        prefix = " ".join(header.split()[:2])  # "## 1." style
        assert any(h.startswith(prefix) for h in mod.EXPECTED_SECTIONS), (
            f"unexpected section emitted: {header!r}"
        )
