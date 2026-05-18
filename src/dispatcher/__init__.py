"""Dispatcher product layer — KEI-110 Part 17.

Customer-facing product surface: container lifecycle (KEI-115), tenant JWT
minting (KEI-164), governance proxy (KEI-165), LiteLLM routing (KEI-166).
Supervisor surface: container_monitor (KEI-163), watchdog + reaper (KEI-211).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.dispatcher.reaper import Reaper
    from src.dispatcher.watchdog import Watchdog


def supervisor_health_snapshot(
    watchdog: Watchdog | None = None,
    reaper: Reaper | None = None,
) -> dict[str, object]:
    """Aggregate KEI-211 watchdog + reaper status for the dispatcher
    health endpoint.

    Top-level ``status`` is "green" iff every component reports "green".
    Missing components are absent from the response (not synthesised as
    green) so the consumer can see which supervisor pieces are wired up.
    """
    components: list[dict[str, object]] = []
    if watchdog is not None:
        components.append(watchdog.health_snapshot())
    if reaper is not None:
        components.append(reaper.health_snapshot())

    overall = "green"
    for c in components:
        if c.get("status") != "green":
            overall = "degraded"
            break

    return {"status": overall, "components": components}
