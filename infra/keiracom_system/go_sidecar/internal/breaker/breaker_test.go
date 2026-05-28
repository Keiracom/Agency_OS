package breaker

import (
	"testing"
	"time"
)

// fakeClock — deterministic clock so cooldown tests don't sleep.
type fakeClock struct{ t time.Time }

func (c *fakeClock) now() time.Time { return c.t }

// 1. closed breaker allows.
func TestAllow_ClosedAllows(t *testing.T) {
	b := New(Default())
	if err := b.Allow(); err != nil {
		t.Fatalf("closed breaker should allow; got %v", err)
	}
}

// 2. N consecutive failures trip Open.
func TestFailure_TripsOpenAfterThreshold(t *testing.T) {
	b := New(Config{FailureThreshold: 3, Cooldown: time.Minute, Now: time.Now})
	for i := 0; i < 3; i++ {
		_ = b.Allow()
		b.Failure()
	}
	if b.State() != StateOpen {
		t.Fatalf("expected Open after 3 failures; got state=%v", b.State())
	}
	if err := b.Allow(); err != ErrBreakerOpen {
		t.Fatalf("expected ErrBreakerOpen; got %v", err)
	}
}

// 3. After cooldown the breaker transitions to HalfOpen on next Allow.
func TestAllow_CooldownToHalfOpen(t *testing.T) {
	clk := &fakeClock{t: time.Unix(0, 0)}
	b := New(Config{FailureThreshold: 2, Cooldown: 5 * time.Second, Now: clk.now})
	for i := 0; i < 2; i++ {
		_ = b.Allow()
		b.Failure()
	}
	clk.t = clk.t.Add(6 * time.Second)
	if err := b.Allow(); err != nil {
		t.Fatalf("expected HalfOpen probe to allow; got %v", err)
	}
	if b.State() != StateHalfOpen {
		t.Fatalf("expected HalfOpen after cooldown; got %v", b.State())
	}
	// second concurrent caller while probing is rejected
	if err := b.Allow(); err != ErrBreakerOpen {
		t.Fatalf("expected second probe to be rejected; got %v", err)
	}
}

// 4. HalfOpen probe success → Closed.
func TestHalfOpen_SuccessClosesBreaker(t *testing.T) {
	clk := &fakeClock{t: time.Unix(0, 0)}
	b := New(Config{FailureThreshold: 1, Cooldown: time.Second, Now: clk.now})
	_ = b.Allow()
	b.Failure()
	clk.t = clk.t.Add(2 * time.Second)
	_ = b.Allow() // half-open probe
	b.Success()
	if b.State() != StateClosed {
		t.Fatalf("expected Closed after probe Success; got %v", b.State())
	}
}

// 5. HalfOpen probe failure → Open again.
func TestHalfOpen_FailureReopens(t *testing.T) {
	clk := &fakeClock{t: time.Unix(0, 0)}
	b := New(Config{FailureThreshold: 1, Cooldown: time.Second, Now: clk.now})
	_ = b.Allow()
	b.Failure()
	clk.t = clk.t.Add(2 * time.Second)
	_ = b.Allow() // half-open probe
	b.Failure()
	if b.State() != StateOpen {
		t.Fatalf("expected Open after probe Failure; got %v", b.State())
	}
}

// 6. Manager hands out one Breaker per server name, stable across Gets.
func TestManager_GetIsStablePerServer(t *testing.T) {
	m := NewManager(Default())
	a := m.Get("mcp_search")
	b := m.Get("mcp_search")
	c := m.Get("mcp_telnyx")
	if a != b {
		t.Fatal("Manager.Get returned different breakers for same server")
	}
	if a == c {
		t.Fatal("Manager.Get returned same breaker for different servers")
	}
}
