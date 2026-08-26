import time
from collections import defaultdict, deque
import threading
from typing import List, Dict, Deque

from .types import QuotaPolicy, TokenUsage

class AnomalyDetector:
    """Detects velocity anomalies."""

    def __init__(self, policy: QuotaPolicy):
        self.policy = policy
        self._history: Dict[str, Deque[TokenUsage]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._window_size = 60.0  # 1 minute

    def _cleanup(self, agent_id: str, now: float):
        dq = self._history[agent_id]
        while dq and (now - dq[0].timestamp) > self._window_size:
            dq.popleft()

    def record(self, usage: TokenUsage):
        """Record usage event."""
        with self._lock:
            self._history[usage.agent_id].append(usage)
            self._cleanup(usage.agent_id, time.monotonic())

    def check(self, agent_id: str) -> List[str]:
        """Returns list of anomaly descriptions."""
        anomalies = []
        with self._lock:
            now = time.monotonic()
            self._cleanup(agent_id, now)
            dq = self._history.get(agent_id, [])

            if not dq:
                return anomalies

            tokens_per_min = sum(u.tokens_in + u.tokens_out for u in dq)
            cost_per_min = sum(u.cost_usd for u in dq)

            if self.policy.per_minute_token_limit > 0 and tokens_per_min > self.policy.per_minute_token_limit:
                anomalies.append(f"Token velocity {tokens_per_min}/min exceeds limit {self.policy.per_minute_token_limit}/min")

            if self.policy.per_minute_cost_limit_usd > 0 and cost_per_min > self.policy.per_minute_cost_limit_usd:
                anomalies.append(f"Cost velocity ${cost_per_min:.2f}/min exceeds limit ${self.policy.per_minute_cost_limit_usd:.2f}/min")

            # Basic spike detection (rate > 3x average) could be implemented here with longer history, 
            # for now we focus on the per-minute limits.

        return anomalies

    def is_anomalous(self, agent_id: str) -> bool:
        return len(self.check(agent_id)) > 0
