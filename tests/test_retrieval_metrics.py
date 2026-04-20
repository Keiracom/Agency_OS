"""Tests for src/telegram_bot/retrieval_metrics.py"""

import pytest
from src.telegram_bot.retrieval_metrics import (
    STOPWORDS,
    tokenize,
    compute_cited_flags,
    compute_hit_rate,
    compute_mrr,
    compute_source_type_breakdown,
    generate_summary,
)


# ---------------------------------------------------------------------------
# tokenize
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_removes_stopwords(self):
        tokens = tokenize("what does this pipeline have")
        assert "what" not in tokens
        assert "does" not in tokens
        assert "this" not in tokens
        assert "have" not in tokens
        # 'pipeline' is a stopword too
        assert "pipeline" not in tokens

    def test_removes_short_words(self):
        tokens = tokenize("go run the big bat")
        # "go", "run", "the", "big", "bat" are all < 4 chars or stopwords
        assert tokens == []

    def test_keeps_meaningful_words(self):
        tokens = tokenize("quarterly revenue forecast")
        assert "quarterly" in tokens
        assert "revenue" in tokens
        assert "forecast" in tokens

    def test_lowercases(self):
        tokens = tokenize("QUARTERLY Revenue")
        assert "quarterly" in tokens
        assert "revenue" in tokens

    def test_strips_punctuation(self):
        tokens = tokenize("hello, world! testing.")
        assert "hello" in tokens
        assert "world" in tokens
        assert "testing" in tokens

    def test_alphanumeric_tokens_retained(self):
        tokens = tokenize("stage3 v2dot1 run")
        assert "stage3" in tokens
        assert "v2dot1" in tokens

    def test_callsigns_removed(self):
        tokens = tokenize("dave said elliot should recall the info")
        assert "dave" not in tokens
        assert "elliot" not in tokens
        assert "recall" not in tokens

    def test_empty_string(self):
        assert tokenize("") == []

    def test_returns_list(self):
        result = tokenize("quarterly revenue")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# compute_cited_flags
# ---------------------------------------------------------------------------

class TestComputeCitedFlags:
    def _make_row(self, row_id, content, source_type="core_fact"):
        return {"id": row_id, "content": content, "source_type": source_type}

    def test_cited_when_2_shared_tokens(self):
        rows = [self._make_row("r1", "quarterly revenue forecast growth")]
        response = "The quarterly revenue showed strong growth this period"
        flags = compute_cited_flags(rows, response)
        assert len(flags) == 1
        assert flags[0]["cited"] is True
        assert flags[0]["shared_tokens"] >= 2

    def test_not_cited_when_fewer_than_2_shared(self):
        rows = [self._make_row("r1", "quarterly revenue forecast")]
        response = "Nothing relevant here at all whatsoever"
        flags = compute_cited_flags(rows, response)
        assert flags[0]["cited"] is False
        assert flags[0]["shared_tokens"] < 2

    def test_exactly_1_shared_not_cited(self):
        rows = [self._make_row("r1", "quarterly revenue forecast")]
        # Only 'quarterly' in response
        response = "The quarterly results were mixed"
        flags = compute_cited_flags(rows, response)
        # 'quarterly' is the only shared meaningful token -> not cited
        assert flags[0]["shared_tokens"] <= 1
        assert flags[0]["cited"] is False

    def test_row_id_propagated(self):
        rows = [self._make_row("abc-123", "quarterly revenue forecast growth")]
        response = "quarterly revenue"
        flags = compute_cited_flags(rows, response)
        assert flags[0]["row_id"] == "abc-123"

    def test_source_type_propagated(self):
        rows = [self._make_row("r1", "quarterly revenue forecast growth", "daily_log")]
        response = "quarterly revenue growth projection"
        flags = compute_cited_flags(rows, response)
        assert flags[0]["source_type"] == "daily_log"

    def test_missing_id_defaults_to_unknown(self):
        rows = [{"content": "quarterly revenue forecast growth"}]
        response = "quarterly revenue growth"
        flags = compute_cited_flags(rows, response)
        assert flags[0]["row_id"] == "unknown"

    def test_missing_source_type_defaults_to_unknown(self):
        rows = [{"id": "r1", "content": "quarterly revenue forecast growth"}]
        response = "quarterly revenue growth"
        flags = compute_cited_flags(rows, response)
        assert flags[0]["source_type"] == "unknown"

    def test_multiple_rows(self):
        rows = [
            self._make_row("r1", "quarterly revenue forecast growth"),
            self._make_row("r2", "completely unrelated xyzzy bloop"),
        ]
        response = "The quarterly revenue growth surprised analysts"
        flags = compute_cited_flags(rows, response)
        assert flags[0]["cited"] is True
        assert flags[1]["cited"] is False

    def test_total_row_tokens_field_present(self):
        rows = [self._make_row("r1", "quarterly revenue forecast growth expansion")]
        response = "some text"
        flags = compute_cited_flags(rows, response)
        assert "total_row_tokens" in flags[0]
        assert flags[0]["total_row_tokens"] > 0

    def test_empty_rows_returns_empty(self):
        assert compute_cited_flags([], "some response") == []

    def test_empty_response(self):
        rows = [self._make_row("r1", "quarterly revenue forecast growth")]
        flags = compute_cited_flags(rows, "")
        assert flags[0]["cited"] is False
        assert flags[0]["shared_tokens"] == 0


