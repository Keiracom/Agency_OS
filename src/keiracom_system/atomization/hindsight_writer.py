"""hindsight_writer.py — canonical AtomV1 → Hindsight one-source seam.

SECRET_MANIFEST-style single source: the ONE place that defines (a) how an
AtomV1 serializes into a Hindsight memory item and (b) how items are POSTed to
a Hindsight bank. Both the live spawn-exit writer (exit_cycle, Agency_OS-9goi)
and the historical backfill (decisions_backfill, Agency_OS-c66k / PR #1278)
import from here so live + backfilled atoms are byte-identical in the same bank.

Direct-write model (Path 1, Dave-ratified 2026-05-29, ceo:ephemeral_capture_model_v1
v2): an agent writes an AtomV1 DIRECTLY to the Hindsight `fleet_decisions` bank on
spawn exit — no ceo_memory, no atomiser two-step. Hindsight computes the
embedding at ingest, so the live path needs no AtomStore / TEIClient / pgvector.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from src.keiracom_system.atomization.schema import AtomV1

DEFAULT_BANK = "fleet_decisions"
HINDSIGHT_BASE = os.environ.get("HINDSIGHT_BASE", "http://localhost:8889")
HINDSIGHT_TENANT = os.environ.get("HINDSIGHT_TENANT_SLUG", "default")

# (bank, items) -> None — injectable so unit tests record without a live POST.
IngestFn = Callable[[str, list[dict[str, Any]]], None]


def atom_to_hindsight_item(atom: AtomV1, *, source: str = "decisions_backfill") -> dict[str, Any]:
    """Serialize an AtomV1 into a Hindsight memory item.

    `source` is the only field that legitimately differs between writers —
    "decisions_backfill" (historical) vs "live_spawn_exit" (exit_cycle). All
    other fields are identical so the two writers are indistinguishable to
    recall ranking.

      content  = atom.content (the decision statement; what recall ranks on)
      tags     = ["atom_v1", state:<>, schema_v<N>] + composition-tag axis values
      metadata = the full structured atom (so retrieval keeps trigger/provenance)
    """
    ct = atom.composition_tags or {}
    tags = ["atom_v1", f"state:{atom.state}", f"schema_v{atom.schema_version}"]
    tags += [v for v in (ct.get("domain"), ct.get("concern"), ct.get("applicable_context")) if v]
    # Hindsight metadata values MUST all be strings (PR #1130 G2; the /memories
    # endpoint 422s on a non-string value e.g. an int schema_version).
    metadata = {
        "atom_id": str(atom.atom_id),
        "tenant_id": str(atom.tenant_id),
        "schema_version": str(atom.schema_version),
        "state": atom.state,
        "trigger_condition": json.dumps(atom.trigger_condition),
        "anti_pattern": atom.anti_pattern or "",
        "example": atom.example or "",
        "provenance": json.dumps(atom.provenance),
        "composition_tags": json.dumps(ct),
        "source": source,
    }
    return {"content": atom.content, "tags": tags, "metadata": metadata}


def default_hindsight_ingest(bank: str, items: list[dict[str, Any]]) -> None:
    """POST items to the Hindsight bank (synchronous retain). Live path only."""
    from urllib import request as urlrequest

    body = json.dumps({"items": items, "async": False}).encode()
    url = f"{HINDSIGHT_BASE}/v1/{HINDSIGHT_TENANT}/banks/{bank}/memories"
    req = urlrequest.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    with urlrequest.urlopen(req, timeout=120) as resp:  # noqa: S310 — fixed internal host
        if resp.status >= 300:
            raise RuntimeError(f"hindsight ingest HTTP {resp.status} for bank {bank}")
