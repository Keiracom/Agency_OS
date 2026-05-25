// Tests for DefaultValidator — security-gate negative-path coverage per
// feedback_negative_path_test_before_approve. Engineer-tier extends these as
// the validator surface grows (regex secret patterns, schema versioning, etc).
package validator

import (
	"strings"
	"testing"

	"github.com/keiracom/keiracom_system/go_sidecar/internal/config"
)

// fixture — small static config exercised by all tests.
func fixture() *config.Config {
	return &config.Config{
		Tenants: map[string]config.Tenant{
			"tenant_a": {
				ID:             "tenant_a",
				AllowedTools:   []string{"read_file", "http_get"},
				AllowedDomains: []string{"api.example.com"},
				AllowedPaths:   []string{"/workspace/tenant_a/"},
				SystemPathDeny: []string{"/var/keiracom/system/", "/var/keiracom/reasoning_traces/"},
				SecretPatterns: []string{"sk-ant-"},
			},
		},
		GlobalSecretPatterns: []string{"BEGIN RSA PRIVATE KEY"},
	}
}

// 1. negative — unknown tenant denied.
func TestAllow_UnknownTenant(t *testing.T) {
	v := New(fixture())
	err := v.Allow(ToolCall{TenantID: "tenant_ghost", Tool: "read_file"})
	if err == nil {
		t.Fatal("expected deny for unknown tenant; got nil")
	}
	if !strings.Contains(err.Error(), "unknown tenant") {
		t.Fatalf("expected 'unknown tenant' reason; got %v", err)
	}
}

// 2. negative — tool not in tenant allowlist.
func TestAllow_ToolNotInAllowlist(t *testing.T) {
	v := New(fixture())
	err := v.Allow(ToolCall{TenantID: "tenant_a", Tool: "shell_exec"})
	if err == nil {
		t.Fatal("expected deny for out-of-allowlist tool; got nil")
	}
	if !strings.Contains(err.Error(), "tool not in tenant allowlist") {
		t.Fatalf("expected 'tool not in tenant allowlist' reason; got %v", err)
	}
}

// 3. negative — system path access denied (closes ux.files.system_files_hidden GAP).
func TestAllow_SystemPathDenied(t *testing.T) {
	v := New(fixture())
	err := v.Allow(ToolCall{
		TenantID: "tenant_a",
		Tool:     "read_file",
		Path:     "/var/keiracom/system/reasoning.log",
	})
	if err == nil {
		t.Fatal("expected deny for system path; got nil")
	}
	if !strings.Contains(err.Error(), "system path access denied") {
		t.Fatalf("expected 'system path access denied' reason; got %v", err)
	}
}

// 4. negative — outbound domain not whitelisted.
func TestAllow_DomainNotAllowed(t *testing.T) {
	v := New(fixture())
	err := v.Allow(ToolCall{
		TenantID: "tenant_a",
		Tool:     "http_get",
		Domain:   "evil.example.org",
	})
	if err == nil {
		t.Fatal("expected deny for non-whitelisted domain; got nil")
	}
	if !strings.Contains(err.Error(), "domain not in tenant allowlist") {
		t.Fatalf("expected 'domain not in tenant allowlist' reason; got %v", err)
	}
}

// 5. negative — empty payload (zero-value ToolCall) — no tenant resolves.
func TestAllow_EmptyPayload(t *testing.T) {
	v := New(fixture())
	err := v.Allow(ToolCall{})
	if err == nil {
		t.Fatal("expected deny for empty payload (no tenant id); got nil")
	}
	if !strings.Contains(err.Error(), "unknown tenant") {
		t.Fatalf("expected 'unknown tenant' on empty payload; got %v", err)
	}
}

// 6. positive — valid tenant + tool + safe path + whitelisted domain.
func TestAllow_ValidCall(t *testing.T) {
	v := New(fixture())
	cases := []ToolCall{
		{TenantID: "tenant_a", Tool: "read_file", Path: "/workspace/tenant_a/notes.md"},
		{TenantID: "tenant_a", Tool: "http_get", Domain: "api.example.com"},
	}
	for i, c := range cases {
		if err := v.Allow(c); err != nil {
			t.Fatalf("case %d: expected allow; got deny: %v", i, err)
		}
	}
}

// 7. negative ScanResponse — secret pattern in body triggers deny.
func TestScanResponse_SecretLeak(t *testing.T) {
	v := New(fixture())
	body := []byte("here is your key sk-ant-deadbeef1234, do not share")
	err := v.ScanResponse("tenant_a", body)
	if err == nil {
		t.Fatal("expected deny on tenant-specific secret pattern hit; got nil")
	}
	// global pattern variant — same gate.
	body2 := []byte("-----BEGIN RSA PRIVATE KEY-----\nMIIEo...")
	if err := v.ScanResponse("tenant_a", body2); err == nil {
		t.Fatal("expected deny on global secret pattern hit; got nil")
	}
}

// 8. positive ScanResponse — clean body passes.
func TestScanResponse_Clean(t *testing.T) {
	v := New(fixture())
	body := []byte(`{"result":"ok","items":[1,2,3]}`)
	if err := v.ScanResponse("tenant_a", body); err != nil {
		t.Fatalf("expected allow on clean response; got deny: %v", err)
	}
}
