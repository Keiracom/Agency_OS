"""
Signal Configuration Repository — Directive #256
Single source of truth for vertical signal patterns.
Every pipeline stage reads from here.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class ServiceSignal:
    service_name: str
    label: str
    dfs_technologies: list[str]
    gmb_categories: list[str]
    scoring_weights: dict[str, int]
    must_not_have_technologies: list[str] = field(default_factory=list)


@dataclass
class SignalConfig:
    id: str
    vertical_slug: str
    display_name: str
    description: str | None
    service_signals: list[ServiceSignal]
    discovery_config: dict[str, Any]
    enrichment_gates: dict[str, Any]
    channel_config: dict[str, bool]
    created_at: Any
    updated_at: Any

    @property
    def all_dfs_technologies(self) -> list[str]:
        """Flat deduplicated list of all DFS technologies across all service signals."""
        seen: set[str] = set()
        result: list[str] = []
        for svc in self.service_signals:
            for tech in svc.dfs_technologies:
                if tech not in seen:
                    seen.add(tech)
                    result.append(tech)
        return result

    @property
    def all_gmb_categories(self) -> list[str]:
        """Flat deduplicated list of all GMB categories across all service signals."""
        seen: set[str] = set()
        result: list[str] = []
        for svc in self.service_signals:
            for cat in svc.gmb_categories:
                if cat not in seen:
                    seen.add(cat)
                    result.append(cat)
        return result

    @property
    def min_score_to_enrich(self) -> int:
        return int(self.enrichment_gates.get("min_score_to_enrich", 30))

    @property
    def min_score_to_dm(self) -> int:
        return int(self.enrichment_gates.get("min_score_to_dm", 50))

    @property
    def min_score_to_outreach(self) -> int:
        return int(self.enrichment_gates.get("min_score_to_outreach", 65))


class VerticalNotFoundError(Exception):
    pass


class SignalConfigRepository:
    """
    Async repository for reading signal_configurations from Supabase.
    Usage:
        repo = SignalConfigRepository(conn)
        config = await repo.get_config("marketing_agency")
    """

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get_config(self, vertical_slug: str) -> SignalConfig:
        row = await self._conn.fetchrow(
            "SELECT * FROM signal_configurations WHERE vertical_slug = $1",
            vertical_slug,
        )
        if row is None:
            raise VerticalNotFoundError(f"No signal config found for vertical: {vertical_slug!r}")
        return self._row_to_config(row)

    async def list_verticals(self) -> list[str]:
        rows = await self._conn.fetch(
            "SELECT vertical_slug FROM signal_configurations ORDER BY vertical_slug"
        )
        return [row["vertical_slug"] for row in rows]

    async def get_services_for_vertical(self, vertical_slug: str) -> list[ServiceSignal]:
        config = await self.get_config(vertical_slug)
        return config.service_signals

    @staticmethod
    def _row_to_config(row: asyncpg.Record) -> SignalConfig:
        service_signals = [
            ServiceSignal(
                service_name=svc["service_name"],
                label=svc.get("label", svc["service_name"]),
                dfs_technologies=svc.get("dfs_technologies", []),
                gmb_categories=svc.get("gmb_categories", []),
                scoring_weights=svc.get("scoring_weights", {}),
                must_not_have_technologies=svc.get("must_not_have_technologies", []),
            )
            for svc in (row["service_signals"] or [])
        ]
        return SignalConfig(
            id=str(row["id"]),
            vertical_slug=row["vertical_slug"],
            display_name=row["display_name"],
            description=row["description"],
            service_signals=service_signals,
            discovery_config=dict(row["discovery_config"] or {}),
            enrichment_gates=dict(row["enrichment_gates"] or {}),
            channel_config=dict(row["channel_config"] or {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
