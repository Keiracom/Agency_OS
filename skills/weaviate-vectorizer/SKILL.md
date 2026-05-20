---
name: weaviate-vectorizer
description: Canonical configuration for Weaviate text2vec-google against AI Studio v1beta. Use for any new collection schema that needs embeddings, or when patching a script that creates / re-creates a Weaviate class. Covers schema config, per-request auth header, and the two empirical traps from KEI-196 + KEI-201.
---

# Weaviate text2vec-google — AI Studio v1beta configuration

Dave Option A (KEI-196 ratified): use Google AI Studio (`generativelanguage.googleapis.com`) over Vertex AI for embeddings — no projectId, no service account, no self-hosted inference container. Auth is API-key based via a per-request header attached by the calling script.

## Schema config (use this verbatim for new collections)

```python
NEW_MODULE_CONFIG = {
    "text2vec-google": {
        "apiEndpoint": "generativelanguage.googleapis.com",
        "modelId": "gemini-embedding-001",
        "vectorizeClassName": False,
    }
}
```

Two traps documented by empirical KEI-201 work (PR #1025 commit `ef408fe05`):

1. **`apiEndpoint` is REQUIRED.** Without it, Weaviate's text2vec-google module assumes Vertex AI and demands `projectId`. Setting `apiEndpoint=generativelanguage.googleapis.com` flips the module into AI-Studio (key-based) mode.

2. **`modelId` is `gemini-embedding-001`, not `text-embedding-004`.** `text-embedding-004` is the Vertex AI name; AI Studio v1beta returns 404. `gemini-embedding-001` is the supported AI Studio name per Gemini ListModels.

## Per-request auth header (REQUIRED on every embedding-triggering request)

Weaviate process does NOT carry `GOOGLE_API_KEY` in its env. Auth must come from a per-request header attached by the script that POSTs to Weaviate. Read the key at the script-process level:

```python
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

def _attach_studio_key(req: urlrequest.Request) -> None:
    if GOOGLE_API_KEY:
        req.add_header("X-Goog-Studio-Api-Key", GOOGLE_API_KEY)
```

Apply on every:
- `POST /v1/objects` (insert — vectorizer fires to compute embedding)
- `POST /v1/graphql` with `nearText` (query — vectorizer fires to embed the query string)

Schema CRUD (`POST /v1/schema`, `DELETE /v1/schema/<class>`) and read endpoints (`GET /v1/objects?class=...`) don't trigger embeddings so the header is optional there — but attaching it uniformly is safe and avoids per-call decisions.

## Live-code references

- `scripts/orchestrator/slack_history_ingest.py` — Slack_history collection ingest (PR #1025, the empirical reference)
- `scripts/orchestrator/kei196_reingest_with_vectorizer.py` — multi-collection reingest tool covering `Discoveries, Keis, AgentMemories, Decisions, Codebase` (this skill's update PR — see commit on `atlas/kei201-followup-reingest-vectorizer-fix`)

## Failure modes that this skill prevents

| Symptom | Root cause |
|---|---|
| `422` on first non-dry-run POST `/v1/objects` | Missing `apiEndpoint` OR wrong `modelId` |
| `404` from AI Studio `/v1beta/models/<id>:embedContent` in Weaviate logs | `modelId=text-embedding-004` (Vertex name) on AI Studio endpoint |
| Vectorizer-active class accepts inserts but `nearText` returns empty / score 0.0 | Missing `X-Goog-Studio-Api-Key` header on query requests |
| All embeddings zero / `certainty=0.0` on probe | Same — header missing, OR `GOOGLE_API_KEY` unset in script-process env |

## Verification probe

After bringing up a vectorizer-active class, run:

```python
gql = '{ Get { <Class>(nearText: {concepts: ["memory recall"]}, limit: 1) { _additional { certainty } } } }'
```

Top `certainty > 0.0` confirms the vectorizer is computing real embeddings. `0.0` indicates the embedding pipeline is broken — check `GOOGLE_API_KEY` env + the per-request header is being attached.

## Sources

- KEI-196 commit `12cfaf93a` — original schema swap (had two of the three bugs documented above).
- KEI-201 PR #1025 commit `ef408fe05` — Scout's empirical fix on `slack_history_ingest.py`; canonical working pattern.
- KEI-201 follow-up (this PR) — applied the same pattern to `kei196_reingest_with_vectorizer.py` + created this skill.
