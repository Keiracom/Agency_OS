"""Composer unit tests — Week 2 atomization pilot."""

from uuid import uuid4

import pytest

from src.keiracom_system.atomization.composer import (
    DEFAULT_MAX_ATOMS_IN_RESPONSE,
    DEFAULT_MIN_SCORE_FOR_INCLUSION,
    VALID_ENDPOINTS,
    ComposedOutput,
    Composer,
    ComposerError,
    select_provenance_trail,
)
from src.keiracom_system.atomization.retriever import RetrievalResult
from src.keiracom_system.atomization.schema import AtomV1


def _make_retrieval_result(
    *,
    content: str,
    score: float,
    anti_pattern: str | None = None,
    example: str | None = None,
) -> RetrievalResult:
    atom = AtomV1(
        atom_id=uuid4(),
        tenant_id=uuid4(),
        trigger_condition={"kind": "request_shape", "params": {"q": "x"}},
        content=content,
        anti_pattern=anti_pattern,
        example=example,
        provenance={
            "source": "test",
            "freshness": "2026-05-26T11:00:00Z",
            "confidence": 0.9,
            "last_validated": "2026-05-26T11:00:00Z",
        },
    )
    return RetrievalResult(atom=atom, score=score)


# ---- Construction + validation --------------------------------------------


def test_composer_rejects_zero_max_atoms():
    with pytest.raises(ComposerError, match="max_atoms must be > 0"):
        Composer(max_atoms=0)


def test_compose_rejects_unknown_endpoint():
    composer = Composer()
    with pytest.raises(ComposerError, match="not in"):
        composer.compose(atoms=[], endpoint="email")


def test_valid_endpoints_chat_reply_only_week_2():
    """Week 2 supports chat_reply only; other endpoints via Endpoint Translator."""
    assert frozenset({"chat_reply"}) == VALID_ENDPOINTS


# ---- Empty / no-confidence path -------------------------------------------


def test_compose_empty_atoms_returns_non_hallucinating_placeholder():
    composer = Composer()
    output = composer.compose_chat_reply(atoms=[], query_text="how do I X?")
    assert "don't have high-confidence knowledge" in output.text
    assert "how do I X?" in output.text
    assert output.atoms_used == []
    assert output.endpoint == "chat_reply"


def test_compose_no_query_text_placeholder_is_generic():
    composer = Composer()
    output = composer.compose_chat_reply(atoms=[], query_text=None)
    assert "don't have high-confidence knowledge" in output.text


def test_compose_below_min_score_treated_as_empty():
    composer = Composer(min_score=0.5)
    results = [_make_retrieval_result(content="low-score atom", score=0.1)]
    output = composer.compose_chat_reply(atoms=results, query_text="q")
    # All atoms below threshold → empty path triggers
    assert "don't have high-confidence knowledge" in output.text
    assert output.atoms_used == []


# ---- Happy paths ----------------------------------------------------------


def test_compose_single_atom_returns_content_verbatim():
    composer = Composer()
    results = [_make_retrieval_result(content="The answer is 42.", score=0.9)]
    output = composer.compose_chat_reply(atoms=results, query_text="what?")
    assert "The answer is 42." in output.text
    assert len(output.atoms_used) == 1


def test_compose_multi_atom_numbered_list_with_preamble():
    composer = Composer()
    results = [
        _make_retrieval_result(content="First fact.", score=0.9),
        _make_retrieval_result(content="Second fact.", score=0.8),
        _make_retrieval_result(content="Third fact.", score=0.7),
    ]
    output = composer.compose_chat_reply(atoms=results, query_text="tell me")
    # Numbered + with preamble (>1 atom)
    assert "Based on what I know" in output.text
    assert "1. First fact." in output.text
    assert "2. Second fact." in output.text
    assert "3. Third fact." in output.text
    assert len(output.atoms_used) == 3


def test_compose_renders_anti_pattern_when_present():
    composer = Composer()
    results = [
        _make_retrieval_result(
            content="Use bullet points for summaries.",
            score=0.9,
            anti_pattern="Returning a paragraph instead.",
        )
    ]
    output = composer.compose_chat_reply(atoms=results, query_text="how")
    assert "(Avoid: Returning a paragraph instead.)" in output.text


def test_compose_renders_example_when_present():
    composer = Composer()
    results = [
        _make_retrieval_result(
            content="Summarize as bullets.",
            score=0.9,
            example="Q: tell me about X. A: - point 1\n- point 2",
        )
    ]
    output = composer.compose_chat_reply(atoms=results, query_text="how")
    assert "Example:" in output.text
    assert "Q: tell me about X" in output.text


def test_compose_renders_only_first_line_of_multiline_example():
    composer = Composer()
    results = [
        _make_retrieval_result(
            content="Atom.",
            score=0.9,
            example="line one\nline two\nline three",
        )
    ]
    output = composer.compose_chat_reply(atoms=results)
    assert "Example: line one" in output.text
    # Second line of example NOT included in chat-reply rendering
    assert "line two" not in output.text


# ---- Truncation ------------------------------------------------------------


def test_compose_truncates_to_max_atoms_default():
    composer = Composer()
    assert DEFAULT_MAX_ATOMS_IN_RESPONSE == 5
    results = [_make_retrieval_result(content=f"atom {i}", score=0.9 - 0.01 * i) for i in range(10)]
    output = composer.compose_chat_reply(atoms=results, query_text="q")
    assert len(output.atoms_used) == 5
    assert output.truncated_count == 5


def test_compose_custom_max_atoms():
    composer = Composer(max_atoms=2)
    results = [_make_retrieval_result(content=f"a{i}", score=0.9) for i in range(5)]
    output = composer.compose_chat_reply(atoms=results, query_text="q")
    assert len(output.atoms_used) == 2
    assert output.truncated_count == 3


# ---- Defaults --------------------------------------------------------------


def test_default_min_score_for_inclusion():
    assert DEFAULT_MIN_SCORE_FOR_INCLUSION == 0.1


# ---- Provenance trail ------------------------------------------------------


def test_select_provenance_trail_returns_audit_dict():
    composer = Composer()
    results = [
        _make_retrieval_result(content="A.", score=0.9),
        _make_retrieval_result(content="B.", score=0.8),
    ]
    output = composer.compose_chat_reply(atoms=results, query_text="x")
    trail = select_provenance_trail(output)
    assert trail["endpoint"] == "chat_reply"
    assert len(trail["atoms_used"]) == 2
    assert trail["truncated_count"] == 0
    assert trail["text_length_chars"] > 0


# ---- Hard-constraint awareness --------------------------------------------


def test_composer_output_is_user_facing_string_only():
    """ComposedOutput.text MUST be a plain string for user-facing output.

    Hard constraint: Composer output never reaches agent reasoning input.
    The contract is enforced at the type level: ComposedOutput.text is str,
    not a structured atom-list. Agents that need atoms call MalRetriever
    directly — they don't (and can't sensibly) consume ComposedOutput.
    """
    composer = Composer()
    results = [_make_retrieval_result(content="a", score=0.9)]
    output = composer.compose_chat_reply(atoms=results)
    assert isinstance(output, ComposedOutput)
    assert isinstance(output.text, str)
    # Atoms list is for audit provenance, not for agent consumption
    assert isinstance(output.atoms_used, list)
    assert all(isinstance(x, str) for x in output.atoms_used)
