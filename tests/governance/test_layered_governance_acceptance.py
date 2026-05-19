"""Acceptance test fixture — Layered Governance Matrix v1.

Per Agency_OS-vib9 + matrix §ACCEPTANCE TEST. Five contract-shape tests
gating the layered-governance rollout. Each test class corresponds to
one of the 5 scenarios in matrix §ACCEPTANCE TEST.

Real implementations are separate KEIs (matrix §RATIFICATION PATH item 6):
- T1 HOT contents — runs against the live matrix doc (source of truth).
- T2 Pointer recall — awaits layered_governance_loader KEI.
- T3 Fail-loud — awaits fail_loud_recall_sentinel KEI (Cognee + Weaviate).
- T4 Freshness — awaits freshness_slo_probe KEI.
- T5 Layer 3 block — awaits pretooluse_hook_risky_op_enum KEI.

Tests use mocks that match the contract shape the real implementations
must satisfy. When implementations land, the mocks swap for real clients
and these tests become live regression gates. Per matrix
§RATIFICATION PATH item 7, all 5 must pass before agents flip to
layered model.
"""

from __future__ import annotations

import inspect
import re
import time
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MATRIX_PATH = REPO_ROOT / "docs" / "governance" / "layered_governance_matrix.md"

# Sentinels — implementations MUST emit these on failure
SENTINEL_RECALL_UNAVAILABLE = "[GOVERNANCE RECALL UNAVAILABLE"
SENTINEL_FRESHNESS_WARN = "[GOVERNANCE FRESHNESS WARNING"
SENTINEL_INDEX_DRIFT = "[GOVERNANCE INDEX DRIFT"
SENTINEL_HOT_OVERSIZE = "[HOT-TIER OVERSIZE"

# Token / latency budget contract (matrix §BUDGET RULES + appendix A.2)
HOT_HARD_CAP_TOKENS = 8_000
HOT_SOFT_TARGET_TOKENS = 6_500
POINTER_RECALL_HARD_TOKENS = 1_500
RECALL_LATENCY_HARD_SECONDS = 2.0
FRESHNESS_GOVERNANCE_SLO_SECONDS = 3_600.0  # ≤1h per matrix §FRESHNESS SLO


# ─── matrix parsing helpers (shared across tests) ───────────────────────────


@pytest.fixture(scope="module")
def matrix_text() -> str:
    assert MATRIX_PATH.exists(), f"matrix doc missing at {MATRIX_PATH}"
    return MATRIX_PATH.read_text()


@pytest.fixture(scope="module")
def hot_section(matrix_text: str) -> str:
    """Extract TIER 1 — HOT section content."""
    m = re.search(
        r"## TIER 1 — HOT.*?(?=\n## TIER 2 —)",
        matrix_text,
        re.DOTALL,
    )
    assert m, "matrix missing TIER 1 — HOT section"
    return m.group(0)


@pytest.fixture(scope="module")
def pointer_section(matrix_text: str) -> str:
    m = re.search(
        r"## TIER 2 — POINTER.*?(?=\n## TIER 3 —)",
        matrix_text,
        re.DOTALL,
    )
    assert m, "matrix missing TIER 2 — POINTER section"
    return m.group(0)


# ─── T1: HOT-only operation — every-action LAWs in HOT ──────────────────────


class TestT1HotOnlyOperation:
    """Scenario 1: HOT contains every-action LAWs.

    Contract: matrix §1.1-§1.7 must include IDENTITY, Step 0 RESTATE,
    the 5 prohibitions, the 5 imperatives, and the authority hierarchy.
    Without these in HOT, an agent operating with recall layer offline
    cannot satisfy ambient governance.
    """

    def test_identity_in_hot(self, hot_section: str) -> None:
        assert "IDENTITY.md" in hot_section

    def test_step0_in_hot(self, hot_section: str) -> None:
        assert "Step 0" in hot_section
        assert "Objective" in hot_section
        assert "Success criteria" in hot_section

    def test_prohibitions_in_hot(self, hot_section: str) -> None:
        for tag in ("P1", "P2", "P3", "P4", "P5"):
            assert f"| {tag} |" in hot_section, f"prohibition {tag} missing"

    def test_imperatives_in_hot(self, hot_section: str) -> None:
        for tag in ("I1", "I2", "I3", "I4", "I5"):
            assert f"| {tag} |" in hot_section, f"imperative {tag} missing"

    def test_authority_hierarchy_in_hot(self, hot_section: str) -> None:
        assert "Dave" in hot_section
        assert "Elliot" in hot_section
        assert "Workers" in hot_section or "Atlas" in hot_section

    def test_hot_total_under_hard_cap(self, hot_section: str) -> None:
        """HOT TIER TOTAL declared in §1.8 must be < 8k hard cap."""
        m = re.search(r"\*\*HOT total\*\*[^|]*\|\s*\*?\*?~?(\d+)", hot_section)
        assert m, "matrix missing HOT total token declaration"
        declared = int(m.group(1))
        assert declared < HOT_HARD_CAP_TOKENS, (
            f"HOT total {declared}t exceeds hard cap {HOT_HARD_CAP_TOKENS}t"
        )

    def test_hot_section_loadable_as_string(self, hot_section: str) -> None:
        """Smoke: HOT section is non-empty markdown loadable in <1ms."""
        start = time.monotonic()
        assert len(hot_section) > 1_000
        assert (time.monotonic() - start) < 0.001


