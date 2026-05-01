# Phase 2 — Auditor (Arize Phoenix self-hosted observability).
# Phoenix UI: port 6006. OTLP ingest: 4317 (gRPC), 4318 (HTTP).
# Persistent SQLite state at /tmp/phoenix to survive restarts (volume mount).

FROM arizephoenix/phoenix:latest

EXPOSE 6006 4317 4318

ENV PHOENIX_PORT=6006
ENV PHOENIX_GRPC_PORT=4317
ENV PHOENIX_WORKING_DIR=/tmp/phoenix
ENV PHOENIX_HOST=0.0.0.0
