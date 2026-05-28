package ratelimit

import (
	"testing"
	"time"
)

// fakeClock — deterministic clock for refill math.
type fakeClock struct{ t time.Time }

func (c *fakeClock) now() time.Time { return c.t }

// 1. Unregistered tenant defaults to allow (no spec).
func TestAllow_UnregisteredAllows(t *testing.T) {
	l := New(time.Now)
	if !l.Allow("tenant_unknown") {
		t.Fatal("unregistered tenant should allow (no spec)")
	}
}

// 2. IsZero spec disables limit (allow).
func TestAllow_ZeroSpecAllows(t *testing.T) {
	l := New(time.Now)
	l.SetTenant("tenant_x", Spec{RPS: 0, Burst: 0})
	if !l.Allow("tenant_x") {
		t.Fatal("zero spec should allow (rate limit disabled)")
	}
}

// 3. Initial burst is honoured — Burst N calls succeed back-to-back.
func TestAllow_InitialBurst(t *testing.T) {
	clk := &fakeClock{t: time.Unix(0, 0)}
	l := New(clk.now)
	l.SetTenant("tenant_a", Spec{RPS: 1, Burst: 5})
	for i := 0; i < 5; i++ {
		if !l.Allow("tenant_a") {
			t.Fatalf("burst call %d should allow", i)
		}
	}
	if l.Allow("tenant_a") {
		t.Fatal("6th call should deny — burst exhausted")
	}
}

// 4. Refill at RPS — 1 second after exhaustion gives 1 token back at RPS=1.
func TestAllow_RefillsAtRPS(t *testing.T) {
	clk := &fakeClock{t: time.Unix(0, 0)}
	l := New(clk.now)
	l.SetTenant("tenant_b", Spec{RPS: 2, Burst: 2})
	if !l.Allow("tenant_b") {
		t.Fatal("first call should allow")
	}
	if !l.Allow("tenant_b") {
		t.Fatal("second call should allow")
	}
	if l.Allow("tenant_b") {
		t.Fatal("third call should deny")
	}
	clk.t = clk.t.Add(time.Second) // RPS=2 → 2 tokens back
	if !l.Allow("tenant_b") {
		t.Fatal("after 1s refill should allow")
	}
	if !l.Allow("tenant_b") {
		t.Fatal("second after-refill call should allow")
	}
	if l.Allow("tenant_b") {
		t.Fatal("third after-refill call should deny")
	}
}

// 5. Refill caps at Burst — long sleep doesn't yield more than Burst tokens.
func TestAllow_RefillCapsAtBurst(t *testing.T) {
	clk := &fakeClock{t: time.Unix(0, 0)}
	l := New(clk.now)
	l.SetTenant("tenant_c", Spec{RPS: 100, Burst: 3})
	for i := 0; i < 3; i++ {
		_ = l.Allow("tenant_c")
	}
	clk.t = clk.t.Add(time.Hour) // huge refill — still capped at Burst=3
	allowed := 0
	for i := 0; i < 10; i++ {
		if l.Allow("tenant_c") {
			allowed++
		}
	}
	if allowed != 3 {
		t.Fatalf("expected exactly 3 allows after cap; got %d", allowed)
	}
}

// 6. Per-tenant isolation — exhausting A leaves B's bucket untouched.
func TestAllow_PerTenantIsolation(t *testing.T) {
	clk := &fakeClock{t: time.Unix(0, 0)}
	l := New(clk.now)
	l.SetTenant("tenant_a", Spec{RPS: 1, Burst: 1})
	l.SetTenant("tenant_b", Spec{RPS: 1, Burst: 1})
	_ = l.Allow("tenant_a")
	if l.Allow("tenant_a") {
		t.Fatal("tenant_a should be exhausted")
	}
	if !l.Allow("tenant_b") {
		t.Fatal("tenant_b should be untouched by tenant_a exhaustion")
	}
}

// 7. SetTenant resets the bucket — useful for config reload.
func TestSetTenant_ResetsBucket(t *testing.T) {
	clk := &fakeClock{t: time.Unix(0, 0)}
	l := New(clk.now)
	l.SetTenant("tenant_d", Spec{RPS: 1, Burst: 1})
	_ = l.Allow("tenant_d")
	if l.Allow("tenant_d") {
		t.Fatal("tenant_d should be exhausted before reset")
	}
	l.SetTenant("tenant_d", Spec{RPS: 1, Burst: 1}) // reset
	if !l.Allow("tenant_d") {
		t.Fatal("after SetTenant reset, bucket should be full again")
	}
}
