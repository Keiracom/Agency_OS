#!/usr/bin/env python3
"""provision_fleet_tenant.py — insert fleet tenant_id=1 row into keiracom_tenants.

Phase A1 acceptance criterion 3 (Agency_OS-njhl). Uses Atlas's provision_tenant
from PR #1131 against the just-applied keiracom_tenants table.

Per `tenant.single_supabase` row in V2.0 inventory: "Dave is tenant_id=1;
customers are tenant_id=2+". The schema uses UUID PK — fleet's deterministic
tenant_id is `00000000-0000-0000-0000-000000000001` (the canonical "fleet"
UUID; documented here so downstream callers can route to it without lookup).

Idempotent: re-runs return the existing row per provision_tenant's
idempotent_replay contract.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.keiracom_system.tenant import provision_tenant  # noqa: E402

FLEET_TENANT_ID = "00000000-0000-0000-0000-000000000001"
FLEET_TIER = "pro"  # Fleet runs as Pro tier — internal use needs 4-tool MCP surface incl. Synthesize + Supersede
FLEET_LLM_MODEL = "gpt-4o-mini"
FLEET_LLM_API_KEY_PLACEHOLDER = (
    "fleet-key-managed-via-env-not-vault-pre-secrets-management-substrate"
)


class _SupabaseDB:
    """Thin Supabase HTTP adapter satisfying provisioning._DBProtocol shape.

    Phase A1 boundary: no Vault yet (`infra.secrets_management` LOOSE-BLOCKER per
    Cat 16 spot-check), so the llm_api_key_encrypted field carries a placeholder
    sentinel. Real envelope encryption wires in when Vault lands; the column +
    schema are ready, only the encryption layer is deferred.
    """

    def __init__(self) -> None:
        import os
        import urllib.request

        self._urllib = urllib.request
        self._url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1"
        self._headers = {
            "apikey": os.environ["SUPABASE_SERVICE_KEY"],
            "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _req(self, method: str, path: str, body: dict | None = None) -> Any:
        import json as _json

        data = _json.dumps(body).encode() if body is not None else None
        req = self._urllib.Request(
            f"{self._url}{path}", data=data, method=method, headers=self._headers
        )
        with self._urllib.urlopen(req, timeout=30) as resp:
            text = resp.read().decode()
            return _json.loads(text) if text else None

    def insert_tenant(self, row: dict[str, Any]) -> dict[str, Any]:
        out = self._req("POST", "/keiracom_tenants", row)
        return out[0] if isinstance(out, list) else out

    def select_tenant(self, tenant_id: str) -> dict[str, Any] | None:
        out = self._req("GET", f"/keiracom_tenants?tenant_id=eq.{tenant_id}&select=*")
        return out[0] if out else None

    def create_schema(self, schema_name: str) -> None:
        # Topology B requires the per-tenant schema. For fleet we use the
        # _fleet schema; if it already exists the IF NOT EXISTS guards it.
        # The Supabase REST API can't run DDL — invoke via execute_sql RPC.
        import json as _json
        import os
        import urllib.request

        rpc_url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/rpc/exec_sql"
        body = _json.dumps({"sql": f'CREATE SCHEMA IF NOT EXISTS "{schema_name}";'}).encode()
        req = urllib.request.Request(rpc_url, data=body, method="POST", headers=self._headers)
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception as exc:  # noqa: BLE001
            # exec_sql RPC may not exist on this Supabase project; log + continue
            # since fleet schema creation can be done out-of-band via the SQL
            # editor if the RPC path isn't available.
            print(f"[provision] create_schema RPC fallback: {exc} — run manually:")
            print(f'  CREATE SCHEMA IF NOT EXISTS "{schema_name}";')


class _StdoutEvents:
    def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        import json as _json

        print(f"[event] {event_name} {_json.dumps(payload)}")


def main() -> int:
    db = _SupabaseDB()
    events = _StdoutEvents()
    record = provision_tenant(
        db=db,
        events=events,
        tier=FLEET_TIER,
        llm_api_key_encrypted=FLEET_LLM_API_KEY_PLACEHOLDER,
        llm_model=FLEET_LLM_MODEL,
        tenant_id=FLEET_TENANT_ID,
    )
    print("\nFleet tenant provisioned/retrieved:")
    print(f"  tenant_id:   {record.tenant_id}")
    print(f"  tier:        {record.tier}")
    print(f"  topology:    {record.topology}")
    print(f"  schema_name: {record.schema_name}")
    print(f"  llm_model:   {record.llm_model}")
    print(f"  status:      {record.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
