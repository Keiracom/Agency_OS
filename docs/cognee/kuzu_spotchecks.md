# KuzuDB Spot-Check Queries — Post-Ingest Verification

Critical context (verified in `cognee/infrastructure/databases/graph/ladybug/LadybugDatasetDatabaseHandler.py`):

**Cognee writes ONE Kuzu database file per dataset.** Files live under `{system_root}/databases/{owner_id}/{dataset_id}.pkl` (provider=`kuzu`) or `.lbug` (provider=`ladybug`). Every spot-check below runs inside a single file via `kuzu.Connection(kuzu.Database(path))`. There is no cross-dataset query inside one Kuzu file.

**Cognee's Kuzu schema** (verified in `cognee/infrastructure/databases/graph/ladybug/adapter.py`):

```cypher
CREATE NODE TABLE Node(
    id STRING PRIMARY KEY, name STRING, type STRING,
    created_at TIMESTAMP, updated_at TIMESTAMP, properties STRING
);
CREATE REL TABLE EDGE(
    FROM Node TO Node, relationship_name STRING,
    created_at TIMESTAMP, updated_at TIMESTAMP, properties STRING
);
```

Note: `Node.properties` is a JSON-encoded STRING, not typed columns. Filter on `type` (the typed column) where possible; for nested fields, parse `properties` in Python after fetching.

Python connection pattern (Kuzu docs: https://docs.kuzudb.com/):

```python
import kuzu, json
db = kuzu.Database(f"databases/{owner_id}/{dataset_id}.pkl")
conn = kuzu.Connection(db)
df = conn.execute("MATCH (n:Node) RETURN count(*) AS c").get_as_df()
```

---

## (a) Total node count

```cypher
MATCH (n:Node) RETURN count(*) AS total_nodes;
```

**Expected after one ingest of a small corpus:** non-zero. For Phase 1 smoke (CLAUDE.md + ARCHITECTURE.md as input), expect roughly 50–300 nodes depending on chunk size.

**Fail:** `total_nodes == 0` → cognify failed silently. Check pipeline run logs.

---

## (b) Per-type breakdown (substitutes for "nodes per dataset" — irrelevant in per-file model)

```cypher
MATCH (n:Node) RETURN n.type AS type, count(*) AS n ORDER BY n DESC;
```

**Expected types** (from cognee task list): `DocumentChunk`, `TextSummary`, `EntityNode` / `Entity`, plus user-defined types from the `graph_model` Pydantic schema (e.g., `Person`, `Organization` for default `KnowledgeGraph`).

**Pass criterion for Phase 1:** ≥3 distinct types present and the dominant type is either `DocumentChunk` or `EntityNode`.

**Fail:** Only one type → extraction step didn't run (LLM call failed or `extract_graph_and_summarize` was skipped).

---

## (c) Edges of any node (by name)

```cypher
MATCH (n:Node {name: $name})-[r:EDGE]-(m:Node)
RETURN r.relationship_name AS rel, m.name AS neighbor, m.type AS neighbor_type
LIMIT 50;
```

Bind `$name` to a known entity from the source corpus (e.g. `"Pipeline F"`, `"Bright Data"`). Use Python: `conn.execute(stmt, parameters={"name": "Pipeline F"})`.

**Pass:** ≥1 edge returned for entities you know are mentioned in the source.

**Fail:** Zero edges for a clearly-related entity → relationship extraction is broken or entity wasn't recognized. Cross-check `(b)` for whether the node exists at all.

---

## (d) Shortest path between two named entities

```cypher
MATCH (a:Node {name: $a}), (b:Node {name: $b})
MATCH p = (a)-[:EDGE* SHORTEST 1..6]-(b)
RETURN length(p) AS hops, [n IN nodes(p) | n.name] AS path
LIMIT 1;
```

Kuzu syntax: `[:EDGE* SHORTEST 1..6]` is Kuzu's variable-length shortest-path operator (Neo4j uses `shortestPath()` function — different). Source: https://docs.kuzudb.com/cypher/query-clauses/match (recursive relationships).

**Pass:** Returns hops 1–6 for entities that should be connected (e.g. `"Pipeline F"` ↔ `"Bright Data"`).

**Fail:** Empty result for entities that ARE thematically connected → entity resolution/co-reference is broken; chunks reference the entities but extracted nodes are disconnected.

---

## (e) Orphan node count (zero-degree nodes)

```cypher
MATCH (n:Node)
WHERE NOT EXISTS { MATCH (n)-[:EDGE]-() }
RETURN count(*) AS orphans, collect(n.name)[0..10] AS sample;
```

**Pass:** Orphan ratio `orphans / total_nodes < 0.3`. Some orphans are expected (top-level `TextSummary` nodes can be sparsely connected if `triplet_embedding=False`).

**Fail:** Ratio > 0.5 → extraction is producing nodes without relationships. Likely a graph_model misconfiguration or a structured-output failure where LLM emits entities but no triplets.

---

## (f) Source-type breakdown (DocumentChunk vs Entity vs Summary)

```cypher
MATCH (n:Node)
RETURN
    CASE
        WHEN n.type CONTAINS 'Chunk' THEN 'chunks'
        WHEN n.type CONTAINS 'Summary' THEN 'summaries'
        WHEN n.type CONTAINS 'Entity' OR n.type CONTAINS 'Node' THEN 'entities'
        ELSE 'other'
    END AS bucket,
    count(*) AS n
ORDER BY n DESC;
```

**Pass:** All three buckets non-zero. For default `cognify()` ingest, expect roughly `chunks ≈ summaries` (one summary per chunk) and `entities` > chunks (multiple entities extracted per chunk).

**Fail:** `summaries == 0` → summarization step failed. `entities == 0` → extraction step failed. `chunks == 0` → chunker/classifier failed (pre-LLM stage broke).

---

## (g) Tenant-isolation check (cross-file, run from Python)

Per-file model means "no edges cross org boundaries" is automatic — different files cannot share edges. The real isolation risk is **node-ID collision indicating accidental shared writes**. Python-level check:

```python
import kuzu
def node_ids(path):
    conn = kuzu.Connection(kuzu.Database(path))
    return set(
        conn.execute("MATCH (n:Node) RETURN n.id").get_as_df()["n.id"].tolist()
    )

ids_a = node_ids(f"databases/{owner_id}/{uuid_for('keiracom__agency_os')}.pkl")
ids_b = node_ids(f"databases/{owner_id}/{uuid_for('keiracom__hardhats')}.pkl")

overlap = ids_a & ids_b
assert len(overlap) == 0, f"ISOLATION BREACH: {len(overlap)} shared node ids — {list(overlap)[:5]}"
```

**Pass:** `overlap == set()`. Two datasets sharing zero node IDs proves writes went to physically separate Kuzu files.

**Fail:** Any overlap → either (i) both datasets resolved to the same `dataset_id` UUID (wrapper bug — check `get_unique_dataset_id` inputs), or (ii) Cognee deduplicated entities across datasets via a shared content-addressable ID (unlikely but possible — check `id` derivation in `add_data_points`).

This is the Kuzu-level companion to Validation Query 4. Both must pass for Phase 1 to clear.

---

## Quick-run wrapper

```bash
python -c "
import kuzu, sys
from cognee.modules.data.methods.get_unique_dataset_id import get_unique_dataset_id
# ... boilerplate elided — see scripts/cognee_smoke_check.py
"
```

Sequence to run after every cohort ingest: `(a)` → `(b)` → `(f)` → `(e)` → `(c)` → `(d)` → `(g)`. Cheap-to-expensive ordering; first failure short-circuits the rest.