# ─── T2: Pointer-recall — LAW VI text in budget + latency ───────────────────


class MockRecallClient:
    """Stand-in for layered_governance_loader recall API.

    Real implementation will hit Cognee/Weaviate. Contract: given a recall
    key, return text + token count + latency. Token count uses a 4-char-
    per-token approximation matching common tokeniser behaviour.
    """

    def __init__(
        self,
        content: dict[str, str],
        latency_seconds: float = 0.05,
    ) -> None:
        self._content = content
        self._latency = latency_seconds
        self.calls: list[str] = []

    def recall(self, key: str) -> dict[str, Any]:
        time.sleep(self._latency)
        self.calls.append(key)
        text = self._content.get(key, "")
        tokens = len(text) // 4
        return {"key": key, "text": text, "tokens": tokens}


class TestT2PointerRecall:
    """Scenario 2: recall(LAW VI) returns full text ≤1500t and <2s.

    Contract: POINTER entries' recall keys must return payloads under
    the token and latency caps.
    """

    LAW_VI_TEXT = (
        "LAW VI Skills-First Operations — use skill -> MCP -> exec hierarchy. "
        "Decision tree: (1) Skill exists -> use skill. (2) No skill, MCP "
        "available -> use MCP bridge. (3) No skill, no MCP -> use exec as last "
        "resort, then write a skill. Never call external services ad-hoc."
    )

    def test_law_vi_recall_returns_text(self) -> None:
        client = MockRecallClient({"law-vi": self.LAW_VI_TEXT})
        result = client.recall("law-vi")
        assert result["text"] == self.LAW_VI_TEXT

    def test_law_vi_recall_under_token_cap(self) -> None:
        client = MockRecallClient({"law-vi": self.LAW_VI_TEXT})
        result = client.recall("law-vi")
        assert result["tokens"] <= POINTER_RECALL_HARD_TOKENS

    def test_law_vi_recall_under_latency_cap(self) -> None:
        client = MockRecallClient({"law-vi": self.LAW_VI_TEXT}, latency_seconds=0.05)
        start = time.monotonic()
        client.recall("law-vi")
        elapsed = time.monotonic() - start
        assert elapsed < RECALL_LATENCY_HARD_SECONDS

    def test_pointer_index_declares_law_vi_key(self, pointer_section: str) -> None:
        assert "law-vi" in pointer_section.lower()


# ─── T3: Fail-loud — recall layer down does NOT silently proceed ────────────


class MockRecallClientDown:
    """Recall layer simulator in failed state.

    Real implementation: Cognee/Weaviate unreachable → raise with sentinel.
    Forbidden pattern: silent empty-return + agent proceeds with no recall.
    """

    def recall(self, key: str) -> dict[str, Any]:
        raise ConnectionError(
            f"{SENTINEL_RECALL_UNAVAILABLE} — recall layer unreachable, "
            f"requested key={key}, HOT-only mode"
        )


