"""
Contract: src/enrichment/signal_config.py
Purpose: Signal configuration repository — v6 schema (services jsonb, competitor_config)
Layer: 2 - integrations (reads DB only, no engine imports)
Imports: asyncpg
Consumers: engines, orchestration
Directive: #271 (v6 redesign from #256)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class ServiceSignal:
    """
    Per-service signal configuration.

    Field order preserves v5 positional backward compat:
      service_name, label, dfs_technologies, gmb_categories, scoring_weights,
      must_not_have_technologies (all positional args used in existing tests)

    v6 additions (keyword-only in practice): weight, problem_signals,
      budget_signals, not_served_signals
    """

    service_name: str
    label: str
    # Backward-compat positional fields (stage_4_scoring.py reads these directly)
    dfs_technologies: list[str] = field(default_factory=list)
    gmb_categories: list[str] = field(default_factory=list)
    scoring_weights: dict[str, int] = field(default_factory=dict)
    must_not_have_technologies: list[str] = field(default_factory=list)
    # v6 new fields
    weight: float = 1.0
    problem_signals: list[dict] = field(default_factory=list)
    budget_signals: list[dict] = field(default_factory=list)
    not_served_signals: list[dict] = field(default_factory=list)


@dataclass
class SignalConfig:
    """
    v6: primary fields are `vertical` and `services`.
    Backward-compat properties `vertical_slug` and `service_signals` are preserved
    for all existing consumers.
    """

    id: str
    vertical: str
    services: list[ServiceSignal]
    discovery_config: dict[str, Any]
    enrichment_gates: dict[str, Any]
    competitor_config: dict[str, Any]
    channel_config: dict[str, bool]
    created_at: Any
    updated_at: Any

    # ── Backward-compat aliases ────────────────────────────────────────────────

    @property
    def vertical_slug(self) -> str:
        """Backward compat: vertical_slug → vertical."""
        return self.vertical

    @property
    def service_signals(self) -> list[ServiceSignal]:
        """Backward compat: service_signals → services."""
        return self.services

    # ── Aggregate helpers ──────────────────────────────────────────────────────

    @property
    def all_dfs_technologies(self) -> list[str]:
        """
        Flat deduplicated list of DFS technology names for stage_1 discovery.
        In v6 these are drawn from each service's dfs_technologies field
        (which is populated from not_served_signals thresholds in _row_to_config).
        """
        seen: set[str] = set()
        result: list[str] = []
        for svc in self.services:
            for tech in svc.dfs_technologies:
                if tech not in seen:
                    seen.add(tech)
                    result.append(tech)
        return result

    @property
    def all_gmb_categories(self) -> list[str]:
        """Flat deduplicated list of GMB categories across all services."""
        seen: set[str] = set()
        result: list[str] = []
        for svc in self.services:
            for cat in svc.gmb_categories:
                if cat not in seen:
                    seen.add(cat)
                    result.append(cat)
        return result

    # ── Enrichment gate properties ─────────────────────────────────────────────

    @property
    def min_score_to_qualify(self) -> int:
        return int(self.enrichment_gates.get("min_score_to_qualify", 30))

    @property
    def min_score_to_compete(self) -> int:
        return int(self.enrichment_gates.get("min_score_to_compete", 50))

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
    Supports both v5 (vertical_slug/service_signals columns) and
    v6 (vertical/services columns) via graceful fallback in _row_to_config.

    Usage:
        repo = SignalConfigRepository(conn)
        config = await repo.get_config("marketing_agency")
    """

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get_config(self, vertical: str) -> SignalConfig:
        row = await self._conn.fetchrow(
            "SELECT * FROM signal_configurations WHERE vertical = $1",
            vertical,
        )
        if row is None:
            raise VerticalNotFoundError(f"No signal config found for vertical: {vertical!r}")
        return self._row_to_config(row)

    async def list_verticals(self) -> list[str]:
        rows = await self._conn.fetch(
            "SELECT vertical FROM signal_configurations ORDER BY vertical"
        )
        return [row["vertical"] for row in rows]

    async def get_services_for_vertical(self, vertical: str) -> list[ServiceSignal]:
        config = await self.get_config(vertical)
        return config.services

    @staticmethod
    def _row_to_config(row: asyncpg.Record) -> SignalConfig:
        """
        Map a DB row to SignalConfig.
        Handles v6 columns (vertical, services) with fallback to v5 names
        (vertical_slug, service_signals) for mock compatibility.
        """
        # v6 primary column names with v5 fallback
        vertical = row.get("vertical") or row.get("vertical_slug") or ""

        raw_services = row.get("services") or row.get("service_signals") or []

        services = []
        for svc in raw_services:
            # v6 uses service_key/display_name; v5 used service_name/label
            service_name = svc.get("service_key") or svc.get("service_name", "")
            label = svc.get("display_name") or svc.get("label", service_name)

            # dfs_technologies: use explicit field if present (v5 compat),
            # otherwise derive from not_served_signals threshold lists
            explicit_techs: list[str] = svc.get("dfs_technologies", [])
            if not explicit_techs:
                for sig in svc.get("not_served_signals", []):
                    if sig.get("field") == "tech_stack" and sig.get("operator") == "missing":
                        t = sig.get("threshold", [])
                        if isinstance(t, list):
                            explicit_techs = t
                            break

            services.append(
                ServiceSignal(
                    service_name=service_name,
                    label=label,
                    dfs_technologies=explicit_techs,
                    gmb_categories=svc.get("gmb_categories", []),
                    scoring_weights=svc.get("scoring_weights", {}),
                    must_not_have_technologies=svc.get("must_not_have_technologies", []),
                    weight=float(svc.get("weight", 1.0)),
                    problem_signals=svc.get("problem_signals", []),
                    budget_signals=svc.get("budget_signals", []),
                    not_served_signals=svc.get("not_served_signals", []),
                )
            )

        return SignalConfig(
            id=str(row["id"]),
            vertical=vertical,
            services=services,
            discovery_config=dict(row.get("discovery_config") or {}),
            enrichment_gates=dict(row.get("enrichment_gates") or {}),
            competitor_config=dict(row.get("competitor_config") or {}),
            channel_config=dict(row.get("channel_config") or {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
