#!/usr/bin/env python3
"""smoke_wrappers.py — wire all 4 memory wrappers against deployed fleet Hindsight.

Phase A1 acceptance criterion 2 (Agency_OS-njhl): "All 4 wrappers connected
(smoke test: write Decision/Artifact/TaskContext/AntiPattern, read back)."

Uses the wrappers from PR #1134 + the fleet tenant from provision_fleet_tenant.py
+ a thin HTTP client + a minimal TenantExtension shim. The TenantExtension here
is a Phase-A1 placeholder — Orion's KeiracomTenantExtension (PR #1132) plugs in
identically once it's wired through the fleet's control-plane substrate.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.keiracom_system.memory.wrappers import (  # noqa: E402
    AntiPatternWrapper,
    ArtifactWrapper,
    DecisionWrapper,
    TaskContextWrapper,
)

FLEET_TENANT_ID = "00000000-0000-0000-0000-000000000001"
FLEET_HINDSIGHT_BASE = "http://localhost:8889"  # Phase A1 fleet variant port
FLEET_BANK_ID = "fleet_smoke"


class FleetHindsightClient:
    """Thin HTTP client satisfying the wrappers' HindsightClient Protocol."""

    def retain(self, *, bank_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post(f"/v1/default/banks/{bank_id}/memories", {"items": items, "async": False})

    def recall(
        self, *, bank_id: str, query: str, tags: list[str] | None = None, top_k: int = 5
    ) -> list[dict[str, Any]]:
        body = {"query": query, "max_tokens": 2000}
        if tags:
            body["tags"] = tags
            body["tags_match"] = "all"
        resp = self._post(f"/v1/default/banks/{bank_id}/memories/recall", body)
        return resp.get("memories", []) or resp.get("results", []) or []

    def reflect(self, *, bank_id: str, query: str) -> dict[str, Any]:
        return self._post(f"/v1/default/banks/{bank_id}/reflect", {"query": query})

    def _post(self, path: str, body: dict) -> Any:
        data = json.dumps(body).encode()
        req = urlrequest.Request(
            f"{FLEET_HINDSIGHT_BASE}{path}",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlrequest.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode())
        except urlerror.HTTPError as e:
            return {"error": f"HTTP_{e.code}", "body": e.read().decode()[:500]}
        except (urlerror.URLError, json.JSONDecodeError, TimeoutError) as e:
            return {"error": str(e)}


class FleetTenantExtension:
    """Phase A1 placeholder TenantExtension. Maps tenant_id → bank_id 1:1.

    Orion's KeiracomTenantExtension (PR #1132) replaces this once the
    fleet's control-plane substrate is wired through; the wrappers don't
    notice the swap (Protocol-typed dependency).
    """

    def get_bank_id(self, tenant_id: str) -> str:
        if tenant_id != FLEET_TENANT_ID:
            raise KeyError(f"unknown fleet tenant {tenant_id}")
        return FLEET_BANK_ID


def _put_bank(client: FleetHindsightClient) -> None:
    """Idempotent bank create (PUT /v1/default/banks/{id} per Orion's README)."""
    data = json.dumps({"mission": "fleet smoke test bank"}).encode()
    req = urlrequest.Request(
        f"{FLEET_HINDSIGHT_BASE}/v1/default/banks/{FLEET_BANK_ID}",
        data=data,
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    try:
        urlrequest.urlopen(req, timeout=30)
        print(f"[bank] PUT /v1/default/banks/{FLEET_BANK_ID} OK")
    except urlerror.HTTPError as e:
        # 409 conflict = already exists; treat as success.
        if e.code in (409,):
            print(f"[bank] {FLEET_BANK_ID} already exists ({e.code})")
        else:
            print(f"[bank] PUT failed rc={e.code}: {e.read().decode()[:200]}")
            raise


def main() -> int:
    print(f"=== Phase A1 smoke: wire 4 wrappers against {FLEET_HINDSIGHT_BASE} ===\n")
    client = FleetHindsightClient()
    tenants = FleetTenantExtension()

    _put_bank(client)
    print()

    results = {}

    # Decision → World
    t0 = time.time()
    decision_w = DecisionWrapper(client, tenants)
    r = decision_w.ingest(
        tenant_id=FLEET_TENANT_ID,
        content="Decision: Phase A1 deploys Hindsight to fleet via systemd-managed docker compose on Vultr (impl-feasibility call by Atlas 2026-05-25).",
        metadata={"phase": "A1", "decision_ref": "fleet-hindsight-vultr"},
    )
    results["decision"] = {
        "ok": "error" not in (r or {}),
        "dt": round(time.time() - t0, 2),
        "resp": str(r)[:200],
    }
    print(
        f"[decision] write {'OK' if results['decision']['ok'] else 'FAIL'} ({results['decision']['dt']}s)"
    )

    # Artifact → Experience
    t0 = time.time()
    artifact_w = ArtifactWrapper(client, tenants)
    r = artifact_w.ingest(
        tenant_id=FLEET_TENANT_ID,
        content="PR opened for Phase A1: keiracom_system/fleet/hindsight/ — docker-compose + provision + smoke wrappers.",
        author="atlas",
        artifact_ref="phase-a1-fleet-deploy",
        metadata={"phase": "A1"},
    )
    results["artifact"] = {
        "ok": "error" not in (r or {}),
        "dt": round(time.time() - t0, 2),
        "resp": str(r)[:200],
    }
    print(
        f"[artifact] write {'OK' if results['artifact']['ok'] else 'FAIL'} ({results['artifact']['dt']}s)"
    )

    # TaskContext → Observation
    t0 = time.time()
    task_w = TaskContextWrapper(client, tenants)
    r = task_w.ingest(
        tenant_id=FLEET_TENANT_ID,
        content="Agency_OS-njhl Phase A1: fleet Hindsight deploy + tenant=1 + 4 wrappers wired + smoke pass.",
        metadata={"phase": "A1", "kei": "Agency_OS-njhl"},
    )
    results["taskcontext"] = {
        "ok": "error" not in (r or {}),
        "dt": round(time.time() - t0, 2),
        "resp": str(r)[:200],
    }
    print(
        f"[taskcontext] write {'OK' if results['taskcontext']['ok'] else 'FAIL'} ({results['taskcontext']['dt']}s)"
    )

    # AntiPattern → Opinion (with supersession edge)
    t0 = time.time()
    anti_w = AntiPatternWrapper(client, tenants)
    r = anti_w.ingest(
        tenant_id=FLEET_TENANT_ID,
        context="Phase A1 host-UID volume mount (Hindsight smoke spike PR #1130 G1)",
        failed_path="documented docker-compose `-v $HOME/.hindsight-docker:/home/hindsight/.pg0` fails with Permission denied because container UID 1000 != host UID 1001",
        verified_path="use named docker volume (keiracom_fleet_hindsight_pg_data:/home/hindsight/.pg0) — docker manages ownership, no host-UID mismatch",
        metadata={"phase": "A1", "source_pr": "1130", "gap_ref": "G1"},
    )
    results["antipattern"] = {
        "ok": "error" not in (r or {}),
        "dt": round(time.time() - t0, 2),
        "resp": str(r)[:200],
    }
    print(
        f"[antipattern] write {'OK' if results['antipattern']['ok'] else 'FAIL'} ({results['antipattern']['dt']}s)"
    )

    print("\n=== read-back probe (recall by mal_node tag per wrapper) ===")
    for node, wrapper_cls in [
        ("decision", DecisionWrapper),
        ("artifact", ArtifactWrapper),
        ("taskcontext", TaskContextWrapper),
        ("antipattern", AntiPatternWrapper),
    ]:
        w = wrapper_cls(client, tenants)
        rows = w.recall(tenant_id=FLEET_TENANT_ID, query=f"Phase A1 {node}", top_k=3)
        results[f"read_{node}"] = {"count": len(rows) if isinstance(rows, list) else 0}
        print(f"[recall {node}] returned {results[f'read_{node}']['count']} rows")

    write_pass = sum(
        1
        for k, v in results.items()
        if k in ("decision", "artifact", "taskcontext", "antipattern") and v["ok"]
    )
    print("\n=== Phase A1 smoke verdict ===")
    print(f"4 wrapper writes:     {write_pass}/4")
    print(
        f"4 wrapper read-backs: total_rows = {sum(results[f'read_{n}']['count'] for n in ('decision', 'artifact', 'taskcontext', 'antipattern'))}"
    )
    return 0 if write_pass == 4 else 1


if __name__ == "__main__":
    sys.exit(main())