class TestT3FailLoud:
    """Scenario 3: recall failure surfaces sentinel, no silent proceed.

    Contract: when Cognee/Weaviate unreachable, recall MUST raise (or emit
    a payload containing GOVERNANCE RECALL UNAVAILABLE sentinel). Agent
    enters HOT-only mode + posts to elliot.inbox + #ceo per matrix
    §FAIL-LOUD SEMANTICS.
    """

    def test_recall_raises_on_layer_down(self) -> None:
        client = MockRecallClientDown()
        with pytest.raises(ConnectionError) as exc_info:
            client.recall("law-xii")
        assert SENTINEL_RECALL_UNAVAILABLE in str(exc_info.value)

    def test_fail_loud_never_returns_empty_silently(self) -> None:
        """The forbidden pattern: empty return + caller proceeds."""
        client = MockRecallClientDown()
        try:
            client.recall("law-xii")
            pytest.fail(
                "recall returned silently — fail-open mode forbidden "
                "per matrix §FAIL-LOUD SEMANTICS"
            )
        except ConnectionError as e:
            assert SENTINEL_RECALL_UNAVAILABLE in str(e)

    def test_matrix_declares_fail_loud_contract(self, matrix_text: str) -> None:
        """Matrix §FAIL-LOUD SEMANTICS must declare the sentinel + ban."""
        assert "GOVERNANCE RECALL UNAVAILABLE" in matrix_text
        lowered = matrix_text.lower()
        assert "no fail-open" in lowered or "never fail-open" in lowered

    def test_matrix_lists_all_4_sentinels(self, matrix_text: str) -> None:
        """All four sentinels referenced in matrix §FAIL-LOUD SEMANTICS."""
        for sentinel in (
            SENTINEL_RECALL_UNAVAILABLE,
            SENTINEL_FRESHNESS_WARN,
            SENTINEL_INDEX_DRIFT,
            SENTINEL_HOT_OVERSIZE,
        ):
            assert sentinel in matrix_text, f"sentinel missing: {sentinel}"


# ─── T4: Freshness — synthetic ratify at T=0 recalls at T=1h ────────────────


class MockIndexer:
    """Simulator for governance content indexer with controllable timestamps.

    Real implementation: indexer reads governance doc commits + writes
    rows to a search backend with `created_at` timestamps. Recall queries
    return both content + lag (now - created_at) for SLO checks.
    """

    def __init__(self) -> None:
        self._entries: dict[str, tuple[str, float]] = {}

    def ratify(self, key: str, text: str, ts: float) -> None:
        self._entries[key] = (text, ts)

    def recall(self, key: str, query_ts: float) -> dict[str, Any]:
        if key not in self._entries:
            raise KeyError(key)
        text, ratify_ts = self._entries[key]
        return {
            "key": key,
            "text": text,
            "lag_seconds": query_ts - ratify_ts,
        }


class TestT4Freshness:
    """Scenario 4: governance change at T=0 recallable at T=1h.

    Contract: per matrix §FRESHNESS SLO, governance docs index lag ≤1h.
    A synthetic ratify must be queryable at T=1h with the new text.
    """

    SIX_HOURS_SECONDS = 21_600.0

    def test_ratify_at_t0_recalls_at_t1h(self) -> None:
        indexer = MockIndexer()
        new_text = "LAW XX — synthetic ratified rule for freshness test."
        indexer.ratify("law-xx", new_text, ts=0.0)
        result = indexer.recall("law-xx", query_ts=FRESHNESS_GOVERNANCE_SLO_SECONDS)
        assert result["text"] == new_text
        assert result["lag_seconds"] <= FRESHNESS_GOVERNANCE_SLO_SECONDS

    def test_stale_recall_above_slo_detectable(self) -> None:
        """Recall at T=6h reports lag exceeding 1h SLO."""
        indexer = MockIndexer()
        indexer.ratify("law-xx", "text", ts=0.0)
        result = indexer.recall("law-xx", query_ts=self.SIX_HOURS_SECONDS)
        assert result["lag_seconds"] > FRESHNESS_GOVERNANCE_SLO_SECONDS

    def test_matrix_declares_governance_freshness_slo(self, matrix_text: str) -> None:
        m = re.search(r"Governance docs.*?≤\s*1\s*hour", matrix_text, re.DOTALL)
        assert m, "matrix §FRESHNESS SLO missing governance ≤1h declaration"

    def test_missing_key_raises_not_silently_returns(self) -> None:
        """Recall on non-existent key must raise — index-drift signal."""
        indexer = MockIndexer()
        with pytest.raises(KeyError):
            indexer.recall("nonexistent-key", query_ts=0.0)


# ─── T5: Layer 3 PreToolUse block — LAW XII violation ───────────────────────


