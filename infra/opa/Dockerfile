# Governance Phase 1 Track A — A2 Gatekeeper
#
# Open Policy Agent sidecar serving the completion-claims policy bundle.
# Run mode: server, listening on :8181, decision logs to stdout. The
# Python client at src/governance/gatekeeper.py POSTs claim payloads to
# /v1/data/agency/completion_claims/allow.
#
# Build:   docker build -t agency-os/opa:dev .
# Run:     docker run --rm -p 8181:8181 agency-os/opa:dev
# Verify:  curl http://localhost:8181/v1/data/agency/completion_claims

FROM openpolicyagent/opa:0.65.0-rootless

WORKDIR /policies

COPY policies/ ./

EXPOSE 8181

ENTRYPOINT ["/opa"]
CMD [ \
    "run", \
    "--server", \
    "--addr=0.0.0.0:8181", \
    "--log-level=info", \
    "--log-format=json", \
    "--set=decision_logs.console=true", \
    "/policies" \
]
