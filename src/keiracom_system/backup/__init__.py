"""keiracom_system.backup — Cloudflare R2 backup pipeline (KEI-242 / KEI-243).

Daily Weaviate snapshots + hourly Postgres dumps to Cloudflare R2, with
retention pruning, end-to-end restore verification, and ceo_memory failure
alerting.
"""
