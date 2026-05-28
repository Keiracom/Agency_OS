"""Wave 6 — continuous adversarial retrieval probe suite.

Asks a fixed battery of *known* questions against the live memory layer
(`agent_query.query`) and verifies that the relevant memories surface — and,
just as importantly, that content which should NOT surface (superseded
material, another tenant's data) stays out of the result set.

Two layers live here:

  1. **Harness layer (always runs, no network).** The pure probe-evaluation
     logic (`evaluate_probe` / `evaluate_all` / `precision`) is unit-tested
     with an injected fake `query_fn`, including a synthetic-offender
     negative-path test. This guarantees the gate's own logic is correct even
     in hermetic CI where no Hindsight instance exists.

  2. **Live layer (skips without a live Hindsight).** Parametrised probes +
     an aggregate precision gate that hit the real retrieval path. Gated on
     the `HINDSIGHT_URL` env var per the Wave 6 dispatch.

Env-var reconciliation (GOV-9 gap, resolved in-PR): the orchestrator reads
`HINDSIGHT_BASE` (default `http://localhost:8889`). The dispatch specifies the
probe's opt-in signal as `HINDSIGHT_URL` ("skip if HINDSIGHT_URL not set") —
an operator's explicit "there is a live instance to probe" flag. When set, the
`live_hindsight` fixture points `orchestrator.HINDSIGHT_BASE` at that URL for
the probe's duration, so the two names cannot drift.

Corpus-calibration note (GOV-9 gap): the `expected_contains` substrings are
best-effort calibration targets keyed off known-canonical governance facts and
discovery-log lessons. They are tuned against the live corpus over time; the
CI gate is non-blocking (warning) initially precisely so miscalibration cannot
break the build before the corpus is characterised (cf. the FlashRank
characterisation baseline, PR #1241). It upgrades to blocking at cutover via
`RETRIEVAL_PROBE_BLOCKING` (see scripts/ci/check_retrieval_probe.py).
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from src.retrieval import agent_query, orchestrator

PROBE_AGENT = "wave6-adversarial-probe"
HINDSIGHT_URL_ENV = "HINDSIGHT_URL"
# Aggregate pass-rate the live suite must hold. Conservative while the corpus
# is being characterised; raise toward 1.0 as probes are tuned.
PRECISION_THRESHOLD = float(os.environ.get("RETRIEVAL_PROBE_THRESHOLD", "0.70"))

CATEGORIES: tuple[str, ...] = (
    "governance",
    "past_failure",
    "canonical",
    "superseded",
    "tenant_isolation",
)

# A tenant slug that is NOT the fleet's — used by the isolation probes to prove
# a foreign tenant's query never returns fleet-tenant content.
FOREIGN_TENANT_SLUG = "probe-isolation-tenant-x"

QueryFn = Callable[..., agent_query.QueryResult]


@dataclass(frozen=True)
class Probe:
    """One adversarial probe.

    `expected_contains` substrings must ALL appear (case-insensitive) in the
    TOP result's haystack (source_id + collection + excerpt + synthesised
    answer). `should_not_contain` substrings must appear in NONE of the
    returned results' haystacks. Either tuple may be empty — an isolation
    negative probe carries only `should_not_contain`.
    """

    name: str
    category: str
    query: str
    expected_contains: tuple[str, ...] = ()
    should_not_contain: tuple[str, ...] = ()
    tenant_id: str = orchestrator.FLEET_TENANT_SLUG
    collections: tuple[str, ...] | None = None


@dataclass(frozen=True)
class ProbeResult:
    name: str
    category: str
    passed: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    top_source_id: str = ""
    citation_count: int = 0


# ─── Probe battery (10) ──────────────────────────────────────────────────────
# governance(3) + past_failure(2) + canonical(2) + superseded(1) +
# tenant_isolation(2 = foreign negative + fleet positive control) = 10.
PROBES: tuple[Probe, ...] = (
    Probe(
        name="gov_merge_pattern",
        category="governance",
        query="What is the approved process for merging a pull request to main?",
        expected_contains=("concur",),
    ),
    Probe(
        name="gov_australia_currency",
        category="governance",
        query="What currency must all financial outputs use?",
        expected_contains=("aud",),
    ),
    Probe(
        name="gov_callsign_discipline",
        category="governance",
        query="What must every PR title and commit message be tagged with?",
        expected_contains=("callsign",),
    ),
    Probe(
        name="fail_ulimit_oom",
        category="past_failure",
        query="Why did capping virtual memory with ulimit cause a false OOM, and what works instead?",
        expected_contains=("cgroup",),
    ),
    Probe(
        name="fail_min_score_filter",
        category="past_failure",
        query="Why did the retrieval min_score hard filter return zero citations?",
        expected_contains=("score",),
    ),
    Probe(
        name="canon_hindsight_recall",
        category="canonical",
        query="How does the retrieval orchestrator source memories at recall time?",
        expected_contains=("hindsight",),
    ),
    Probe(
        name="canon_memory_engine",
        category="canonical",
        query="What engine backs the memory abstraction layer?",
        expected_contains=("hindsight",),
    ),
    Probe(
        name="superseded_memory_store",
        category="superseded",
        query="Where is persistent agent memory stored today?",
        expected_contains=("hindsight",),
        # Deprecated file-based store must not be returned as the answer.
        should_not_contain=("memory.md",),
    ),
    Probe(
        name="tenant_isolation_foreign",
        category="tenant_isolation",
        query="What is the approved process for merging a pull request to main?",
        # Foreign tenant must see NONE of these fleet-specific markers.
        should_not_contain=("nats concur", "orchestrator-merge", "admin-bypass"),
        tenant_id=FOREIGN_TENANT_SLUG,
    ),
    Probe(
        name="tenant_isolation_fleet_control",
        category="tenant_isolation",
        # Same query from the fleet tenant — positive control proving the
        # content EXISTS under fleet, so the foreign probe's absence is true
        # isolation and not merely an empty corpus.
        query="What is the approved process for merging a pull request to main?",
        expected_contains=("concur",),
    ),
)


# ─── Pure harness logic (shared with scripts/ci/check_retrieval_probe.py) ─────


def _haystack(citation: agent_query.Citation) -> str:
    return f"{citation.source_id} {citation.collection} {citation.excerpt}".lower()


def evaluate_probe(probe: Probe, query_fn: QueryFn) -> ProbeResult:
    """Run one probe through `query_fn` and check expected / forbidden content."""
    result = query_fn(probe.query, tenant_id=probe.tenant_id, collections=probe.collections)
    citations = result.citations
    answer = (result.answer or "").lower()
    top_hay = (answer + " " + _haystack(citations[0])) if citations else answer
    all_hay = answer + " " + " ".join(_haystack(c) for c in citations)

    reasons: list[str] = []
    for needle in probe.expected_contains:
        if needle.lower() not in top_hay:
            reasons.append(f"expected '{needle}' missing from top result")
    for forbidden in probe.should_not_contain:
        if forbidden.lower() in all_hay:
            reasons.append(f"forbidden '{forbidden}' present in results")

    return ProbeResult(
        name=probe.name,
        category=probe.category,
        passed=not reasons,
        reasons=tuple(reasons),
        top_source_id=citations[0].source_id if citations else "",
        citation_count=len(citations),
    )


def evaluate_all(query_fn: QueryFn, probes: tuple[Probe, ...] = PROBES) -> tuple[ProbeResult, ...]:
    return tuple(evaluate_probe(p, query_fn) for p in probes)


def precision(results: tuple[ProbeResult, ...]) -> float:
    """Fraction of probes that passed (0.0 for an empty result set)."""
    if not results:
        return 0.0
    return sum(1 for r in results if r.passed) / len(results)


def real_query(
    text: str, *, tenant_id: str, collections: tuple[str, ...] | None
) -> agent_query.QueryResult:
    """Adapter binding `agent_query.query` to the QueryFn protocol."""
    kwargs: dict = {"agent": PROBE_AGENT, "tenant_id": tenant_id}
    if collections is not None:
        kwargs["collections"] = collections
    return agent_query.query(text, **kwargs)


# ─── Harness unit tests (always run — no live Hindsight required) ─────────────


def _mk_result(*triples: tuple[str, str, str]) -> agent_query.QueryResult:
    """Build a QueryResult from (source_id, excerpt, collection) triples."""
    cits = tuple(
        agent_query.Citation(source_id=s, collection=c, score=0.9, excerpt=e)
        for (s, e, c) in triples
    )
    answer = f"{cits[0].excerpt} (sources)" if cits else ""
    return agent_query.QueryResult(answer=answer, citations=cits, elapsed_ms=1, bypass_rerank=True)


def test_evaluate_probe_passes_when_expected_in_top():
    probe = Probe("p", "governance", "q", expected_contains=("concur",))
    fn = lambda *a, **k: _mk_result(("D-1", "two-of-three NATS concur required", "Decisions"))  # noqa: E731
    res = evaluate_probe(probe, fn)
    assert res.passed
    assert res.reasons == ()
    assert res.top_source_id == "D-1"


def test_evaluate_probe_fails_when_expected_missing():
    probe = Probe("p", "governance", "q", expected_contains=("concur",))
    fn = lambda *a, **k: _mk_result(("D-1", "an unrelated memory", "Decisions"))  # noqa: E731
    res = evaluate_probe(probe, fn)
    assert not res.passed
    assert any("missing" in r for r in res.reasons)


def test_evaluate_probe_fails_on_forbidden_present_synthetic_offender():
    """Negative path: a regression where deprecated file-based store resurfaces."""
    probe = Probe("p", "superseded", "q", should_not_contain=("memory.md",))
    fn = lambda *a, **k: _mk_result(("F-1", "store memory in MEMORY.md file", "Decisions"))  # noqa: E731
    res = evaluate_probe(probe, fn)
    assert not res.passed
    assert any("forbidden" in r for r in res.reasons)


def test_isolation_probe_passes_when_foreign_tenant_returns_nothing():
    probe = Probe(
        "iso",
        "tenant_isolation",
        "q",
        should_not_contain=("nats concur", "dave"),
        tenant_id=FOREIGN_TENANT_SLUG,
    )
    fn = lambda *a, **k: _mk_result()  # empty — foreign tenant has no fleet content  # noqa: E731
    res = evaluate_probe(probe, fn)
    assert res.passed
    assert res.citation_count == 0


def test_isolation_probe_fails_on_cross_tenant_leak():
    probe = Probe(
        "iso",
        "tenant_isolation",
        "q",
        should_not_contain=("nats concur",),
        tenant_id=FOREIGN_TENANT_SLUG,
    )
    fn = lambda *a, **k: _mk_result(("LEAK-1", "fleet rule: NATS concur two-of-three", "Decisions"))  # noqa: E731
    res = evaluate_probe(probe, fn)
    assert not res.passed


def test_query_fn_receives_probe_tenant_and_collections():
    captured: dict = {}

    def fn(text, *, tenant_id, collections):
        captured.update(text=text, tenant_id=tenant_id, collections=collections)
        return _mk_result(("D-1", "x", "Decisions"))

    probe = Probe("p", "canonical", "the query", tenant_id="t-123", collections=("Decisions",))
    evaluate_probe(probe, fn)
    assert captured == {"text": "the query", "tenant_id": "t-123", "collections": ("Decisions",)}


def test_precision_is_pass_fraction():
    results = (
        ProbeResult("a", "governance", True),
        ProbeResult("b", "governance", False, reasons=("r",)),
        ProbeResult("c", "canonical", True),
        ProbeResult("d", "canonical", True),
    )
    assert precision(results) == 0.75


def test_precision_empty_is_zero():
    assert precision(()) == 0.0


def test_evaluate_all_runs_every_probe():
    fn = lambda *a, **k: _mk_result(("X", "y", "Decisions"))  # noqa: E731
    results = evaluate_all(fn)
    assert len(results) == len(PROBES)
    assert {r.name for r in results} == {p.name for p in PROBES}


# ─── Probe-battery shape tests (always run) ───────────────────────────────────


def test_probe_battery_is_ten():
    assert len(PROBES) == 10


def test_probe_names_unique():
    names = [p.name for p in PROBES]
    assert len(names) == len(set(names))


def test_probe_battery_covers_all_categories():
    assert {p.category for p in PROBES} == set(CATEGORIES)


def test_superseded_probe_guards_against_deprecated_content():
    superseded = [p for p in PROBES if p.category == "superseded"]
    assert superseded
    assert all(p.should_not_contain for p in superseded)


def test_tenant_isolation_has_foreign_negative_and_fleet_control():
    iso = [p for p in PROBES if p.category == "tenant_isolation"]
    foreign = [p for p in iso if p.tenant_id != orchestrator.FLEET_TENANT_SLUG]
    fleet = [p for p in iso if p.tenant_id == orchestrator.FLEET_TENANT_SLUG]
    # foreign probe forbids fleet markers; fleet control expects fleet content
    assert foreign and all(p.should_not_contain for p in foreign)
    assert fleet and all(p.expected_contains for p in fleet)


# ─── Live layer (skips without a live Hindsight) ──────────────────────────────


def _live_base() -> str | None:
    base = os.environ.get(HINDSIGHT_URL_ENV)
    return base or None


@pytest.fixture(scope="module")
def live_hindsight():
    """Point the orchestrator at the operator-specified live Hindsight.

    Skips the entire live layer when `HINDSIGHT_URL` is unset (hermetic CI,
    local dev without a memory layer). Restores the prior base on teardown so
    the override never leaks into other test modules.
    """
    base = _live_base()
    if not base:
        pytest.skip(f"{HINDSIGHT_URL_ENV} not set — adversarial probe needs a live Hindsight")
    prev = orchestrator.HINDSIGHT_BASE
    orchestrator.HINDSIGHT_BASE = base
    yield base
    orchestrator.HINDSIGHT_BASE = prev


@pytest.mark.parametrize("probe", PROBES, ids=lambda p: p.name)
def test_probe_live(probe: Probe, live_hindsight):
    res = evaluate_probe(probe, real_query)
    assert res.passed, (
        f"{probe.name} ({probe.category}): {'; '.join(res.reasons)} "
        f"[top={res.top_source_id!r}, n={res.citation_count}]"
    )


def test_live_precision_meets_threshold(live_hindsight):
    results = evaluate_all(real_query)
    score = precision(results)
    failing = [r.name for r in results if not r.passed]
    assert score >= PRECISION_THRESHOLD, (
        f"precision {score:.0%} < threshold {PRECISION_THRESHOLD:.0%}; failing probes: {failing}"
    )
