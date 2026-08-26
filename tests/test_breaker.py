import time
import pytest
from swarmmeter.breaker import CircuitBreaker
from swarmmeter.types import BreakerConfig, BreakerState, CircuitOpenError

def test_breaker_success():
    breaker = CircuitBreaker(BreakerConfig())
    def success_fn():
        return 42
    assert breaker.call(success_fn) == 42
    assert breaker.state == BreakerState.CLOSED

def test_breaker_failure_threshold():
    breaker = CircuitBreaker(BreakerConfig(failure_threshold=2))
    def fail_fn():
        raise ValueError("Error")
    
    with pytest.raises(ValueError):
        breaker.call(fail_fn)
    assert breaker.state == BreakerState.CLOSED

    with pytest.raises(ValueError):
        breaker.call(fail_fn)
    assert breaker.state == BreakerState.OPEN

def test_breaker_half_open():
    breaker = CircuitBreaker(BreakerConfig(failure_threshold=1, reset_timeout_seconds=0.1, half_open_max_calls=1))
    def fail_fn():
        raise ValueError("Error")
    
    with pytest.raises(ValueError):
        breaker.call(fail_fn)
    assert breaker.state == BreakerState.OPEN

    time.sleep(0.15)
    assert breaker.state == BreakerState.HALF_OPEN
    
    # Successful call in half-open state should close it
    def success_fn():
        return True
    
    breaker.call(success_fn)
    assert breaker.state == BreakerState.CLOSED
