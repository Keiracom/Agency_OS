"""skill_gen — Drevon PR-B internal tooling.

Reads a directive-bounded slice of session_store turn_logs, compresses to a
prompt, invokes the `claude` CLI with `--no-hooks` to synthesise a SKILL.md,
writes the result to skills/<derived-name>/SKILL.md, and opens a PR for human
review. OAuth-only — no API key required, $0 incremental cost under Max plan.

Not part of the Agency OS pipeline. Pipeline (Stage 7/10/keyword_expander/
anthropic_batch) stays on the API; this module is internal tooling.
"""
