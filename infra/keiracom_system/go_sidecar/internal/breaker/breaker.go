// Package breaker — per-MCP-server circuit breaker.
//
// Wave 1 dispatch Agency_OS-2c7m. One Breaker per logical MCP-server upstream;
// Manager hands them out by name. Three states: Closed (forward), Open (reject
// fast), HalfOpen (one probe at a time). Threshold + cooldown configurable.
//
// Fail-closed posture: when the breaker is Open or HalfOpen-probing, Allow()
// returns ErrBreakerOpen and the /proxy handler returns 503 to the caller.
// Consistent with the sidecar's Cat 10 mechanical-enforcement posture.
package breaker

import (
	"errors"
	"sync"
	"time"
)

// ErrBreakerOpen — returned by Allow when the breaker is Open or probing.
var ErrBreakerOpen = errors.New("breaker: open")

// State — closed | open | halfOpen.
type State int

const (
	StateClosed State = iota
	StateOpen
	StateHalfOpen
)

// Config — per-breaker settings. Zero-value safe via Default().
type Config struct {
	FailureThreshold int           // consecutive failures before Open
	Cooldown         time.Duration // time in Open before HalfOpen probe
	Now              func() time.Time
}

// Default — production defaults: 5 failures → Open, 30s cooldown.
func Default() Config {
	return Config{FailureThreshold: 5, Cooldown: 30 * time.Second, Now: time.Now}
}

// Breaker — one per upstream MCP server. Safe for concurrent use.
type Breaker struct {
	cfg      Config
	mu       sync.Mutex
	state    State
	failures int
	openedAt time.Time
	probing  bool
}

// New — construct a Breaker with the supplied config.
func New(cfg Config) *Breaker {
	if cfg.Now == nil {
		cfg.Now = time.Now
	}
	if cfg.FailureThreshold <= 0 {
		cfg.FailureThreshold = 5
	}
	if cfg.Cooldown <= 0 {
		cfg.Cooldown = 30 * time.Second
	}
	return &Breaker{cfg: cfg}
}

// Allow — call before forwarding. nil = forward; ErrBreakerOpen = reject fast.
func (b *Breaker) Allow() error {
	b.mu.Lock()
	defer b.mu.Unlock()
	switch b.state {
	case StateClosed:
		return nil
	case StateOpen:
		if b.cfg.Now().Sub(b.openedAt) < b.cfg.Cooldown {
			return ErrBreakerOpen
		}
		b.state = StateHalfOpen
		b.probing = true
		return nil
	case StateHalfOpen:
		if b.probing {
			return ErrBreakerOpen
		}
		b.probing = true
		return nil
	}
	return ErrBreakerOpen
}

// Success — call on forward success. Resets the breaker.
func (b *Breaker) Success() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.state = StateClosed
	b.failures = 0
	b.probing = false
}

// Failure — call on forward failure. May trip the breaker open.
func (b *Breaker) Failure() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.probing = false
	if b.state == StateHalfOpen {
		b.state = StateOpen
		b.openedAt = b.cfg.Now()
		return
	}
	b.failures++
	if b.failures >= b.cfg.FailureThreshold {
		b.state = StateOpen
		b.openedAt = b.cfg.Now()
	}
}

// State — current state, for /health/breakers diagnostics.
func (b *Breaker) State() State {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.state
}

// Manager — lazy-instantiates one Breaker per upstream name.
type Manager struct {
	cfg Config
	mu  sync.Mutex
	bs  map[string]*Breaker
}

// NewManager — construct a Manager that hands out Breakers built from cfg.
func NewManager(cfg Config) *Manager {
	return &Manager{cfg: cfg, bs: map[string]*Breaker{}}
}

// Get — return (creating if needed) the breaker for the named MCP server.
func (m *Manager) Get(server string) *Breaker {
	m.mu.Lock()
	defer m.mu.Unlock()
	if b, ok := m.bs[server]; ok {
		return b
	}
	b := New(m.cfg)
	m.bs[server] = b
	return b
}
