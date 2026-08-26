import time
import threading

class TokenBucket:
    """Token bucket rate limiter."""
    
    def __init__(self, capacity: int, refill_rate: float, refill_interval: float = 1.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed > self.refill_interval:
            intervals = elapsed // self.refill_interval
            new_tokens = intervals * self.refill_rate
            self._tokens = min(self.capacity, self._tokens + new_tokens)
            self._last_refill += intervals * self.refill_interval

    def consume(self, tokens: int) -> bool:
        """Attempt to consume tokens, returns True if allowed."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def wait_and_consume(self, tokens: int) -> float:
        """Blocking wait, returns wait time."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return 0.0
                
                needed = tokens - self._tokens
                intervals = (needed + self.refill_rate - 1) // self.refill_rate
                wait_time = intervals * self.refill_interval - (time.monotonic() - self._last_refill)
                if wait_time < 0:
                    wait_time = 0.0
            
            if wait_time > 0:
                time.sleep(wait_time)

    def remaining(self) -> int:
        """Current available tokens."""
        with self._lock:
            self._refill()
            return int(self._tokens)

    def reset(self):
        """Refill to capacity."""
        with self._lock:
            self._tokens = float(self.capacity)
            self._last_refill = time.monotonic()
