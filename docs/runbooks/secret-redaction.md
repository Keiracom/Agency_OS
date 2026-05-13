# Secret Redaction Middleware — Operator Runbook

**Module:** `src/memory/sanitise.py`
**KEI:** KEI-57
**Status:** Shipped. Integration deferred to KEI-46 / KEI-47 / KEI-48.

---

## What it does

`sanitise(text)` scans arbitrary text and replaces detected secrets with
`[REDACTED]` before the text is written to agent memory, passed to an
embedding model, or indexed into Weaviate.

`sanitise_with_audit(text, source, agent, kei)` does the same and also
returns a list of `audit_event` dicts — one per matched pattern — that the
caller persists to Supabase `audit_logs`.

---

## Where it integrates (5 capture sources, per Dave's KEI-57 spec)

Wiring ships in the pipeline KEIs listed. Do not wire here.

| # | Capture source | KEI |
|---|---|---|
| 1 | LlamaIndex document ingestion (pre-embed) | KEI-46 |
| 2 | Weaviate object write path | KEI-47 |
| 3 | Auto-indexing pipeline (cohort runner output) | KEI-48 |
| 4 | Agent memory `store()` call in `src/memory/store.py` | KEI-48 |
| 5 | Supabase `agent_memories` insert pre-hook | KEI-48 |

---

## How to add a new pattern

1. Open `src/memory/sanitise.py`.
2. Append a `(raw_regex, human_name)` tuple to `_RAW_PATTERNS`.
   - `raw_regex`: Python raw string, no anchors (it will be applied to the full text via `re.sub`).
   - `human_name`: snake_case, concise, goes into `audit_logs.pattern_matched`.
3. Add at least one positive test to `tests/memory/test_sanitise.py` in the `POSITIVE_CASES` list.
4. Add a negative test if the pattern risks false positives.
5. Run quality gates (see below). All must pass.

**Pattern ordering matters.** Longer / more-specific patterns should come
before shorter / more-general ones.  The `anthropic_key` pattern (`sk-ant-`)
appears before the generic `openai_or_anthropic_legacy_key` (`sk-`) for this
reason.

---

## How to read the audit log

Audit events are written to Supabase by the caller (the pipeline KEI that
wires `sanitise_with_audit`). Query example:

```sql
SELECT source, pattern_matched, agent, kei, redacted_at
FROM audit_logs
WHERE pattern_matched IS NOT NULL
ORDER BY redacted_at DESC
LIMIT 50;
```

`pattern_matched` is the human-readable name from `summarise_match()` — never
the raw regex string.

---

## False-positive vs false-negative tradeoff

| Concern | Impact | Mitigation |
|---|---|---|
| False negative (secret not caught) | Secret lands in embedding store / Weaviate | Add pattern + test, ship in same PR |
| False positive (legitimate text redacted) | Memory record becomes useless blob | Keep patterns narrow and prefix-anchored; test negatives |

The `[A-Z0-9/+]{40}` "AWS secret contextual" pattern from the original spec
was **omitted** because it matches SHA-1 hashes, compressed IDs, and
Supabase row IDs — causing false positives on nearly every memory record.
The `AKIA[0-9A-Z]{16}` AWS access key ID pattern (narrow, prefixed) and the
`env_file_secret` / `generic_secret_assignment` patterns together cover the
real AWS secret exposure cases without the blast radius.

---

## Quality gates (run before any PR on this module)

```bash
python -m pytest tests/memory/test_sanitise.py -v
ruff check src/memory/sanitise.py tests/memory/test_sanitise.py
mypy src/memory/sanitise.py
```

All three must be clean (zero failures, zero errors).
