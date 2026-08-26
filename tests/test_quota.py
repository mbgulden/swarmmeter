import time
import pytest
from swarmmeter.quota import QuotaManager
from swarmmeter.types import QuotaPolicy, TokenUsage, QuotaExhausted

def test_quota_manager_within_limits():
    policy = QuotaPolicy(daily_budget_usd=10.0, per_agent_budget_usd=5.0)
    manager = QuotaManager(policy)
    
    usage = TokenUsage(
        agent_id="agent1",
        tokens_in=10,
        tokens_out=10,
        cost_usd=4.0,
        timestamp=time.time(),
        model="test",
        provider="test"
    )
    
    manager.record_usage(usage)
    assert manager.is_within_quota("agent1") is True
    assert manager.remaining_budget("agent1") == 1.0

def test_quota_manager_exhausts_agent_budget():
    policy = QuotaPolicy(per_agent_budget_usd=5.0)
    manager = QuotaManager(policy)
    
    usage = TokenUsage(
        agent_id="agent1",
        tokens_in=10,
        tokens_out=10,
        cost_usd=6.0,
        timestamp=time.time(),
        model="test",
        provider="test"
    )
    
    with pytest.raises(QuotaExhausted):
        manager.record_usage(usage)

def test_quota_manager_exhausts_daily_budget():
    policy = QuotaPolicy(daily_budget_usd=10.0)
    manager = QuotaManager(policy)
    
    usage1 = TokenUsage("agent1", 10, 10, 6.0, time.time(), "test", "test")
    usage2 = TokenUsage("agent2", 10, 10, 5.0, time.time(), "test", "test")
    
    manager.record_usage(usage1)
    with pytest.raises(QuotaExhausted):
        manager.record_usage(usage2)
