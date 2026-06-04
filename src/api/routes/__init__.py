"""API routes package.

Repo-split curation (keiracom-core): the Agency-OS dashboard router aggregator
was removed with its app (src/api/main.py — dead BDR). The live/product routes
(customer_api_keys = BYOK, webhooks/linear, webhooks/paddle) are imported
directly by their consumers, so this package __init__ no longer aggregates the
dead BDR routers (campaigns/pool/admin/leads/crm/...). The product app re-wires
its own routers. KEPT as the package marker for the live/product route modules.
"""

__all__: list[str] = []
