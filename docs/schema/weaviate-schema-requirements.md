# Weaviate Schema Requirements

**Status:** Pre-deployment specification (Weaviate not yet installed — KEI-46 / Linear KEI-48)
**KEI:** KEI-60 (Linear: https://linear.app/keiracom/issue/KEI-62)
**Author:** Elliot (COO) — 2026-05-14
**Authority:** Dave (CEO), ratified via KEI-60 spec

---

## Purpose

This document defines the mandatory properties, naming conventions, and embedding model
pinning requirements for every Weaviate collection deployed in Agency OS. It must be
read before any collection is created or migrated. It is the pre-condition for KEI-46.

---

## Required Properties — Every Collection

Every Weaviate collection MUST include these four properties. No exceptions.

| Property | Type | Required | Description |
|---|---|---|---|
| `raw_text` | `text` | Yes | Sanitised source text used to generate the object's vector. Must always be populated. Empty string is a schema violation. |
| `environment_hash` | `text` | Yes | SHA-256 hex string of the full execution context at write time (see structure below). Enables reproducible re-embedding. |
| `created_at` | `date` | Yes | ISO-8601 timestamp of when the object was written, in UTC. Format: `YYYY-MM-DDTHH:MM:SSZ`. |
| `agent` | `text` | Yes | Callsign of the agent or system that wrote the object (e.g. `elliot`, `aiden`, `atlas`, `system`). |
| `kei` | `text` | No | KEI issue ID that triggered the write (e.g. `KEI-48`), or null if system-generated outside a KEI context. |

### Why `raw_text` Is Mandatory

The re-embedding migration script (`scripts/re_embed_corpus.py`) reads `raw_text` to
regenerate vectors when the embedding model is upgraded. If `raw_text` is absent, the
object cannot be re-embedded without fetching the source again — which may not be
possible (deleted record, vendor API change, etc.). Populate `raw_text` at write time,
every time, no exceptions.

---

## `environment_hash` JSON Structure

The `environment_hash` field stores a SHA-256 hex string. The preimage is the
canonical JSON of the following structure (produced by `src/memory/environment_hash.py`):

```json
{
  "infrastructure": "<socket.gethostname()>",
  "container_runtime": "<docker/<version> | host>",
  "os": "<platform.system()>/<platform.release()>",
  "embedding_model": "<pinned model version from AGENCY_OS_EMBEDDING_MODEL env>",
  "key_software": {
    "cognee": "<importlib.metadata version or 'unknown'>",
    "weaviate": "<importlib.metadata version or 'unknown'>"
  }
}
```

The `hash` field itself is NOT part of the preimage. Canonical JSON uses
`sort_keys=True` and no extra whitespace (`separators=(",", ":")`).

Call `src.memory.environment_hash.get_environment_hash()` at write time and store
the returned `"hash"` value in the `environment_hash` property.

---

## Embedding Model Pinning Convention

**Rule: NEVER use a floating alias like `gemini-embedding` or `text-embedding-ada`. Always
pin to an explicit versioned model string.**

Correct examples:

```
gemini-embedding-001
text-embedding-3-small
text-embedding-3-large
```

Incorrect (must not use):

```
gemini-embedding        # floating — model can change under you
text-embedding-ada      # floating — deprecated but still resolves
latest                  # explicitly forbidden
```

Set the pinned model in the `AGENCY_OS_EMBEDDING_MODEL` environment variable. The
`environment_hash` module reads this value and bakes it into every object's hash, so
a model change is always detectable by comparing hashes across objects.

When upgrading the embedding model:

1. Update `AGENCY_OS_EMBEDDING_MODEL` in Railway environment variables.
2. Run `scripts/re_embed_corpus.py --dry-run False` to migrate existing objects.
3. Verify spot-checks pass (10/10 queries return results).
4. Update this document's "Current pinned model" field below.

**Current pinned model:** (to be set when KEI-46 deploys Weaviate)

---

## Insurance Policy — re_embed_corpus.py

`scripts/re_embed_corpus.py` is the migration script written pre-deployment as the
"insurance policy" Dave specified in KEI-60. It must be:

- **Run in dry-run mode first** (`--dry-run True`, the default) to count objects and
  validate connectivity before any mutation.
- **Run in live mode only with explicit `--dry-run False`** to prevent accidental corpus
  mutation.

The script reads `raw_text` from every object in the specified collections,
re-embeds using the new model, overwrites the vector in-place via Weaviate's batch
API, runs 10 spot-check queries to verify the index is queryable, and writes an
audit log entry with the model transition details.

See the script's module docstring for full CLI reference and exit codes.

---

## Related KEIs

| KEI | Description | Status |
|---|---|---|
| KEI-60 (Linear: KEI-62) | Embedding model independence — this schema doc + re_embed_corpus.py | Shipped |
| KEI-46 (Linear: KEI-48) | Weaviate deployment | Backlog — blocked until KEI-60 merged |
| KEI-48 | Capture pipelines that write to Weaviate | Blocked on KEI-46 |
