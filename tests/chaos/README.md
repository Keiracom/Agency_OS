# Chaos harness — `tests/chaos/`

KEI-132. Real chaos engineering scenarios run on every PR. Failures **block merge** (no `|| true` mask in CI).

## What's here

| File | Purpose |
|---|---|
| `__init__.py` | Package marker + scope rules summary. |
| `conftest.py` | `assert_completes_within()`, `simulate_stall()`, `db_available()` helpers + `chaos_db` / `chaos_redis` markers + autouse `pytest.mark.timeout(10)` backstop. |
| `test_db_timeout.py` | DB-timeout scenario (1 of 2 — KEI-132 brief). |

## Running locally

```bash
pytest tests/chaos -v --timeout=10
```

Real-infrastructure tests (`@pytest.mark.chaos_db`) skip cleanly when `DATABASE_URL` isn't set to a `postgresql://` DSN. To run the live-DB variant:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres pytest tests/chaos -v
```

## Adding a new scenario

Every scenario must include:

1. **A happy-path negative control** — a sub-budget op passes the wrapper. Guards against framework false-positives.
2. **The chaos assertion** — the failure mode the scenario detects (timeout, exception, wrong result).
3. **Either pure mock-time OR a `@pytest.mark.chaos_<X>` skip-gate** — never a flaky real-network call that can hang CI.

Skeleton:

```python
def test_my_scenario_happy_path() -> None:
    """Negative control — fast op passes the chaos wrapper."""
    assert_completes_within(BUDGET, fast_op)


def test_my_scenario_detects_failure_mode() -> None:
    """Acceptance: the chaos pattern triggers the framework's assertion."""
    with pytest.raises(ChaosTimeoutError):
        assert_completes_within(BUDGET, lambda: simulate_stall(BUDGET + 1))
```

## Why two timeout layers

- **Scenario-level (`assert_completes_within`)** — raises `ChaosTimeoutError` (an AssertionError, not a TimeoutError) with a diagnostic message. Lets tests assert ON the chaos detection working correctly.
- **pytest-timeout backstop (`@pytest.mark.timeout(10)` autouse)** — safety net for tests that forget the scenario wrapper. Without this, a runaway thread could hang CI for the full job-timeout window.

`ChaosTimeoutError` is deliberately NOT a `TimeoutError` so real network timeouts in test code don't get conflated with chaos-framework overrun signalling.

## CI integration

`.github/workflows/ci.yml` — `chaos-test` job. Runs after install on every PR, no `|| true` mask. KEI-132 acceptance: "PR blocked on chaos test failure."

## Scenario catalogue (current + planned)

| ID | File | Status | Description |
|---|---|---|---|
| C-1 | `test_db_timeout.py` | landed | 5s DB stall detection (mock + optional real psycopg via `chaos_db`) |
| C-2 | tbd | planned (KEI-133) | 4 additional scenarios (network partition, Redis disconnect, OOM, etc.) |
