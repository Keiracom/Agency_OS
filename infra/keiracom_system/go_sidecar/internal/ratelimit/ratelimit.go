// Package ratelimit — per-tenant token-bucket rate limiter.
//
// Wave 1 dispatch Agency_OS-2c7m. One bucket per tenant_id, configured from
// the tenant block in sidecar config. Standard token-bucket: continuous
// refill at RPS tokens/sec, capped at Burst. Allow consumes one token; if the
// bucket is empty Allow returns false and the caller emits 429.
//
// Fail-closed posture: unknown tenants get a NOT-FOUND response from the
// caller, not a "no-limit" pass. Empty/zero RateLimit means "unlimited"
// (explicit opt-in by absence), so RateLimit must be set in production.
package ratelimit

import (
	"sync"
	"time"
)

// Spec — per-tenant token-bucket parameters loaded from config.
type Spec struct {
	RPS   float64 `json:"rps"`   // refill rate (tokens per second)
	Burst int     `json:"burst"` // bucket capacity
}

// IsZero — true when no rate-limit applies (rate limit disabled for tenant).
func (s Spec) IsZero() bool { return s.RPS <= 0 || s.Burst <= 0 }

// bucket — internal state for a single tenant.
type bucket struct {
	spec   Spec
	tokens float64
	last   time.Time
}

// Limiter — manages one bucket per tenant. Safe for concurrent use.
type Limiter struct {
	now     func() time.Time
	mu      sync.Mutex
	buckets map[string]*bucket
	specs   map[string]Spec
}

// New — construct a Limiter wired to a clock (production: time.Now).
func New(now func() time.Time) *Limiter {
	if now == nil {
		now = time.Now
	}
	return &Limiter{now: now, buckets: map[string]*bucket{}, specs: map[string]Spec{}}
}

// SetTenant — register/replace the rate-limit spec for a tenant. Idempotent.
// Wiped buckets re-initialise at capacity on next Allow.
func (l *Limiter) SetTenant(tenantID string, spec Spec) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.specs[tenantID] = spec
	delete(l.buckets, tenantID)
}

// Allow — consume one token. Returns true if the call is permitted.
// Tenants without a spec return true (unlimited). Tenants with IsZero spec
// also return true — explicit disable.
func (l *Limiter) Allow(tenantID string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	spec, ok := l.specs[tenantID]
	if !ok || spec.IsZero() {
		return true
	}
	b, ok := l.buckets[tenantID]
	if !ok {
		b = &bucket{spec: spec, tokens: float64(spec.Burst), last: l.now()}
		l.buckets[tenantID] = b
	}
	now := l.now()
	elapsed := now.Sub(b.last).Seconds()
	if elapsed > 0 {
		b.tokens += elapsed * spec.RPS
		if b.tokens > float64(spec.Burst) {
			b.tokens = float64(spec.Burst)
		}
		b.last = now
	}
	if b.tokens >= 1 {
		b.tokens--
		return true
	}
	return false
}
