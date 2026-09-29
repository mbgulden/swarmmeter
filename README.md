# ⏱️ SwarmMeter

[![CI](https://github.com/mbgulden/swarmmeter/actions/workflows/ci.yml/badge.svg)](https://github.com/mbgulden/swarmmeter/actions)
[![PyPI version](https://img.shields.io/badge/pypi-v0.1.0-blue.svg)](https://pypi.org/project/swarmmeter/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Distributed token velocity meter, rate limiter, and circuit breaker for AI agent swarm cost control.**
> *Prevents runaway prompt loops, enforces per-agent rate limits, and tracks cluster-wide spend quotas — so one misbehaving agent can never take down the budget or the provider connection.*

---

## 💡 Why SwarmMeter?

An agent swarm burns tokens at machine speed, and the failure modes are expensive:

- **Runaway prompt loops**: one agent stuck in a retry spiral spends your budget in minutes.
- **Rate-limit crashes**: a burst of parallel agents trips provider 429s and cascades into failed tasks.
- **Invisible spend**: no single place sees total tokens and dollars across all agents and models.
- **Provider outages**: one flaky endpoint takes every agent down with it because nothing trips a breaker.

**SwarmMeter** solves this by giving every agent a shared, thread-safe metering layer:
a token bucket per agent for rate limits, a circuit breaker per agent for flaky providers,
an anomaly detector for velocity spikes, and a SQLite-backed quota manager for daily and
per-agent dollar budgets. All of it wraps in one `TokenMeter` facade with zero runtime dependencies.

---

## 🏛️ System Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │               AI Agent Swarm                 │
                    │      (N agents calling LLM providers)        │
                    └──────────────────────┬───────────────────────┘
                                           │
                                token usage events
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │                TokenMeter                    │
                    │   - TokenBucket (per-agent rate limiting)    │
                    │   - CircuitBreaker (per-agent fault cutout)  │
                    │   - AnomalyDetector (per-minute velocity)    │
                    │   - QuotaManager (SQLite dollar budgets)     │
                    └──────────────────────┬───────────────────────┘
                                           │
                               enforcement & stats
                                           ▼
             ┌──────────────────┬──────────────────┬──────────────────┐
             │  RateLimitExceeded  │  CircuitOpenError │  QuotaExhausted │
             │  back off / queue   │  fail over model  │  halt agent     │
             └──────────────────┴──────────────────┴──────────────────┘
```

---

## 🧩 Components

| Component | What it does | Key API |
|---|---|---|
| **TokenBucket** | Thread-safe token-bucket rate limiter with refill over a monotonic clock. | `consume(tokens) -> bool`, `wait_and_consume(tokens)`, `remaining()`, `reset()` |
| **CircuitBreaker** | Classic closed → open → half-open breaker around provider calls. Trips after `failure_threshold` failures, probes again after `reset_timeout_seconds`. | `call(fn, *args, **kwargs)`, `record_success()`, `record_failure()`, `state` |
| **AnomalyDetector** | Flags per-minute token or cost velocity over policy limits using a 60-second sliding window. | `record(usage)`, `check(agent_id) -> list[str]`, `is_anomalous(agent_id)` |
| **QuotaManager** | SQLite-persisted usage ledger enforcing `daily_budget_usd` and `per_agent_budget_usd`. Point `db_path` at a shared file to sync quota across processes. | `record_usage(usage)`, `remaining_budget(agent_id)`, `reset_daily()`, `stats()` |
| **TokenMeter** | Top-level facade combining all four behind one thread-safe API. | `record(usage)`, `check_rate(agent_id, tokens)`, `get_breaker(agent_id)`, `stats()` |

Fail-closed exceptions (all subclasses of `MeterError`):
`RateLimitExceeded` · `CircuitOpenError` · `QuotaExhausted`

---

## 📦 Installation

```bash
pip install swarmmeter
```

*Pure Python standard library. Zero runtime dependencies.*

Requires Python 3.9+.

---

## 🚀 Quick Start (< 5 minutes)

```python
import time
from swarmmeter import TokenMeter, TokenUsage, QuotaPolicy

# 1. Build a meter with a daily budget and a per-minute velocity cap
policy = QuotaPolicy(
    daily_budget_usd=25.00,
    per_agent_budget_usd=5.00,
    per_minute_token_limit=200_000,
    per_minute_cost_limit_usd=1.00,
)
meter = TokenMeter(policy=policy)  # pass db_path=Path(...) to persist quota across processes

# 2. Rate-limit before a provider call (per-agent token bucket)
if not meter.check_rate("agent-1", tokens=1500):
    raise SystemExit("rate limited — back off")

# 3. Run the call through a per-agent circuit breaker
breaker = meter.get_breaker("agent-1")
response = breaker.call(my_provider_call, prompt)

# 4. Record what the call actually used (tokens + dollars)
meter.record(TokenUsage(
    agent_id="agent-1",
    tokens_in=1200, tokens_out=340, cost_usd=0.004,
    timestamp=time.time(), model="claude-4", provider="anthropic",
))

# 5. Read aggregate stats across the whole swarm
stats = meter.stats()
print(f"{stats.total_tokens} tokens, ${stats.total_cost_usd:.2f}, "
      f"{stats.active_agents} agents, {stats.quota_violations} quota violations")
```

Quota over the limit? `meter.record(...)` raises `QuotaExhausted` — catch it and halt the agent.
Agent burning too fast? `AnomalyDetector.is_anomalous(agent_id)` tells you before the budget is gone.
Provider flapping? `breaker.call(...)` raises `CircuitOpenError` while the circuit is open so you can fail over.

---

## ⌨️ CLI Usage

The `swarmmeter` entry point ships a lightweight operational CLI:

```bash
# Show help
swarmmeter --help

# Quick liveness check
swarmmeter status        # -> Status: OK

# Reset an agent's state
swarmmeter reset agent-1 # -> Resetting agent: agent-1

# Check quota posture
swarmmeter quota         # -> Quota: checking...

# Dump usage stats
swarmmeter stats         # -> Stats: 0 tokens used
```

---

## 🐍 Python SDK Integration

The library is typed (`py.typed` ships in the wheel) and thread-safe, so you can share one
`TokenMeter` across threads or point several processes at the same SQLite file:

```python
from pathlib import Path
from swarmmeter import (
    TokenMeter, TokenBucket, CircuitBreaker, AnomalyDetector, QuotaManager,
    QuotaPolicy, TokenUsage, BreakerConfig,
    MeterError, RateLimitExceeded, CircuitOpenError, QuotaExhausted,
)

# Share quota state across processes via one SQLite file
meter = TokenMeter(policy=QuotaPolicy(daily_budget_usd=100.0),
                   db_path=Path("/var/run/swarm/quota.db"))

try:
    meter.record(usage)
except QuotaExhausted:
    shutdown_agent(agent_id)
except MeterError as e:
    log(f"meter error: {e}")
```

### Enforcing hard budgets in an agent loop

```python
def agent_step(agent_id, prompt):
    if meter.anomaly_detector.is_anomalous(agent_id):
        return "paused: velocity anomaly"          # per-minute cap exceeded
    if meter.quota_manager.remaining_budget(agent_id) <= 0:
        return "paused: agent budget exhausted"    # per-agent dollar cap
    breaker = meter.get_breaker(agent_id)
    try:
        result = breaker.call(provider.chat, prompt)
    except CircuitOpenError:
        return "paused: provider circuit open"    # fail over to another model
    meter.record(usage_from(result, agent_id))
    return result
```

---

## 🤖 CI / CD Integration (GitHub Actions)

SwarmMeter ships with its own CI (3 OS × Python 3.9–3.12, build + `twine check`, CLI smoke test).
To gate your own agent swarm on budgets in a pipeline:

```yaml
name: Agent Swarm Gatekeeper

on:
  workflow_dispatch:

jobs:
  budget-gate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install SwarmMeter
        run: pip install swarmmeter

      - name: Assert spend is within budget
        run: python scripts/check_swarm_budget.py
```

---

## 🗺️ Swarm Ecosystem

SwarmMeter is part of the **Swarm Primitives Ecosystem** for autonomous agent swarms:

- 🔒 **SwarmLock**: Tokenized, non-blocking distributed advisory locks.
- ⏱️ **SwarmCron**: Native high-precision background cron scheduling.
- 🛡️ **SwarmProof**: Truth Oracle, evidence ledgers, and anti-hallucination gates.
- ⏱️ **SwarmMeter**: Token velocity metering, rate limiting, circuit breakers, and quota enforcement *(this package)*.
- 🔀 **SwarmRouter**: Intelligent query routing and model cascading *(coming soon)*.
- 🧠 **SwarmCurator**: Long-term memory distillation and context compaction *(coming soon)*.

SwarmMeter is the **cost-control primitive** of the family: it pairs naturally with
prismatic-engine, the multi-agent orchestration engine, metering every agent's
provider spend inside the swarm.

---

## 📄 License

MIT © GrowthWebDev
