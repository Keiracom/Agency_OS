// Command sidecar — Go HTTP listener for the Keiracom security interceptor.
//
// Shape B from the research doc: per-tenant HTTP sidecar co-located with the
// agent container. Agents POST tool calls; sidecar validates against static
// config + forwards (or rejects) via /proxy. Wave 1 dispatch Agency_OS-2c7m
// adds:
//   - per-tenant token-bucket rate limiter (429 on bucket empty)
//   - per-MCP-server circuit breaker (503 on breaker open)
//   - /proxy endpoint that forwards to upstream MCP server on success
package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/keiracom/keiracom_system/go_sidecar/internal/breaker"
	"github.com/keiracom/keiracom_system/go_sidecar/internal/config"
	"github.com/keiracom/keiracom_system/go_sidecar/internal/ratelimit"
	"github.com/keiracom/keiracom_system/go_sidecar/internal/validator"
)

const maxBodyBytes = 64 * 1024 // 64 KB request cap — DoS guard per README §security posture.

// proxyRequest — body shape for /proxy. Mirrors ToolCall + adds Server + Body.
type proxyRequest struct {
	TenantID string          `json:"tenant_id"`
	Tool     string          `json:"tool"`
	Server   string          `json:"server"` // logical MCP-server name from tenant.mcp_servers
	Path     string          `json:"path,omitempty"`
	Domain   string          `json:"domain,omitempty"`
	Body     json.RawMessage `json:"body,omitempty"`
}

func main() {
	cfgPath := os.Getenv("SIDECAR_CONFIG_PATH")
	if cfgPath == "" {
		cfgPath = "/etc/keiracom/sidecar.json"
	}
	cfg, err := config.Load(cfgPath)
	if err != nil {
		log.Fatalf("config load: %v", err)
	}
	v := validator.New(cfg)
	rl := ratelimit.New(time.Now)
	for id, t := range cfg.Tenants {
		rl.SetTenant(id, t.RateLimit)
	}
	bm := breaker.NewManager(breaker.Default())
	httpClient := &http.Client{Timeout: 10 * time.Second}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", health)
	mux.HandleFunc("/validate", validateHandler(v, rl))
	mux.HandleFunc("/proxy", proxyHandler(cfg, v, rl, bm, httpClient))

	addr := os.Getenv("SIDECAR_ADDR")
	if addr == "" {
		addr = ":4100"
	}
	log.Printf("go_sidecar listening on %s (config %s)", addr, cfgPath)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatal(err)
	}
}

func health(w http.ResponseWriter, _ *http.Request) {
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"ok":true}`))
}

func validateHandler(v validator.Validator, rl *ratelimit.Limiter) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
		var c validator.ToolCall
		if err := json.NewDecoder(r.Body).Decode(&c); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		if !rl.Allow(c.TenantID) {
			http.Error(w, "rate-limit: tenant bucket empty", http.StatusTooManyRequests)
			return
		}
		if err := v.Allow(c); err != nil {
			http.Error(w, err.Error(), http.StatusForbidden)
			return
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"allow":true}`))
	}
}

func proxyHandler(cfg *config.Config, v validator.Validator, rl *ratelimit.Limiter, bm *breaker.Manager, hc *http.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
		var req proxyRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		if !rl.Allow(req.TenantID) {
			http.Error(w, "rate-limit: tenant bucket empty", http.StatusTooManyRequests)
			return
		}
		if err := v.Allow(validator.ToolCall{TenantID: req.TenantID, Tool: req.Tool, Path: req.Path, Domain: req.Domain}); err != nil {
			http.Error(w, err.Error(), http.StatusForbidden)
			return
		}
		tenant, ok := cfg.Tenants[req.TenantID]
		if !ok {
			http.Error(w, "proxy: unknown tenant", http.StatusForbidden)
			return
		}
		upstream, ok := tenant.MCPServers[req.Server]
		if !ok || upstream == "" {
			http.Error(w, "proxy: server not in tenant mcp_servers", http.StatusForbidden)
			return
		}
		br := bm.Get(req.Server)
		if err := br.Allow(); err != nil {
			http.Error(w, "proxy: circuit breaker open for "+req.Server, http.StatusServiceUnavailable)
			return
		}
		body, status, err := forward(hc, upstream, req.Body)
		if err != nil || status >= 500 {
			br.Failure()
			if err != nil {
				http.Error(w, "proxy: upstream error: "+err.Error(), http.StatusBadGateway)
				return
			}
			http.Error(w, "proxy: upstream 5xx", status)
			return
		}
		br.Success()
		if scanErr := v.ScanResponse(req.TenantID, body); scanErr != nil {
			http.Error(w, "proxy: response blocked by secret-scanner", http.StatusForbidden)
			return
		}
		w.WriteHeader(status)
		_, _ = w.Write(body)
	}
}

// forward — POST the validated body to the upstream MCP server.
// Returns (body, status, err); transport-level error returns status=0.
// hc.Timeout bounds the request; richer per-request cancellation is a
// future-work item once the agent-side client passes a deadline header.
func forward(hc *http.Client, upstream string, body []byte) ([]byte, int, error) {
	if upstream == "" {
		return nil, 0, errors.New("forward: empty upstream url")
	}
	resp, err := hc.Post(upstream, "application/json", bytes.NewReader(body))
	if err != nil {
		return nil, 0, err
	}
	defer resp.Body.Close()
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, resp.StatusCode, err
	}
	return b, resp.StatusCode, nil
}
