// Command sidecar — Go HTTP listener for the Keiracom security interceptor.
//
// Shape B from the research doc: per-tenant HTTP sidecar co-located with the
// agent container. Agents POST tool calls; sidecar validates against static
// config + forwards or rejects. Engineer-tier wires the forwarding half.
package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"

	"github.com/keiracom/keiracom_system/go_sidecar/internal/config"
	"github.com/keiracom/keiracom_system/go_sidecar/internal/validator"
)

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

	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"ok":true}`))
	})
	mux.HandleFunc("/validate", func(w http.ResponseWriter, r *http.Request) {
		var c validator.ToolCall
		if err := json.NewDecoder(r.Body).Decode(&c); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		if err := v.Allow(c); err != nil {
			// 403 + reason — agent caller logs and surfaces a sanitised denial to the LLM.
			http.Error(w, err.Error(), http.StatusForbidden)
			return
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"allow":true}`))
	})

	addr := os.Getenv("SIDECAR_ADDR")
	if addr == "" {
		addr = ":4100"
	}
	log.Printf("go_sidecar listening on %s (config %s)", addr, cfgPath)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatal(err)
	}
}
