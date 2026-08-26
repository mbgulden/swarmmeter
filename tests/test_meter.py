import time
import pytest
from swarmmeter.meter import TokenMeter
from swarmmeter.types import TokenUsage, QuotaPolicy, QuotaExhausted, BreakerState

def test_token_meter_record_and_stats():
    meter = TokenMeter()
    usage = TokenUsage(
        agent_id="agent1",
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.05,
        timestamp=time.time(),
        model="test",
        provider="test"
    )
    
    meter.record(usage)
    stats = meter.stats()
    assert stats.total_tokens == 30
    assert stats.total_cost_usd == 0.05
    assert stats.active_agents == 1

def test_token_meter_quota_exhaustion():
    policy = QuotaPolicy(daily_budget_usd=1.0)
    meter = TokenMeter(policy=policy)
    
    usage = TokenUsage(
        agent_id="agent1",
        tokens_in=10,
        tokens_out=20,
        cost_usd=1.5,
        timestamp=time.time(),
        model="test",
        provider="test"
    )
    
    with pytest.raises(QuotaExhausted):
        meter.record(usage)

def test_token_meter_breaker_access():
    meter = TokenMeter()
    breaker = meter.get_breaker("agent1")
    assert breaker.state == BreakerState.CLOSED
