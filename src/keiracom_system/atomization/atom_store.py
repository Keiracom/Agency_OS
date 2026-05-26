"""AtomStore — tenant-scoped Postgres+pgvector access for keiracom_atoms.

Per-tenant store with read+write tenant-prefix guards. Mirrors the
ValkeyClient defence-in-depth pattern from PR #1173:
  - Constructed bound to a single tenant_id
  - Every query filters by self._tenant_id; no caller override possible
  - Cross-tenant reads raise AtomStoreError at the boundary

Per boundary-matrix-v1 guard (b) (PR #1169) the cache module exempts
src/keiracom_system/control_plane/ but NOT atomization/. So this module
uses _DBProtocol DI (no asyncpg/psycopg import) — caller injects a real
connection. Same pattern as TenantBudgetPolicy.from_db (PR #1173).

Embedding is computed via TEIClient (PR #1133) — also injected so unit
tests don't need a live TEI sidecar.

CI guard scripts/ci/check_no_raw_atom_store_outside_module.sh forbids raw
SQL against keiracom_atoms outside this module (mirrors A7 CB-10 pattern).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol
from uuid import UUID

from src.keiracom_system.atomization.schema import (
    AtomV1,
    SupersessionEdgeV1,
)
from src.keiracom_system.embeddings.tei_client import TEIClient

log = logging.getLogger(__name__)


class _DBProtocol(Protocol):
    """Subset of a DB cursor/connection we depend on for AtomStore.

    Mirrors PR #1173 TenantBudgetPolicy._DBProtocol pattern — lets unit tests
    inject a fake without importing asyncpg/psycopg inside the atomization
    module (BMV1 guard b only exempts memory/ + control_plane/).
    """

    def execute(self, query: str, *params: Any) -> Any: ...
    def fetchone(self) -> Any: ...
    def fetchall(self) -> Any: ...


class AtomStoreError(RuntimeError):
    """Raised on any atom-store side or tenant-isolation violation."""


class AtomStore:
    """Per-tenant atom store.

    Bound to a single tenant_id at construction. Cross-tenant access raises
    AtomStoreError via the read/write guards.
    """

    def __init__(
        self,
        *,
        db: _DBProtocol,
        tenant_id: str | UUID,
        embedder: TEIClient,
    ):
        if not tenant_id:
            raise AtomStoreError("tenant_id is required (cross-tenant isolation invariant)")
        self._db = db
        self._tenant_id = str(tenant_id)
        self._embedder = embedder

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    def _enforce_tenant_match(self, query_tenant_id: str | UUID) -> None:
        """Reject any read/write that names a different tenant_id than the
        store's bound tenant. Defence-in-depth read/write boundary guard."""
        qtid = str(query_tenant_id)
        if qtid != self._tenant_id:
            raise AtomStoreError(
                f"tenant_id mismatch: store bound to {self._tenant_id!r} but "
                f"caller passed {qtid!r} — cross-tenant access forbidden"
            )

    def insert_atom(self, atom: AtomV1) -> UUID:
        """Insert one atom into keiracom_atoms. Returns its atom_id.

        Atom MUST be constructed with tenant_id matching this store's
        tenant_id (enforced at the boundary).
        """
        self._enforce_tenant_match(atom.tenant_id)
        # Compute embedding from content if not pre-supplied (defensive — atoms
        # arriving from atomizer carry embeddings; tests may construct without).
        embedding = atom.content_embedding or self._embedder.embed([atom.content])[0]
        if len(embedding) != self._embedder.dimension:
            raise AtomStoreError(
                f"embedding dimension mismatch: got {len(embedding)}, "
                f"expected {self._embedder.dimension}"
            )
        self._db.execute(
            "INSERT INTO keiracom_atoms ("
            "atom_id, tenant_id, trigger_condition, content, anti_pattern, "
            "example, provenance, composition_tags, content_embedding, "
            "schema_version, state"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING atom_id",
            str(atom.atom_id),
            self._tenant_id,
            json.dumps(atom.trigger_condition),
            atom.content,
            atom.anti_pattern,
            atom.example,
            json.dumps(atom.provenance),
            json.dumps(atom.composition_tags),
            self._embedding_to_pgvector(embedding),
            atom.schema_version,
            atom.state,
        )
        row = self._db.fetchone()
        if row is None:
            raise AtomStoreError("insert_atom: no atom_id returned from INSERT")
        return UUID(str(row[0]))

    def get_atom(self, atom_id: UUID) -> AtomV1 | None:
        """Fetch one atom by atom_id, scoped to this store's tenant.

        Returns None if not found OR atom exists but belongs to a different
        tenant (collapsed for non-leak — caller cannot distinguish).
        """
        self._db.execute(
            "SELECT atom_id, tenant_id, trigger_condition, content, "
            "anti_pattern, example, provenance, composition_tags, "
            "schema_version, state "
            "FROM keiracom_atoms WHERE atom_id = %s AND tenant_id = %s",
            str(atom_id),
            self._tenant_id,
        )
        row = self._db.fetchone()
        if row is None:
            return None
        return self._row_to_atom(row)

    def retrieve_top_k(self, query_text: str, top_k: int = 10) -> list[AtomV1]:
        """Cosine-similarity nearest atoms in this tenant's namespace.

        Uses pgvector HNSW index on content_embedding. State filter applies —
        only active atoms returned (superseded and cold_archive excluded).
        """
        if top_k <= 0:
            raise AtomStoreError("top_k must be > 0")
        query_embedding = self._embedder.embed([query_text])[0]
        self._db.execute(
            "SELECT atom_id, tenant_id, trigger_condition, content, "
            "anti_pattern, example, provenance, composition_tags, "
            "schema_version, state "
            "FROM keiracom_atoms "
            "WHERE tenant_id = %s AND state = 'active' "
            "ORDER BY content_embedding <=> %s "
            "LIMIT %s",
            self._tenant_id,
            self._embedding_to_pgvector(query_embedding),
            int(top_k),
        )
        rows = self._db.fetchall() or []
        return [self._row_to_atom(r) for r in rows]

    def transition_state(self, atom_id: UUID, new_state: str) -> None:
        """Update an atom's state column. Must be from VALID_STATES."""
        from src.keiracom_system.atomization.schema import VALID_STATES

        if new_state not in VALID_STATES:
            raise AtomStoreError(f"new_state {new_state!r} not in {sorted(VALID_STATES)}")
        self._db.execute(
            "UPDATE keiracom_atoms SET state = %s WHERE atom_id = %s AND tenant_id = %s",
            new_state,
            str(atom_id),
            self._tenant_id,
        )

    def insert_supersession_edge(self, edge: SupersessionEdgeV1) -> UUID:
        """Insert a supersession edge. Both predecessor + successor MUST be
        atoms owned by this store's tenant — enforced at boundary."""
        self._enforce_tenant_match(edge.tenant_id)
        # Defence-in-depth: verify both endpoint atoms exist + belong to this
        # tenant before inserting the edge.
        if self.get_atom(edge.predecessor_atom) is None:
            raise AtomStoreError(
                f"predecessor_atom {edge.predecessor_atom} not found in tenant {self._tenant_id}"
            )
        if self.get_atom(edge.successor_atom) is None:
            raise AtomStoreError(
                f"successor_atom {edge.successor_atom} not found in tenant {self._tenant_id}"
            )
        self._db.execute(
            "INSERT INTO keiracom_atom_supersession_edges ("
            "edge_id, tenant_id, predecessor_atom, successor_atom, "
            "relationship_type, confidence"
            ") VALUES (%s, %s, %s, %s, %s, %s) RETURNING edge_id",
            str(edge.edge_id),
            self._tenant_id,
            str(edge.predecessor_atom),
            str(edge.successor_atom),
            edge.relationship_type,
            float(edge.confidence),
        )
        row = self._db.fetchone()
        if row is None:
            raise AtomStoreError("insert_supersession_edge: no edge_id returned")
        return UUID(str(row[0]))

    # ------------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------------

    @staticmethod
    def _embedding_to_pgvector(embedding: list[float]) -> str:
        """pgvector wire format: '[0.1, 0.2, ...]' string with brackets."""
        return "[" + ",".join(repr(float(x)) for x in embedding) + "]"

    @staticmethod
    def _row_to_atom(row: Any) -> AtomV1:
        """Build an AtomV1 from a DB row tuple in canonical column order."""
        atom_id, tenant_id, trigger_condition, content, anti_pattern = row[:5]
        example, provenance, composition_tags, schema_version, state = row[5:]
        return AtomV1(
            atom_id=UUID(str(atom_id)),
            tenant_id=UUID(str(tenant_id)),
            trigger_condition=_parse_jsonb(trigger_condition),
            content=content,
            anti_pattern=anti_pattern,
            example=example,
            provenance=_parse_jsonb(provenance),
            composition_tags=_parse_jsonb(composition_tags) if composition_tags else {},
            content_embedding=[],  # Not selected back; would re-embed on retrieve.
            schema_version=int(schema_version),
            state=state,
        )


def _parse_jsonb(value: Any) -> dict[str, Any]:
    """Postgres JSONB columns may come back as either dict (psycopg adapts) or
    str (raw); tolerate both."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return {}
