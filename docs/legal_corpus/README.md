# Legal Corpus — KEI-187

Curated reference corpus for drafting Privacy Policy, Terms of Service, and
Data Processing Agreement. Ingested into Weaviate `Legal_corpus` collection
via `scripts/orchestrator/legal_corpus_ingest.py`.

## Categories (7)

| Slug | Scope |
|---|---|
| `privacy-act-au` | Australian Privacy Act 1988 + Australian Privacy Principles (APPs) |
| `gdpr` | EU GDPR — Articles 5/6/13/17/20/28 |
| `ccpa` | California Consumer Privacy Act basics |
| `oaic` | OAIC notifiable data breach scheme |
| `paddle-dpa` | Paddle Merchant-of-Record DPA template |
| `saas-tos-pattern` | Standard SaaS ToS clauses we'll need (acceptable use, IP, indemnity, term/termination, governing law) |
| `ai-compliance-precedent` | EU AI Act draft + adjacent guidance |

## Chunk file format

Each category lives in `<category>.md`. Inside, chunks are separated by `---`
lines. Each chunk has a YAML-style header (3 fields required) and a body:

```
chunk_id: app-1-collection
source_url: https://www.oaic.gov.au/privacy/australian-privacy-principles
source_date: 2014-03-12

<normative passage — one self-contained reference paragraph or clause set>
---
chunk_id: app-3-quality
source_url: ...
source_date: ...

<...>
```

Fields:
- `chunk_id` — stable kebab-case slug, unique within the category file
- `source_url` — canonical link (legislation register / vendor doc / OAIC page)
- `source_date` — ISO date the source was last revised (when known)

Body is plain prose. Keep chunks self-contained: each one should answer one
question without needing context from a sibling chunk.

## Acceptance per KEI-187

- `Legal_corpus` collection exists in Weaviate
- All 7 categories populated
- `bd recall <topic>` returns relevant chunks
- CEO can draft Privacy / ToS / DPA referencing the corpus

## Source policy

This is a curated reference corpus — **not** a substitute for legal counsel.
Chunks summarise canonical sources for retrieval and drafting guidance. Final
legal review of any Keiracom-facing policy stays with the engaged practitioner
(KEI-118 covers the engagement). Each chunk carries `source_url` + `source_date`
so a drafter can pull the canonical text directly when a clause needs verbatim.

## Adding chunks

1. Add the chunk to the relevant `<category>.md` file using the format above
2. Run `python3 scripts/orchestrator/legal_corpus_ingest.py --dry-run` to check parse
3. Live ingest happens on Vultr via the operational pipeline (or
   `python3 scripts/orchestrator/legal_corpus_ingest.py` against a writeable Weaviate)
4. Deterministic UUIDs make re-ingest idempotent — same `(category, chunk_id)`
   tuple maps to the same Weaviate object id; re-runs are no-ops on unchanged content