class MockPreToolUseHook:
    """Simulator for the Layer-3 risky-op block hook (separate KEI).

    Real implementation: PreToolUse hook on tool-call boundary, matches
    against risky-op enum, recalls relevant LAW text, blocks or warns.
    """

    RISKY_DESTRUCTIVE_OPS = frozenset(
        {
            "git_push_force",
            "gh_pr_merge",
            "supabase_apply_migration",
            "rm_rf",
            "db_delete_no_where",
            "git_reset_hard",
        }
    )

    def __init__(self, recall_client: MockRecallClient) -> None:
        self._recall = recall_client
        self.blocks: list[tuple[str, str]] = []

    def on_tool_call(self, op: str, payload: str) -> dict[str, Any]:
        if op == "code_write" and "from src.integrations." in payload:
            recall_result = self._recall.recall("law-xii")
            self.blocks.append(("law-xii-violation", payload))
            return {
                "action": "block",
                "recall_key": "law-xii",
                "recall_text": recall_result["text"],
            }
        if op in self.RISKY_DESTRUCTIVE_OPS:
            self.blocks.append((f"{op}-destructive", payload))
            return {"action": "block", "recall_key": "law-xv-c"}
        return {"action": "allow"}


class TestT5Layer3Block:
    """Scenario 5: LAW XII violation triggers hook + block + recall.

    Contract: code write containing `from src.integrations.X import Y`
    outside skill execution triggers PreToolUse hook, blocks the op,
    surfaces LAW XII text via recall. Destructive ops in the risky-op
    enum also block.
    """

    LAW_XII_TEXT = (
        "LAW XII Skills-First Integration — direct calls to "
        "src/integrations/ outside skill execution are forbidden. "
        "Violation: log governance debt with type LAW_XII_VIOLATION."
    )

    def test_law_xii_violation_blocked(self) -> None:
        recall = MockRecallClient({"law-xii": self.LAW_XII_TEXT})
        hook = MockPreToolUseHook(recall)
        result = hook.on_tool_call(
            op="code_write",
            payload="from src.integrations.salesforge_client import send_email",
        )
        assert result["action"] == "block"
        assert result["recall_key"] == "law-xii"
        assert "LAW XII" in result["recall_text"]

    def test_law_xii_compliant_code_allowed(self) -> None:
        recall = MockRecallClient({"law-xii": self.LAW_XII_TEXT})
        hook = MockPreToolUseHook(recall)
        result = hook.on_tool_call(
            op="code_write",
            payload="from skills.salesforge import send_email",
        )
        assert result["action"] == "allow"

    def test_risky_destructive_op_blocked(self) -> None:
        recall = MockRecallClient({"law-xv-c": "destructive op LAW"})
        hook = MockPreToolUseHook(recall)
        result = hook.on_tool_call(op="rm_rf", payload="/")
        assert result["action"] == "block"

    def test_non_risky_op_allowed(self) -> None:
        recall = MockRecallClient({})
        hook = MockPreToolUseHook(recall)
        result = hook.on_tool_call(op="read_file", payload="/etc/hosts")
        assert result["action"] == "allow"

    def test_block_records_audit_trail(self) -> None:
        recall = MockRecallClient({"law-xii": self.LAW_XII_TEXT})
        hook = MockPreToolUseHook(recall)
        hook.on_tool_call(
            op="code_write",
            payload="from src.integrations.salesforge_client import send",
        )
        assert len(hook.blocks) == 1
        assert hook.blocks[0][0] == "law-xii-violation"

    def test_matrix_declares_layer3_risky_op_enum(self, matrix_text: str) -> None:
        """Matrix §LAYER 3 must enumerate the initial risky-op set."""
        for op in ("git_push_force", "rm_rf", "db_delete_no_where"):
            assert op in matrix_text, f"risky-op {op} missing from matrix"


# ─── meta: 5 scenarios covered + smoke ──────────────────────────────────────


def test_all_5_acceptance_scenarios_covered() -> None:
    """This file must contain a TestT1-T5 class for each matrix scenario."""
    this_module = inspect.getmodule(test_all_5_acceptance_scenarios_covered)
    classes = {
        name
        for name, _ in inspect.getmembers(this_module, inspect.isclass)
        if name.startswith("TestT")
    }
    expected = {
        "TestT1HotOnlyOperation",
        "TestT2PointerRecall",
        "TestT3FailLoud",
        "TestT4Freshness",
        "TestT5Layer3Block",
    }
    assert classes == expected, (
        f"acceptance test classes mismatch: expected {expected}, got {classes}"
    )


def test_matrix_doc_exists_and_loadable() -> None:
    assert MATRIX_PATH.exists()
    text = MATRIX_PATH.read_text()
    assert "Layered Governance Matrix" in text
    assert "ACCEPTANCE TEST" in text
