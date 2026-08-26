from dataclasses import dataclass
from enum import Enum

class MeterError(Exception):
    """Base exception for meter errors."""

class RateLimitExceeded(MeterError):
    """Raised when a rate limit is exceeded."""

class CircuitOpenError(MeterError):
    """Raised when a circuit breaker is open."""

class QuotaExhausted(MeterError):
    """Raised when a budget quota is exhausted."""

@dataclass
class TokenUsage:
    agent_id: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    timestamp: float
    model: str
    provider: str

@dataclass
class RateWindow:
    window_seconds: float
    max_tokens: int
    max_cost_usd: float
    current_tokens: int = 0
    current_cost_usd: float = 0.0

class BreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

@dataclass
class BreakerConfig:
    failure_threshold: int = 5
    reset_timeout_seconds: float = 60.0
    half_open_max_calls: int = 3

@dataclass
class QuotaPolicy:
    daily_budget_usd: float = 0.0
    per_agent_budget_usd: float = 0.0
    per_minute_token_limit: int = 0
    per_minute_cost_limit_usd: float = 0.0

@dataclass
class MeterStats:
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    active_agents: int = 0
    breaker_trips: int = 0
    quota_violations: int = 0
