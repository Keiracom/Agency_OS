"""Three-tier governance loader — Agency_OS-ngw2 / KEI-ngw2.

Replaces the flat `@-import` auto-load chain in CLAUDE.md with a tier-aware
loader per Layered Governance Matrix v1 (ratified 2026-05-19).

Tiers:
  - HOT (always loaded, pre-prompt, ≤8000 tokens hard):
        slim CLAUDE.md + docs/governance/_hot_pointer_cache.md + IDENTITY.md
  - POINTER (lazy, on agent trigger via cognee_recall, ≤500 tokens/call):
        the agent passes a recall_key from _hot_pointer_cache.md; the
        loader runs cognee_recall and returns the top-N matched chunks.
  - REFERENCE (on-demand only):
        raw file content for a specific rule/persona document; counts
        against the cumulative session-recall budget (≤5000 tokens
        across all POINTER + REFERENCE fetches in one session).

Fail-loud per Layered Governance Matrix v1 §FAIL-LOUD SEMANTICS:
  Any budget violation raises GovernanceBudgetExceeded AND writes
  `FAIL-LOUD: <detail>` to stderr. Required-file-missing raises
  GovernanceConfigError. Callers MUST NOT silently swallow these.

Phase 1 (this PR): loader module + tests. The CLAUDE.md @-import chain
removal + SessionStart hook wiring is a Phase 2 follow-up KEI so the
mechanism + the call-site migration are reviewable separately.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

BUDGET_HOT_TOKENS = 8000
BUDGET_POINTER_PER_CALL_TOKENS = 500
BUDGET_SESSION_RECALL_TOKENS = 5000

# Same chars-per-token heuristic as scripts/governance/regen_hot_pointer_cache.py
# so HOT-tier accounting stays consistent across writer + loader.
CHARS_PER_TOKEN = 4


class GovernanceBudgetExceeded(RuntimeError):
    """Raised when a tier load would exceed its budget. Fail-loud — never swallow."""


class GovernanceConfigError(RuntimeError):
    """Raised when a required governance file is missing. Fail-loud."""


def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


def _fail_loud(detail: str, exc: type[Exception]) -> None:
    """Emit FAIL-LOUD marker to stderr and raise."""
    print(f"FAIL-LOUD: {detail}", file=sys.stderr)
    raise exc(detail)


def _default_cognee_recall(recall_key: str, repo_root: Path) -> str:
    """Default POINTER backend: shell out to scripts/cognee_recall.py.

    Wraps the existing CLI used by inbox-watcher delivery enrichment.
    The CLI is fail-open by contract — empty stdout means no hits or
    cognee unavailable. The loader's per-call budget still applies.
    """
    script = repo_root / "scripts" / "cognee_recall.py"
    if not script.exists():
        _fail_loud(f"cognee_recall script missing at {script}", GovernanceConfigError)
    python = shutil.which("python3") or "python3"
    proc = subprocess.run(
        [python, str(script), "--text", recall_key, "--limit", "5"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return proc.stdout


@dataclass
class GovernanceLoader:
    """Three-tier loader with budget enforcement + fail-loud semantics."""

    repo_root: Path
    callsign: str
    recall_fn: Callable[[str], str] | None = None
    _session_recall_used: int = field(default=0, init=False)

    # ------------------------------------------------------------------
    # HOT tier — always loaded into every session pre-prompt
    # ------------------------------------------------------------------

    def load_hot(self) -> str:
        """Concatenate the three HOT files and assert ≤8000 token budget."""
        identity = self.repo_root / "IDENTITY.md"
        cache = self.repo_root / "docs" / "governance" / "_hot_pointer_cache.md"
        claude_md = self.repo_root / "CLAUDE.md"

        for required in (identity, cache, claude_md):
            if not required.exists():
                _fail_loud(
                    f"HOT-tier required file missing: {required}",
                    GovernanceConfigError,
                )

        parts = [
            f"<!-- HOT TIER 1/3 — IDENTITY.md ({self.callsign}) -->\n",
            identity.read_text(),
            "\n<!-- HOT TIER 2/3 — _hot_pointer_cache.md -->\n",
            cache.read_text(),
            "\n<!-- HOT TIER 3/3 — CLAUDE.md -->\n",
            claude_md.read_text(),
        ]
        combined = "".join(parts)
        tokens = estimate_tokens(combined)
        if tokens > BUDGET_HOT_TOKENS:
            _fail_loud(
                f"HOT tier {tokens} tokens exceeds {BUDGET_HOT_TOKENS} budget. "
                f"Slim CLAUDE.md or trim _hot_pointer_cache.md before re-running.",
                GovernanceBudgetExceeded,
            )
        return combined

    # ------------------------------------------------------------------
    # POINTER tier — lazy, on agent trigger
    # ------------------------------------------------------------------

    def load_pointer(self, recall_key: str) -> str:
        """Fetch a POINTER-tier slice via cognee_recall by recall_key.

        Enforces per-call budget (≤500 tokens) AND cumulative
        session-recall budget (≤5000 tokens across all pointer+reference
        loads in this loader instance's lifetime).
        """
        recall_fn = self.recall_fn or (lambda k: _default_cognee_recall(k, self.repo_root))
        result = recall_fn(recall_key)
        tokens = estimate_tokens(result)
        if tokens > BUDGET_POINTER_PER_CALL_TOKENS:
            _fail_loud(
                f"POINTER recall_key={recall_key!r} returned {tokens} tokens "
                f"(>{BUDGET_POINTER_PER_CALL_TOKENS} per-call budget). "
                f"Tighten the recall key or split the underlying source.",
                GovernanceBudgetExceeded,
            )
        self._charge_session_recall(tokens, source=f"pointer:{recall_key}")
        return result

    # ------------------------------------------------------------------
    # REFERENCE tier — on-demand, raw file
    # ------------------------------------------------------------------

    def load_reference(self, rel_path: str) -> str:
        """Read a governance/reference file relative to repo_root.

        Counts toward the cumulative session-recall budget. No per-call
        cap (reference files are explicitly opt-in by the agent), but
        the session-cumulative cap still applies — pulling 6 KB of
        reference text uses ~1500 tokens of the 5000-token session
        budget.
        """
        target = self.repo_root / rel_path
        if not target.exists():
            _fail_loud(
                f"REFERENCE file missing: {rel_path}",
                GovernanceConfigError,
            )
        text = target.read_text()
        tokens = estimate_tokens(text)
        self._charge_session_recall(tokens, source=f"reference:{rel_path}")
        return text

    # ------------------------------------------------------------------
    # Session-recall budget accounting
    # ------------------------------------------------------------------

    @property
    def session_recall_used(self) -> int:
        return self._session_recall_used

    @property
    def session_recall_remaining(self) -> int:
        return BUDGET_SESSION_RECALL_TOKENS - self._session_recall_used

    def _charge_session_recall(self, tokens: int, *, source: str) -> None:
        proposed = self._session_recall_used + tokens
        if proposed > BUDGET_SESSION_RECALL_TOKENS:
            _fail_loud(
                f"session-recall total would reach {proposed} tokens "
                f"(>{BUDGET_SESSION_RECALL_TOKENS} budget) after charging "
                f"{tokens} tokens from {source}. Drop a previously-loaded "
                f"slice or end the session.",
                GovernanceBudgetExceeded,
            )
        self._session_recall_used = proposed
