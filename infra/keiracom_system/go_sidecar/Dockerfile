# Multi-stage build — produces a ~10MB static binary on top of distroless.
# Engineer-tier may swap to scratch + CGO_ENABLED=0 once dependencies are pinned.

FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod ./
# Engineer-tier adds go.sum once external deps land; scaffold has none.
COPY cmd ./cmd
COPY internal ./internal
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/sidecar ./cmd/sidecar

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/sidecar /usr/local/bin/sidecar
EXPOSE 4100
USER nonroot:nonroot
ENTRYPOINT ["/usr/local/bin/sidecar"]