# ---------------------------------------------------------------------------
# compute_hit_rate
# ---------------------------------------------------------------------------

class TestComputeHitRate:
    def _flags(self, cited_list):
        """Build a single retrieval's flags list from a list of booleans."""
        return [{"cited": c, "source_type": "core_fact"} for c in cited_list]

    def test_empty_list_returns_zero(self):
        assert compute_hit_rate([]) == 0.0

    def test_all_hits(self):
        data = [self._flags([True, False]), self._flags([True, True])]
        assert compute_hit_rate(data) == 1.0

    def test_all_misses(self):
        data = [self._flags([False, False]), self._flags([False])]
        assert compute_hit_rate(data) == 0.0

    def test_mixed(self):
        # 2 hits out of 4 retrievals
        data = [
            self._flags([True]),
            self._flags([False]),
            self._flags([False, True]),
            self._flags([False]),
        ]
        assert compute_hit_rate(data) == pytest.approx(0.5)

    def test_single_hit(self):
        data = [self._flags([True])]
        assert compute_hit_rate(data) == 1.0

    def test_single_miss(self):
        data = [self._flags([False])]
        assert compute_hit_rate(data) == 0.0


# ---------------------------------------------------------------------------
# compute_mrr
# ---------------------------------------------------------------------------

class TestComputeMRR:
    def _flags(self, cited_list):
        return [{"cited": c, "source_type": "core_fact"} for c in cited_list]

    def test_empty_list_returns_zero(self):
        assert compute_mrr([]) == 0.0

    def test_first_position_cited(self):
        # rank 1 -> reciprocal = 1.0
        data = [self._flags([True, False, False])]
        assert compute_mrr(data) == pytest.approx(1.0)

    def test_second_position_cited(self):
        # rank 2 -> reciprocal = 0.5
        data = [self._flags([False, True, False])]
        assert compute_mrr(data) == pytest.approx(0.5)

    def test_third_position_cited(self):
        # rank 3 -> reciprocal = 1/3
        data = [self._flags([False, False, True])]
        assert compute_mrr(data) == pytest.approx(1 / 3)

    def test_no_cited_contributes_zero(self):
        data = [self._flags([False, False, False])]
        assert compute_mrr(data) == pytest.approx(0.0)

    def test_mixed_retrievals(self):
        # retrieval 1: rank 1 -> 1.0; retrieval 2: no hit -> 0.0; average = 0.5
        data = [
            self._flags([True, False]),
            self._flags([False, False]),
        ]
        assert compute_mrr(data) == pytest.approx(0.5)

    def test_multiple_cited_uses_first(self):
        # Both rank 1 and 2 are cited — only rank 1 counts
        data = [self._flags([True, True, False])]
        assert compute_mrr(data) == pytest.approx(1.0)

    def test_average_across_three(self):
        # 1.0 + 0.5 + 0.0 = 1.5 / 3 = 0.5
        data = [
            self._flags([True]),
            self._flags([False, True]),
            self._flags([False, False]),
        ]
        assert compute_mrr(data) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# compute_source_type_breakdown
