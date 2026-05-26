"""Keiracom atomization — Phase 10029 pilot Week 1 implementation.

Per ceo:atomization_architecture_v1 (RATIFIED-CEO 2026-05-26T11:25:00Z) +
PR #1178 schema-lock proposal. Implements the 5-component architecture:

  1. Atomizer       — src.keiracom_system.atomization.atomizer
  2. Atom Store     — src.keiracom_system.atomization.atom_store
  3. MAL Retriever  — Week 2 dispatch (out of scope)
  4. Composer       — Week 2 dispatch (out of scope)
  5. Endpoint Tx    — Week 2-3 dispatch (out of scope)

Feature flag (default OFF): KEIRACOM_ATOMIZER_ENABLED.

Public surface re-exported for callers.
"""

from src.keiracom_system.atomization.atom_store import (
    AtomStore,
    AtomStoreError,
)
from src.keiracom_system.atomization.atomizer import (
    Atomizer,
    AtomizerError,
    AtomizerJob,
)
from src.keiracom_system.atomization.schema import (
    SCHEMA_VERSION,
    VALID_COMPOSITION_TAGS,
    VALID_RELATIONSHIP_TYPES,
    VALID_SOURCE_KINDS,
    VALID_STATES,
    VALID_TRIGGER_KINDS,
    AtomV1,
    SupersessionEdgeV1,
    is_valid_composition_tag,
)
from src.keiracom_system.atomization.verifier import (
    Verifier,
    VerifierError,
    VerifierFlag,
)

__all__ = [
    "SCHEMA_VERSION",
    "VALID_COMPOSITION_TAGS",
    "VALID_RELATIONSHIP_TYPES",
    "VALID_SOURCE_KINDS",
    "VALID_STATES",
    "VALID_TRIGGER_KINDS",
    "AtomStore",
    "AtomStoreError",
    "AtomV1",
    "Atomizer",
    "AtomizerError",
    "AtomizerJob",
    "SupersessionEdgeV1",
    "Verifier",
    "VerifierError",
    "VerifierFlag",
    "is_valid_composition_tag",
]
