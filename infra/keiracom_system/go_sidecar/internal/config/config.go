// Package config — static whitelist config struct loaded from YAML at startup.
//
// Mechanical enforcement per `mcp.go_sidecar` Cat 10: "static config not
// knowledge graph". No policy language, no runtime mutation — agents see what
// the YAML lets them see.
package config

import (
	"encoding/json"
	"errors"
	"os"
)

// Tenant — the unit of isolation. One tenant per Keiracom customer.
type Tenant struct {
	ID              string   `json:"id"`
	AllowedTools    []string `json:"allowed_tools"`     // MCP tool names whitelisted for this tenant
	AllowedDomains  []string `json:"allowed_domains"`   // outbound HTTP domains allowed
	AllowedPaths    []string `json:"allowed_paths"`     // file-system paths customer may read/write (PREFIX match)
	SystemPathDeny  []string `json:"system_path_deny"`  // explicit deny list — system files NEVER queryable (ux.files.system_files_hidden)
	SecretPatterns  []string `json:"secret_patterns"`   // regex/substring patterns scanned against responses (no raw secret leaks)
}

// Config — top level: tenant map + global deny patterns.
type Config struct {
	Tenants               map[string]Tenant `json:"tenants"`
	GlobalSecretPatterns  []string          `json:"global_secret_patterns"`
}

// Load reads a JSON config file. YAML support is an engineer-tier choice;
// JSON is stdlib-only and keeps the scaffold dependency-free.
func Load(path string) (*Config, error) {
	if path == "" {
		return nil, errors.New("config: path required")
	}
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var c Config
	if err := json.Unmarshal(b, &c); err != nil {
		return nil, err
	}
	if c.Tenants == nil {
		c.Tenants = make(map[string]Tenant)
	}
	return &c, nil
}
