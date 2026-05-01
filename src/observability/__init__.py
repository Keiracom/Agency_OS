"""Phase 2 — Auditor / observability layer.

Wraps Arize Phoenix self-hosted observability. The Phoenix server itself
is deployed on Railway (see infra/phoenix/). This package contains the
Python ingestion side: convert governance_events rows into Phoenix spans
via OTLP.
"""