# ---------------------------------------------------------------------------

class TestComputeSourceTypeBreakdown:
    def _flag(self, source_type, cited):
        return {"cited": cited, "source_type": source_type}

    def test_empty_returns_empty_dict(self):
        assert compute_source_type_breakdown([]) == {}

    def test_single_type_all_cited(self):
        data = [[self._flag("core_fact", True), self._flag("core_fact", True)]]
        result = compute_source_type_breakdown(data)
        assert result["core_fact"]["cited"] == 2
        assert result["core_fact"]["total"] == 2

    def test_single_type_none_cited(self):
        data = [[self._flag("daily_log", False)]]
        result = compute_source_type_breakdown(data)
        assert result["daily_log"]["cited"] == 0
        assert result["daily_log"]["total"] == 1

    def test_multiple_types(self):
        data = [
            [self._flag("core_fact", True), self._flag("daily_log", False)],
            [self._flag("core_fact", False), self._flag("daily_log", True)],
        ]
        result = compute_source_type_breakdown(data)
        assert result["core_fact"]["cited"] == 1
        assert result["core_fact"]["total"] == 2
        assert result["daily_log"]["cited"] == 1
        assert result["daily_log"]["total"] == 2

    def test_aggregates_across_retrievals(self):
        data = [
            [self._flag("core_fact", True)],
            [self._flag("core_fact", True)],
            [self._flag("core_fact", False)],
        ]
        result = compute_source_type_breakdown(data)
        assert result["core_fact"]["cited"] == 2
        assert result["core_fact"]["total"] == 3


# ---------------------------------------------------------------------------
# generate_summary
# ---------------------------------------------------------------------------

class TestGenerateSummary:
    def _flags(self, cited_list, source_type="core_fact"):
        return [{"cited": c, "source_type": source_type} for c in cited_list]

    def test_returns_string(self):
        data = [self._flags([True])]
        result = generate_summary(data)
        assert isinstance(result, str)

    def test_contains_retrieval_count(self):
        data = [self._flags([True]), self._flags([False])]
        result = generate_summary(data)
        assert "2 retrievals" in result

    def test_contains_hit_rate(self):
        data = [self._flags([True]), self._flags([False])]
        result = generate_summary(data)
        assert "Hit Rate@5" in result

    def test_contains_mrr(self):
        data = [self._flags([True])]
        result = generate_summary(data)
        assert "MRR@5" in result

    def test_contains_source_type(self):
        data = [self._flags([True], "daily_log")]
        result = generate_summary(data)
        assert "daily_log" in result

    def test_empty_retrievals(self):
        result = generate_summary([])
        assert "0 retrievals" in result
        assert "Hit Rate@5: 0.0%" in result
        assert "MRR@5: 0.000" in result

    def test_100_percent_hit_rate_format(self):
        data = [self._flags([True])]
        result = generate_summary(data)
        assert "100.0%" in result

    def test_multiline_output(self):
        data = [
            self._flags([True], "core_fact"),
            self._flags([False, True], "daily_log"),
        ]
        result = generate_summary(data)
        lines = result.strip().split("\n")
        assert len(lines) >= 4  # header + hit rate + mrr + breakdown header + at least 1 type
