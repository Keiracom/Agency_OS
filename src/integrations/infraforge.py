"""
InfraForge Integration - Domain and Mailbox Provisioning
API: https://api.infraforge.ai/public
Auth: Authorization header (plain key)
"""

import httpx
from src.config.settings import get_settings

class InfraForgeClient:
    def __init__(self):
        settings = get_settings()
        self.api_url = settings.infraforge_api_url
        self.api_key = settings.infraforge_api_key
        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={"Authorization": self.api_key, "Content-Type": "application/json"},
            timeout=30.0,
        )

    async def list_workspaces(self):
        resp = await self._client.get("/workspaces")
        resp.raise_for_status()
        return resp.json()

    async def list_domains(self, page=1, page_size=50):
        resp = await self._client.get("/domains", params={"page": page, "page_size": page_size})
        resp.raise_for_status()
        return resp.json()

    async def check_domain_availability(self, domain: str):
        resp = await self._client.get("/check-domain-availability", params={"domain": domain})
        resp.raise_for_status()
        return resp.json()

    async def buy_domains(self, domains: list[dict]):
        resp = await self._client.post("/domains", json={"domains": domains})
        resp.raise_for_status()
        return resp.json()

    async def generate_alternative_domains(self, base_name: str, count: int = 10):
        resp = await self._client.post("/domains/alternative-domains", json={"baseName": base_name, "count": count})
        resp.raise_for_status()
        return resp.json()

    async def list_mailboxes(self, page=1, page_size=50):
        resp = await self._client.get("/mailboxes", params={"page": page, "page_size": page_size})
        resp.raise_for_status()
        return resp.json()

    async def create_mailboxes(self, mailboxes: list[dict]):
        resp = await self._client.post("/mailboxes", json={"mailboxes": mailboxes})
        resp.raise_for_status()
        return resp.json()

    async def export_to_salesforge(self, from_workspace_id: str, to_workspace_id: str, to_warmforge_workspace_id: str, tag_name: str, warmup_activated: bool = True):
        resp = await self._client.post("/mailboxes/export-to-salesforge", json={
            "fromWorkspaceId": from_workspace_id,
            "toWorkspaceId": to_workspace_id,
            "toWarmforgeWorkspaceId": to_warmforge_workspace_id,
            "tagName": tag_name,
            "warmupActivated": warmup_activated,
        })
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self._client.aclose()

_client = None
def get_infraforge_client():
    global _client
    if _client is None:
        _client = InfraForgeClient()
    return _client
