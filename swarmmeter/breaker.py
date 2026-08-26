import time
import threading
from typing import Callable, Any
from .types import BreakerState, BreakerConfig, CircuitOpenError

class CircuitBreaker:
    """Circuit breaker pattern."""

    def __init__(self, config: BreakerConfig):
        self.config = config
        self._state = BreakerState.CLOSED
        self._failures = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> BreakerState:
        with self._lock:
            if self._state == BreakerState.OPEN:
                now = time.monotonic()
                if now - self._last_failure_time >= self.config.reset_timeout_seconds:
                    self._state = BreakerState.HALF_OPEN
                    self._half_open_calls = 0
            return self._state

    def call(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute function through breaker."""
        state = self.state
        if state == BreakerState.OPEN:
            raise CircuitOpenError("Circuit is OPEN")
        elif state == BreakerState.HALF_OPEN:
            with self._lock:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitOpenError("Circuit is HALF_OPEN, max calls reached")
                self._half_open_calls += 1

        try:
            result = fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise e

    def record_success(self):
        """Record successful call."""
        with self._lock:
            self._failures = 0
            self._state = BreakerState.CLOSED

    def record_failure(self):
        """Record failed call."""
        with self._lock:
            self._failures += 1
            if self._failures >= self.config.failure_threshold or self._state == BreakerState.HALF_OPEN:
                self._state = BreakerState.OPEN
                self._last_failure_time = time.monotonic()

    def reset(self):
        """Force reset to CLOSED."""
        with self._lock:
            self._state = BreakerState.CLOSED
            self._failures = 0
            self._half_open_calls = 0
