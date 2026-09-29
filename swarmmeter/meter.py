from __future__ import annotations

import threading
from pathlib import Path

from .anomaly import AnomalyDetector
from .breaker import CircuitBreaker
from .bucket import TokenBucket
from .quota import QuotaManager
from .types import BreakerConfig, MeterStats, QuotaPolicy, TokenUsage


class TokenMeter:
    """Top-level facade combining bucket, breaker, anomaly, and quota."""

    def __init__(self, policy: QuotaPolicy | None = None, db_path: Path | None = None):
        self.policy = policy or QuotaPolicy()
        self.quota_manager = QuotaManager(self.policy, db_path)
        self.anomaly_detector = AnomalyDetector(self.policy)
        self._breakers: dict[str, CircuitBreaker] = {}
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()
        self._breaker_config = BreakerConfig()

    def get_breaker(self, agent_id: str) -> CircuitBreaker:
        """Get per-agent circuit breaker."""
        with self._lock:
            if agent_id not in self._breakers:
                self._breakers[agent_id] = CircuitBreaker(self._breaker_config)
            return self._breakers[agent_id]

    def _get_bucket(self, agent_id: str) -> TokenBucket:
        with self._lock:
            if agent_id not in self._buckets:
                # Default rate limits if policy limits exist
                cap = self.policy.per_minute_token_limit or 1000000
                self._buckets[agent_id] = TokenBucket(capacity=cap, refill_rate=cap/60.0)
            return self._buckets[agent_id]

    def record(self, usage: TokenUsage):
        """Record usage, check all policies."""
        # 1. Quota
        self.quota_manager.record_usage(usage)
        
        # 2. Anomaly
        self.anomaly_detector.record(usage)
        
        # 3. Bucket consumer (if applicable, typically done beforehand, but we can do it here too)
        self._get_bucket(usage.agent_id).consume(usage.tokens_in + usage.tokens_out)

    def check_rate(self, agent_id: str, tokens: int) -> bool:
        """Check if rate allows."""
        return self._get_bucket(agent_id).consume(tokens)

    def stats(self) -> MeterStats:
        return self.quota_manager.stats()
