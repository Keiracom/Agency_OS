// Package validator — Validator interface + DefaultValidator stub.
//
// Enforces the three mcp.go_sidecar responsibilities surfaced in the V2 lock:
//  1. Tool-call whitelist (Cat 10).
//  2. System file isolation (Cat 19 ux.files.system_files_hidden — deny prefix match).
//  3. Secret leak detection on responses (Cat 16 infra.secrets_management).
//
// Engineer-tier fills out the per-rule logic; this scaffold proves the shape compiles.
package validator

import (
	"errors"
	"strings"

	"github.com/keiracom/keiracom_system/go_sidecar/internal/config"
)

// ToolCall — minimal shape of an MCP tool invocation.
type ToolCall struct {
	TenantID string
	Tool     string
	Path     string // file-system tools only (read_file, write_file, etc.)
	Domain   string // http tools only
}

// Validator — interface that interceptors call before forwarding to MCP server.
type Validator interface {
	Allow(c ToolCall) error                // returns nil on allow, error on deny (with reason)
	ScanResponse(tenantID string, body []byte) error // post-call: deny if secret pattern hit
}

// DefaultValidator — static-config implementation. Mechanical: string match, no regex eval at hot path.
type DefaultValidator struct {
	cfg *config.Config
}

func New(cfg *config.Config) *DefaultValidator {
	return &DefaultValidator{cfg: cfg}
}

func (v *DefaultValidator) Allow(c ToolCall) error {
	t, ok := v.cfg.Tenants[c.TenantID]
	if !ok {
		return errors.New("validator: unknown tenant")
	}
	if !contains(t.AllowedTools, c.Tool) {
		return errors.New("validator: tool not in tenant allowlist")
	}
	for _, deny := range t.SystemPathDeny {
		if c.Path != "" && strings.HasPrefix(c.Path, deny) {
			return errors.New("validator: system path access denied (ux.files.system_files_hidden)")
		}
	}
	if c.Domain != "" && !contains(t.AllowedDomains, c.Domain) {
		return errors.New("validator: domain not in tenant allowlist")
	}
	return nil
}

func (v *DefaultValidator) ScanResponse(tenantID string, body []byte) error {
	t := v.cfg.Tenants[tenantID]
	patterns := append([]string{}, v.cfg.GlobalSecretPatterns...)
	patterns = append(patterns, t.SecretPatterns...)
	s := string(body)
	for _, p := range patterns {
		if strings.Contains(s, p) {
			return errors.New("validator: secret pattern hit in response")
		}
	}
	return nil
}

func contains(xs []string, x string) bool {
	for _, v := range xs {
		if v == x {
			return true
		}
	}
	return false
}
