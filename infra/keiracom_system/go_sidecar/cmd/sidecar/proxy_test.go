package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/keiracom/keiracom_system/go_sidecar/internal/breaker"
	"github.com/keiracom/keiracom_system/go_sidecar/internal/config"
	"github.com/keiracom/keiracom_system/go_sidecar/internal/ratelimit"
	"github.com/keiracom/keiracom_system/go_sidecar/internal/validator"
)

// helper — assemble a Config with one tenant pointing at upstreamURL as "search".
func fixtureCfg(upstreamURL string) *config.Config {
	return &config.Config{
		Tenants: map[string]config.Tenant{
			"tenant_a": {
				ID:             "tenant_a",
				AllowedTools:   []string{"read_file", "http_get"},
				AllowedDomains: []string{"api.example.com"},
				SystemPathDeny: []string{"/var/keiracom/system/"},
				SecretPatterns: []string{"sk-ant-"},
				RateLimit:      ratelimit.Spec{RPS: 100, Burst: 100},
				MCPServers:     map[string]string{"search": upstreamURL},
			},
		},
		GlobalSecretPatterns: []string{"BEGIN RSA PRIVATE KEY"},
	}
}

func setupSidecar(cfg *config.Config) (validator.Validator, *ratelimit.Limiter, *breaker.Manager, *http.Client) {
	v := validator.New(cfg)
	rl := ratelimit.New(time.Now)
	for id, t := range cfg.Tenants {
		rl.SetTenant(id, t.RateLimit)
	}
	bm := breaker.NewManager(breaker.Config{FailureThreshold: 2, Cooldown: 100 * time.Millisecond, Now: time.Now})
	return v, rl, bm, &http.Client{Timeout: 5 * time.Second}
}

// 1. /proxy happy path — validate + rate-limit + breaker pass; upstream 200; response returned.
func TestProxy_HappyPath(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
		_, _ = w.Write([]byte(`{"result":"ok"}`))
	}))
	defer upstream.Close()
	cfg := fixtureCfg(upstream.URL)
	v, rl, bm, hc := setupSidecar(cfg)
	h := proxyHandler(cfg, v, rl, bm, hc)

	body, _ := json.Marshal(proxyRequest{TenantID: "tenant_a", Tool: "read_file", Server: "search", Body: json.RawMessage(`{"q":"hi"}`)})
	req := httptest.NewRequest("POST", "/proxy", bytes.NewReader(body))
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	if rr.Code != 200 {
		t.Fatalf("expected 200; got %d body=%s", rr.Code, rr.Body.String())
	}
	if !strings.Contains(rr.Body.String(), `"result":"ok"`) {
		t.Fatalf("expected upstream body passthrough; got %s", rr.Body.String())
	}
}

// 2. /proxy denies when validator rejects (tool not allowed).
func TestProxy_ValidatorDeny(t *testing.T) {
	cfg := fixtureCfg("http://unused")
	v, rl, bm, hc := setupSidecar(cfg)
	h := proxyHandler(cfg, v, rl, bm, hc)
	body, _ := json.Marshal(proxyRequest{TenantID: "tenant_a", Tool: "shell_exec", Server: "search"})
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, httptest.NewRequest("POST", "/proxy", bytes.NewReader(body)))
	if rr.Code != http.StatusForbidden {
		t.Fatalf("expected 403; got %d", rr.Code)
	}
}

// 3. /proxy denies unknown MCP server.
func TestProxy_UnknownServer(t *testing.T) {
	cfg := fixtureCfg("http://unused")
	v, rl, bm, hc := setupSidecar(cfg)
	h := proxyHandler(cfg, v, rl, bm, hc)
	body, _ := json.Marshal(proxyRequest{TenantID: "tenant_a", Tool: "read_file", Server: "phantom"})
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, httptest.NewRequest("POST", "/proxy", bytes.NewReader(body)))
	if rr.Code != http.StatusForbidden {
		t.Fatalf("expected 403 unknown server; got %d body=%s", rr.Code, rr.Body.String())
	}
}

