"""
FILE: tests/test_seed_facts.py
PURPOSE: Validate the curated CLAUDE.md fact list in seed_claude_md_facts.py
         before any real seeding run.

Tests:
- Fact count is between 20 and 50 (sanity bounds)
- Each fact has required fields
- No fact contains meta-instruction prose
- All facts carry the 'governance_doc' tag
"""

import importlib.util
import os
import sys

import pytest

# ---------------------------------------------------------------------------
# Load the FACTS list directly from the script without executing seed_all()
# ---------------------------------------------------------------------------
SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts",
    "seed_claude_md_facts.py",
)

spec = importlib.util.spec_from_file_location("seed_module", SCRIPT_PATH)
seed_module = importlib.util.module_from_spec(spec)

# Patch sys.modules so the import-time env/path setup doesn't blow up in CI
# (store import may fail without env — we only need the FACTS constant)
_store_was_loaded = "src.memory.store" in sys.modules
_store_backup = sys.modules.get("src.memory.store")
sys.modules.setdefault("src.memory.store", type(sys)("src.memory.store"))
sys.modules["src.memory.store"].store = lambda **kw: None  # type: ignore[attr-defined]

try:
    spec.loader.exec_module(seed_module)  # type: ignore[union-attr]
except Exception:
    # If store import fails (missing env), load the constants another way
    import ast

    with open(SCRIPT_PATH) as f:
        source = f.read()

    # Extract just the FACTS list via ast literal_eval on the assignment
    tree = ast.parse(source)
    facts_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "FACTS":
                    facts_node = node.value
    if facts_node is None:
        raise RuntimeError("Could not locate FACTS in seed_claude_md_facts.py")
    FACTS = ast.literal_eval(facts_node)
else:
    FACTS = seed_module.FACTS  # type: ignore[attr-defined]

# Cleanup: restore or remove the polluted sys.modules entry so memory tests
# get a fresh import of src.memory.store (prevents test pollution)
if _store_was_loaded and _store_backup is not None:
    sys.modules["src.memory.store"] = _store_backup
elif not _store_was_loaded and "src.memory.store" in sys.modules:
    del sys.modules["src.memory.store"]


# ---------------------------------------------------------------------------
# Required fields on every fact
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = {"content", "tags", "section"}

# ---------------------------------------------------------------------------
# Banned phrases — meta-instruction prose that must NOT appear in any fact
# ---------------------------------------------------------------------------
BANNED_PHRASES = [
    "Before ANY",
    "HARD BLOCK",
    "Wait for Dave",
    "Do not",
    "Never",
    "MUST",
    "Step 0",
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFactCount:
    def test_between_20_and_50_facts(self):
        count = len(FACTS)
        assert 20 <= count <= 50, (
            f"Expected 20–50 facts for a healthy curated seed set, got {count}. "
            "Too few means content was under-extracted; too many likely includes meta-prose."
        )


class TestRequiredFields:
    @pytest.mark.parametrize("idx,fact", list(enumerate(FACTS)))
    def test_fact_has_required_fields(self, idx, fact):
        missing = REQUIRED_FIELDS - set(fact.keys())
        assert not missing, f"Fact #{idx} missing required fields: {missing}\nFact: {fact}"

    @pytest.mark.parametrize("idx,fact", list(enumerate(FACTS)))
    def test_content_is_non_empty_string(self, idx, fact):
        assert isinstance(fact.get("content"), str) and fact["content"].strip(), (
            f"Fact #{idx} has empty or non-string content."
        )

    @pytest.mark.parametrize("idx,fact", list(enumerate(FACTS)))
    def test_tags_is_list(self, idx, fact):
        assert isinstance(fact.get("tags"), list), (
            f"Fact #{idx} tags must be a list, got {type(fact.get('tags'))}."
        )

    @pytest.mark.parametrize("idx,fact", list(enumerate(FACTS)))
    def test_section_is_non_empty_string(self, idx, fact):
        assert isinstance(fact.get("section"), str) and fact["section"].strip(), (
            f"Fact #{idx} has empty or non-string section."
        )


class TestNoMetaInstructionProse:
    @pytest.mark.parametrize("idx,fact", list(enumerate(FACTS)))
    def test_no_banned_phrases(self, idx, fact):
        content = fact.get("content", "")
        hits = [phrase for phrase in BANNED_PHRASES if phrase in content]
        assert not hits, (
            f"Fact #{idx} contains meta-instruction prose {hits!r}.\nContent: {content[:200]!r}"
        )


class TestGovernanceDocTag:
    @pytest.mark.parametrize("idx,fact", list(enumerate(FACTS)))
    def test_has_governance_doc_tag(self, idx, fact):
        tags = fact.get("tags", [])
        assert "governance_doc" in tags, f"Fact #{idx} missing 'governance_doc' tag. Tags: {tags}"

    @pytest.mark.parametrize("idx,fact", list(enumerate(FACTS)))
    def test_has_claude_md_tag(self, idx, fact):
        tags = fact.get("tags", [])
        assert "claude_md" in tags, f"Fact #{idx} missing 'claude_md' tag. Tags: {tags}"