// 4. /proxy: upstream 5xx flips the breaker after threshold; subsequent calls 503.
func TestProxy_BreakerOpensOnUpstream5xx(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(500)
	}))
	defer upstream.Close()
	cfg := fixtureCfg(upstream.URL)
	v, rl, bm, hc := setupSidecar(cfg)
	h := proxyHandler(cfg, v, rl, bm, hc)

	body, _ := json.Marshal(proxyRequest{TenantID: "tenant_a", Tool: "read_file", Server: "search"})
	// first two requests forward and fail → breaker trips
	for i := 0; i < 2; i++ {
		rr := httptest.NewRecorder()
		h.ServeHTTP(rr, httptest.NewRequest("POST", "/proxy", bytes.NewReader(body)))
		if rr.Code != 500 {
			t.Fatalf("iter %d: expected 500 from upstream passthrough; got %d", i, rr.Code)
		}
	}
	// third request — breaker is open
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, httptest.NewRequest("POST", "/proxy", bytes.NewReader(body)))
	if rr.Code != http.StatusServiceUnavailable {
		t.Fatalf("expected 503 breaker-open; got %d body=%s", rr.Code, rr.Body.String())
	}
}

// 5. /proxy: response scanner blocks leaked secret.
func TestProxy_ResponseScanBlocksLeakedSecret(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(200)
		_, _ = w.Write([]byte(`{"oops":"sk-ant-deadbeef1234"}`))
	}))
	defer upstream.Close()
	cfg := fixtureCfg(upstream.URL)
	v, rl, bm, hc := setupSidecar(cfg)
	h := proxyHandler(cfg, v, rl, bm, hc)
	body, _ := json.Marshal(proxyRequest{TenantID: "tenant_a", Tool: "read_file", Server: "search"})
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, httptest.NewRequest("POST", "/proxy", bytes.NewReader(body)))
	if rr.Code != http.StatusForbidden {
		t.Fatalf("expected 403 from secret scanner; got %d body=%s", rr.Code, rr.Body.String())
	}
}

// 6. /validate: rate-limit returns 429 once bucket empty.
func TestValidate_RateLimit429(t *testing.T) {
	cfg := fixtureCfg("http://unused")
	// tighten rate limit for this test
	tA := cfg.Tenants["tenant_a"]
	tA.RateLimit = ratelimit.Spec{RPS: 0.0001, Burst: 1}
	cfg.Tenants["tenant_a"] = tA
	v, rl, _, _ := setupSidecar(cfg)
	h := validateHandler(v, rl)
	body, _ := json.Marshal(validator.ToolCall{TenantID: "tenant_a", Tool: "read_file"})
	// first allowed
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, httptest.NewRequest("POST", "/validate", bytes.NewReader(body)))
	if rr.Code != 200 {
		t.Fatalf("first call expected 200; got %d", rr.Code)
	}
	// second denied — bucket empty
	rr = httptest.NewRecorder()
	h.ServeHTTP(rr, httptest.NewRequest("POST", "/validate", bytes.NewReader(body)))
	if rr.Code != http.StatusTooManyRequests {
		t.Fatalf("second call expected 429; got %d", rr.Code)
	}
}

// 7. /proxy: tenant-scoped — call rejected when tenant unknown.
func TestProxy_UnknownTenant(t *testing.T) {
	cfg := fixtureCfg("http://unused")
	v, rl, bm, hc := setupSidecar(cfg)
	h := proxyHandler(cfg, v, rl, bm, hc)
	body, _ := json.Marshal(proxyRequest{TenantID: "tenant_ghost", Tool: "read_file", Server: "search"})
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, httptest.NewRequest("POST", "/proxy", bytes.NewReader(body)))
	if rr.Code != http.StatusForbidden {
		t.Fatalf("expected 403 unknown tenant; got %d body=%s", rr.Code, rr.Body.String())
	}
}

var _ = io.EOF // keep io imported for future helpers
